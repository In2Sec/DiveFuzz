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

from .instr_formats import INSTRUCTION_FORMATS
from math import exp, log

def find_instruction_extension(instruction):
    for extension, instrs in INSTRUCTION_FORMATS.items():
        if instruction in instrs:
            return extension
    return "Unknown"

def compute_geometric_mean(numbers):
    non_zero_numbers = [x for x in numbers if x > 0]
    if not non_zero_numbers:
        return 0
    log_sum = sum(log(x) for x in non_zero_numbers)
    return exp(log_sum / len(non_zero_numbers))  # Use the number of non-zero values as the divisor


def classify_instructions(instruction_freq):
    # Create a new dictionary excluding the "rv_zifencei" extension
    classified_instructions = {
        ext: {'instructions': {instr: 0 for instr in instrs}, 'flag': False}
        for ext, instrs in INSTRUCTION_FORMATS.items()
        if ext != 'ILL'  # Exclude "rv_zifencei"
    }

    classified_instructions["Unknown"] = {'instructions': {}, 'flag': False}

    geometric_means = {} 

    for instr, count in instruction_freq.items():
        extension = find_instruction_extension(instr)
        classified_instructions[extension]['instructions'][instr] = count
        classified_instructions[extension]['flag'] = True

    increase_queue = []
    decrease_queue = []
    missing_ext    = []
    for extension in classified_instructions:
        
        sorted_instrs = sorted(classified_instructions[extension]['instructions'].items(), key=lambda x: x[1], reverse=True)
        classified_instructions[extension]['instructions'] = dict(sorted_instrs)


    for extension, data in classified_instructions.items():
        if data['flag']:
            counts = data['instructions'].values()
            geometric_mean = compute_geometric_mean(counts)
            # For printing the geometric mean of each extension, for debugging purposes
            geometric_means[extension] = geometric_mean

            for instr, count in data['instructions'].items():
                if count > geometric_mean:
                    decrease_queue.append(instr)
                elif count < geometric_mean:
                    increase_queue.append(instr)
        else:
            missing_ext.extend(data['instructions'].keys())
    # Next, process the instructions that have not appeared before
    for extension, instrs in INSTRUCTION_FORMATS.items():

        for instr in instrs:
            if instr not in increase_queue and instr not in decrease_queue:
                # Extensions that have not appeared, used for experiments !
                missing_ext.append(instr)


    return increase_queue, decrease_queue, classified_instructions, geometric_means, missing_ext
