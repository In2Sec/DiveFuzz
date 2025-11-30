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

# Preprocessing utilities for assembly files
import os
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor

from ...utils.helpers import list2str_without_indent

# Macro variable defining the maximum number of cores
MAX_WORKERS = 8

def extract_main_function(file_path):
    """Extract the main function content from an assembly file."""
    with open(file_path, 'r') as file:
        lines = file.readlines()

    main_function = []
    inside_main = False

    for line in lines:
        # Change based on seed characteristics
        # TODO .align 2? changed to main
        if 'main:' in line:
            inside_main = True
            continue

        if 'write_tohost:' in line and inside_main:
            # TODO should not ignore the last two instrs before write_tohost
            main_function.pop()
            main_function.pop()
            break

        if inside_main:
            main_function.append(line)

    return ''.join(main_function)

def process_file(file_path):
    """Process a single file to extract its main function."""
    return file_path, extract_main_function(file_path)

def preprocess_directory(directory):
    """Preprocess all .S files in a directory using multiprocessing."""
    file_paths = [os.path.join(root, file)
                  for root, _, files in os.walk(directory)
                  for file in files if file.endswith(".S")]

    processed_contents = {}
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(tqdm(executor.map(process_file, file_paths), total=len(file_paths)))

    # Save the results in a dictionary
    for file_path, content in results:
        processed_contents[file_path] = content

    return processed_contents

def replace_content(original_file_path, updated_content, new_file_path):
    """Replace the main function content in an assembly file."""
    with open(original_file_path, 'r') as file:
        lines = file.readlines()

    start_index = -1
    end_index = len(lines)
    for i, line in enumerate(lines):
        # TODO .align 2? changed to main
        if 'main:' in line:
            start_index = i + 1
        elif 'write_tohost:' in line and start_index != -1:
            # TODO should not ignore the last two instrs before write_tohost
            end_index = i - 2
            break

    if start_index == -1 or end_index == len(lines):
        print("NOTFOUND")
        return

    # Replace the content and apply join only to updated_content
    new_content = lines[:start_index] + [list2str_without_indent(updated_content)] + lines[end_index:]

    with open(new_file_path, 'w') as new_file:
        new_file.writelines(new_content)
