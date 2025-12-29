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
from ...reg_analyzer.nop_template_gen import generate_nop_elf, NOP_REDUNDANCY
from ...reg_analyzer.spike_session import SpikeSession, SPIKE_ENGINE_AVAILABLE
from ...reg_analyzer.instruction_validator import InstructionValidator
from ...reg_analyzer.xor_cache import XORCache
from ...reg_analyzer.hybrid_encoder import HybridEncoder
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

    Note: Memory-modifying instructions (AMO, STORE) are excluded to avoid
    state divergence between spike_engine validation and final program execution.
    These instructions are not individually validated by InstructionValidator,
    so their memory modifications could cause different behavior in subsequent
    instructions that depend on memory state.
    """
    middle_instrs = []

    # Categories that modify memory - excluded to avoid state divergence
    # AMO instructions read-modify-write memory, STORE instructions write memory
    MEMORY_MODIFYING_CATEGORIES = {
        'AMO', 'AMO_LOAD', 'AMO_STORE',
        'STORE', 'STORE_SP', 'FLOAT_STORE'
    }

    for _ in range(target_distance):
        # Select extension
        ext = np.random.choice(allowed_extensions, p=probabilities)

        # Get instruction list for this extension
        if ext not in INSTRUCTION_FORMATS:
            continue

        instrs_complete = INSTRUCTION_FORMATS[ext]
        instrs = list(instrs_complete.keys())

        # Filter out jumps, branches, compressed instructions, and memory-modifying instructions
        # Memory-modifying instructions are excluded because:
        # 1. They are not individually validated by InstructionValidator
        # 2. Their side effects could cause state divergence in subsequent instructions
        filtered = [instr for instr in instrs
                   if 'LABEL' not in get_instruction_format(instr).get('variables', [])
                   and 'JUMP' not in get_instruction_format(instr).get('category', [])
                   and 'BRANCH' not in get_instruction_format(instr).get('category', [])
                   and get_instruction_format(instr).get('category', '') not in MEMORY_MODIFYING_CATEGORIES
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

    Note: Memory-modifying instructions (AMO, STORE) are excluded for the same
    reason as in generate_forward_jump_instrs - to avoid state divergence.
    """
    loop_body = []

    # Categories that modify memory - excluded to avoid state divergence
    MEMORY_MODIFYING_CATEGORIES = {
        'AMO', 'AMO_LOAD', 'AMO_STORE',
        'STORE', 'STORE_SP', 'FLOAT_STORE'
    }

    for _ in range(target_distance):
        # Select extension
        ext = np.random.choice(allowed_extensions, p=probabilities)

        if ext not in INSTRUCTION_FORMATS:
            continue

        instrs_complete = INSTRUCTION_FORMATS[ext]
        instrs = list(instrs_complete.keys())

        # Filter out jumps, branches, compressed instructions, and memory-modifying instructions
        filtered = [instr for instr in instrs
                   if 'LABEL' not in get_instruction_format(instr).get('variables', [])
                   and 'JUMP' not in get_instruction_format(instr).get('category', [])
                   and 'BRANCH' not in get_instruction_format(instr).get('category', [])
                   and get_instruction_format(instr).get('category', '') not in MEMORY_MODIFYING_CATEGORIES
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
                          shared_xor_cache,  # Deprecated: kept for API compatibility
                          architecture: str,
                          debug_config: dict = None):
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
        shared_xor_cache: (Deprecated) Not used - XOR cache is now per-process LOCAL mode
        architecture: Architecture for bug filtering ('xs', 'nts', 'rkt', 'kmh')
        debug_config: Debug configuration dict (see generate_instructions_parallel)
    """
    # Note: shared_xor_cache is no longer used (v4.0 architecture uses LOCAL XORCache)

    # Create fresh template instance for this seed with random type and values
    # This ensures each seed gets independent random content (MSTATUS, register init, etc.)
    template = create_template_instance(arch, template_type)

    try:
        # Initialize Spike session for eliminate mode (checkpoint-based validation)
        spike_session = None
        validator = None
        xor_cache = None
        if eliminate_enable and SPIKE_ENGINE_AVAILABLE:
            try:
                # Generate NOP ELF template
                # Note: generate_nop_elf internally adds NOP_REDUNDANCY extra NOPs
                elf_path = f"/dev/shm/template_{seed_times}_{instr_number}.elf"
                elf_path = generate_nop_elf(template, instr_number, elf_path)

                # Create SpikeSession with total instruction capacity (including redundancy)
                # This ensures spike_engine can handle pseudo-instruction expansion
                spike_session = SpikeSession(
                    elf_path,
                    template.isa,
                    instr_number + NOP_REDUNDANCY
                )
                if spike_session.initialize():
                    # Create XOR cache for this process
                    xor_cache = XORCache()
                    xor_cache.create()

                    # Create validator with simplified architecture (v4.0)
                    encoder = HybridEncoder(quiet=True)
                    validator = InstructionValidator(
                        spike_session=spike_session,
                        xor_cache=xor_cache,
                        architecture=architecture,
                        encoder=encoder
                    )

                    # Enable detailed debug output if debug_config is provided
                    if debug_config and debug_config.get('enabled', False):
                        debug_output_dir = debug_config.get('output_dir', out_dir)
                        debug_file = os.path.join(debug_output_dir, f"spike_debug_seed_{seed_times}.log")
                        InstructionValidator.enable_detailed_debug(
                            filepath=debug_file,
                            mode=debug_config.get('mode', 'DIFF'),
                            log_csr=debug_config.get('log_csr', True),
                            log_fpr=debug_config.get('log_fpr', True),
                            accepted_only=debug_config.get('accepted_only', False)
                        )
                        mode_str = debug_config.get('mode', 'DIFF')
                        acc_str = " (ACCEPTED only)" if debug_config.get('accepted_only', False) else ""
                        print(f"[Seed {seed_times}] Detailed debug enabled (mode={mode_str}{acc_str}): {debug_file}")

                    # Legacy: Enable debug output if DEBUG_SPIKE_ENGINE environment variable is set
                    debug_mode = os.environ.get('DEBUG_SPIKE_ENGINE', '').lower()
                    if debug_mode and not (debug_config and debug_config.get('enabled', False)):
                        debug_file = os.path.join(out_dir, f"spike_engine_debug_{seed_times}.txt")
                        accepted_only = (debug_mode == 'accepted')
                        InstructionValidator.enable_debug_output(debug_file, accepted_only=accepted_only)
                        mode_str = "ACCEPTED only" if accepted_only else "ALL"
                        print(f"[Seed {seed_times}] Legacy debug output enabled ({mode_str}): {debug_file}")
                else:
                    print(f"[Seed {seed_times}] Spike initialization failed")
                    spike_session = None
                    validator = None
                    xor_cache = None
                    encoder = None
                    return 0, 0
            except Exception as e:
                print(f"[Seed {seed_times}] Failed to initialize Spike session: {e}")
                spike_session = None
                validator = None
                xor_cache = None
                encoder = None
                return 0, 0
        else:
            # Non-eliminate mode: still create encoder for offset calculation
            try:
                encoder = HybridEncoder(quiet=True)
            except Exception:
                encoder = None

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

        # Maximum bytes in NOP template's main region
        # Each nop is 4 bytes, so total = (instr_number + NOP_REDUNDANCY) * 4
        max_bytes = (instr_number + NOP_REDUNDANCY) * 4
        # Track actual bytes of machine instructions executed in spike
        actual_bytes = 0
        # Track logical instruction index (for user-requested instruction count)
        logical_instr_index = 0

        # Use while loop to properly track actual bytes
        # (for loop index cannot be modified in Python)
        while logical_instr_index < instr_number and actual_bytes < max_bytes:
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
                # ILL instructions are single 4-byte machine instructions
                actual_bytes += 4

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
                        if logical_instr_index == instr_number - 1:
                            logical_instr_index += 1
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

                            # Initialize compiled_seq for fallback estimation
                            compiled_seq = None

                            # If encoder and spike_session are available, compile and execute
                            if encoder is not None and spike_session is not None:
                                try:
                                    compiled_seq = encoder.compile_backward_loop(
                                        init_instr, loop_body, decr_instr, branch_instr, label
                                    )
                                    # Execute the loop sequence using unified execute_sequence
                                    # max_steps = loop_iterations * (body + decr + branch) + init
                                    max_steps = loop_iterations * (len(loop_body) + 2) + 2
                                    spike_session.execute_sequence(compiled_seq.codes, compiled_seq.sizes, max_steps)
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

                            # Update byte counts based on compiled machine code
                            # compiled_seq contains actual machine instructions after pseudo-instruction expansion
                            if compiled_seq is not None:
                                seq_actual_bytes = sum(compiled_seq.sizes)
                                if os.environ.get('DEBUG_BYTES', ''):
                                    print(f"[Seed {seed_times}] Backward loop: sizes={compiled_seq.sizes}, total={seq_actual_bytes}")
                            else:
                                # Fallback: estimate based on assembly lines (assume 4 bytes each)
                                # init(li) may expand to multiple instructions, body, decr, branch
                                seq_actual_bytes = (len(loop_body) + 4) * 4  # conservative estimate

                            actual_bytes += seq_actual_bytes
                            logical_instr_index += len(loop_body) + 4  # init + body + decr + branch
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

                            # Initialize compiled_seq for fallback estimation
                            compiled_seq = None

                            # If encoder and spike_session are available, compile and execute
                            if encoder is not None and spike_session is not None:
                                try:
                                    compiled_seq = encoder.compile_forward_jump(
                                        jump_instr, middle_instrs, label
                                    )
                                    spike_session.execute_sequence(compiled_seq.codes, compiled_seq.sizes)
                                except Exception as e:
                                    # If execution fails, just continue with assembly output
                                    pass

                            # Append to output with labels
                            # IMPORTANT: Use actual offset from compiled_seq instead of label reference
                            # This ensures the .S file matches the machine codes executed by spike_engine
                            # (riscv-as may generate different opcodes when using labels)
                            if compiled_seq is not None and len(compiled_seq.asm_list) >= 1:
                                # Use the actual jump instruction with offset (e.g., "jal a0, . + 28")
                                entire_instrs.append(compiled_seq.asm_list[0])
                            else:
                                # Fallback to label-based instruction (may cause mismatch)
                                entire_instrs.append(jump_instr.replace('{LABEL}', label))
                            entire_instrs.extend(middle_instrs)
                            entire_instrs.append(f'{label}:')

                            # Update byte counts based on compiled machine code
                            if compiled_seq is not None:
                                seq_actual_bytes = sum(compiled_seq.sizes)
                                if os.environ.get('DEBUG_BYTES', ''):
                                    print(f"[Seed {seed_times}] Forward jump: sizes={compiled_seq.sizes}, total={seq_actual_bytes}")
                            else:
                                # Fallback: jump + middle instructions (assume 4 bytes each)
                                seq_actual_bytes = (len(middle_instrs) + 1) * 4

                            actual_bytes += seq_actual_bytes
                            logical_instr_index += len(middle_instrs) + 1  # jump + middle
                            continue

                    elif is_indirect_jump:
                        # The last instruction cannot be a jump instruction because there are no subsequent labels.
                        if logical_instr_index == instr_number - 1:
                            logical_instr_index += 1
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

                        # Initialize compiled_seq for fallback estimation
                        compiled_seq = None

                        # If encoder and spike_session are available, compile and execute
                        if encoder is not None and spike_session is not None:
                            try:
                                compiled_seq = encoder.compile_indirect_jump(
                                    f'la {chosen_reg}, {{LABEL}}',
                                    jump_instr_str,
                                    middle_instrs,
                                    label
                                )
                                spike_session.execute_sequence(compiled_seq.codes, compiled_seq.sizes)
                            except Exception as e:
                                pass

                        # Append to output with labels
                        # IMPORTANT: Use actual auipc+addi from compiled_seq instead of 'la' pseudo-instruction
                        # This ensures the .S file matches the machine codes executed by spike_engine
                        # (riscv-as may generate different opcodes for 'la' pseudo-instruction)
                        if compiled_seq is not None and len(compiled_seq.asm_list) >= 2:
                            # Use the actual auipc and addi instructions from compilation
                            entire_instrs.append(compiled_seq.asm_list[0])  # auipc
                            entire_instrs.append(compiled_seq.asm_list[1])  # addi
                        else:
                            # Fallback to la pseudo-instruction (may cause mismatch)
                            entire_instrs.append(f'la {chosen_reg}, {label}')
                        entire_instrs.append(jump_instr_str)
                        entire_instrs.extend(middle_instrs)
                        entire_instrs.append(f'{label}:')

                        # Update byte counts based on compiled machine code
                        if compiled_seq is not None:
                            seq_actual_bytes = sum(compiled_seq.sizes)
                            if os.environ.get('DEBUG_BYTES', ''):
                                print(f"[Seed {seed_times}] Indirect jump: sizes={compiled_seq.sizes}, total={seq_actual_bytes}")
                        else:
                            # Fallback: la(2×4) + jump(4) + middle (assume 4 bytes each)
                            seq_actual_bytes = (len(middle_instrs) + 3) * 4

                        actual_bytes += seq_actual_bytes
                        logical_instr_index += len(middle_instrs) + 2  # la + jump + middle (la counts as 1 logical)
                        continue


                    # --------- Instruction validation with duplicate elimination -----------
                    # TODO Currently does not support spike debug for vector instructions (vec)

                    if eliminate_enable and extension != 'RV_V':
                        # Use checkpoint-based validation with decoupled XOR and bug filtering
                        if validator is not None:
                            mutate_time = 0
                            instr_actual_bytes = 4  # Default for single 4-byte instruction
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
                                # Returns (is_valid, actual_bytes) where actual_bytes
                                # reflects pseudo-instruction expansion in bytes
                                is_valid, instr_actual_bytes = validator.validate_instruction(complete_instr)
                                if is_valid:
                                    break
                                mutate_time += 1

                            # Update statistics
                            if mutate_time >= MAX_MUTATE_TIME:
                                resolve_duplicates_fail += 1
                                # Skip this instruction since validation failed
                                logical_instr_index += 1
                                continue
                            else:
                                resolve_duplicates += 1
                                # Update actual bytes with the bytes from validator
                                actual_bytes += instr_actual_bytes

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
                        # In non-eliminate mode, assume each logical instruction = 4 bytes
                        # (pseudo-instruction expansion is not tracked without spike validation)
                        actual_bytes += 4
                except IndexError as e:
                    complete_instr = 'nop'
                    actual_bytes += 4  # nop is 4 bytes
                    pass

            entire_instrs.append(complete_instr)
            logical_instr_index += 1

        # Pad with NOPs to match the NOP template layout
        # This ensures the assembly file compiles to the same memory layout as the spike template
        # max_bytes = (instr_number + NOP_REDUNDANCY) * 4 (each nop is 4 bytes)
        padding_bytes = max_bytes - actual_bytes

        # Debug output for byte tracking verification
        if os.environ.get('DEBUG_BYTES', ''):
            print(f"[Seed {seed_times}] DEBUG: max_bytes={max_bytes}, actual_bytes={actual_bytes}, "
                  f"padding_bytes={padding_bytes}, logical_instr_index={logical_instr_index}")

        if padding_bytes > 0:
            # Calculate number of 4-byte NOPs needed
            nop_count = padding_bytes // 4
            remaining_bytes = padding_bytes % 4

            # If there are remaining bytes, it indicates a byte tracking error
            # Round up to ensure we don't exceed the NOP template boundary
            if remaining_bytes != 0:
                # Add one extra nop to cover the remaining bytes
                # This ensures alignment but may slightly exceed the template
                # Better to be safe than to have misaligned code
                nop_count += 1
                print(f"[Seed {seed_times}] Warning: actual_bytes={actual_bytes} not aligned to 4 bytes "
                      f"(remaining={remaining_bytes}), adding extra nop for safety")

            for _ in range(nop_count):
                entire_instrs.append('nop')

        write_instructions_to_file(new_filename, list2str(entire_instrs), template)

        # Cleanup Spike session
        if spike_session is not None:
            spike_session.cleanup()

        # Disable debug output
        InstructionValidator.disable_debug_output()
        InstructionValidator.disable_detailed_debug()

        # TODO: Count how many identical cases have been eliminated
        # print("resolve_duplicates:",resolve_duplicates,"\nresolve_duplicates_fail:",resolve_duplicates_fail)
        return resolve_duplicates, resolve_duplicates_fail

    finally:
        # Clean up XOR cache (release shared memory)
        if xor_cache is not None:
            try:
                xor_cache.close()
            except Exception:
                pass

        # Clean up Spike session
        if spike_session is not None:
            try:
                spike_session.close()
            except Exception:
                pass

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
