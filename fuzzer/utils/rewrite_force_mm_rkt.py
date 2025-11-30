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

# This script is used to adjust inconsistencies specific to a certain CPU version.
import os
import sys
import time
from utils.elf_to_img import process_assembly_files_to_force_mm, process_file

def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    """
    Progress bar updated on the same line

    :param iteration: Current iteration (Int)
    :param total: Total iterations (Int)
    :param prefix: Progress bar prefix (Str)
    :param suffix: Progress bar suffix (Str)
    :param length: Progress bar length (Int)
    :param fill: Progress bar fill character (Str)
    """
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()


def modify_assembly_code(file_path, new_file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    in_mepc_setup = False
    modified_lines = []
    line_index = 0

    for line in lines:
       
        if line.strip() == 'init_user_mode:' or line.strip() == 'init_supervisor_mode:':
            in_mepc_setup = True
       
        elif line.strip().endswith(':') and in_mepc_setup:
            in_mepc_setup = False
            modified_lines.append(line)
            line_index += 1
          
            break
        if in_mepc_setup and ('mret' in line):
            line_index += 1
            continue

        modified_lines.append(line)
        line_index += 1
    # Write the modified code back to the file
    modified_lines.extend(lines[line_index:])
    with open(new_file_path, 'w') as file:
        file.writelines(modified_lines)

def process_folders(img_folder):
    # Check and create the destination folder
    asm_folder='./seeds/5000_first/rand/asm'
    target_folder = os.path.join(img_folder, 'rewrite_to_mmode')

    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    img_files = [f for f in os.listdir(img_folder) if f.endswith('.img')]
    total_files = len(img_files)


    for i, filename in enumerate(img_files):
        base_name = os.path.splitext(filename)[0]
        asm_file = base_name + '.S'
        asm_file_path = os.path.join(asm_folder, asm_file)

        if os.path.exists(asm_file_path):
            new_file_path = os.path.join(target_folder, asm_file)
            modify_assembly_code(asm_file_path, new_file_path)

        print_progress_bar(i + 1, total_files, prefix='Rewriting asm:', suffix='Complete', length=50)
        time.sleep(0.1) 

    process_assembly_files_to_force_mm(target_folder)


