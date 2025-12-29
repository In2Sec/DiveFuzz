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
Instruction Validator (v4.0 - Simplified Architecture)

All-in-one instruction validation with:
- Instruction encoding (HybridEncoder)
- Instruction parsing (InstructionParser)
- XOR uniqueness checking (XORCache - fast Bloom filter)
- Bug filtering (bug_filter)
- Spike execution (SpikeSession)
- Debug logging (SpikeDebugLogger)

No external post_processor needed - all logic is integrated here.
"""

from typing import Optional, Tuple, List

try:
    from .hybrid_encoder import HybridEncoder
    from .instruction_parser import InstructionParser
    from .spike_session import SpikeSession
    from .xor_cache import XORCache, compute_xor
    from .spike_debug_logger import SpikeDebugLogger
    from ..bug_filter import bug_filter
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

# FPR offset for register indexing (0-31 = XPR, 32-63 = FPR)
FPR_OFFSET = 32


class InstructionValidator:
    """
    Simplified instruction validator (v4.0).

    Integrates all validation logic directly:
    - XOR computation and uniqueness check via XORCache
    - Bug filtering via bug_filter
    - No external post_processor dependency

    Usage:
        # Create XOR cache (in main process)
        xor_cache = XORCache()
        xor_cache.create()

        # Create validator
        validator = InstructionValidator(
            spike_session=session,
            xor_cache=xor_cache,
            architecture='xs'
        )

        # Validate instruction
        is_valid, actual_bytes = validator.validate_instruction("add x1, x2, x3")
    """

    # Class-level debug settings
    _debug_file = None
    _debug_enabled = False
    _debug_logger: Optional[SpikeDebugLogger] = None
    _debug_logger_enabled = False
    _instr_counter = 0

    def __init__(
        self,
        spike_session: SpikeSession,
        xor_cache: XORCache = None,
        architecture: str = "",
        encoder: Optional[HybridEncoder] = None
    ):
        """
        Initialize validator.

        Args:
            spike_session: Initialized SpikeSession instance
            xor_cache: XORCache for uniqueness checking (None = no checking)
            architecture: Architecture for bug filter ('xs', 'nts', 'rkt', 'kmh', 'cva6')
            encoder: HybridEncoder instance (creates default if None)
        """
        self.spike_session = spike_session
        self.xor_cache = xor_cache
        self.encoder = encoder or HybridEncoder(quiet=True)
        self.parser = InstructionParser()

        # Initialize bug filter
        if architecture:
            bug_filter.set_architecture(architecture)

    def _read_register(self, reg_idx: int) -> int:
        """Read register value by index (0-31: XPR, 32-63: FPR)."""
        if reg_idx < 32:
            return self.spike_session.get_xpr(reg_idx)
        return self.spike_session.get_fpr(reg_idx - FPR_OFFSET)

    def _check_xor_unique(self, opcode: str, source_values: List[int]) -> Tuple[int, bool]:
        """
        Compute XOR and check uniqueness.

        Returns:
            Tuple of (xor_value, is_unique)
        """
        xor_value = compute_xor(source_values)

        if self.xor_cache is None:
            return xor_value, True  # No cache = always unique

        is_unique = self.xor_cache.check_and_add(opcode, xor_value)
        return xor_value, is_unique

    def _check_bug(self, opcode: str, source_values: List[int]) -> Optional[str]:
        """Check if instruction triggers a known bug."""
        return bug_filter.filter_known_bug(opcode, source_values)

    def validate_instruction(self, instruction: str) -> Tuple[bool, int]:
        """
        Validate and execute instruction.

        Pipeline:
        1. Encode instruction to machine code
        2. Parse to extract registers
        3. Set checkpoint
        4. Read source values
        5. Check XOR uniqueness
        6. Check bug filter
        7. Execute if valid
        8. Log and confirm

        Args:
            instruction: Assembly instruction string

        Returns:
            Tuple of (is_valid, actual_bytes)
        """
        # 1. Encode instruction
        instruction_seq = self.encoder.encode_sequence(instruction)
        if not instruction_seq:
            return False, 0

        # 2. Parse instruction
        opcode, source_regs, dest_regs, immediate = self.parser.parse_instruction_full(instruction)
        actual_bytes = sum(size for _, size in instruction_seq)

        try:
            # 3. Set checkpoint
            if not self.spike_session.checkpoint_set:
                self.spike_session.set_checkpoint()

            # Capture pre-state for debug
            if self._debug_logger_enabled and self._debug_logger:
                self._debug_logger.capture_pre_state(self.spike_session)

            # 4. Read source values
            source_values = [self._read_register(r) for r in source_regs]
            if immediate is not None:
                source_values.append(immediate)

            # 5. Check XOR uniqueness
            xor_value, is_unique = self._check_xor_unique(opcode, source_values)
            if not is_unique:
                self.spike_session.restore_checkpoint_and_reset()
                return False, 0

            # 6. Check bug filter
            bug_name = self._check_bug(opcode, source_values)
            if bug_name:
                self.spike_session.restore_checkpoint_and_reset()
                return False, 0

            # 7. Execute instruction
            machine_codes = [mc for mc, _ in instruction_seq]
            sizes = [sz for _, sz in instruction_seq]
            self.spike_session.execute_sequence(machine_codes, sizes)

            # 8. Log (after execution to see changes)
            self._log_instruction(
                instruction, instruction_seq, opcode,
                source_regs, source_values, dest_regs,
                xor_value, immediate
            )

            # 9. Confirm
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
        immediate: Optional[int]
    ):
        """Log accepted instruction."""
        # Get trap information
        was_trapped = self.spike_session.was_last_execution_trapped()
        trap_handler_steps = self.spike_session.get_last_trap_handler_steps()

        # Detailed debug logger
        if self._debug_logger_enabled and self._debug_logger:
            # Read destination register values after execution
            dest_values = [self._read_register(r) for r in dest_regs] if dest_regs else []

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
                trap_handler_steps=trap_handler_steps
            )

        # Legacy debug file
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
                f.write(f"  Imm: {immediate} (0x{immediate & 0xffffffffffffffff:x})\n")
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

    # === Class methods for debug control ===

    @classmethod
    def enable_detailed_debug(
        cls,
        filepath: str,
        mode: str = "FULL",
        log_csr: bool = True,
        log_fpr: bool = True,
        accepted_only: bool = True
    ):
        """Enable detailed debug logging."""
        cls._debug_logger = SpikeDebugLogger(
            filepath=filepath,
            mode=mode,
            log_csr=log_csr,
            log_fpr=log_fpr,
            accepted_only=accepted_only
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
        cls._debug_file = open(filepath, 'w')
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


if __name__ == "__main__":
    print("InstructionValidator v4.0 - Simplified Architecture")
    print("No external post_processor needed")
