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
RISC-V instruction compiler wrapper
Compiles single instructions to machine code using riscv-gnu-toolchain

Supports pseudo-instructions that expand to multiple machine instructions:
- li with large immediate -> lui + addi + slli + ... sequence
- la (load address) -> auipc + addi
- etc.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple, Union


class RiscvCompiler:
    """Compile RISC-V instructions using riscv-gnu-toolchain"""

    def __init__(
        self,
        as_cmd: str = "riscv64-unknown-elf-as",
        objcopy_cmd: str = "riscv64-unknown-elf-objcopy",
        default_march: str = "rv64imafdcv_zicsr_zifencei_zba_zbb_zbc_zbs_zfh"
    ):
        """
        Initialize the compiler

        Args:
            as_cmd: Assembler command
            objcopy_cmd: objcopy command
            default_march: Default architecture string (supports as many extensions as possible)
        """
        self.as_cmd = as_cmd
        self.objcopy_cmd = objcopy_cmd
        self.default_march = default_march

        # Verify toolchain availability
        self._verify_toolchain()

    def _verify_toolchain(self):
        """Verify if the RISC-V toolchain is available"""
        try:
            result = subprocess.run(
                [self.as_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError(f"Assembler verification failed: {result.stderr}")
        except FileNotFoundError:
            raise RuntimeError(
                f"RISC-V toolchain not found: {self.as_cmd}\n"
                f"Please install riscv-gnu-toolchain and ensure it's in PATH"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Assembler verification timed out")

    def compile_instruction(
        self,
        asm_instruction: str,
        march: Optional[str] = None
    ) -> int:
        """
        Compile a single assembly instruction to machine code

        Args:
            asm_instruction: Assembly instruction string (e.g., "add x1, x2, x3")
            march: Optional architecture string, uses default_march if not specified

        Returns:
            32-bit machine code (integer)

        Raises:
            RuntimeError: If compilation fails
        """
        if march is None:
            march = self.default_march

        with tempfile.TemporaryDirectory() as tmpdir:
            asm_file = Path(tmpdir) / "inst.s"
            obj_file = Path(tmpdir) / "inst.o"
            bin_file = Path(tmpdir) / "inst.bin"

            # Write assembly file
            # Use .option norvc to disable compressed instructions
            # This ensures all instructions are 4 bytes for consistent layout
            with open(asm_file, 'w') as f:
                f.write(".text\n")
                f.write(".option norvc\n")
                f.write(f"    {asm_instruction}\n")

            # Assemble
            as_result = subprocess.run(
                [self.as_cmd, f"-march={march}", "-o", str(obj_file), str(asm_file)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if as_result.returncode != 0:
                # Try to extract more useful error information
                error_msg = as_result.stderr.strip()
                raise RuntimeError(
                    f"Failed to assemble instruction: '{asm_instruction}'\n"
                    f"Architecture: {march}\n"
                    f"Error: {error_msg}"
                )

            # Extract binary
            objcopy_result = subprocess.run(
                [self.objcopy_cmd, "-O", "binary", str(obj_file), str(bin_file)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if objcopy_result.returncode != 0:
                raise RuntimeError(
                    f"Failed to extract binary from object file\n"
                    f"Error: {objcopy_result.stderr}"
                )

            # Read machine code
            with open(bin_file, 'rb') as f:
                machine_code_bytes = f.read()

            if len(machine_code_bytes) == 0:
                raise RuntimeError(
                    f"Invalid machine code length: 0 bytes\n"
                    f"Failed to generate machine code for instruction"
                )

            # Handle compressed instructions (2 bytes) and standard instructions (4 bytes)
            if len(machine_code_bytes) == 2:
                # Compressed instruction (C extension): zero-pad to 4 bytes
                # Spike will correctly execute 2-byte instructions, ignoring the trailing zero padding
                machine_code_bytes = machine_code_bytes + b'\x00\x00'
            elif len(machine_code_bytes) < 2:
                raise RuntimeError(
                    f"Invalid machine code length: {len(machine_code_bytes)} bytes\n"
                    f"Expected at least 2 bytes for a RISC-V instruction"
                )

            # Convert to integer (little-endian), using the first 4 bytes
            machine_code = int.from_bytes(machine_code_bytes[:4], byteorder='little')

            return machine_code

    def compile_instruction_sequence(
        self,
        asm_instruction: str,
        march: Optional[str] = None
    ) -> List[Tuple[int, int]]:
        """
        Compile an assembly instruction and return all expanded machine codes.

        For pseudo-instructions like `li x1, 0x123456789`, the assembler may expand
        them into multiple real instructions. This method returns ALL instructions.

        Args:
            asm_instruction: Assembly instruction string (e.g., "li x1, 0x123456789")
            march: Optional architecture string, uses default_march if not specified

        Returns:
            List of (machine_code, size) tuples where:
            - machine_code: 32-bit integer (2-byte compressed instructions zero-padded)
            - size: Actual instruction size in bytes (2 or 4)

        Raises:
            RuntimeError: If compilation fails

        Example:
            >>> compiler.compile_instruction_sequence("li x1, 0x123456789")
            [(0x00000537, 4), (0x00050513, 4), (0x00c51513, 4), ...]  # lui + addi + slli...
        """
        if march is None:
            march = self.default_march

        with tempfile.TemporaryDirectory() as tmpdir:
            asm_file = Path(tmpdir) / "inst.s"
            obj_file = Path(tmpdir) / "inst.o"
            bin_file = Path(tmpdir) / "inst.bin"

            # Write assembly file
            # Use .option norvc to disable compressed instructions
            # This ensures all instructions are 4 bytes for consistent layout
            with open(asm_file, 'w') as f:
                f.write(".text\n")
                f.write(".option norvc\n")
                f.write(f"    {asm_instruction}\n")

            # Assemble
            as_result = subprocess.run(
                [self.as_cmd, f"-march={march}", "-o", str(obj_file), str(asm_file)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if as_result.returncode != 0:
                error_msg = as_result.stderr.strip()
                raise RuntimeError(
                    f"Failed to assemble instruction: '{asm_instruction}'\n"
                    f"Architecture: {march}\n"
                    f"Error: {error_msg}"
                )

            # Extract binary
            objcopy_result = subprocess.run(
                [self.objcopy_cmd, "-O", "binary", str(obj_file), str(bin_file)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if objcopy_result.returncode != 0:
                raise RuntimeError(
                    f"Failed to extract binary from object file\n"
                    f"Error: {objcopy_result.stderr}"
                )

            # Read all machine code bytes
            with open(bin_file, 'rb') as f:
                machine_code_bytes = f.read()

            if len(machine_code_bytes) == 0:
                raise RuntimeError(
                    f"Invalid machine code length: 0 bytes\n"
                    f"Failed to generate machine code for instruction"
                )

            # Parse all instructions from the binary
            instructions = []
            offset = 0

            while offset < len(machine_code_bytes):
                # Check if this is a compressed instruction (C extension)
                # Compressed instructions have bits [1:0] != 11
                first_halfword = int.from_bytes(
                    machine_code_bytes[offset:offset+2],
                    byteorder='little'
                )

                if (first_halfword & 0x3) != 0x3:
                    # Compressed instruction (2 bytes)
                    # Zero-pad to 4 bytes for consistency
                    machine_code = first_halfword
                    instructions.append((machine_code, 2))
                    offset += 2
                else:
                    # Standard instruction (4 bytes)
                    if offset + 4 <= len(machine_code_bytes):
                        machine_code = int.from_bytes(
                            machine_code_bytes[offset:offset+4],
                            byteorder='little'
                        )
                        instructions.append((machine_code, 4))
                        offset += 4
                    else:
                        # Incomplete instruction at end (shouldn't happen normally)
                        remaining = machine_code_bytes[offset:]
                        padded = remaining + b'\x00' * (4 - len(remaining))
                        machine_code = int.from_bytes(padded, byteorder='little')
                        instructions.append((machine_code, len(remaining)))
                        break

            return instructions

    def compile_multiple(
        self,
        instructions: list[str],
        march: Optional[str] = None
    ) -> list[int]:
        """
        Batch compile multiple instructions

        Args:
            instructions: List of instructions
            march: Optional architecture string

        Returns:
            List of machine codes
        """
        results = []
        for instruction in instructions:
            machine_code = self.compile_instruction(instruction, march)
            results.append(machine_code)
        return results


# Convenience function
def compile_instruction(
    instruction: str,
    march: str = "rv64imafdcv_zicsr_zifencei_zba_zbb_zbc_zbs_zfh"
) -> int:
    """
    Convenience function: compile a single instruction

    Args:
        instruction: Assembly instruction
        march: Architecture string

    Returns:
        Machine code
    """
    compiler = RiscvCompiler(default_march=march)
    return compiler.compile_instruction(instruction)


if __name__ == "__main__":
    # Test the compiler
    compiler = RiscvCompiler()

    print("=" * 70)
    print("Testing RISC-V compiler - Single instruction encoding")
    print("=" * 70)

    test_instructions = [
        "add x1, x2, x3",
        "addi x1, x2, 100",
        "lui x1, 0x12345",
    ]

    for instruction in test_instructions:
        try:
            machine_code = compiler.compile_instruction(instruction)
            print(f"✓ {instruction:30s} -> 0x{machine_code:08x}")
        except Exception as e:
            print(f"✗ {instruction:30s} -> Error: {e}")

    print("\n" + "=" * 70)
    print("Testing RISC-V compiler - Pseudo-instruction sequence encoding")
    print("=" * 70)

    pseudo_instructions = [
        "li x1, 0x12345",           # Small immediate - should be 1-2 instructions
        "li x1, 0x123456789",       # Large immediate - multiple instructions
        "li x1, -1",                # Negative - should be 1 instruction (addi x1, x0, -1)
        "li x1, 0x7fffffff",        # Max positive 32-bit
    ]

    for instruction in pseudo_instructions:
        try:
            sequence = compiler.compile_instruction_sequence(instruction)
            print(f"\n{instruction}:")
            print(f"  Expanded to {len(sequence)} instruction(s):")
            for i, (mc, size) in enumerate(sequence):
                print(f"    [{i}] 0x{mc:08x} (size={size})")
        except Exception as e:
            print(f"✗ {instruction}: Error: {e}")
