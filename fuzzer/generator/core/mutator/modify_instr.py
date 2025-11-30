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

import re
import random
from ...instr_generator import (
    INSTRUCTION_FORMATS,
    special_instr,
    variable_range,
    gen_imm,
)

def modify_instruction_dec(ori_instr, rand_instr, increase_prob, extension):
    extension = extension.upper()

    special_registers = ['ra', 'sp', 'gp', 'tp']
    contains_special = any(reg in ori_instr for reg in special_registers)

    if contains_special and random.random() >= 0.05:
        return ori_instr

    instr_parts = rand_instr.split()
    instr_key = instr_parts[0]
    instr_format = INSTRUCTION_FORMATS.get(extension, {}).get(instr_key, {})
    format_str = instr_format.get("format", "")
    variables = instr_format.get("variables", [])

    format_to_instr_map = {}
    format_parts = re.split(r'(\{[^}]*\})', format_str)  
    part_index = 1

    for part in format_parts:
        if part.startswith('{') and part.endswith('}'):
            var_name = part[1:-1]
            if var_name in variables:
                if part_index < len(instr_parts):
                    format_to_instr_map[var_name] = instr_parts[part_index]
                else:
                    format_to_instr_map[var_name] = part
                part_index += 1

    new_parts = {}
    for var in variables:
        if var == 'LABEL':
            new_parts[var] = format_to_instr_map.get(var, "{" + var + "}")
        elif var in variable_range and variable_range[var] is not None:
            new_parts[var] = random.choice(variable_range[var])
        elif var == 'IMM':
            imm = gen_imm('IMM', 12)
            new_parts[var] = str(imm)
        elif 'IMM_' in var:
            imm = gen_imm(var, 1) 
            new_parts[var] = str(imm)
        else:
            new_parts[var] = format_to_instr_map.get(var, "{" + var + "}")

    
    new_instr = format_str
    for var, replacement in new_parts.items():
        new_instr = new_instr.replace("{" + var + "}", replacement)

    return new_instr



def modify_instruction_inc(ori_instr, increase_prob, extension):
   

    extension = extension.upper()
    special_registers = ['ra', 'sp', 'gp', 'tp']
    contains_special = any(reg in ori_instr for reg in special_registers)

    if contains_special and random.random() >= 0.05:
        return ori_instr

    instr_parts = ori_instr.split()
    
    instr_key_index = 1 if ':' in instr_parts[0] else 0
    instr_key = instr_parts[instr_key_index]

    instr_format = INSTRUCTION_FORMATS.get(extension, {}).get(instr_key, {})
    format_str = instr_format.get("format", "")
    variables = instr_format.get("variables", [])
    
    format_to_instr_map = {}
    format_parts = re.split(r'(\{[^}]*\})', format_str) 
    part_index = 1 + instr_key_index 
    for part in format_parts:
        if part.startswith('{') and part.endswith('}'):
            var_name = part[1:-1]
            if var_name in variables:
                
                if part_index < len(instr_parts):
                    
                    if '(' in instr_parts[part_index] and ')' in instr_parts[part_index]:
                        imm_rs1_part = instr_parts[part_index]
                        match_result = re.match(r'([^(]*)\(([^)]+)\)', imm_rs1_part)
                        if match_result:
                            imm, rs1 = match_result.groups()
                           
                            imm = imm if imm else '0'
                        else: 
                            
                            print(f"Unexpected format encountered in instruction: {instr_parts}")
                            
                            imm = '0'
                            rs1 = 'UNDEFINED'  
                        if var_name == variables[0]:  
                            format_to_instr_map[var_name] = imm
                            continue 
                        elif var_name == variables[1]:
                            format_to_instr_map[var_name] = rs1
                    else:
                        format_to_instr_map[var_name] = instr_parts[part_index]
                else:
                    format_to_instr_map[var_name] = None
                part_index += 1


    new_parts = {}
    for var in variables:
            if instr_key in special_instr and var == 'LABEL':
                new_parts[var] = format_to_instr_map.get(var, "{" + var + "}")
            elif var in variable_range and variable_range[var] is not None:
                new_parts[var] = random.choice(variable_range[var])
            elif 'IMM' in var:
                imm = gen_imm(var, 1) 
                new_parts[var] = str(imm)
            else:
                new_parts[var] = format_to_instr_map.get(var, "{" + var + "}")

    new_instr = format_str
    for var, replacement in new_parts.items():
        new_instr = new_instr.replace("{" + var + "}", replacement)

    return new_instr


#TODO If you refer to the historical write data when generating instructions, you can change the following code.
# def modify_instruction_inc(ori_instr, increase_prob, extension):
   

#     extension = extension.upper()

#     special_registers = ['ra', 'sp', 'gp', 'tp']
#     contains_special = any(reg in ori_instr for reg in special_registers)

#     if contains_special and random.random() >= 0.05:
#         return ori_instr

#     instr_parts = ori_instr.split()

#     instr_key_index = 1 if ':' in instr_parts[0] else 0
#     instr_key = instr_parts[instr_key_index]
#     # if ':' in instr_parts[0]:
#     #     instr_key = instr_parts[1]
#     # else:
#     #     instr_key = instr_parts[0]
#     instr_format = INSTRUCTION_FORMATS.get(extension, {}).get(instr_key, {})
#     format_str = instr_format.get("format", "")
#     variables = instr_format.get("variables", [])


#     format_to_instr_map = {}
#     format_parts = re.split(r'(\{[^}]*\})', format_str)  
#     part_index = 1 + instr_key_index

#     for part in format_parts:
#         if part.startswith('{') and part.endswith('}'):
#             var_name = part[1:-1]
#             if var_name in variables:
#                 if part_index < len(instr_parts):
#                     if '(' in instr_parts[part_index] and ')' in instr_parts[part_index]:
#                         imm_rs1_part = instr_parts[part_index]
#                         # repair imm maybe 0 ,so no 0 at ()
#                         # imm, rs1 = re.match(r'([^(]+)\(([^)]+)\)', imm_rs1_part).groups()
#                         match_result = re.match(r'([^(]*)\(([^)]+)\)', imm_rs1_part)
#                         if match_result:
#                             imm, rs1 = match_result.groups()
#                             imm = imm if imm else '0'
#                         else: # Never run
#                           
#                             print(f"Unexpected format encountered in instruction: {instr_parts}")
#             
#                             imm = '0'
#                             rs1 = 'UNDEFINED'  


#                       
#                         if var_name == variables[0]: 
#                             format_to_instr_map[var_name] = imm
#                             continue  
#                         elif var_name == variables[1]:
#                             format_to_instr_map[var_name] = rs1
#                     else:
#                         format_to_instr_map[var_name] = instr_parts[part_index]
#                 else:
#                    
#                     format_to_instr_map[var_name] = None
#                 part_index += 1


#     new_parts = {}
#     for var in variables:
#             if instr_key in special_instr and var == 'LABEL':
#                 new_parts[var] = format_to_instr_map.get(var, "{" + var + "}")
#             elif var in variable_range and variable_range[var] is not None:
#                 new_parts[var] = random.choice(variable_range[var])
#             elif 'IMM' in var:
#                 imm = gen_imm(var, 1)  # 1 作为占位符
#                 new_parts[var] = str(imm)
#             else:
#                 new_parts[var] = format_to_instr_map.get(var, "{" + var + "}")

#     new_instr = format_str
#     for var, replacement in new_parts.items():
#         new_instr = new_instr.replace("{" + var + "}", replacement)


#     # print(f"New parts: {new_parts}")
#     #print(f"2222Generated instruction: {new_instr}")

#     return new_instr
