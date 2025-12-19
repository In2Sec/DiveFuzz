"""
Instruction Validator

Integrates encoder + parser + spike_session for high-level instruction validation.
Provides a simple API: validate_instruction(instruction_str) -> Optional[xor_value]
"""

from typing import Optional, Tuple, List

try:
    from .hybrid_encoder import HybridEncoder
    from .instruction_parser import InstructionParser
    from .spike_session import SpikeSession
except ImportError:
    # For standalone testing
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    from hybrid_encoder import HybridEncoder
    from instruction_parser import InstructionParser
    from spike_session import SpikeSession


class InstructionValidator:
    """
    High-level instruction validator

    Combines:
    - HybridEncoder: Assembly -> machine code
    - InstructionParser: Extract operands and source registers
    - RegisterMapping: Register names -> indices
    - SpikeSession: Execute and validate uniqueness

    Usage:
        validator = InstructionValidator(spike_session, encoder)
        xor_value = validator.validate_instruction("add x1, x2, x3")
        if xor_value is not None:
            # Unique, accept instruction
            spike_session.confirm_instruction(xor_value, "add x1, x2, x3")
        else:
            # Duplicate, retry with different instruction
    """

    def __init__(
        self,
        spike_session: SpikeSession,
        encoder: Optional[HybridEncoder] = None
    ):
        """
        Initialize validator

        Args:
            spike_session: Initialized SpikeSession instance
            encoder: HybridEncoder instance (optional, creates default if None)
        """
        self.spike_session = spike_session

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

    def validate_instruction(self, instruction: str) -> Tuple[Optional[int], List[int], List[int]]:
        """
        Validate instruction and return XOR, dest values, and source values if unique

        This is the main entry point for instruction validation.
        Complete pipeline:
        1. Parse and encode instruction
        2. Extract source/dest registers and immediate
        3. Execute in Spike (gets source values before, dest values after execution)
        4. Compute XOR and check uniqueness
        5. Return (XOR, dest_values, source_values) for bug filtering

        Args:
            instruction: Assembly instruction string

        Returns:
            Tuple of (xor_value, dest_values, source_values):
            - xor_value: XOR if unique within opcode group, None if duplicate
            - dest_values: Destination register values after execution
            - source_values: Source register values before execution

        Note:
            If xor_value is not None, caller must:
            1. Check bug_filter.filter_known_bug(opcode, dest_values, source_values)
            2. If no bug, call spike_session.confirm_instruction(xor_value, instruction, opcode)

        Example:
            >>> xor_value, dest_vals, src_vals = validator.validate_instruction("sc.w s9, a7, (t6)")
            >>> if xor_value is not None:
            ...     bug_name = bug_filter.filter_known_bug("sc.w", dest_vals, src_vals)
            ...     if not bug_name:
            ...         spike_session.confirm_instruction(xor_value, instruction, "sc.w")
        """
        # Extract all instruction information
        machine_code, opcode, source_regs, dest_regs, immediate = self.extract_instruction_info(instruction)

        if machine_code is None:
            return None, [], []

        # Convert None to IMMEDIATE_NOT_PRESENT for spike_engine
        from .spike_session import IMMEDIATE_NOT_PRESENT
        immediate_value = IMMEDIATE_NOT_PRESENT if immediate is None else immediate

        # Execute in Spike and get XOR, dest values, and source values
        xor_value, dest_values, source_values = self.spike_session.try_instruction(
            machine_code,
            source_regs,
            dest_regs,
            immediate_value,
            opcode=opcode
        )

        return xor_value, dest_values, source_values


if __name__ == "__main__":
    print("InstructionValidator module")
    print("Requires SpikeSession and HybridEncoder")
