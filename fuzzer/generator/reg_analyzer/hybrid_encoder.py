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
The hybrid RISC-V instruction encoder combines a fast encoder and compiler rollback mechanism to support all RISC-V instructions.

Supports pseudo-instructions that expand to multiple machine instructions:
- li with large immediate -> lui + addi + slli + ... sequence
- la (load address) -> auipc + addi
- call/tail -> auipc + jalr
- etc.
"""

import re
from typing import List, Tuple, Union, Optional
from dataclasses import dataclass

try:
    from .instruction_encoder import InstructionEncoder
    from .riscv_compiler import RiscvCompiler
except ImportError:
    from instruction_encoder import InstructionEncoder
    from riscv_compiler import RiscvCompiler


@dataclass
class CompiledSequence:
    """Compiled instruction sequence with metadata"""
    codes: List[int]          # Machine codes
    sizes: List[int]          # Instruction sizes (2 or 4 bytes)
    asm_list: List[str]       # Assembly strings
    total_size: int           # Total size in bytes


class HybridEncoder:
    """
    Hybrid encoder: Prioritize the use of fast encoders and roll back to the compiler in case of failure

    Features
    - First attempt to use InstructionEncoder (supporting 97 extensions)
    - Automatically roll back to RISC-V Compiler in case of failure (supporting all instructions)
    """

    def __init__(
        self,
        march: str = "rv64imafdcv_zicsr_zifencei_zba_zbb_zbc_zbs_zfh",
        quiet: bool = False
    ):
        """
        Initialize the hybrid encoder

        Args:
            march: The schema string used by the compiler
            quiet: Silent mode, no information is printed
        """
        self.encoder = InstructionEncoder()
        self.compiler = RiscvCompiler(default_march=march)
        self.quiet = quiet

        self.stats = {
            'encoder_success': 0,
            'fallback_used': 0,
            'total_calls': 0 
        }

    def encode(self, instruction: str) -> int:
        """
        The encoding process for a single instruction is machine code:
        
        1. Try the encoder -> If successful, return directly
        2. Use compiler Rollback -> Return

        Args:
            instruction: RISC-V assembly instruction

        Returns:
            32 Bit machine code

        Raises:
            RuntimeError: If both the encoder and the compiler fail
        """
        self.stats['total_calls'] += 1

        # Step 1: Try the encoder
        encoder_error = None
        try:
            result = self.encoder.encode(instruction)
            self.stats['encoder_success'] += 1
            return result
        except ValueError as e:
            # The encoder failed. Proceed to the fallback mechanism
            encoder_error = e

        # Step 2: Compiler rollback
        try:
            self.stats['fallback_used'] += 1
            result = self.compiler.compile_instruction(instruction)
            return result
        except RuntimeError as compiler_error:
            # Both the encoder and the compiler failed, throwing a detailed error
            raise RuntimeError(
                f"Failed to encode instruction: '{instruction}'\n"
                f"Encoder error: {encoder_error}\n"
                f"Compiler error: {compiler_error}"
            )

    def encode_multiple(self, instructions: list[str]) -> list[int]:
        """
        Batch encode multiple instructions

        Args:
            instructions: Instruction list

        Returns:
            Machine code list
        """
        return [self.encode(inst) for inst in instructions]

    def encode_sequence(self, instruction: str) -> List[Tuple[int, int]]:
        """
        Encode an instruction and return ALL expanded machine codes.

        For pseudo-instructions like `li x1, 0x123456789`, the assembler may expand
        them into multiple real instructions. This method returns ALL instructions.

        Encoding strategy:
        1. Try fast encoder first - if succeeds, return single instruction
        2. Fall back to compiler with sequence mode - returns all expanded instructions

        Args:
            instruction: RISC-V assembly instruction

        Returns:
            List of (machine_code, size) tuples where:
            - machine_code: 32-bit integer (2-byte compressed instructions zero-padded)
            - size: Actual instruction size in bytes (2 or 4)

        Example:
            >>> encoder.encode_sequence("add x1, x2, x3")
            [(0x003100b3, 4)]  # Single instruction
            >>> encoder.encode_sequence("li x1, 0x123456789")
            [(0x00000537, 4), (0x00050513, 4), ...]  # Multiple instructions

        Raises:
            RuntimeError: If both encoder and compiler fail
        """
        self.stats['total_calls'] += 1

        # Step 1: Try fast encoder (only works for single real instructions)
        encoder_error = None
        try:
            result = self.encoder.encode(instruction)
            self.stats['encoder_success'] += 1
            # Fast encoder succeeded - return single instruction with size 4
            # (fast encoder doesn't support compressed instructions currently)
            return [(result, 4)]
        except ValueError as e:
            encoder_error = e

        # Step 2: Compiler fallback with sequence mode
        try:
            self.stats['fallback_used'] += 1
            result = self.compiler.compile_instruction_sequence(instruction)
            return result
        except RuntimeError as compiler_error:
            raise RuntimeError(
                f"Failed to encode instruction sequence: '{instruction}'\n"
                f"Encoder error: {encoder_error}\n"
                f"Compiler error: {compiler_error}"
            )

    def is_pseudo_instruction(self, instruction: str) -> bool:
        """
        Check if an instruction might be a pseudo-instruction that expands to multiple.

        This is a heuristic check - not guaranteed to be accurate.
        Use encode_sequence() for authoritative expansion.

        Args:
            instruction: Assembly instruction string

        Returns:
            True if instruction is likely a pseudo-instruction
        """
        parts = instruction.strip().split()
        if not parts:
            return False

        opcode = parts[0].lower()

        # Known pseudo-instructions that may expand
        pseudo_opcodes = {
            'li',      # Load immediate (may expand for large values)
            'la',      # Load address (typically auipc + addi)
            'call',    # Call function (auipc + jalr)
            'tail',    # Tail call (auipc + jalr)
            'mv',      # Move (addi rd, rs, 0)
            'not',     # NOT (xori rd, rs, -1)
            'neg',     # Negate (sub rd, zero, rs)
            'negw',    # Negate word (subw rd, zero, rs)
            'sext.w',  # Sign-extend word (addiw rd, rs, 0)
            'seqz',    # Set if equal zero (sltiu rd, rs, 1)
            'snez',    # Set if not zero (sltu rd, zero, rs)
            'sltz',    # Set if less than zero (slt rd, rs, zero)
            'sgtz',    # Set if greater than zero (slt rd, zero, rs)
            'beqz',    # Branch if equal zero
            'bnez',    # Branch if not zero
            'blez',    # Branch if less or equal zero
            'bgez',    # Branch if greater or equal zero
            'bltz',    # Branch if less than zero
            'bgtz',    # Branch if greater than zero
            'bgt',     # Branch if greater than
            'ble',     # Branch if less or equal
            'bgtu',    # Branch if greater than unsigned
            'bleu',    # Branch if less or equal unsigned
            'j',       # Jump (jal zero, offset)
            'jr',      # Jump register (jalr zero, rs, 0)
            'ret',     # Return (jalr zero, ra, 0)
            'nop',     # No operation (addi zero, zero, 0)
        }

        return opcode in pseudo_opcodes

    def encode_to_hex(self, instruction: str) -> str:
        """
        Encode the instruction and return a hexadecimal string

        Args:
            instruction: RISC-V assembly instruction

        Returns:
            Hexadecimal machine code string (such as "0x003100b3")
        """
        machine_code = self.encode(instruction)
        return f"0x{machine_code:08x}"

    def encode_to_bytes(self, instruction: str) -> bytes:
        """
        Encode the instruction and return the byte sequence (little-endian order)

        Args:
            instruction: RISC-V assembly instruction

        Returns:
            4-byte machine code
        """
        machine_code = self.encode(instruction)
        return machine_code.to_bytes(4, byteorder='little')

    def get_stats(self) -> dict:
        """
        Obtain performance statistics

        Returns:
            Statistical dictionary, including:
            - encoder_success: Number of successful encoders
            - fallback_used: The number of compiler fallbacks
            - total_calls: Total number of calls
            - encoder_hit_rate: Encoder hit rate
            - fallback_rate: Compiler rollback rate
        """
        total = self.stats['total_calls']
        if total == 0:
            return {
                **self.stats,
                'encoder_hit_rate': 0.0,
                'fallback_rate': 0.0
            }

        return {
            **self.stats,
            'encoder_hit_rate': self.stats['encoder_success'] / total,
            'fallback_rate': self.stats['fallback_used'] / total
        }

    def print_stats(self):
        """ Print Performance Statistics """
        stats = self.get_stats()
        total = stats['total_calls']

        print("\n" + "="*60)
        print("HybridEncoder Performance Statistics")
        print("="*60)
        print(f"Total calls:           {total}")
        print(f"Encoder success:       {stats['encoder_success']:6d} ({stats['encoder_hit_rate']*100:5.1f}%)")
        print(f"Fallback used:         {stats['fallback_used']:6d} ({stats['fallback_rate']*100:5.1f}%)")
        print("="*60 + "\n")

    # ========================================================================
    # Jump Sequence Compilation Methods
    # ========================================================================

    def get_instruction_size(self, machine_code: int) -> int:
        """
        Get instruction size from machine code

        RISC-V encoding rules:
        - bits[1:0] != 0b11 -> 16-bit compressed instruction
        - bits[1:0] == 0b11 -> 32-bit standard instruction
        """
        if (machine_code & 0x3) != 0x3:
            return 2  # Compressed
        return 4  # Standard

    def _encode_with_size(self, instruction: str) -> Tuple[int, int]:
        """
        Encode instruction and return (machine_code, size)

        Handles pseudo-instructions that expand to multiple instructions
        by returning only the first instruction (for size calculation).
        """
        code = self.encode(instruction)
        size = self.get_instruction_size(code)
        return code, size

    def _encode_sequence_flat(self, instructions: List[str]) -> Tuple[List[int], List[int], int]:
        """
        Encode a list of instructions, handling pseudo-instruction expansion

        Returns:
            (codes, sizes, total_size)
        """
        codes = []
        sizes = []
        total_size = 0

        for inst in instructions:
            # Use encode_sequence to handle pseudo-instructions
            seq = self.encode_sequence(inst)
            for code, size in seq:
                codes.append(code)
                sizes.append(size)
                total_size += size

        return codes, sizes, total_size

    def _format_offset(self, offset: int) -> str:
        """Format offset for assembly using '. + N' syntax"""
        if offset >= 0:
            return f". + {offset}"
        else:
            return f". - {-offset}"

    def _parse_branch_instruction(self, branch_asm: str) -> Tuple[str, List[str]]:
        """
        Extract opcode and operands from branch instruction

        Args:
            branch_asm: e.g., "beq a0, a1, {LABEL}" or "bne s11, zero, loop"

        Returns:
            (opcode, operands) - operands excludes the label
        """
        asm = branch_asm.strip()
        parts = re.split(r'[,\s]+', asm)
        parts = [p.strip() for p in parts if p.strip()]

        if not parts:
            raise ValueError(f"Invalid branch instruction: {branch_asm}")

        opcode = parts[0].lower()
        operands = []

        for p in parts[1:]:
            # Skip label placeholders
            if '{LABEL}' in p or p.startswith('fwd_') or p.startswith('bwd_') or p.startswith('loop_'):
                continue
            # Skip if it looks like an offset (number or . + N)
            if p.startswith('.') or (p.lstrip('-').isdigit()):
                continue
            operands.append(p)

        return opcode, operands

    def compile_forward_jump(
        self,
        jump_instr: str,
        middle_instrs: List[str],
        label: Optional[str] = None
    ) -> CompiledSequence:
        """
        Compile a forward jump sequence

        Structure:
            jump_instr (branch to label)
            middle_instrs[0]
            middle_instrs[1]
            ...
            label:  (target, not included in output)

        Args:
            jump_instr: Jump instruction with {LABEL} placeholder
            middle_instrs: Instructions between jump and target
            label: Optional label name (for asm_list output)

        Returns:
            CompiledSequence with codes, sizes, and total_size
        """
        # Step 1: Compile middle instructions to calculate offset
        middle_codes, middle_sizes, middle_total = self._encode_sequence_flat(middle_instrs)

        # Step 2: Parse jump instruction to get opcode and operands
        opcode, operands = self._parse_branch_instruction(jump_instr)

        # Step 3: Determine jump instruction size based on opcode
        # B-type (beq, bne, blt, bge, bltu, bgeu) and J-type (jal) are 4 bytes
        # Compressed branches (c.beqz, c.bnez, c.j, c.jal) are 2 bytes
        if opcode in {'c.beqz', 'c.bnez', 'c.j', 'c.jal'}:
            jump_size = 2
        else:
            jump_size = 4

        # Step 4: Calculate correct offset: jump_size + middle_total
        # This is the distance from the branch instruction PC to the label
        correct_offset = jump_size + middle_total
        offset_str = self._format_offset(correct_offset)

        # Step 5: Build jump instruction with correct offset
        if opcode in {'beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu'}:
            if len(operands) >= 2:
                jump_asm = f"{opcode} {operands[0]}, {operands[1]}, {offset_str}"
            else:
                raise ValueError(f"B-type branch requires 2 registers: {jump_instr}")
        elif opcode in {'jal'}:
            rd = operands[0] if operands else 'ra'
            jump_asm = f"{opcode} {rd}, {offset_str}"
        elif opcode in {'c.beqz', 'c.bnez'}:
            jump_asm = f"{opcode} {operands[0]}, {offset_str}"
        elif opcode in {'c.j', 'c.jal'}:
            jump_asm = f"{opcode} {offset_str}"
        else:
            raise ValueError(f"Unsupported jump opcode: {opcode}")

        jump_code, actual_jump_size = self._encode_with_size(jump_asm)

        # Verify size assumption matches actual encoded size
        if actual_jump_size != jump_size:
            # Recalculate with actual size if assumption was wrong
            correct_offset = actual_jump_size + middle_total
            offset_str = self._format_offset(correct_offset)
            # Re-encode with correct offset
            if opcode in {'beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu'}:
                jump_asm = f"{opcode} {operands[0]}, {operands[1]}, {offset_str}"
            elif opcode in {'jal'}:
                rd = operands[0] if operands else 'ra'
                jump_asm = f"{opcode} {rd}, {offset_str}"
            elif opcode in {'c.beqz', 'c.bnez'}:
                jump_asm = f"{opcode} {operands[0]}, {offset_str}"
            elif opcode in {'c.j', 'c.jal'}:
                jump_asm = f"{opcode} {offset_str}"
            jump_code, actual_jump_size = self._encode_with_size(jump_asm)

        # Build result
        codes = [jump_code] + middle_codes
        sizes = [actual_jump_size] + middle_sizes
        total_size = actual_jump_size + middle_total

        # Build asm_list with actual offset instruction (matches machine code)
        # This ensures the .S file produces the same machine code as spike_engine executes
        asm_list = [jump_asm] + middle_instrs

        return CompiledSequence(codes, sizes, asm_list, total_size)

    def compile_backward_loop(
        self,
        init_instr: str,
        loop_body: List[str],
        decr_instr: str,
        branch_instr: str,
        label: Optional[str] = None
    ) -> CompiledSequence:
        """
        Compile a backward loop sequence

        Structure:
            init_instr     ; e.g., "li s11, 5"
            label:         ; loop start (implicit)
            loop_body[0]
            loop_body[1]
            ...
            decr_instr     ; e.g., "addi s11, s11, -1"
            branch_instr   ; e.g., "bne s11, zero, label" (jumps back)

        Args:
            init_instr: Loop counter initialization
            loop_body: Instructions in loop body
            decr_instr: Counter decrement instruction
            branch_instr: Conditional branch back to label
            label: Optional label name

        Returns:
            CompiledSequence with codes, sizes, and total_size
        """
        # Step 1: Compile init instruction
        init_seq = self.encode_sequence(init_instr)
        init_codes = [c for c, s in init_seq]
        init_sizes = [s for c, s in init_seq]
        init_total = sum(init_sizes)

        # Step 2: Compile loop body
        body_codes, body_sizes, body_total = self._encode_sequence_flat(loop_body)

        # Step 3: Compile decrement instruction
        decr_seq = self.encode_sequence(decr_instr)
        decr_codes = [c for c, s in decr_seq]
        decr_sizes = [s for c, s in decr_seq]
        decr_total = sum(decr_sizes)

        # Step 4: Calculate backward offset and compile branch
        # Offset is negative: -(body_size + decr_size)
        backward_offset = -(body_total + decr_total)

        opcode, operands = self._parse_branch_instruction(branch_instr)
        offset_str = self._format_offset(backward_offset)

        if opcode in {'beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu'}:
            if len(operands) >= 2:
                branch_asm = f"{opcode} {operands[0]}, {operands[1]}, {offset_str}"
            else:
                raise ValueError(f"B-type branch requires 2 registers: {branch_instr}")
        elif opcode in {'c.beqz', 'c.bnez'}:
            branch_asm = f"{opcode} {operands[0]}, {offset_str}"
        else:
            raise ValueError(f"Unsupported branch opcode for loop: {opcode}")

        branch_code, branch_size = self._encode_with_size(branch_asm)

        # Build result
        codes = init_codes + body_codes + decr_codes + [branch_code]
        sizes = init_sizes + body_sizes + decr_sizes + [branch_size]
        total_size = init_total + body_total + decr_total + branch_size

        # Build asm_list with actual offset instruction (matches machine code)
        # This ensures the .S file produces the same machine code as spike_engine executes
        asm_list = [init_instr] + loop_body + [decr_instr, branch_asm]

        return CompiledSequence(codes, sizes, asm_list, total_size)

    def compile_indirect_jump(
        self,
        la_instr: str,
        jump_instr: str,
        middle_instrs: List[str],
        label: Optional[str] = None
    ) -> CompiledSequence:
        """
        Compile an indirect jump sequence

        Structure:
            la_instr       ; "la t0, label" -> auipc + addi
            jump_instr     ; "jalr ra, 0(t0)"
            middle_instrs[0]
            ...
            label:

        Args:
            la_instr: Load address instruction (pseudo-instruction)
            jump_instr: Indirect jump instruction
            middle_instrs: Instructions between jump and target
            label: Optional label name

        Returns:
            CompiledSequence with codes, sizes, and total_size
        """
        # Step 1: Compile middle instructions
        middle_codes, middle_sizes, middle_total = self._encode_sequence_flat(middle_instrs)

        # Step 2: Parse la instruction to get register
        la_parts = la_instr.strip().split()
        if len(la_parts) < 2 or la_parts[0].lower() != 'la':
            raise ValueError(f"Invalid la instruction: {la_instr}")
        la_reg = la_parts[1].rstrip(',')

        # Step 3: Compile jump instruction to get its size
        jump_seq = self.encode_sequence(jump_instr)
        jump_codes = [c for c, s in jump_seq]
        jump_sizes = [s for c, s in jump_seq]
        jump_total = sum(jump_sizes)

        # Step 4: Calculate offset for 'la' pseudo-instruction
        # 'la' expands to: auipc rd, %pcrel_hi(target) + addi rd, rd, %pcrel_lo(target)
        # Target offset from auipc = 8 (auipc+addi) + jump_size + middle_size
        target_offset = 8 + jump_total + middle_total

        # Split into hi20 and lo12 with sign adjustment
        lo12 = target_offset & 0xFFF
        if lo12 >= 0x800:
            lo12 = lo12 - 0x1000
            hi20 = ((target_offset >> 12) + 1) & 0xFFFFF
        else:
            hi20 = (target_offset >> 12) & 0xFFFFF

        # Encode auipc and addi
        auipc_asm = f"auipc {la_reg}, {hi20}"
        addi_asm = f"addi {la_reg}, {la_reg}, {lo12}"

        auipc_code, auipc_size = self._encode_with_size(auipc_asm)
        addi_code, addi_size = self._encode_with_size(addi_asm)

        # Build result
        codes = [auipc_code, addi_code] + jump_codes + middle_codes
        sizes = [auipc_size, addi_size] + jump_sizes + middle_sizes
        total_size = auipc_size + addi_size + jump_total + middle_total

        # Build asm_list
        asm_list = [auipc_asm, addi_asm, jump_instr] + middle_instrs

        return CompiledSequence(codes, sizes, asm_list, total_size)


if __name__ == "__main__":
    # Test the hybrid encoder
    encoder = HybridEncoder()

    print("=" * 70)
    print("Testing HybridEncoder with various instructions")
    print("=" * 70)

    # Standard instructions (encoders should be used)
    standard_instructions = [
        "add x1, x2, x3",
        "addi x1, x2, 100",
        "lw x1, 100(x2)",
        "sw x2, 200(x3)",
    ]

    print("\nStandard instructions (should use fast encoder):")
    for inst in standard_instructions:
        result = encoder.encode_to_hex(inst)
        print(f"  {inst:30s} -> {result}")

    print("\n" + "=" * 70)
    print("Testing encode_sequence() for pseudo-instructions")
    print("=" * 70)

    pseudo_instructions = [
        "add x1, x2, x3",           # Standard - should return single instruction
        "li x1, 100",               # Small immediate - likely 1-2 instructions
        "li x1, 0x123456789",       # Large immediate - multiple instructions
        "li x1, -1",                # Negative immediate
    ]

    for inst in pseudo_instructions:
        sequence = encoder.encode_sequence(inst)
        print(f"\n{inst}:")
        if len(sequence) == 1:
            mc, sz = sequence[0]
            print(f"  -> Single instruction: 0x{mc:08x} (size={sz})")
        else:
            print(f"  -> Expanded to {len(sequence)} instructions:")
            for i, (mc, sz) in enumerate(sequence):
                print(f"       [{i}] 0x{mc:08x} (size={sz})")

    print("\n" + "=" * 70)
    print("Testing is_pseudo_instruction()")
    print("=" * 70)

    test_opcodes = ["add", "li", "la", "mv", "neg", "call", "nop", "lw", "sw"]
    for op in test_opcodes:
        is_pseudo = encoder.is_pseudo_instruction(f"{op} x1, x2")
        print(f"  {op:10s} -> {'pseudo' if is_pseudo else 'real'}")

    encoder.print_stats()

    print("\nNote: For testing fallback with P/B extension instructions,")
    print("those instructions need to be added manually in a test environment.")
