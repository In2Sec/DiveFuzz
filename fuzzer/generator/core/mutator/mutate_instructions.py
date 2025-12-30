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
import os
import random
import numpy as np
from typing import List
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from ...instr_generator import (
    INSTRUCTION_FORMATS,
    special_instr,
    get_instruction_format,
    get_instruction_type,
    classify_instructions,
    find_instruction_extension,
)
from .modify_instr import (
    modify_instruction_dec,
    modify_instruction_inc,
)
from ...asm_template_manager import create_template_instance, TemplateInstance
from ...asm_template_manager.riscv_asm_syntex import ArchConfig
from ...utils import list2str_without_indent
from ...reg_analyzer.nop_template_gen import generate_nop_elf
from ...reg_analyzer.spike_session import SpikeSession, SPIKE_ENGINE_AVAILABLE
from ...reg_analyzer.instruction_validator import InstructionValidator
from ...config.config_manager import MAX_MUTATE_TIME
from ...bug_filter import bug_filter


# Initial mutation, search within the current extension set.
def process_content(file_path: str,
                    file_content: str,
                    directory_path: Path,
                    mutate_directory: Path,
                    enable_ext: bool,
                    exclude_extensions: List[str],
                    eliminate_enable: bool,
                    arch: ArchConfig,
                    template_type: str):
    """
    Process and mutate instructions in a single file.

    Args:
        file_path: Path to the source file
        file_content: Content of the source file
        directory_path: Path to source directory
        mutate_directory: Path to output directory
        enable_ext: Allow introducing new extension instructions
        exclude_extensions: Extensions to exclude from mutation
        eliminate_enable: Enable conflict elimination via Spike
        arch: Architecture configuration for template creation
    """
    # Create fresh template instance for this mutated file with random type and values
    template = create_template_instance(arch, template_type)

    # Initialize Spike session for eliminate mode (similar to generate_instructions)
    spike_session = None
    validator = None
    shared_xor_cache = {}  # Local XOR cache for mutation

    if eliminate_enable and SPIKE_ENGINE_AVAILABLE:
        try:
            # Estimate instruction count from file content
            instr_count = len([line for line in file_content.split('\n')
                             if line.strip() and not line.strip().startswith('#')
                             and ':' not in line.strip()[0:1]])

            # Generate NOP ELF template
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.elf', delete=False) as tmp:
                elf_path = tmp.name
            elf_path = generate_nop_elf(template, instr_count, elf_path)

            spike_session = SpikeSession(
                elf_path,
                template.isa,
                instr_count,
                shared_xor_cache
            )

            if spike_session.initialize():
                validator = InstructionValidator(spike_session)
            else:
                spike_session = None
                validator = None

        except Exception as e:
            print(f"[Mutate] Failed to initialize Spike session: {e}")
            spike_session = None
            validator = None

    instruction_freq = count_instructions({file_path: file_content})
    increase_queue, decrease_queue, classified_instructions, geometric_means, missing_ext = classify_instructions(instruction_freq)

    updated_content = []  # Store the mutated content
    instr_probabilities = {}  # Create a dictionary for storing probabilities
    
    for extension, instr_data in classified_instructions.items():
        counts = list(instr_data['instructions'].values())
        if counts:  
            mean = np.mean(counts)
            std = np.std(counts)
            p_decs, p_incs, valid_counts = calculate_probabilities_z_score_full(counts, mean, std, min_prob=0.3, max_prob=0.9)

            for instr, count in instr_data['instructions'].items():
                prob = p_decs.get(count, 0.3) if count > mean else p_incs.get(count, 0.9)
                instr_probabilities[instr] = prob
    # Instructions in the mutated file
    for line in file_content.split('\n'):

        line_parts = line.split()
        if not line_parts:
            updated_content.append(line)
            continue
        # Check whether the line contains a section description (i.e., whether it contains a colon)
        if ':' in line_parts[0]:
            # If there is a section description, then the instruction name should be the first word after the colon
            if len(line_parts) > 1:
                instr_name = line_parts[1]
                segment_label = line_parts[0] + " "  # Keep the section identifier
            else:
                updated_content.append(line)
                continue  # Skip lines that contain only a section description without instructions
        else:
            instr_name = line_parts[0]
            segment_label = ""
        # Handle UNKNOWN instructions
        if instr_name == 'la':
            updated_content.append(line)
            continue
        # Get the instruction type and check whether there is a label tag in the format
        instr_type = get_instruction_type(instr_name)
        instr_format = INSTRUCTION_FORMATS.get(instr_type.upper(), {}).get(instr_name, {})

        # TODO: Add register value checking!
        if instr_name in increase_queue:
            prob = instr_probabilities.get(instr_name, 0.5)
            if random.random() < prob:
                if eliminate_enable and validator is not None:
                    # Check if instruction needs special handling (skip validation)
                    if  'LABEL' in get_instruction_format(instr_name).get('variables', []) or 'LOAD' in get_instruction_format(instr_name).get('category', []) \
                        or 'STORE' in get_instruction_format(instr_name).get('category', []) or 'JUMP' in get_instruction_format(instr_name).get('category', []) \
                        or 'BRANCH' in get_instruction_format(instr_name).get('category', []) or 'LOAD_SP' in get_instruction_format(instr_name).get('category', []) \
                        or 'STORE_SP' in get_instruction_format(instr_name).get('category', []):
                        updated_content.append(line)
                    else:
                        # Use validator for instruction validation
                        # validate_instruction handles XOR check, bug filter, and checkpoint management
                        is_valid = False
                        mutate_time = 0

                        while not is_valid and mutate_time < MAX_MUTATE_TIME:
                            modified_instr = modify_instruction_inc(line, prob, get_instruction_type(instr_name))

                            # Validate instruction (returns (is_valid, actual_bytes))
                            # Internally handles: XOR uniqueness, bug filter, checkpoint restore/confirm
                            is_valid, _ = validator.validate_instruction(modified_instr)
                            if is_valid:
                                updated_content.append(segment_label + modified_instr)
                            else:
                                mutate_time += 1

                        if mutate_time >= MAX_MUTATE_TIME:
                            # Failed to find unique instruction, keep original
                            updated_content.append(line)
                else:
                    modified_instr = modify_instruction_inc(line, prob, get_instruction_type(instr_name))
                    updated_content.append(segment_label + modified_instr)

            else:
                updated_content.append(line)
        # Instructions to be reduced
        elif instr_name in decrease_queue:
            # Check whether the instruction contains the 'LABEL' variable
            if 'LABEL' not in instr_format.get('variables', []):
                prob = instr_probabilities.get(instr_name, 0.5)
                if random.random() < prob:
                    # With a 50% probability, replace with NOP or randomly select an instruction from the addition queue that does not contain LABEL
                    prob_choose_stgy = random.random()
                    if prob_choose_stgy < 0.001:  # Originally 0.5, for experimental
                        # TODO: Originally replaced with nop
                        updated_content.append(segment_label + "")
                        pass
                    elif (prob_choose_stgy < 0.1 and enable_ext) or not enable_ext:
                        # Randomly select an instruction from the addition queue that does not contain LABEL
                        # Randomly select an instruction from the addition queue that does not contain STORE
                        # Randomly select an instruction from the addition queue that does not contain LOAD
                        # TODO Two strategies: should we add it to a specific extension that has not appeared yet?
                        no_label_increase_queue = [instr for instr in increase_queue if 'LABEL' not in get_instruction_format(instr).get('variables', []) \
                                                                                and 'LOAD' not in get_instruction_format(instr).get('category', []) \
                                                                                and 'STORE' not in get_instruction_format(instr).get('category', []) \
                                                                                and 'SYSTEM' not in get_instruction_format(instr).get('category', [])\
                                                                                and 'JUMP' not in get_instruction_format(instr).get('category', [])]# 为了做实验

                        if no_label_increase_queue:
                            random_increase_instr = random.choice(no_label_increase_queue)
                            while random_increase_instr in special_instr:
                                random_increase_instr = random.choice(no_label_increase_queue)
                            modified_instr = modify_instruction_dec(line, random_increase_instr, 1, get_instruction_type(random_increase_instr))
                            updated_content.append(segment_label + modified_instr)
                    # Enable extension
                    else:
                        # Filter instructions excluding certain categories and extensions
                        no_label_increase_queue = [instr for instr in missing_ext if 'LABEL' not in get_instruction_format(instr).get('variables', []) \
                                                                                and 'LOAD' not in get_instruction_format(instr).get('category', []) \
                                                                                and 'STORE' not in get_instruction_format(instr).get('category', []) \
                                                                                and 'SYSTEM' not in get_instruction_format(instr).get('category', [])\
                                                                                and 'JUMP' not in get_instruction_format(instr).get('category', [])\
                                                                                and find_instruction_extension(instr) not in exclude_extensions]# 为了做实验

                        if no_label_increase_queue:
                            random_increase_instr = random.choice(no_label_increase_queue)
                            while random_increase_instr in special_instr:
                                random_increase_instr = random.choice(no_label_increase_queue)
                            modified_instr = modify_instruction_dec(line, random_increase_instr, 1, get_instruction_type(random_increase_instr))
                            updated_content.append(segment_label + modified_instr)
                else:
                    updated_content.append(line)
            else:
                updated_content.append(line)
        else:
            updated_content.append(line)
    base_filename = os.path.basename(file_path)
    new_filename = base_filename.replace('.S', '_mutated.S')

    new_file_path = os.path.join(mutate_directory, new_filename)
    
    # TODO use template rather than replace content
    # replace_content(file_path, updated_content, new_file_path)  # Assume updated_content is a list of strings
    write_instructions_to_file(new_file_path, list2str_without_indent(updated_content), template)

    # Cleanup Spike session
    if spike_session is not None:
        spike_session.cleanup()

    return f"Processed {base_filename}"


def write_instructions_to_file(new_filename: str, instructions: str, template: TemplateInstance):
    """
    Write mutated instructions to file with template wrapper.

    Args:
        new_filename: Output file path
        instructions: Mutated instruction sequence
        template: Template instance to wrap instructions
    """
    lines = template.get_complete_template(instructions)

    os.makedirs(os.path.dirname(new_filename), exist_ok=True)

    with open(new_filename, 'w') as file:
        file.writelines(lines)


def count_instructions(processed_data):
    freq_counter = {}
    # Update the regular expression to match instructions containing numbers and decimal points
    instruction_pattern = re.compile(r'^\s*[^:\s]*:\s*([\w.]+)|^\s*([\w.]+)', re.MULTILINE) 
    #instruction_pattern = re.compile(r'^\s*_[a-zA-Z0-9]+:\s*([^\s].*?)(?=\s\s)', re.MULTILINE) # difuzz-rtl
    #instruction_pattern = re.compile(r'^\s*([\w.]+)\s*|(^\s*$)', re.MULTILINE) # difuzz-rtl

    for _, content in processed_data.items():
        matches = instruction_pattern.findall(content)

        for match in matches:
            # Extract instructions from the matching results
            instr = next((x for x in match if x), None)

            if instr:
                freq_counter[instr] = freq_counter.get(instr, 0) + 1

    return freq_counter

# Compute z-score normalization
def calculate_probabilities_z_score_full(counts, mean, std, min_prob=0.3, max_prob=0.9):
    p_decs = {}
    p_incs = {}
    valid_counts = [count for count in counts if count > 0]
    for count in counts:
        z_score = (count - mean) / std if std != 0 else 0
        p_decs[count] = np.clip(1 / (1 + np.exp(-z_score)), min_prob, max_prob) if count > 0 else 0.3
        p_incs[count] = np.clip(1 / (1 + np.exp(z_score)), min_prob, max_prob) if count > 0 else 0.9

    return p_decs, p_incs, valid_counts

def get_label_from_instruction(instruction, extension):
    instr_parts = instruction.split()
    instr_key = instr_parts[0]  # The keyword of the instruction, such as 'c.j'

    instr_format = INSTRUCTION_FORMATS.get(extension, {}).get(instr_key, {})
    format_str = instr_format.get("format", "")
    variables = instr_format.get("variables", [])
    # Check if LABEL is in a variable and find its position
    if "LABEL" in variables:
        label_position = format_str.split().index("{" + "LABEL" + "}")
        if label_position < len(instr_parts):
            return instr_parts[label_position]
    
    return None
