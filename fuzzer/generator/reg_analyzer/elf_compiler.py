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

import os
import subprocess
from pathlib import Path
from ..asm_template_manager import temp_file_manager

def generate_elf(source_path: str, spike_args: str, arch_bits: int = 64):
    # For spike resolution RS value
    """
    Process a single assembly file.

    Parameters:
    source_path: Path to the source assembly file
    spike_args: Additional arguments for the assembler (e.g., -march=rv64gc)
    arch_bits: Architecture bit width (32 or 64)
    """

    filename = os.path.basename(source_path)
    base_name = os.path.splitext(filename)[0]
    folder_path = os.path.dirname(source_path)

    object_file = os.path.join(folder_path, base_name + '.o')
    elf_file = os.path.join(folder_path, base_name + '.elf')


    # Register temporary file to the manager
    temp_file_manager.register_temp_file(object_file)
    temp_file_manager.register_temp_file(elf_file)

    # riscv-gnu-toolchain --enable-multilib for different arch_bits, use riscv64-unknown-elf-gcc
    prefix = 'riscv64-unknown-elf-'
    compiler_as = prefix + 'as'
    compiler_ld = prefix + 'ld'

    # Linking in reg_analyzer/liner directory
    link_dir = Path(__file__).parent / 'linker/link.ld'
    if arch_bits == 32:
        link_dir = Path(__file__).parent / 'linker/link_32.ld'
            
    try:
        compile_cmd = [compiler_as, spike_args, source_path, '-o', object_file]
        result = subprocess.run(compile_cmd)
        if result.returncode != 0:
            print(f"Compilation failed.")
            return None

        link_cmd = [compiler_ld, '-T', str(link_dir), object_file, '-o', elf_file]
        result = subprocess.run(link_cmd)
        if result.returncode != 0:
            print(f"Linking failed.")
            return None
        
        return elf_file

    except Exception as e:
        print(f"Error occurred during compilation: {e}")
        return None
