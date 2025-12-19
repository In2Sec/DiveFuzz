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
NOP Template Generator

Generates ELF files with N nop instructions for spike_engine initialization.
This replaces the cumulative compilation approach with a one-time template generation.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

try:
    from ..asm_template_manager import TemplateInstance
    from .elf_compiler import generate_elf
except ImportError:
    # For standalone testing
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from asm_template_manager import TemplateInstance
    from reg_analyzer.elf_compiler import generate_elf


class NopTemplateGenerator:
    """
    Generate ELF templates with N nop instructions

    Workflow:
    1. Create assembly file: template_header + N×nop + template_footer
    2. Compile to ELF using riscv-gnu-toolchain
    3. Return ELF path for spike_engine initialization
    """

    def __init__(self, template: TemplateInstance):
        """
        Initialize generator with a template instance

        Args:
            template: Template instance (contains ISA, arch, initialization code)
        """
        self.template = template

    def generate_nop_payload(self, num_instrs: int) -> str:
        """
        Generate instruction payload with N nop instructions

        Args:
            num_instrs: Number of nop instructions to generate

        Returns:
            String containing N lines of "nop" instructions (with trailing newline)
        """
        # Add trailing newline to ensure proper separation from footer
        return '\n'.join(['  nop'] * num_instrs) + '\n'

    def generate_nop_elf(
        self,
        num_instrs: int,
        output_path: Optional[str] = None,
        keep_asm: bool = False
    ) -> str:
        """
        Generate ELF file with N nop instructions

        Args:
            num_instrs: Number of nop instructions
            output_path: Output ELF path (default: /dev/shm/template_{num_instrs}.elf)
            keep_asm: Keep intermediate assembly file (for debugging)

        Returns:
            Path to generated ELF file

        Raises:
            RuntimeError: If compilation fails
        """
        # Generate nop payload
        nop_payload = self.generate_nop_payload(num_instrs)

        # Get complete assembly code from template
        complete_asm = self.template.get_complete_template(nop_payload)

        # Create temporary assembly file
        if output_path is None:
            output_path = f"/dev/shm/template_{num_instrs}.elf"

        # Write assembly to temporary file
        asm_path = output_path.replace('.elf', '.S')
        with open(asm_path, 'w') as f:
            f.write(complete_asm)

        try:
            # Compile to ELF
            elf_path = generate_elf(
                source_path=asm_path,
                spike_args=f'-march={self.template.isa}',
                arch_bits=self.template.arch_bits
            )

            # Check if compilation succeeded
            if elf_path is None:
                raise RuntimeError(f"generate_elf returned None - compilation failed. Check {asm_path}")

            # Copy to desired output path if different
            if elf_path != output_path:
                import shutil
                shutil.move(elf_path, output_path)
                elf_path = output_path

            # Clean up assembly file unless keep_asm is True
            if not keep_asm:
                try:
                    os.remove(asm_path)
                except:
                    pass  # Ignore cleanup errors

            return elf_path

        except Exception as e:
            # Keep assembly file on error for debugging
            print(f"[NopTemplateGenerator] Error - assembly file kept at: {asm_path}")
            raise RuntimeError(f"Failed to generate nop ELF: {e}")

    def generate_nop_elf_with_symbol(
        self,
        num_instrs: int,
        main_symbol: str = "main",
        output_path: Optional[str] = None
    ) -> tuple[str, int]:
        """
        Generate ELF and extract main symbol address

        This is useful when you need to know where the nop region starts.

        Args:
            num_instrs: Number of nop instructions
            main_symbol: Symbol name to mark nop region start (default: "main")
            output_path: Output ELF path

        Returns:
            Tuple of (elf_path, main_address)
            main_address will be 0 if symbol not found

        Note:
            The current template system doesn't directly support custom symbols.
            This method generates the ELF and returns address as 0.
            Address extraction should be done via objdump or readelf if needed.
        """
        elf_path = self.generate_nop_elf(num_instrs, output_path)

        # Try to extract symbol address using objdump
        try:
            import subprocess
            result = subprocess.run(
                ['riscv64-unknown-elf-objdump', '-t', elf_path],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Parse output for main symbol
            # Format: "address  flags section size name"
            for line in result.stdout.split('\n'):
                if main_symbol in line:
                    parts = line.split()
                    if len(parts) >= 1:
                        try:
                            address = int(parts[0], 16)
                            return elf_path, address
                        except ValueError:
                            pass
        except Exception:
            pass  # If objdump fails, return 0

        return elf_path, 0


# Convenience function
def generate_nop_elf(
    template: TemplateInstance,
    num_instrs: int,
    output_path: Optional[str] = None
) -> str:
    """
    Convenience function to generate nop ELF

    Args:
        template: Template instance
        num_instrs: Number of nop instructions
        output_path: Output ELF path (optional)

    Returns:
        Path to generated ELF file
    """
    generator = NopTemplateGenerator(template)
    return generator.generate_nop_elf(num_instrs, output_path)


if __name__ == "__main__":
    # Test standalone
    print("NopTemplateGenerator test")
    print("This module requires TemplateInstance from asm_template_manager")
    print("Run from main project context with proper imports")
