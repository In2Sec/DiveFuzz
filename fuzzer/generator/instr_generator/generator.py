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
from .config import special_instr
from .formats import INSTRUCTION_FORMATS
from .sets import INSTRUCTION_SETS
from .variables import variable_range
from .memory_manager import MemoryAccessManager
from ..bug_filter import bug_filter

def gen_imm(imm_type, length):
    """
    Generates a hexadecimal immediate value based on the specified type and bit length.
    Supports formats like 'IMM_x_y', where x is the bit length and y is a multiple requirement.
    Additionally, there is a 10% chance to generate extreme or special values.

    :param imm_type: The type of immediate value ('IMM_x', 'UNIMM_x', 'IMM_x_y' etc.).
    :param length: Bit length of the immediate value. Ignored if 'IMM_x' or 'IMM_x_y' format is used.
    :return: Generated hexadecimal immediate value.
    """
    # Extract bit length and type from imm_type if it's in the IMM_x or UNIMM_x format
    multiple = 0
    imm = -1
    match = re.match(r'(IMM|NZIMM|NZUIMM|UIMM|ZIMM)(?:_(\d+)(?:_(\d+))?)?', imm_type)
    if match:
        imm_type = match.group(1)
        length = int(match.group(2)) if match.group(2) else 12 # Default 12-bit immediate value
        # Used for aes64ks1i instructions
        # if int(match.group(3)) == 104:
        #     return hex(random.randint(0x0, 0xA))
        # else:
        #multiple = int(match.group(3)) if match.group(3) else 0 # How many bytes must be aligned
        if match.group(3):
            if int(match.group(3)) == 104:
                return hex(random.randint(0x0, 0xA))
            else:
                multiple = int(match.group(3))
        else:
            multiple = 0

    if length is None:
        raise ValueError("Bit length must be specified")
    if imm_type in ['IMM', 'NZIMM']:
        min_value = -2 ** (length - 1)
        max_value = 2 ** (length - 1) - 1
    elif imm_type in ['UIMM', 'NZUIMM', 'ZIMM']:
        min_value = 1 if imm_type == 'NZUIMM' else 0
        max_value = 2 ** length - 1
    else:
        print(imm_type)
        raise ValueError("Unsupported immediate type")
    special_values = [min_value, max_value, 1]
    if imm_type in ['IMM']:
        special_values.append(0)
        special_values.append(-1)
    elif imm_type in ['NZIMM']:
        special_values.append(-1)
    elif imm_type in ['UIMM', 'ZIMM']:
        special_values.append(0)

    # 10% chance to generate extreme or special values
    if random.random() < 0.5 and not multiple:
        imm = random.choice(special_values)
    else:
        if multiple:
            # Adjust range for the multiple requirement
            min_value = (min_value + multiple - 1) // multiple * multiple
            max_value = max_value // multiple * multiple
            if imm_type in ['IMM', 'NZIMM', 'UIMM', 'NZUIMM', 'ZIMM']:
                imm = random.randint(min_value // multiple, max_value // multiple) * multiple
                if imm_type in ['NZIMM', 'NZUIMM', 'ZIMM'] and imm == 0:
                    imm = multiple
        else:
            if imm_type in ['IMM', 'NZIMM', 'UIMM', 'NZUIMM', 'ZIMM']:
                imm = random.randint(min_value, max_value)
                if imm_type in ['NZIMM', 'NZUIMM', 'ZIMM'] and imm == 0:
                    while imm == 0:
                        imm = random.randint(min_value, max_value)
            else:
                raise ValueError("Unsupported immediate type")
    # Convert to hexadecimal format, but there are problems with expressing negative numbers, so ignore it for now
    hex_format = '0x{0:0{1}X}'.format(imm, length // 4 if length % 4 == 0 else length // 4 + 1)

    return imm

# TODO
def generate_random_v_instruction():
    """
    Generates a random v instruction in assembly format.
    Returns:
        str: A randomly generated v instruction.
    """
    
    return None


def get_instruction_type(instruction):
    for instr_type, instr_list in INSTRUCTION_SETS.items():
        if instruction in instr_list:
            return instr_type
    return "Unknown"

def get_instruction_format(instruction):
    instr_type = get_instruction_type(instruction)
    return INSTRUCTION_FORMATS.get(instr_type.upper(), {}).get(instruction, {})


def _generate_memop_offset(instr_name, var, category):
    """
    Generate safe offset for load/store instructions.

    Args:
        instr_name: Name of the instruction (e.g., 'lw', 'sw', 'c.lwsp')
        var: Variable name (e.g., 'IMM_12', 'UIMM_8_4')
        category: Instruction category list

    Returns:
        String representation of the safe offset value
    """
    if 'LOAD' in category or 'STORE' in category or \
       'FLOAT_LOAD' in category or 'FLOAT_STORE' in category:
        # T6-based load/store: generate safe offset for IMM_12
        if var == 'IMM_12':
            imm = MemoryAccessManager.get_safe_offset_for_t6(instr_name)
            return str(imm)
        else:
            # Other immediate types (shouldn't happen for standard load/store)
            # Fall back to normal generation
            return None
    else:
        # Not a memory operation
        return None


def generate_new_instr(new_instr_op, extension, rd_history, rs_history,\
                         frd_history, frs_history):
    #extension = extension.upper()

    special_registers = ['ra', 'sp', 'gp', 'tp']

    instr_format = INSTRUCTION_FORMATS.get(extension, {}).get(new_instr_op, {})
    format_str = instr_format.get("format", "")
    variables = instr_format.get("variables", [])
    # ...

    instr_format = INSTRUCTION_FORMATS.get(extension, {}).get(new_instr_op, {})
    format_str = instr_format.get("format", "")
    variables = instr_format.get("variables", [])
    # ...

    # Parse the format string and create a mapping
    format_to_instr_map = {}
    format_parts = re.split(r'(\{[^}]*\})', format_str)  # Use regular expressions to split the string correctly

    part_index = 1

    for part in format_parts:
        if part.startswith('{') and part.endswith('}'):
            var_name = part[1:-1]
            if var_name in variables:
                if part_index < len(new_instr_op):
                    format_to_instr_map[var_name] = new_instr_op[part_index]
                else:
                    format_to_instr_map[var_name] = part
                part_index += 1

    prob_adjust = 0.8
    new_parts = {}
    for var in variables:
        if var == 'LABEL':
            # Always keep LABEL as placeholder for later replacement by label_manager
            # This handles all jump/branch instructions uniformly
            new_parts[var] = "{" + var + "}"
        elif var in variable_range and variable_range[var] is not None:
            # Randomly select one first and make a judgment later
            new_parts[var] = random.choice(variable_range[var])
            # Make sliding windows of RD and RS
            # When RD is used as the destination register, the historical RD should be considered. 
            # 80% of the time, it is selected outside the historical RD, and 80% of the time, it is to avoid starvation register.
            if 'RD' in var:
                if 'FRD' in var:
                    temp_frd = new_parts[var]
                    if temp_frd in frd_history.get_history() and random.random() < prob_adjust:
                        available_frd = [frd for frd in variable_range[var] if frd not in frd_history.get_history()]
                        if available_frd:
                            new_frd = random.choice(available_frd)
                            new_parts[var] = new_frd
                    # else:
                    #     new_parts[var]
                    frd_history.use_register(new_parts[var])
                # RD
                else:
                    temp_rd = new_parts[var]
                    if temp_rd in rd_history.get_history() and random.random() < prob_adjust:
                        available_rd = [rd for rd in variable_range[var] if rd not in rd_history.get_history()]
                        if available_rd:
                            new_rd = random.choice(available_rd)
                            new_parts[var] = new_rd
                    rd_history.use_register(new_parts[var])
            # When choosing RS, try to choose in RD to make WAW, RAW, etc.
            elif 'FRS' in var:
                temp_frs = new_parts[var]
                    # 80% probability of using the nearest FRD register, RAW()
                if random.random() < prob_adjust:
                    available_frs = [frs for frs in variable_range[var] if frs in frd_history.get_history()]
                    if available_frs:
                        new_frs = random.choice(available_frs)
                        new_parts[var] = new_frs
                frs_history.use_register(new_parts[var])
            elif 'RS' in var:
                temp_rs = new_parts[var]
                    # 80% probability of using the nearest FRD register, RAW()
                if random.random() < prob_adjust:
                    available_rs = [rs for rs in variable_range[var] if rs in rd_history.get_history()]
                    if available_rs:
                        new_rs = random.choice(available_rs)
                        new_parts[var] = new_rs
                rs_history.use_register(new_parts[var])
            else:
                # Other special circumstances
                # For CSR, apply blacklist filtering and avoid SATP
                if var == 'CSR':
                    # Filter CSR blacklist
                    csr_blacklist = bug_filter.get_csr_blacklist()
                    available_csrs = [csr for csr in variable_range[var]
                                      if csr.lower() not in csr_blacklist]
                    if not available_csrs:
                        # Fallback to original range if all are blacklisted
                        available_csrs = variable_range[var]
                    new_parts[var] = random.choice(available_csrs)
                    # Also try not to choose SATP (1.7% probability)
                    if 'satp' in new_parts[var]:
                        new_parts[var] = random.choice(available_csrs)
                else:
                    new_parts[var] = random.choice(variable_range[var])

        elif 'IMM' in var or 'UIMM' in var:
            # Check if this is a load/store instruction that needs safe offset
            category = instr_format.get('category', [])
            memop_offset = _generate_memop_offset(new_instr_op, var, category)

            if memop_offset is not None:
                # Load/store instruction: use safe offset
                new_parts[var] = memop_offset
            else:
                # Other instructions: use original immediate generation
                # DEBUG: Print var before calling gen_imm to trace SPUIMM issue
                if 'SP' in var and 'UIMM' in var:
                    print(f"DEBUG: Calling gen_imm with suspicious var='{var}' for instr={new_instr_op}")
                    print(f"DEBUG: format_str='{format_str}', variables={variables}")
                imm = gen_imm(var, 1)
                new_parts[var] = str(imm)
        else:
            new_parts[var] = format_to_instr_map.get(var, "{" + var + "}")


    new_instr = format_str
    for var, replacement in new_parts.items():
        new_instr = new_instr.replace("{" + var + "}", replacement)



# FOR CVA6 TEST
    # To avoid some spec different cva6 and spike ,
    # spike forbidden write senvcfg and scounteren
    if 'senvcfg' in new_instr or 'scounteren' in new_instr:

        parts = new_instr.split(' ')
        parts[1] = 'zero,'
        new_instr = ' '.join(parts)


    return new_instr


def generate_instruction_probabilities(instruction_usage, probabilities, allowed_ext, special_probabilities):
    total_usage = sum(instruction_usage.values())
    if total_usage == 0:
        return probabilities  # If no instruction is used, keep the probability unchanged

    # Update probabilities: Convert instruction usage frequencies into a probability distribution
    new_probabilities = []
    for ext in allowed_ext:
        if ext in special_probabilities:  # If the instruction has a specific probability, do not update it.
            new_probabilities.append(special_probabilities[ext])
        else:
            # Distribute the remaining probability.
            usage_prob = instruction_usage.get(ext, 0) / total_usage
            new_probabilities.append(usage_prob)

    # Normalize the probabilities to ensure they sum to 1.
    sum_probs = sum(new_probabilities)
    normalized_probabilities = [prob / sum_probs for prob in new_probabilities]
    return normalized_probabilities
