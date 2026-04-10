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
Jump Sequence Compiler

Compiles jump sequences (forward jumps, backward loops) into machine code sequences.
Handles offset calculation and branch instruction encoding without using labels.

Design:
- Labels cannot be compiled individually; this compiler calculates offsets directly
- Integrates with HybridEncoder for instruction encoding
- Supports both forward jumps and backward loops
"""

import re
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

try:
    from .instruction_encoder import InstructionEncoder
except ImportError:
    from instruction_encoder import InstructionEncoder


@dataclass
class CompiledInstruction:
    """Compiled instruction with metadata"""
    machine_code: int
    asm_str: str
    size: int  # 2 or 4 bytes
    is_jump: bool  # True for branch/jump instructions


@dataclass
class JumpSequence:
    """Complete jump sequence ready for execution"""
    instructions: List[CompiledInstruction]
    jump_type: str  # 'forward' or 'backward'
    label: str
    total_size: int  # Total size in bytes


class JumpSequenceCompiler:
    """
    Compiles jump sequences with offset calculation

    Handles:
    - Forward jumps: branch/jump instruction followed by target instructions
    - Backward loops: init + label + body + decrement + branch back

    Key insight: Instead of using labels, we calculate byte offsets directly
    and encode them into the branch instructions.
    """

    # Branch instructions that use B-type encoding (12-bit offset)
    B_TYPE_BRANCHES = {'beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu'}

    # Jump instructions that use J-type encoding (20-bit offset)
    J_TYPE_JUMPS = {'jal'}

    # Compressed branch instructions (8-bit offset)
    C_BRANCHES = {'c.beqz', 'c.bnez'}

    # Compressed jump instructions (11-bit offset)
    C_JUMPS = {'c.j', 'c.jal'}

    def __init__(self, encoder: Optional[InstructionEncoder] = None):
        """
        Initialize the jump sequence compiler

        Args:
            encoder: InstructionEncoder instance (creates one if not provided)
        """
        self.encoder = encoder or InstructionEncoder()

    def get_instruction_size(self, machine_code: int) -> int:
        """
        Get instruction size from machine code

        RISC-V encoding rules:
        - bits[1:0] != 0b11 -> 16-bit compressed instruction
        - bits[1:0] == 0b11 and bits[4:2] != 0b111 -> 32-bit standard
        """
        if (machine_code & 0x3) != 0x3:
            return 2  # Compressed
        return 4  # Standard

    def _encode_instruction(self, asm: str) -> Tuple[int, int]:
        """
        Encode an instruction and return (machine_code, size)

        Args:
            asm: Assembly instruction string

        Returns:
            (machine_code, size_in_bytes)
        """
        code = self.encoder.encode(asm)
        size = self.get_instruction_size(code)
        return code, size

    def _extract_branch_parts(self, branch_asm: str) -> Tuple[str, List[str], str]:
        """
        Extract opcode, operands, and label from branch instruction

        Args:
            branch_asm: e.g., "beq a0, a1, {LABEL}" or "bne s11, zero, loop_0"

        Returns:
            (opcode, operands_list, label_placeholder)
        """
        # Remove label placeholder or actual label
        asm = branch_asm.strip()

        # Split into parts
        parts = re.split(r'[,\s]+', asm)
        parts = [p.strip() for p in parts if p.strip()]

        if not parts:
            raise ValueError(f"Invalid branch instruction: {branch_asm}")

        opcode = parts[0].lower()

        # Find operands (registers) and label
        operands = []
        label = None

        for p in parts[1:]:
            # Check if this is a label (contains LABEL, or is a known label format)
            if '{LABEL}' in p or p.startswith('fwd_') or p.startswith('bwd_') or p.startswith('loop_'):
                label = p
            elif not p.startswith('-') and not p.isdigit() and not p.startswith('0x'):
                # It's a register
                operands.append(p)
            else:
                # It's already an offset (shouldn't happen in our use case)
                label = p

        return opcode, operands, label or '{LABEL}'

    def _encode_branch_with_offset(self, opcode: str, operands: List[str], offset: int) -> int:
        """
        Encode a branch instruction with a specific byte offset

        Args:
            opcode: Branch opcode (e.g., 'beq', 'bne', 'jal')
            operands: Register operands (e.g., ['a0', 'a1'] for beq)
            offset: Byte offset (can be negative for backward jumps)

        Returns:
            Encoded machine code
        """
        if opcode in self.B_TYPE_BRANCHES:
            # B-type: beq rs1, rs2, offset
            if len(operands) < 2:
                raise ValueError(f"B-type branch {opcode} requires 2 register operands")
            # Construct instruction with offset as immediate
            asm = f"{opcode} {operands[0]}, {operands[1]}, {offset}"

        elif opcode in self.J_TYPE_JUMPS:
            # J-type: jal rd, offset
            if len(operands) < 1:
                # Default to ra (x1)
                operands = ['ra']
            asm = f"{opcode} {operands[0]}, {offset}"

        elif opcode in self.C_BRANCHES:
            # Compressed branch: c.beqz rs1, offset or c.bnez rs1, offset
            if len(operands) < 1:
                raise ValueError(f"Compressed branch {opcode} requires 1 register operand")
            asm = f"{opcode} {operands[0]}, {offset}"

        elif opcode in self.C_JUMPS:
            # Compressed jump: c.j offset or c.jal offset
            asm = f"{opcode} {offset}"

        else:
            raise ValueError(f"Unknown branch/jump opcode: {opcode}")

        return self.encoder.encode(asm)

    def compile_forward_jump(
        self,
        jump_instr: str,
        middle_instrs: List[str],
        label: str
    ) -> JumpSequence:
        """
        Compile a forward jump sequence

        Structure:
        jump_instr (branch to label)
        middle_instrs[0]
        middle_instrs[1]
        ...
        label:  (target)

        Args:
            jump_instr: Jump instruction with {LABEL} placeholder, e.g., "beq a0, a1, {LABEL}"
            middle_instrs: Instructions between jump and target
            label: Label name (e.g., "fwd_0")

        Returns:
            JumpSequence with compiled instructions
        """
        instructions = []

        # Step 1: Compile middle instructions to calculate total offset
        middle_compiled = []
        total_middle_size = 0

        for asm in middle_instrs:
            code, size = self._encode_instruction(asm)
            middle_compiled.append(CompiledInstruction(
                machine_code=code,
                asm_str=asm,
                size=size,
                is_jump=False
            ))
            total_middle_size += size

        # Step 2: Calculate offset for jump instruction
        # For forward jump: offset = total size of middle instructions
        # (offset is relative to jump instruction address)
        opcode, operands, _ = self._extract_branch_parts(jump_instr)

        # Determine jump instruction size first (needed for some offset calculations)
        # Most branches are 4 bytes, compressed are 2 bytes
        if opcode.startswith('c.'):
            jump_size = 2
        else:
            jump_size = 4

        # Forward offset: skip over middle instructions
        # The offset is from the branch instruction to the target
        forward_offset = total_middle_size

        # Encode jump with calculated offset
        jump_code = self._encode_branch_with_offset(opcode, operands, forward_offset)
        actual_jump_size = self.get_instruction_size(jump_code)

        # Add jump instruction
        instructions.append(CompiledInstruction(
            machine_code=jump_code,
            asm_str=jump_instr.replace('{LABEL}', label),
            size=actual_jump_size,
            is_jump=True
        ))

        # Add middle instructions
        instructions.extend(middle_compiled)

        total_size = actual_jump_size + total_middle_size

        return JumpSequence(
            instructions=instructions,
            jump_type='forward',
            label=label,
            total_size=total_size
        )

    def compile_backward_loop(
        self,
        init_instr: str,
        loop_body: List[str],
        decr_instr: str,
        branch_instr: str,
        label: str,
        loop_iterations: int = 1
    ) -> JumpSequence:
        """
        Compile a backward loop sequence

        Structure:
        init_instr     ; e.g., "li s11, 5"
        label:         ; loop start (implicit, not in output)
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
            label: Label name
            loop_iterations: Number of loop iterations (for metadata)

        Returns:
            JumpSequence with compiled instructions
        """
        instructions = []

        # Step 1: Compile init instruction
        init_code, init_size = self._encode_instruction(init_instr)
        instructions.append(CompiledInstruction(
            machine_code=init_code,
            asm_str=init_instr,
            size=init_size,
            is_jump=False
        ))

        # Step 2: Compile loop body
        body_size = 0
        for asm in loop_body:
            code, size = self._encode_instruction(asm)
            instructions.append(CompiledInstruction(
                machine_code=code,
                asm_str=asm,
                size=size,
                is_jump=False
            ))
            body_size += size

        # Step 3: Compile decrement instruction
        decr_code, decr_size = self._encode_instruction(decr_instr)
        instructions.append(CompiledInstruction(
            machine_code=decr_code,
            asm_str=decr_instr,
            size=decr_size,
            is_jump=False
        ))

        # Step 4: Calculate backward offset and compile branch
        # Offset is negative: -(body_size + decr_size)
        # The branch jumps back to the start of loop body (after init)
        opcode, operands, _ = self._extract_branch_parts(branch_instr)

        # Determine branch size
        if opcode.startswith('c.'):
            branch_size = 2
        else:
            branch_size = 4

        # Backward offset (negative)
        backward_offset = -(body_size + decr_size)

        branch_code = self._encode_branch_with_offset(opcode, operands, backward_offset)
        actual_branch_size = self.get_instruction_size(branch_code)

        instructions.append(CompiledInstruction(
            machine_code=branch_code,
            asm_str=branch_instr.replace('{LABEL}', label),
            size=actual_branch_size,
            is_jump=True
        ))

        total_size = init_size + body_size + decr_size + actual_branch_size

        return JumpSequence(
            instructions=instructions,
            jump_type='backward',
            label=label,
            total_size=total_size
        )

    def compile_indirect_jump(
        self,
        la_instr: str,
        jump_instr: str,
        middle_instrs: List[str],
        label: str
    ) -> JumpSequence:
        """
        Compile an indirect jump sequence

        Structure:
        la_instr       ; e.g., "la t0, label" -> auipc + addi
        jump_instr     ; e.g., "jalr ra, 0(t0)"
        middle_instrs[0]
        ...
        label:

        Note: Indirect jumps are more complex because 'la' is a pseudo-instruction.
        For now, we handle this by computing the actual address offset.

        Args:
            la_instr: Load address instruction (pseudo-instruction)
            jump_instr: Indirect jump instruction
            middle_instrs: Instructions between jump and target
            label: Label name

        Returns:
            JumpSequence with compiled instructions
        """
        instructions = []

        # Step 1: Compile middle instructions to get offset
        middle_compiled = []
        middle_size = 0
        for asm in middle_instrs:
            code, size = self._encode_instruction(asm)
            middle_compiled.append(CompiledInstruction(
                machine_code=code,
                asm_str=asm,
                size=size,
                is_jump=False
            ))
            middle_size += size

        # Step 2: Handle 'la' pseudo-instruction
        # 'la rd, label' expands to: auipc rd, %pcrel_hi(label) + addi rd, rd, %pcrel_lo(label)
        # For our case, we need to calculate the offset to the target

        # Parse la instruction: "la reg, label"
        la_parts = la_instr.strip().split()
        if len(la_parts) < 3 or la_parts[0].lower() != 'la':
            raise ValueError(f"Invalid la instruction: {la_instr}")

        la_reg = la_parts[1].rstrip(',')

        # Parse jump instruction to get its size
        # jalr rd, offset(rs1) or c.jr rs1 or c.jalr rs1
        jump_parts = jump_instr.strip().split()
        jump_opcode = jump_parts[0].lower()

        if jump_opcode.startswith('c.'):
            jump_size = 2
        else:
            jump_size = 4

        # 'la' typically expands to auipc + addi (8 bytes total)
        # But we'll use a simpler approach: encode auipc with the high 20 bits
        # and addi with the low 12 bits of the offset

        # Total offset from auipc to target:
        # auipc (4) + addi (4) + jalr (4) + middle_size = target
        # So target_offset = 8 + jump_size + middle_size
        target_offset = 8 + jump_size + middle_size

        # Split into hi20 and lo12
        # Handle the sign extension properly
        if target_offset < 0:
            # For negative offsets, we need to adjust hi20
            lo12 = target_offset & 0xFFF
            if lo12 >= 0x800:
                lo12 = lo12 - 0x1000  # Sign extend
            hi20 = (target_offset - lo12) >> 12
        else:
            lo12 = target_offset & 0xFFF
            if lo12 >= 0x800:
                lo12 = lo12 - 0x1000
                hi20 = ((target_offset >> 12) + 1) & 0xFFFFF
            else:
                hi20 = (target_offset >> 12) & 0xFFFFF

        # Encode auipc
        auipc_asm = f"auipc {la_reg}, {hi20}"
        auipc_code, auipc_size = self._encode_instruction(auipc_asm)
        instructions.append(CompiledInstruction(
            machine_code=auipc_code,
            asm_str=auipc_asm,
            size=auipc_size,
            is_jump=False
        ))

        # Encode addi
        addi_asm = f"addi {la_reg}, {la_reg}, {lo12}"
        addi_code, addi_size = self._encode_instruction(addi_asm)
        instructions.append(CompiledInstruction(
            machine_code=addi_code,
            asm_str=addi_asm,
            size=addi_size,
            is_jump=False
        ))

        # Step 3: Compile jump instruction
        jump_code, actual_jump_size = self._encode_instruction(jump_instr)
        instructions.append(CompiledInstruction(
            machine_code=jump_code,
            asm_str=jump_instr,
            size=actual_jump_size,
            is_jump=True
        ))

        # Step 4: Add middle instructions
        instructions.extend(middle_compiled)

        total_size = auipc_size + addi_size + actual_jump_size + middle_size

        return JumpSequence(
            instructions=instructions,
            jump_type='indirect',
            label=label,
            total_size=total_size
        )

    def get_asm_sequence(self, jump_seq: JumpSequence, include_label: bool = True) -> List[str]:
        """
        Get assembly string sequence from compiled jump sequence

        Args:
            jump_seq: Compiled jump sequence
            include_label: Whether to include the label definition at the end (for forward jumps)

        Returns:
            List of assembly strings (for writing to file)
        """
        result = [instr.asm_str for instr in jump_seq.instructions]

        if include_label and jump_seq.jump_type in ('forward', 'indirect'):
            result.append(f"{jump_seq.label}:")

        return result

    def get_machine_codes(self, jump_seq: JumpSequence) -> List[Tuple[int, int]]:
        """
        Get machine codes from compiled jump sequence

        Args:
            jump_seq: Compiled jump sequence

        Returns:
            List of (machine_code, size) tuples
        """
        return [(instr.machine_code, instr.size) for instr in jump_seq.instructions]


if __name__ == "__main__":
    # Test the jump sequence compiler
    compiler = JumpSequenceCompiler()

    print("Testing JumpSequenceCompiler...")
    print("=" * 60)

    # Test forward jump
    print("\n1. Forward Jump Test:")
    forward_seq = compiler.compile_forward_jump(
        jump_instr="beq a0, a1, {LABEL}",
        middle_instrs=["add t0, t1, t2", "sub t3, t4, t5", "and t6, a0, a1"],
        label="fwd_0"
    )
    print(f"   Jump type: {forward_seq.jump_type}")
    print(f"   Total size: {forward_seq.total_size} bytes")
    print("   Instructions:")
    for instr in forward_seq.instructions:
        print(f"     {instr.asm_str:30s} -> 0x{instr.machine_code:08x} ({instr.size}B)")
    print("   Assembly output:")
    for asm in compiler.get_asm_sequence(forward_seq):
        print(f"     {asm}")

    # Test backward loop
    print("\n2. Backward Loop Test:")
    backward_seq = compiler.compile_backward_loop(
        init_instr="li s11, 5",
        loop_body=["add t0, t1, t2", "sub t3, t4, t5"],
        decr_instr="addi s11, s11, -1",
        branch_instr="bne s11, zero, {LABEL}",
        label="loop_0"
    )
    print(f"   Jump type: {backward_seq.jump_type}")
    print(f"   Total size: {backward_seq.total_size} bytes")
    print("   Instructions:")
    for instr in backward_seq.instructions:
        print(f"     {instr.asm_str:30s} -> 0x{instr.machine_code:08x} ({instr.size}B)")
    print("   Assembly output:")
    for asm in compiler.get_asm_sequence(backward_seq, include_label=False):
        print(f"     {asm}")

    print("\n" + "=" * 60)
    print("Tests completed!")
