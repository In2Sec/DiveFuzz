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
from typing import List
from ...asm_template_manager import create_template_instance, TemplateInstance, temp_file_manager
from ...asm_template_manager.riscv_asm_syntex import ArchConfig
from ...asm_template_manager.ext_list import allowed_ext
from ...instr_generator import (
    INSTRUCTION_FORMATS,
    special_instr,
    rv32_not_support_instr,
    rv32_not_support_csrs,
    # generate_random_vsetvli_instruction,
    get_instruction_format,
    generate_new_instr,
    reg_range
)
from ...reg_analyzer.nop_template_gen import generate_nop_elf
from ...reg_analyzer.spike_session import SpikeSession, SPIKE_ENGINE_AVAILABLE
from ...reg_analyzer.instruction_validator import InstructionValidator
from ...reg_analyzer.instruction_post_processor import InstructionPostProcessor
from ...reg_analyzer.hybrid_encoder import HybridEncoder
from ...reg_analyzer.jump_sequence_compiler import JumpSequenceCompiler
from ...utils import list2str
from .register_history import RegisterHistory
from ...instr_generator.label_manager import LabelManager
from ...config.config_manager import MAX_MUTATE_TIME


def generate_forward_jump_instrs(
    jump_instr: str,
    target_distance: int,
    extension: str,
    rd_history,
    rs_history,
    frd_history,
    frs_history,
    is_rv32: bool,
    instrs_filter: list,
    probabilities: list,
    allowed_extensions: list
) -> List[str]:
    """
    Generate middle instructions for forward jump sequence.

    Returns list of assembly instruction strings (without jump/branch).
    """
    middle_instrs = []

    for _ in range(target_distance):
        # Select extension
        ext = np.random.choice(allowed_extensions, p=probabilities)

        # Get instruction list for this extension
        if ext not in INSTRUCTION_FORMATS:
            continue

        instrs_complete = INSTRUCTION_FORMATS[ext]
        instrs = list(instrs_complete.keys())

        # Filter out jumps, branches, and compressed instructions
        filtered = [instr for instr in instrs
                   if 'LABEL' not in get_instruction_format(instr).get('variables', [])
                   and 'JUMP' not in get_instruction_format(instr).get('category', [])
                   and 'BRANCH' not in get_instruction_format(instr).get('category', [])
                   and not instr.startswith('c.')
                   and instr not in special_instr]

        if not filtered:
            continue

        instr = random.choice(filtered)

        # Filter for RV32
        if is_rv32:
            while instr in rv32_not_support_instr and filtered:
                filtered.remove(instr)
                if filtered:
                    instr = random.choice(filtered)
                else:
                    break

        if filtered:
            complete_instr = generate_new_instr(instr, ext, rd_history, rs_history,
                                               frd_history, frs_history)
            middle_instrs.append(complete_instr)

    return middle_instrs


def generate_loop_body_instrs(
    target_distance: int,
    counter_reg: str,
    rd_history,
    rs_history,
    frd_history,
    frs_history,
    is_rv32: bool,
    probabilities: list,
    allowed_extensions: list
) -> List[str]:
    """
    Generate loop body instructions (excluding counter register modifications).

    Returns list of assembly instruction strings.
    """
    loop_body = []

    for _ in range(target_distance):
        # Select extension
        ext = np.random.choice(allowed_extensions, p=probabilities)

        if ext not in INSTRUCTION_FORMATS:
            continue

        instrs_complete = INSTRUCTION_FORMATS[ext]
        instrs = list(instrs_complete.keys())

        # Filter out jumps, branches, compressed instructions
        filtered = [instr for instr in instrs
                   if 'LABEL' not in get_instruction_format(instr).get('variables', [])
                   and 'JUMP' not in get_instruction_format(instr).get('category', [])
                   and 'BRANCH' not in get_instruction_format(instr).get('category', [])
                   and not instr.startswith('c.')
                   and instr not in special_instr]

        if not filtered:
            continue

        instr = random.choice(filtered)

        if is_rv32:
            while instr in rv32_not_support_instr and filtered:
                filtered.remove(instr)
                if filtered:
                    instr = random.choice(filtered)
                else:
                    break

        if not filtered:
            continue

        # Generate instruction and check if it modifies counter register
        max_attempts = 5
        for _ in range(max_attempts):
            complete_instr = generate_new_instr(instr, ext, rd_history, rs_history,
                                               frd_history, frs_history)
            # Check if instruction writes to counter register
            instr_parts = complete_instr.split()
            if len(instr_parts) >= 2:
                dest_reg = instr_parts[1].rstrip(',')
                if dest_reg == counter_reg:
                    continue  # Retry with different operands
            loop_body.append(complete_instr)
            break

    return loop_body


def generate_instructions(instr_number: int,
                          seed_times: int,
                          eliminate_enable: bool,
                          is_cva6: bool,
                          is_rv32: bool,
                          arch: ArchConfig,
                          template_type: str,
                          out_dir: str,
                          shared_xor_cache,
                          architecture: str):
    """
    Generate random RISC-V instructions for a single seed.

    Args:
        instr_number: Number of instructions to generate
        seed_times: Seed index (used for filename)
        eliminate_enable: Enable conflict elimination via Spike
        is_cva6: Target CVA6 processor
        is_rv32: Use RV32 architecture
        arch: Architecture configuration for template creation
        template_type: Template type name
        out_dir: Output directory for seeds and XOR cache
        shared_xor_cache: Manager.dict for cross-process XOR sharing
        architecture: Architecture for bug filtering ('xs', 'nts', 'rkt', 'kmh')
    """

    # Create fresh template instance for this seed with random type and values
    # This ensures each seed gets independent random content (MSTATUS, register init, etc.)
    template = create_template_instance(arch, template_type)

    try:
        # Initialize Spike session for eliminate mode (checkpoint-based validation)
        spike_session = None
        validator = None
        post_processor = None
        if eliminate_enable and SPIKE_ENGINE_AVAILABLE:
            try:
                # Generate NOP ELF template
                elf_path = f"/dev/shm/template_{seed_times}_{instr_number}.elf"
                elf_path = generate_nop_elf(template, instr_number, elf_path)

                # Create SpikeSession (decoupled from XOR logic)
                spike_session = SpikeSession(
                    elf_path,
                    template.isa,
                    instr_number
                )
                if spike_session.initialize():
                    # Create post processor for XOR computation and bug filtering
                    # This handles cross-process XOR sharing and bug pattern matching
                    post_processor = InstructionPostProcessor(
                        shared_xor_cache,
                        architecture
                    )

                    # Create validator with spike_session and post_processor
                    encoder = HybridEncoder(quiet=True)
                    validator = InstructionValidator(spike_session, post_processor, encoder)
                    # print(f"[Seed {seed_times}] Using checkpoint-based validation")
                    # Create jump sequence compiler for handling jump instructions
                    jump_compiler = JumpSequenceCompiler(encoder.encoder)

                    # Enable debug output if DEBUG_SPIKE_ENGINE environment variable is set
                    # Values:
                    #   - "1" or "all": Log all instructions (ACCEPTED and REJECTED)
                    #   - "accepted": Log only ACCEPTED instructions
                    import os
                    debug_mode = os.environ.get('DEBUG_SPIKE_ENGINE', '').lower()
                    if debug_mode:
                        debug_file = os.path.join(out_dir, f"spike_engine_debug_{seed_times}.txt")
                        accepted_only = (debug_mode == 'accepted')
                        InstructionValidator.enable_debug_output(debug_file, accepted_only=accepted_only)
                        mode_str = "ACCEPTED only" if accepted_only else "ALL"
                        print(f"[Seed {seed_times}] Debug output enabled ({mode_str}): {debug_file}")
                else:
                    print(f"[Seed {seed_times}] Spike initialization failed")
                    spike_session = None
                    validator = None
                    post_processor = None
                    jump_compiler = None
                    return 0, 0
            except Exception as e:
                print(f"[Seed {seed_times}] Failed to initialize Spike session: {e}")
                spike_session = None
                validator = None
                post_processor = None
                jump_compiler = None
                return 0, 0
        else:
            # Non-eliminate mode: still create jump_compiler for offset calculation
            try:
                from ...reg_analyzer.instruction_encoder import InstructionEncoder
                jump_compiler = JumpSequenceCompiler(InstructionEncoder())
            except Exception:
                jump_compiler = None

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
        # Use provided out_dir instead of hardcoded path
        new_directory = Path(out_dir)

        new_filename = os.path.join(new_directory, os.path.basename(file_name))
        # TODO: Currently only one mode is supported, more will be added later  
        # TODO: Add directory for DUT input
        # template_path = current_dir / 'template/xiangshan'
        # all_template_files = [f for f in os.listdir(template_path) if f.endswith('.S')]
        # # Randomly select one from the templates
        # template_file = os.path.join(template_path, random.choice(all_template_files)) if all_template_files else None
    
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

            # Note: Jump sequences are now generated atomically, so we don't need to
            # check for incomplete jump sequences at the end of the loop

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

                    instrs_filter = [instr for instr in instrs if not instr.startswith('c.')]
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

                        # 50% probability to generate backward loop if bne instruction
                        if (instr == 'bne') and random.random() < 0.5:
                            # === BACKWARD LOOP WITH FIXED COUNTER (s11) ===
                            counter_reg = 's11'
                            loop_iterations = random.randint(1, 8)
                            label = label_mgr.generate_backward_label()
                            target_distance = random.randint(3, 8)

                            # Generate loop body instructions
                            loop_body = generate_loop_body_instrs(
                                target_distance, counter_reg,
                                rd_history, rs_history, frd_history, frs_history,
                                is_rv32, probabilities, allowed_ext.allowed_ext
                            )

                            # Construct loop components
                            init_instr = f'li {counter_reg}, {loop_iterations}'
                            decr_instr = f'addi {counter_reg}, {counter_reg}, -1'
                            branch_instr = f'bne {counter_reg}, zero, {{LABEL}}'

                            # If jump_compiler and spike_session are available, compile and execute
                            if jump_compiler is not None and spike_session is not None:
                                try:
                                    loop_seq = jump_compiler.compile_backward_loop(
                                        init_instr, loop_body, decr_instr, branch_instr, label
                                    )
                                    # Get machine codes and sizes for execution
                                    codes_and_sizes = jump_compiler.get_machine_codes(loop_seq)
                                    if codes_and_sizes:
                                        # Extract init, body, decr, branch parts
                                        init_code, init_size = codes_and_sizes[0]
                                        body_codes = [c for c, s in codes_and_sizes[1:-2]]
                                        body_sizes = [s for c, s in codes_and_sizes[1:-2]]
                                        decr_code, decr_size = codes_and_sizes[-2]
                                        branch_code, branch_size = codes_and_sizes[-1]

                                        # Execute the loop sequence
                                        spike_session.execute_loop_sequence(
                                            init_code, init_size,
                                            body_codes, body_sizes,
                                            decr_code, decr_size,
                                            branch_code, branch_size,
                                            max_iterations=loop_iterations + 1
                                        )
                                except Exception as e:
                                    # If execution fails, just continue with assembly output
                                    pass

                            # Append to output with labels (for assembly file readability)
                            entire_instrs.append(init_instr)
                            entire_instrs.append(f'{label}:')
                            entire_instrs.extend(loop_body)
                            entire_instrs.append(decr_instr)
                            entire_instrs.append(f'bne {counter_reg}, zero, {label}')

                            # Update register history
                            rd_history.use_register(counter_reg)

                            # Skip i increment for the number of instructions added
                            i += len(loop_body) + 3  # init + body + decr + branch
                            continue

                        else:
                            # === FORWARD DIRECT JUMP ===
                            label = label_mgr.generate_forward_label()
                            target_distance = random.randint(3, 8)

                            # Generate jump instruction with placeholder
                            jump_instr = generate_new_instr(instr, extension, rd_history, rs_history,
                                                           frd_history, frs_history)

                            # Generate middle instructions
                            middle_instrs = generate_forward_jump_instrs(
                                jump_instr, target_distance, extension,
                                rd_history, rs_history, frd_history, frs_history,
                                is_rv32, instrs_filter, probabilities, allowed_ext.allowed_ext
                            )

                            # If jump_compiler and spike_session are available, compile and execute
                            if jump_compiler is not None and spike_session is not None:
                                try:
                                    fwd_seq = jump_compiler.compile_forward_jump(
                                        jump_instr, middle_instrs, label
                                    )
                                    # Get machine codes and sizes for execution
                                    codes_and_sizes = jump_compiler.get_machine_codes(fwd_seq)
                                    if codes_and_sizes:
                                        codes = [c for c, s in codes_and_sizes]
                                        sizes = [s for c, s in codes_and_sizes]
                                        spike_session.execute_jump_sequence(codes, sizes)
                                except Exception as e:
                                    # If execution fails, just continue with assembly output
                                    pass

                            # Append to output with labels (for assembly file readability)
                            entire_instrs.append(jump_instr.replace('{LABEL}', label))
                            entire_instrs.extend(middle_instrs)
                            entire_instrs.append(f'{label}:')

                            # Skip i increment for the number of instructions added
                            i += len(middle_instrs) + 1  # jump + middle
                            continue

                    elif is_indirect_jump:
                        # The last instruction cannot be a jump instruction because there are no subsequent labels.
                        if i == instr_number - 1:
                            continue
                        # === FORWARD INDIRECT JUMP ONLY ===
                        label = label_mgr.generate_forward_label()
                        target_distance = random.randint(3, 8)

                        # Choose a safe register for address loading (avoid zero, sp, gp, tp)
                        safe_regs = [r for r in reg_range if r not in ['zero', 'sp', 'gp', 'tp']]
                        chosen_reg = random.choice(safe_regs) if safe_regs else random.choice(reg_range)

                        # Construct jump instruction
                        if instr == 'jalr':
                            rd = random.choice(reg_range)
                            jump_instr_str = f'jalr {rd}, 0({chosen_reg})'
                            rd_history.use_register(rd)
                        elif instr == 'c.jr':
                            jump_instr_str = f'c.jr {chosen_reg}'
                        elif instr == 'c.jalr':
                            jump_instr_str = f'c.jalr {chosen_reg}'

                        rs_history.use_register(chosen_reg)

                        # Generate middle instructions
                        middle_instrs = generate_forward_jump_instrs(
                            jump_instr_str, target_distance, extension,
                            rd_history, rs_history, frd_history, frs_history,
                            is_rv32, instrs_filter, probabilities, allowed_ext.allowed_ext
                        )

                        # If jump_compiler and spike_session are available, compile and execute
                        if jump_compiler is not None and spike_session is not None:
                            try:
                                ind_seq = jump_compiler.compile_indirect_jump(
                                    f'la {chosen_reg}, {{LABEL}}',
                                    jump_instr_str,
                                    middle_instrs,
                                    label
                                )
                                codes_and_sizes = jump_compiler.get_machine_codes(ind_seq)
                                if codes_and_sizes:
                                    codes = [c for c, s in codes_and_sizes]
                                    sizes = [s for c, s in codes_and_sizes]
                                    spike_session.execute_jump_sequence(codes, sizes)
                            except Exception as e:
                                pass

                        # Append to output with labels
                        entire_instrs.append(f'la {chosen_reg}, {label}')
                        entire_instrs.append(jump_instr_str)
                        entire_instrs.extend(middle_instrs)
                        entire_instrs.append(f'{label}:')

                        # Skip i increment
                        i += len(middle_instrs) + 2  # la + jump + middle
                        continue


                    # --------- Instruction validation with duplicate elimination -----------
                    # TODO Currently does not support spike debug for vector instructions (vec)

                    if eliminate_enable and extension != 'RV_V':
                        # Use checkpoint-based validation with decoupled XOR and bug filtering
                        if validator is not None:
                            mutate_time = 0
                            while mutate_time < MAX_MUTATE_TIME:
                                # Generate new instruction
                                if is_rv32:
                                    while True:
                                        complete_instr = generate_new_instr(instr, extension, rd_history, rs_history, \
                                                                        frd_history, frs_history)
                                        if (not any(rv32_not_support_csr in complete_instr for rv32_not_support_csr in rv32_not_support_csrs)) and ("minstret" not in complete_instr):
                                            break
                                else:
                                    complete_instr = generate_new_instr(instr, extension, rd_history, rs_history, \
                                                                    frd_history, frs_history)

                                # Validate instruction (auto-confirms if valid, auto-rejects if not)
                                if validator.validate_instruction(complete_instr):
                                    break
                                mutate_time += 1

                            # Update statistics
                            if mutate_time >= MAX_MUTATE_TIME:
                                resolve_duplicates_fail += 1
                                # Skip this instruction since validation failed
                                continue
                            else:
                                resolve_duplicates += 1

                        else:
                            # Validator not available - spike_engine is required for duplicate elimination
                            raise RuntimeError(
                                "spike_engine not available! Cannot use duplicate elimination mode.\n"
                                "Please build spike_engine at: ref/riscv-isa-sim-checkpoint/spike_engine\n"
                                "Or run without -e flag to disable duplicate elimination."
                            )
                    else:
                        # Non-eliminate mode: generate instruction with bug filter retry
                        retry_count = 0
                        while retry_count < MAX_MUTATE_TIME:
                            if is_rv32:
                                while True:
                                    complete_instr = generate_new_instr(instr, extension, rd_history, rs_history, \
                                                                frd_history,frs_history)
                                    if (not any(rv32_not_support_csr in complete_instr for rv32_not_support_csr in rv32_not_support_csrs)) and ("minstret" not in complete_instr):
                                        break
                            else:
                                complete_instr = generate_new_instr(instr, extension, rd_history, rs_history, \
                                                                frd_history,frs_history)
                                # Clean up vector instruction fields: remove the trailing comma if the last field is 0;
                                # or eliminate consecutive commas (,,) caused by missing operands.
                                if extension == 'RV_V':
                                    # First round of filtering
                                    if complete_instr.endswith(", "):
                                        complete_instr = complete_instr[:-2]
                                    # Second round of filtering
                                    if complete_instr.endswith(", "):
                                        complete_instr = complete_instr[:-2]
                                    # Replace two consecutive commas (possibly with space in between) in the string
                                    while ", ," in complete_instr:
                                        complete_instr = complete_instr.replace(", ,", ",")

                            # Instruction is valid, exit retry loop
                            break
                except IndexError as e:
                    complete_instr = 'nop'
                    pass

            entire_instrs.append(complete_instr)
    
        write_instructions_to_file(new_filename, list2str(entire_instrs), template)

        # Cleanup Spike session
        if spike_session is not None:
            spike_session.cleanup()

        # Disable debug output
        InstructionValidator.disable_debug_output()

        # TODO: Count how many identical cases have been eliminated
        # print("resolve_duplicates:",resolve_duplicates,"\nresolve_duplicates_fail:",resolve_duplicates_fail)
        return resolve_duplicates, resolve_duplicates_fail

    finally:
        # Clean up temporary files in /dev/shm
        temp_file_manager.cleanup_all_temp_files()


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
