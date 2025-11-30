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
import re
import random
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from ...asm_template_manager import create_template_instance, TemplateInstance
from ...asm_template_manager.riscv_asm_syntex import ArchConfig
from ...asm_template_manager.ext_list import allowed_ext
from ...instr_generator import (
    INSTRUCTION_FORMATS,
    special_instr,
    rv32_not_support_instr,
    rv32_not_support_csrs,
    # generate_random_v_instruction,
    get_instruction_format,
    generate_new_instr,
    reg_range
)
from ...reg_analyzer import temp_asm_to_debug_generate
from ...utils import list2str
from .register_history import RegisterHistory
from ...instr_generator.label_manager import LabelManager
from ...config.config_manager import MAX_MUTATE_TIME
def generate_instructions(instr_number: int,
                          seed_times: int,
                          eliminate_enable: bool = True,
                          is_cva6: bool = False,
                          is_rv32: bool = False,
                          arch: ArchConfig = None):
    """
    Generate random RISC-V instructions for a single seed.

    Args:
        instr_number: Number of instructions to generate
        seed_times: Seed index (used for filename)
        eliminate_enable: Enable conflict elimination via Spike
        is_cva6: Target CVA6 processor
        is_rv32: Use RV32 architecture
        arch: Architecture configuration for template creation
    """
    # Create fresh template instance for this seed with random type and values
    # This ensures each seed gets independent random content (CSR, register init, etc.)
    template = create_template_instance(arch)

    # Calculate the total of explicitly assigned probabilities
    total_specified_prob = sum(allowed_ext.special_probabilities.values())
    remaining_prob = 1 - total_specified_prob 
    remaining_ext_count = len(allowed_ext.allowed_ext) - len(allowed_ext.special_probabilities)
    default_prob_for_remaining = remaining_prob / (remaining_ext_count )
    # Build a probability list for all extensions
    probabilities = [
        allowed_ext.special_probabilities.get(ext, default_prob_for_remaining) for ext in allowed_ext.allowed_ext
    ]
    # Normalize to ensure the sum of probabilities equals 1
    probabilities = [float(i)/sum(probabilities) for i in probabilities]
    # RU: RD、RS、FRD、FRS
    rd_history = RegisterHistory()
    rs_history = RegisterHistory()
    frd_history = RegisterHistory()
    frs_history = RegisterHistory()
    entire_instrs = []
    instrs_filter = []

    # Initialize LabelManager for jump/branch instruction generation
    label_mgr = LabelManager()
    # Randomly select a template
    file_name = "seeds_{}_.S".format(seed_times)
    current_dir = Path.cwd()
    new_directory = current_dir / 'out-seeds'

    new_filename = os.path.join(new_directory, os.path.basename(file_name))
    
    resolve_duplicates = 0
    resolve_duplicates_fail = 0
    c_instr_consecutive_number = 0
    c_extension = [ "RV64_C", "RV_C"]
    
    #### V ext enable:
    if "RV_V" in allowed_ext.allowed_ext:
        # print(111)
        v_ext_enable = True
    else:
        v_ext_enable = False

    if v_ext_enable:
        # v_instr_init
        entire_instrs.append(v_instr_init)
    # TO rv32
    for i in range(instr_number):
        is_c_extension = False

        # Unified extension selection based on configuration and probabilities
        extension = np.random.choice(allowed_ext.allowed_ext, p=probabilities)

        if extension == 'RV64_C' or extension == 'RV_C':
            c_instr_consecutive_number += 1
            is_c_extension = True
        elif c_instr_consecutive_number %2 != 0:
            extension = random.choice(c_extension)
            c_instr_consecutive_number += 1

        # Increase the jump distance limit; if it's the last instruction, a label should be added forcibly.
        if i == instr_number - 1 and label_mgr.is_jump_active():
            jump_type = label_mgr.get_jump_type()

            if jump_type == 'forward':
                # Forward jump: insert label definition at target position
                label_name = label_mgr.get_current_label()
                entire_instrs.append(f'{label_name}:')
            elif jump_type == 'backward':
                # Backward jump: insert loop control instructions
                jump_instr = label_mgr.get_jump_instruction()  # "addi t0, t0, -1\nbnez t0, bwd_0"
                counter_reg = label_mgr.get_loop_counter_reg()  # "t0"

                # Add loop control instructions
                if '\n' in jump_instr:
                    for line in jump_instr.split('\n'):
                        entire_instrs.append(line)
                else:
                    entire_instrs.append(jump_instr)

                # Update RegisterHistory for loop counter
                # addi t0, t0, -1: reads and writes the counter register
                if counter_reg:
                    rs_history.use_register(counter_reg)  # addi reads counter_reg
                    rd_history.use_register(counter_reg)  # addi writes counter_reg

            label_mgr.end_jump_sequence()
            continue
        
        complete_instr = 'nop'
        if  extension == "ILL":
            instrs_complete = INSTRUCTION_FORMATS[extension]
            instrs = list(instrs_complete.keys())
            instr = random.choice(instrs)
            complete_instr = generate_new_instr(instr, extension, rd_history, rs_history, \
                                            frd_history,frs_history)

        else:
            try: 
                instrs_complete = INSTRUCTION_FORMATS[extension]
                instrs = list(instrs_complete.keys())

                # Filter instructions based on current state
                # If jump sequence is active: exclude jump/branch to avoid nesting
                # Otherwise: allow all instructions (natural probability)
                if label_mgr.is_jump_active():
                    # During active jump sequence: only exclude jump/branch instructions to avoid nesting
                    instrs_filter =[instr for instr in instrs if 'LABEL' not in get_instruction_format(instr).get('variables', []) \
                                                            and 'JUMP' not in get_instruction_format(instr).get('category', [])\
                                                            and 'BRANCH' not in get_instruction_format(instr).get('category', [])\
                                                            and not instr.startswith('c.')]
                else:
                    # Filter out compressed instructions (starting with 'c.') because main section uses .option norvc
                    instrs_filter =[instr for instr in instrs if not instr.startswith('c.')]
                if instrs_filter:
                    instr = random.choice(instrs_filter)
                else:
                    continue

                if is_rv32:
                    while instr in special_instr or instr in rv32_not_support_instr:
                        instr = random.choice(instrs_filter)
                else:
                    # twice filter insters
                    while instr in special_instr:
                        instr = random.choice(instrs_filter)
                        
                
                # Jump instruction handling: detect if this is a jump/branch instruction
                is_direct_jump = instr in ['jal', 'beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu', 'c.j',\
                                              'c.beqz', 'c.bnez', 'c.jal']
                is_indirect_jump = instr in ['jalr', 'c.jr', 'c.jalr']
                
                if is_direct_jump:
                    # The last instruction cannot be a jump instruction because there are no subsequent labels.
                    if i == instr_number - 1:
                        continue
                    # Check if backward jump is possible

                    # 50% probability to generate backward jump if possible
                    if (instr == 'bne') and random.random() < 0.5:
                        # === BACKWARD LOOP WITH FIXED COUNTER (s11) ===
                        # Use fixed register s11 as loop counter (rarely used, avoids conflicts)
                        counter_reg = 's11'

                        # 1. Generate loop iterations (1-8 times)
                        loop_iterations = random.randint(1, 8)

                        # 2. Generate backward label
                        label = label_mgr.generate_backward_label()

                        # 3. Target distance: number of instructions in loop body (3-8)
                        # Similar to forward jump
                        target_distance = random.randint(3, 8)

                        # 4. Append initialization instruction and label to end of entire_instrs
                        # This ensures only newly generated instructions become part of loop body,
                        # avoiding the issue where existing instructions might modify the counter
                        entire_instrs.append(f'li {counter_reg}, {loop_iterations}')
                        entire_instrs.append(f'{label}:')

                        # 5. Construct loop control instructions (decrement + conditional jump)
                        # Use bne (branch if not equal) to check counter against zero
                        loop_control = f'addi {counter_reg}, {counter_reg}, -1\nbne {counter_reg}, zero, {label}'

                        # 6. Update register history (initialization instruction)
                        rd_history.use_register(counter_reg)

                        # 7. Start backward jump sequence with loop counter info
                        label_mgr.start_jump_sequence('backward', label, target_distance, loop_control,
                                                     loop_counter_reg=counter_reg)
                        continue
                    else:
                        # === FORWARD DIRECT JUMP ===
                        # Generate direct jump/branch instruction with {LABEL} placeholder
                        # generate_new_instr will output instruction with {LABEL} placeholder (e.g., "beq a0, a1, {LABEL}")
                        label = label_mgr.generate_forward_label()
                        target_distance = random.randint(3, 8)  
                        complete_instr = generate_new_instr(instr, extension, rd_history, rs_history, \
                                                                frd_history,frs_history)
                        label_mgr.start_jump_sequence('forward', label, target_distance, complete_instr)


                        complete_instr = complete_instr.replace('{LABEL}', label)
                        entire_instrs.append(complete_instr)
                        continue

                elif is_indirect_jump:

                    if i == instr_number - 1:
                        continue
                    # === FORWARD INDIRECT JUMP ONLY ===
                    # Note: Backward indirect jump removed for simplicity
                    # Loops typically use direct jumps, not indirect jumps

                    label = label_mgr.generate_forward_label()
                    target_distance = random.randint(3, 8)


                    safe_regs = [r for r in reg_range if r not in ['zero', 'sp', 'gp', 'tp']]
                    chosen_reg = random.choice(safe_regs) if safe_regs else random.choice(reg_range)


                    if instr == 'jalr':
                        rd = random.choice(reg_range)
                        complete_instr = f'jalr {rd}, 0({chosen_reg})'

                        rd_history.use_register(rd)
                    elif instr == 'c.jr':
                        complete_instr = f'c.jr {chosen_reg}'
                    elif instr == 'c.jalr':
                        complete_instr = f'c.jalr {chosen_reg}'

                    rs_history.use_register(chosen_reg)
                    label_mgr.start_jump_sequence('forward', label, target_distance, complete_instr)

                    # Generate: la reg, label; jalr/c.jr/c.jalr reg
                    entire_instrs.append(f'la {chosen_reg}, {label}')
                    entire_instrs.append(complete_instr)
                    continue

                elif label_mgr.is_jump_active():
                    label_mgr.increment_distance()
                    # Increase the jump distance limit; if it's the last instruction, a label should be added forcibly.
                    if label_mgr.should_finalize_jump() or i == instr_number - 1:
                        jump_type = label_mgr.get_jump_type()

                        if jump_type == 'forward':
                            label_name = label_mgr.get_current_label()
                            entire_instrs.append(f'{label_name}:')
                        elif jump_type == 'backward':
                            jump_instr = label_mgr.get_jump_instruction()  # "addi t0, t0, -1\nbnez t0, bwd_0"
                            counter_reg = label_mgr.get_loop_counter_reg()  # "t0"

                            # Add loop control instructions
                            if '\n' in jump_instr:
                                for line in jump_instr.split('\n'):
                                    entire_instrs.append(line)
                            else:
                                entire_instrs.append(jump_instr)

                            if counter_reg:
                                rs_history.use_register(counter_reg)  # addi reads counter_reg
                                rd_history.use_register(counter_reg)  # addi writes counter_reg

                        label_mgr.end_jump_sequence()
                max_w = 2
                # TODO Currently does not support spike debug for vector instructions (vec)
                if eliminate_enable and extension != 'RV_V':
                    with ThreadPoolExecutor(max_workers = max_w) as executor:
                                is_diff_rs = 0
                                mutate_time = 0
                                while is_diff_rs == 0 and mutate_time < MAX_MUTATE_TIME:
                                    # Note: If the temp_asm_to_debug function directly modifies updated_content,
                                    # be aware of thread safety issues
                                    if is_rv32:
                                        while True:
                                            complete_instr = generate_new_instr(instr, extension, rd_history, rs_history, \
                                                            frd_history,frs_history)
                                            if (not any(rv32_not_support_csr in complete_instr for rv32_not_support_csr in rv32_not_support_csrs)) and ("minstret" not in complete_instr):
                                                break
                                        
                                        # Check backward loop protection before Spike verification
                                        if label_mgr.is_jump_active() and label_mgr.get_jump_type() == 'backward':
                                            counter_reg = label_mgr.get_loop_counter_reg()
                                            instr_parts = complete_instr.split()
                                            if len(instr_parts) >= 2 and instr_parts[1].rstrip(',') == counter_reg:
                                                mutate_time += 1
                                                continue  # Regenerate instruction without Spike verification

                                        future = executor.submit(
                                            temp_asm_to_debug_generate,
                                            tuple(entire_instrs),
                                            complete_instr,
                                            True,
                                            label_mgr.get_current_label(),
                                            template
                                        )
                                        # Wait for thread tasks to complete and retrieve the results
                                        is_diff_rs = future.result()

                                        mutate_time += 1
                                        if is_diff_rs == 3:
                                            continue
                                        elif is_diff_rs == 1:
                                            break

                                    else:
                                        complete_instr = generate_new_instr(instr, extension, rd_history, rs_history, \
                                                            frd_history,frs_history)

                                        
                                        if label_mgr.is_jump_active() and label_mgr.get_jump_type() == 'backward':
                                            counter_reg = label_mgr.get_loop_counter_reg()
                                            instr_parts = complete_instr.split()
                                            if len(instr_parts) >= 2 and instr_parts[1].rstrip(',') == counter_reg:
                                                mutate_time += 1
                                                continue  

                                        future = executor.submit(
                                            temp_asm_to_debug_generate,
                                            tuple(entire_instrs),
                                            complete_instr,
                                            True,
                                            label_mgr.get_current_label(),
                                            template
                                        )

                                        is_diff_rs = future.result()

                                        mutate_time += 1
                                        if is_diff_rs == 3:
                                            continue
                                        elif is_diff_rs == 1:
                                            break
                                
                                if mutate_time >= MAX_MUTATE_TIME:
                                    resolve_duplicates_fail += 1
                                else:
                                    resolve_duplicates += 1
                else:
                    if is_rv32:
                        while True:
                            complete_instr = generate_new_instr(instr, extension, rd_history, rs_history, \
                                                        frd_history,frs_history)
                            if (not any(rv32_not_support_csr in complete_instr for rv32_not_support_csr in rv32_not_support_csrs)) and ("minstret" not in complete_instr):
                                break
                    else:
                        complete_instr = generate_new_instr(instr, extension, rd_history, rs_history, \
                                                        frd_history,frs_history)

                        if extension == 'RV_V':

                            if complete_instr.endswith(", "):
                                complete_instr = complete_instr[:-2]

                            if complete_instr.endswith(", "):
                                complete_instr = complete_instr[:-2]

                            while ", ," in complete_instr:
                                complete_instr = complete_instr.replace(", ,", ",")
            except IndexError as e:
                complete_instr = 'nop'
                pass

        entire_instrs.append(complete_instr)
    
    write_instructions_to_file(new_filename, list2str(entire_instrs), template)

    return resolve_duplicates, resolve_duplicates_fail


def write_instructions_to_file(new_filename: str, instructions: str, template: TemplateInstance):
    """
    Write instructions to file with template wrapper.

    Args:
        new_filename: Output file path
        instructions: Generated instruction sequence
        template: Template instance to wrap instructions
    """
    lines = template.get_complete_template(instructions)

    os.makedirs(os.path.dirname(new_filename), exist_ok=True)

    with open(new_filename, 'w') as file:
        file.writelines(lines)
        
def generate_instr_wrapper(args):
    # A simple wrapper function that allows generate_instr to accept a tuple as an argument

    return generate_instructions(*args)
