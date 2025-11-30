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
from typing import Tuple, Optional
from ..bug_filter import bug_filter
from ..utils import list2str
from ..asm_template_manager import TemplateInstance
from .instruction_parser import InstructionParser
from .spike_resolution import Spike


def temp_asm_to_debug_generate(updated_content: Tuple[str], instr: str, is_first: bool, label: Optional[str], template: TemplateInstance):
    """
    Debug-generate assembly and verify via Spike simulation.

    Args:
        updated_content: Tuple of existing instructions
        instr: New instruction to add
        is_first: Whether this is the first instruction
        label: Optional label for jump targets
        template: Template instance for wrapping content

    Returns:
        1 if new unique value found, 0 if duplicate, 3 if error
    """
    # parse instruction
    instr_processed, instr_info = InstructionParser.parse_instruction(instr)
    if instr_info is None: # Unsupported instruction type
        return 3

    # first time to look up RSx value
    instr_payload_str = list2str(updated_content)
    if is_first:
        if label is not None:
            instr_payload_str += '\n' + instr_processed + '\n' + f'{label}:' + '\n  li t5,0x2727272727\n'
        else:
            instr_payload_str += '\n' + instr_processed + '\n  li t5,0x2727272727\n'


    # Get register values by spike
    register_values = Spike.get_registers_values(instr_info, instr_payload_str, template)
    if register_values is None:
        return 3
    
    bug_name = bug_filter.filter_known_bug(instr_info.op_name, register_values)
    if bug_name is not None:
        print(bug_name)
        return 3   

    # Calculates the XOR value and returns it

    xor_stderr = Spike.xor_register_values(register_values)

    resolution_dir = "./spike_resolution"
    os.makedirs(resolution_dir, exist_ok=True)
    xor_file_path = os.path.join(resolution_dir, f"{instr_info.op_name}_xor_values.txt")
    
    try:
        with open(xor_file_path, "r+") as file:
            existing_values = set(file.read().splitlines())
            if str(xor_stderr) not in existing_values:
                file.write(f"{xor_stderr}\n")
                return 1 
    except FileNotFoundError:
        with open(xor_file_path, "w") as file:
            file.write(f"{xor_stderr}\n")
        return 1
    
    return 0 

def temp_asm_to_debug(updated_content: Tuple[str], instr: str, is_first: bool = False):
    # parse instruction
    instr_processed, instr_info = InstructionParser.parse_instruction(instr)
    if instr_info is None: # Unsupported instruction type
        return 3

    # first time to look up RSx value
    instr_payload_str = list2str(updated_content)
    if is_first:
        instr_payload_str += '\n' + instr_processed + '\n  li t5,0x2727272727\n'
    
    # Get register values by spike
    register_values = Spike.get_registers_values(instr_info, instr_payload_str)
    if register_values is None:
        return 3

    xor_value = Spike.xor_register_values(register_values)
    # Parsing the directory
    resolution_dir = "./spike_resolution"
    os.makedirs(resolution_dir, exist_ok=True)
    xor_file_path = os.path.join(resolution_dir, f"{instr_info.op_name}_xor_values.txt")
    # Check if the file exists and read its contents
    if os.path.exists(xor_file_path):
        with open(xor_file_path, "r") as file:
            existing_values = file.read().splitlines()
            # Check if the value already exists
            if str(xor_value) in existing_values:
                return 0  # Value already exists
    
    # The value does not exist, add it to the file
    with open(xor_file_path, "a") as file:
        file.write(f"{xor_value}\n")
    
    return 1  # Value added
