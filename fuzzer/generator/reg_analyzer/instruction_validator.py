# Copyright (c) 2024-2025 Institute of Information Engineering, Chinese Academy of Sciences
#
# DiveFuzz is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#          http://license.coscl.org.cn/MulanPSL2
#
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
#
# See the Mulan PSL v2 for more details.

"""
Instruction Validator (v5.0 - Precision Filter Integration)

All-in-one instruction validation with:
- Instruction encoding (HybridEncoder)
- Instruction parsing (InstructionParser)
- XOR uniqueness checking (XORCache - fast Bloom filter)
- Legacy bug filtering (bug_filter) - backward compatible
- Precision filtering (FilterRegistry) - two-phase runtime state inspection
- Spike execution (SpikeSession)
- Debug logging (SpikeDebugLogger)

Two-Phase Filtering:
    Pre-execution (Level 1): φ(s_pre, opcode, operand)
        - Checked before instruction execution
        - Uses source register values, opcode, operands
        - No checkpoint needed for rejection

    Post-execution (Level 2 & 3): φ(s_pre, s_post) or φ(s_pre, opcode, operand, s_post)
        - Checked after instruction execution
        - Uses state transitions, side effects, trap info
        - Checkpoint rollback on rejection

Usage:
    # Legacy mode (backward compatible)
    validator = InstructionValidator(
        spike_session=session,
        xor_cache=xor_cache,
        architecture='xs'
    )

    # Precision mode (recommended)
    from bug_filter import FilterRegistry, register_architecture_filters

    registry = FilterRegistry()
    registry.set_architecture('xs')
    register_architecture_filters('xs', registry)

    validator = InstructionValidator(
        spike_session=session,
        xor_cache=xor_cache,
        architecture='xs',
        precision_registry=registry
    )

    is_valid, actual_bytes = validator.validate_instruction("add x1, x2, x3")
"""

from typing import Optional, Tuple, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..bug_filter.registry import FilterRegistry
    from ..bug_filter.context import FilterContext

try:
    from .hybrid_encoder import HybridEncoder
    from .instruction_parser import InstructionParser
    from .spike_session import SpikeSession
    from .xor_cache import XORCache, compute_xor
    from .spike_debug_logger import SpikeDebugLogger
    from ..bug_filter import bug_filter
    from ..bug_filter.context import (
        FilterContext,
        PreExecutionState,
        PostExecutionState,
    )
    from ..bug_filter.registry import FilterRegistry
except ImportError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).parent))
    sys.path.append(str(Path(__file__).parent.parent))
    from hybrid_encoder import HybridEncoder
    from instruction_parser import InstructionParser
    from spike_session import SpikeSession
    from xor_cache import XORCache, compute_xor
    from spike_debug_logger import SpikeDebugLogger
    from bug_filter import bug_filter
    from bug_filter.context import FilterContext, PreExecutionState, PostExecutionState
    from bug_filter.registry import FilterRegistry

FPR_OFFSET = 32


class InstructionValidator:
    """
    Instruction validator with precision filtering (v5.0).

    Integrates:
    - XOR computation and uniqueness check via XORCache
    - Legacy bug filtering via bug_filter (backward compatible)
    - Precision filtering via FilterRegistry (two-phase)
    - Spike execution with checkpoint protection

    Usage:
        validator = InstructionValidator(
            spike_session=session,
            xor_cache=xor_cache,
            architecture='xs',
            precision_registry=registry
        )

        is_valid, actual_bytes = validator.validate_instruction("add x1, x2, x3")
    """

    _debug_file = None
    _debug_enabled = False
    _debug_logger: Optional[SpikeDebugLogger] = None
    _debug_logger_enabled = False
    _instr_counter = 0

    def __init__(
        self,
        spike_session: SpikeSession,
        xor_cache: Optional[XORCache] = None,
        architecture: str = "",
        encoder: Optional[HybridEncoder] = None,
        precision_registry: Optional["FilterRegistry"] = None,
    ):
        """
        Initialize validator.

        Args:
            spike_session: Initialized SpikeSession instance
            xor_cache: XORCache for uniqueness checking (None = no checking)
            architecture: Architecture for bug filter ('xs', 'nts', 'cva6', 'boom', 'rocket')
            encoder: HybridEncoder instance (creates default if None)
            precision_registry: FilterRegistry for precision filtering (None = legacy mode)
        """
        self.spike_session = spike_session
        self.xor_cache = xor_cache
        self.encoder = encoder or HybridEncoder(quiet=True)
        self.parser = InstructionParser()
        self.architecture = architecture
        self.precision_registry = precision_registry

        # Initialize legacy bug filter (backward compatible)
        if architecture:
            bug_filter.set_architecture(architecture)

    def _read_register(self, reg_idx: int) -> int:
        """Read register value by index (0-31: XPR, 32-63: FPR)."""
        if reg_idx < 32:
            return self.spike_session.get_xpr(reg_idx)
        return self.spike_session.get_fpr(reg_idx - FPR_OFFSET)

    def _check_xor_unique(
        self, opcode: str, source_values: List[int]
    ) -> Tuple[int, bool]:
        """
        Compute XOR and check uniqueness.

        Returns:
            Tuple of (xor_value, is_unique)
        """
        xor_value = compute_xor(source_values)

        if self.xor_cache is None:
            return xor_value, True

        is_unique = self.xor_cache.check_and_add(opcode, xor_value)
        return xor_value, is_unique

    def _check_bug_legacy(self, opcode: str, source_values: List[int]) -> Optional[str]:
        """Check if instruction triggers a known bug (legacy filter)."""
        return bug_filter.filter_known_bug(opcode, source_values)

    def _build_pre_execution_state(self) -> PreExecutionState:
        """Build pre-execution state snapshot from SpikeSession."""
        state = PreExecutionState()

        state.xpr = list(self.spike_session.get_all_xpr())
        state.fpr = list(self.spike_session.get_all_fpr())
        state.pc = self.spike_session.get_current_pc()

        priv_state = self.spike_session.get_privilege_state()
        state.privilege = priv_state.prv
        state.virtualization = priv_state.v

        res_state = self.spike_session.get_reservation_state()
        state.reservation_valid = res_state.valid
        state.reservation_addr = res_state.address

        return state

    def _build_post_execution_state(self) -> PostExecutionState:
        """Build post-execution state snapshot from SpikeSession."""
        state = PostExecutionState()

        state.xpr = list(self.spike_session.get_all_xpr())
        state.fpr = list(self.spike_session.get_all_fpr())
        state.pc = self.spike_session.get_current_pc()

        priv_state = self.spike_session.get_privilege_state()
        state.privilege = priv_state.prv
        state.virtualization = priv_state.v
        state.privilege_changed = priv_state.prv_changed
        state.virtualization_changed = priv_state.v_changed

        trap_info = self.spike_session.get_last_trap_info()
        state.trap_occurred = trap_info.occurred
        state.trap_cause = trap_info.cause
        state.trap_tval = trap_info.tval
        state.trap_name = trap_info.name if trap_info.name else ""

        commit_log = self.spike_session.get_commit_log()
        state.reg_writes = [(rw.reg_num, rw.value) for rw in commit_log.reg_writes]
        state.mem_reads = [(ma.addr, ma.value, ma.size) for ma in commit_log.mem_reads]
        state.mem_writes = [
            (ma.addr, ma.value, ma.size) for ma in commit_log.mem_writes
        ]

        res_state = self.spike_session.get_reservation_state()
        state.reservation_valid = res_state.valid
        state.reservation_addr = res_state.address

        return state

    def _build_filter_context(
        self,
        instruction: str,
        opcode: str,
        operands: List[str],
        s_pre: PreExecutionState,
        s_post: Optional[PostExecutionState] = None,
    ) -> FilterContext:
        """Build FilterContext for precision filters."""
        return FilterContext(
            spike_session=self.spike_session,
            opcode=opcode,
            operands=operands,
            machine_code=0,
            instruction_size=4,
            assembly=instruction,
            s_pre=s_pre,
            s_post=s_post,
            architecture=self.architecture,
        )

    def validate_instruction(self, instruction: str) -> Tuple[bool, int]:
        """
        Validate and execute instruction.

        Pipeline:
        1. Encode instruction to machine code
        2. Parse to extract registers
        3. Read source values
        4. Check XOR uniqueness
        5. Check legacy bug filter
        6. Check pre-execution precision filters
        7. Set checkpoint
        8. Execute instruction
        9. Check post-execution precision filters
        10. Log and confirm

        Args:
            instruction: Assembly instruction string

        Returns:
            Tuple of (is_valid, actual_bytes)
        """
        instruction_seq = self.encoder.encode_sequence(instruction)
        if not instruction_seq:
            return False, 0

        opcode, source_regs, dest_regs, immediate = self.parser.parse_instruction_full(
            instruction
        )
        actual_bytes = sum(size for _, size in instruction_seq)

        source_values = [self._read_register(r) for r in source_regs]
        if immediate is not None:
            source_values.append(immediate)

        xor_value, is_unique = self._check_xor_unique(opcode, source_values)
        if not is_unique:
            return False, 0

        bug_name = self._check_bug_legacy(opcode, source_values)
        if bug_name:
            return False, 0

        s_pre = None
        if self.precision_registry:
            s_pre = self._build_pre_execution_state()
            operands = (
                [op.strip().rstrip(",") for op in instruction.split()[1:]]
                if len(instruction.split()) > 1
                else []
            )
            ctx = self._build_filter_context(instruction, opcode, operands, s_pre)

            pre_reason = self.precision_registry.check_pre_execution(ctx)
            if pre_reason:
                return False, 0

        try:
            if not self.spike_session.checkpoint_set:
                self.spike_session.set_checkpoint()

            if self._debug_logger_enabled and self._debug_logger:
                self._debug_logger.capture_pre_state(self.spike_session)

            machine_codes = [mc for mc, _ in instruction_seq]
            sizes = [sz for _, sz in instruction_seq]
            self.spike_session.execute_sequence(machine_codes, sizes)

            if self.precision_registry and s_pre:
                s_post = self._build_post_execution_state()
                operands = (
                    [op.strip().rstrip(",") for op in instruction.split()[1:]]
                    if len(instruction.split()) > 1
                    else []
                )
                ctx = self._build_filter_context(
                    instruction, opcode, operands, s_pre, s_post
                )

                post_reason = self.precision_registry.check_post_execution(ctx)
                if post_reason:
                    self.spike_session.restore_checkpoint_and_reset()
                    return False, 0

            self._log_instruction(
                instruction,
                instruction_seq,
                opcode,
                source_regs,
                source_values,
                dest_regs,
                xor_value,
                immediate,
            )

            self.spike_session.confirm_instruction()
            return True, actual_bytes

        except Exception as e:
            self._log_exception(instruction, e)
            try:
                self.spike_session.restore_checkpoint_and_reset()
            except:
                pass
            return False, 0

    def _log_instruction(
        self,
        instruction: str,
        instruction_seq: List[Tuple[int, int]],
        opcode: str,
        source_regs: List[int],
        source_values: List[int],
        dest_regs: List[int],
        xor_value: int,
        immediate: Optional[int],
    ):
        """Log accepted instruction."""
        was_trapped = self.spike_session.was_last_execution_trapped()
        trap_handler_steps = self.spike_session.get_last_trap_handler_steps()

        if self._debug_logger_enabled and self._debug_logger:
            dest_values = (
                [self._read_register(r) for r in dest_regs] if dest_regs else []
            )

            self._debug_logger.log_instruction(
                spike_session=self.spike_session,
                instruction=instruction,
                machine_codes=instruction_seq,
                is_accepted=True,
                source_regs=source_regs,
                source_values=source_values,
                dest_regs=dest_regs,
                dest_values=dest_values,
                xor_value=xor_value,
                reject_reason=None,
                was_trapped=was_trapped,
                trap_handler_steps=trap_handler_steps,
            )

        if self._debug_enabled and self._debug_file:
            pc = self.spike_session.get_current_pc()
            f = self._debug_file
            trap_info = f" [TRAPPED: {trap_handler_steps} steps]" if was_trapped else ""
            f.write(f"[ACCEPTED]{trap_info} {instruction}\n")
            if len(instruction_seq) > 1:
                f.write(f"  Expanded: {len(instruction_seq)} instrs\n")
                for i, (mc, sz) in enumerate(instruction_seq):
                    f.write(f"    [{i}] 0x{mc:08x} (size={sz})\n")
            else:
                mc, _ = instruction_seq[0]
                f.write(f"  Code: 0x{mc:08x}, PC: 0x{pc:x}\n")
            f.write(f"  Src: {source_regs} -> {[hex(v) for v in source_values]}\n")
            if immediate is not None:
                f.write(f"  Imm: {immediate} (0x{immediate & 0xFFFFFFFFFFFFFFFF:x})\n")
            f.write("\n")
            f.flush()
            InstructionValidator._instr_counter += 1

    def _log_exception(self, instruction: str, e: Exception):
        """Log exception."""
        if self._debug_logger_enabled and self._debug_logger:
            self._debug_logger.log_exception(instruction, e)
        if self._debug_enabled and self._debug_file:
            self._debug_file.write(f"[EXCEPTION] {instruction}\n  Error: {e}\n\n")
            self._debug_file.flush()

    @classmethod
    def enable_detailed_debug(
        cls,
        filepath: str,
        mode: str = "FULL",
        log_csr: bool = True,
        log_fpr: bool = True,
        accepted_only: bool = True,
    ):
        """Enable detailed debug logging."""
        cls._debug_logger = SpikeDebugLogger(
            filepath=filepath,
            mode=mode,
            log_csr=log_csr,
            log_fpr=log_fpr,
            accepted_only=accepted_only,
        )
        cls._debug_logger_enabled = True

    @classmethod
    def disable_detailed_debug(cls):
        """Disable detailed debug logging."""
        if cls._debug_logger:
            cls._debug_logger.close()
            cls._debug_logger = None
        cls._debug_logger_enabled = False

    @classmethod
    def enable_debug_output(cls, filepath: str, accepted_only: bool = False):
        """Enable legacy debug output."""
        cls._debug_file = open(filepath, "w")
        cls._debug_enabled = True
        cls._instr_counter = 0
        cls._debug_file.write("# SPIKE DEBUG OUTPUT\n")
        cls._debug_file.write("#" + "=" * 60 + "\n\n")

    @classmethod
    def disable_debug_output(cls):
        """Disable legacy debug output."""
        if cls._debug_file:
            cls._debug_file.close()
            cls._debug_file = None
        cls._debug_enabled = False

