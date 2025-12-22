"""
Instruction Validator

Integrates encoder + parser + spike_session + post_processor for high-level instruction validation.
Provides a simple API for instruction validation with XOR uniqueness and bug filtering.

Architecture:
- HybridEncoder: Assembly -> machine code
- InstructionParser: Extract operands and registers
- SpikeSession: Execute instruction and manage checkpoints
- InstructionPostProcessor: XOR computation, uniqueness check, bug filtering
"""

from typing import Optional, Tuple, List

try:
    from .hybrid_encoder import HybridEncoder
    from .instruction_parser import InstructionParser
    from .spike_session import SpikeSession, IMMEDIATE_NOT_PRESENT
    from .instruction_post_processor import InstructionPostProcessor
except ImportError:
    # For standalone testing
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    from hybrid_encoder import HybridEncoder
    from instruction_parser import InstructionParser
    from spike_session import SpikeSession, IMMEDIATE_NOT_PRESENT
    from instruction_post_processor import InstructionPostProcessor


class InstructionValidator:
    """
    High-level instruction validator

    Combines:
    - HybridEncoder: Assembly -> machine code
    - InstructionParser: Extract operands and source registers
    - SpikeSession: Execute instruction
    - InstructionPostProcessor: XOR computation, uniqueness check, bug filtering

    Usage:
        post_processor = InstructionPostProcessor(shared_xor_cache, architecture)
        validator = InstructionValidator(spike_session, post_processor, encoder)

        # validate_instruction auto-confirms/rejects based on result
        if validator.validate_instruction("add x1, x2, x3"):
            # Instruction accepted
            pass
        else:
            # Duplicate XOR or triggers bug, retry with different instruction
            pass
    """

    def __init__(
        self,
        spike_session: SpikeSession,
        post_processor: InstructionPostProcessor,
        encoder: Optional[HybridEncoder] = None
    ):
        """
        Initialize validator

        Args:
            spike_session: Initialized SpikeSession instance
            post_processor: InstructionPostProcessor for XOR and bug filtering
            encoder: HybridEncoder instance (optional, creates default if None)
        """
        self.spike_session = spike_session
        self.post_processor = post_processor

        if encoder is None:
            self.encoder = HybridEncoder(quiet=True)
        else:
            self.encoder = encoder

        self.parser = InstructionParser()

    def extract_instruction_info(
        self,
        instruction: str
    ) -> Tuple[Optional[int], str, List[int], List[int], Optional[int]]:
        """
        Extract all instruction information needed for execution and bug filtering

        Args:
            instruction: Assembly instruction string

        Returns:
            Tuple of (machine_code, opcode, source_regs, dest_regs, immediate)
            Returns (None, "", [], [], None) on error
            immediate is None for instructions without immediate operand

        Example:
            >>> machine_code, opcode, src, dst, imm = validator.extract_instruction_info("sc.w s9, a7, (t6)")
            >>> # machine_code = 0x...
            >>> # opcode = "sc.w"
            >>> # src = [17, 31]  # a7, t6
            >>> # dst = [25]      # s9
            >>> # imm = None
        """
        try:
            # 1. Encode to machine code
            machine_code = self.encoder.encode(instruction)
            if machine_code is None:
                return None, "", [], [], None

            # 2. Parse instruction using simplified parser
            opcode, source_regs, dest_regs, immediate = self.parser.parse_instruction_full(instruction)

            return machine_code, opcode, source_regs, dest_regs, immediate

        except Exception as e:
            print(f"[Validator] Exception in extract_instruction_info: {e}")
            print(f"  Instruction: {instruction}")
            import traceback
            traceback.print_exc()
            return None, "", [], [], None

    # Debug output file handle (class-level, shared across instances)
    _debug_file = None
    _debug_enabled = False
    _accepted_only = False  # If True, only log ACCEPTED instructions
    _instr_counter = 0

    @classmethod
    def enable_debug_output(cls, filepath: str, accepted_only: bool = False):
        """
        Enable debug output to file

        Args:
            filepath: Path to the debug output file
            accepted_only: If True, only log ACCEPTED instructions (default: False)
        """
        cls._debug_file = open(filepath, 'w')
        cls._debug_enabled = True
        cls._accepted_only = accepted_only
        cls._instr_counter = 0

        mode_str = "ACCEPTED only" if accepted_only else "ALL (ACCEPTED/REJECTED)"
        cls._debug_file.write("# SPIKE_ENGINE DEBUG OUTPUT\n")
        cls._debug_file.write(f"# Mode: {mode_str}\n")
        cls._debug_file.write("# Format: [ACCEPTED/REJECTED] instruction\n")
        cls._debug_file.write("#   Machine code: 0xXXXX, PC after: 0xXXXX\n")
        cls._debug_file.write("#   Source regs: [indices] -> [hex values]\n")
        cls._debug_file.write("#   Dest regs: [indices] -> [hex values]\n")
        cls._debug_file.write("#" + "=" * 79 + "\n\n")

    @classmethod
    def disable_debug_output(cls):
        """Disable debug output"""
        if cls._debug_file:
            cls._debug_file.close()
            cls._debug_file = None
        cls._debug_enabled = False

    def validate_instruction(self, instruction: str) -> bool:
        """
        Validate instruction with XOR uniqueness and bug filtering.

        Complete pipeline:
        1. Parse and encode instruction
        2. Execute in Spike
        3. Compute XOR and check uniqueness
        4. Check for known bugs
        5. Auto-confirm if valid, auto-reject if invalid

        Args:
            instruction: Assembly instruction string

        Returns:
            True if instruction is valid (unique XOR, no bugs), False otherwise.
            On True: state is confirmed, ready for next instruction.
            On False: checkpoint restored, caller should retry with different instruction.
        """
        # Extract all instruction information
        machine_code, opcode, source_regs, dest_regs, immediate = self.extract_instruction_info(instruction)

        if machine_code is None:
            return False

        # Convert None to IMMEDIATE_NOT_PRESENT for spike_engine
        immediate_value = IMMEDIATE_NOT_PRESENT if immediate is None else immediate

        try:
            # Execute in Spike and get register values
            source_values, dest_values = self.spike_session.execute_instruction(
                machine_code,
                source_regs,
                dest_regs,
                immediate_value
            )

            # Process result: compute XOR, check uniqueness, check bugs
            xor_value, is_unique, bug_name = self.post_processor.process_result(
                opcode,
                source_values,
                dest_values
            )

            # Check validity
            is_valid = is_unique and (bug_name is None)

            # Debug output
            if InstructionValidator._debug_enabled and InstructionValidator._debug_file:
                # Skip REJECTED instructions if accepted_only mode is enabled
                should_log = is_valid or not InstructionValidator._accepted_only

                if should_log:
                    pc_after = self.spike_session.get_current_pc()
                    status = "[ACCEPTED]" if is_valid else "[REJECTED]"
                    f = InstructionValidator._debug_file
                    f.write(f"{status} {instruction}\n")
                    f.write(f"  Machine code: 0x{machine_code:08x}, PC after: 0x{pc_after:x}\n")
                    f.write(f"  Source regs: {source_regs} -> {[hex(v) for v in source_values]}\n")
                    f.write(f"  Dest regs: {dest_regs} -> {[hex(v) for v in dest_values]}\n")
                    if immediate is not None:
                        f.write(f"  Immediate: {immediate} (0x{immediate & 0xffffffffffffffff:x})\n")
                    f.write("\n")
                    f.flush()
                    InstructionValidator._instr_counter += 1

            if is_valid:
                # Confirm XOR and advance checkpoint
                self.post_processor.confirm_xor(opcode, xor_value)
                self.spike_session.confirm_instruction()
            else:
                # Restore checkpoint for retry
                self.spike_session.restore_checkpoint_and_reset()

            return is_valid

        except Exception as e:
            # Debug output for exceptions
            if InstructionValidator._debug_enabled and InstructionValidator._debug_file:
                f = InstructionValidator._debug_file
                f.write(f"[EXCEPTION] {instruction}\n")
                f.write(f"  Error: {e}\n\n")
                f.flush()

            # Restore checkpoint on error
            try:
                self.spike_session.restore_checkpoint_and_reset()
            except:
                pass
            return False


if __name__ == "__main__":
    print("InstructionValidator module")
    print("Requires SpikeSession, InstructionPostProcessor, and HybridEncoder")
