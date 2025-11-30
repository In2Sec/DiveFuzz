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
import threading
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../ref/riscv-isa-sim-adapter/spike_wrapper')))
from typing import Optional, List
import spike_wrapper as spike
from ..asm_template_manager import temp_file_manager, TemplateInstance
from .compiler import generate_elf
from .instruction_parser import InstructionInfo, InstructionParser


class Spike:
    @staticmethod
    def _generate_debug_commands(instr_info: InstructionInfo) -> Optional[str]:
        """Generate Spike debug commands for reading source registers

        Args:
            instr_info: Parsed instruction information

        Returns:
            Spike debug command string, or None if no registers to read
        """
        # Get source registers from instruction
        source_regs = InstructionParser.get_source_registers(instr_info)

        if source_regs is None or len(source_regs) == 0:
            return None

        # Determine register command type (reg or freg)
        reg_cmd = 'freg' if InstructionParser.is_float_instruction(instr_info) else 'reg'

        # Build debug commands
        # A hack method that obtains the endpoint using a specific secret phrase
        debug_cmds = ["until reg 0 t5 0x2727272727"]

        for reg in source_regs:
            debug_cmds.append(f"{reg_cmd} 0 {reg}")
        debug_cmds.append("q")

        return '\n'.join(debug_cmds)

    @staticmethod
    def get_registers_values(instr_info: InstructionInfo, updated_content_str: str, template: TemplateInstance) -> Optional[List[int]]:
        """
        Use Spike to simulate a RISC-V program and extract source register values.

        :param instr_info: Parsed instruction information
        :param updated_content_str: Assembly content to simulate
        :param template: Template instance to wrap the content
        :return: List of register values (and immediate if applicable)
        """

        # Generate Spike debug commands
        debug_cmds_str = Spike._generate_debug_commands(instr_info)
        if debug_cmds_str is None: # no register to read
            return [instr_info.imm] if instr_info.imm is not None else None

        # Get template content and concat updated_content from template instance
        entire_content = template.get_complete_template(updated_content_str)

        temp_asm_path = Spike._write_to_memory_file_system(entire_content)

        elf_file_path = generate_elf(temp_asm_path, '-march=' + template.isa, template.arch_bits)
        if elf_file_path is None:
            print("Please check riscv-gnu-toolchain.")
            return None

        try:
            """Use the dynamic library packaged by spike and directly input the string into spike_wrapper"""
            # Execute Spike and get all output at once
            # Start the Spike process and enter debug mode
            register_values = spike.debug_cmd_str_elf_file(elf_file_path, debug_cmds_str, template.isa)
        except Exception as e:
            print(f"Spike wrapper error: {e}")
            return None
        finally:
            # Remove the temporary file
            temp_file_manager.cleanup_all_temp_files()

        register_values = Spike._convert_hex_values(register_values)
        if register_values is None:
            return None

        if instr_info.imm is not None:
            register_values.append(instr_info.imm)

        return register_values
    
    @staticmethod
    def _convert_hex_values(register_values_str):
        result = []
        for value in register_values_str.strip().splitlines():
            try:
                result.append(int(value, 16))
            except ValueError:
                return None
        return result
        
    @staticmethod
    def _write_to_memory_file_system(entire_content: str) -> str:
        """Intermediate files are placed in the memory file system"""
        # 2. Create a temporary file in memory
        temp_path = f'/dev/shm/temp_asm_{os.getpid()}_{threading.current_thread().ident}.S'

        # Directly write optimized content
        with open(temp_path, 'w') as f:
            f.writelines(entire_content)

        # Registering to the temporary file manager
        temp_file_manager.register_temp_file(temp_path)
        return temp_path

    @staticmethod
    # Output the obtained value after XOR
    def xor_register_values(reg_values: List[int]) -> int:
        """
        Compute V = (operand_N << N) XOR ... XOR (operand_1 << 1) XOR operand_0
        """
        xor_result = 0

        # operand_0 is the least significant bit and is not shifted; operand_i shifts left by i bits.
        for i, value in enumerate(reg_values):
            xor_result ^= (value << i)

        return xor_result
