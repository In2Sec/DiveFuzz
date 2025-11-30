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

# Data collection utilities for assembly files
import os
from tqdm import tqdm
from .preprocess import preprocess_directory

def collect_assembly_files(directory):
    """
    Collect all assembly (.S) files in the given directory with a progress bar.

    :param directory: Path to the directory where assembly files are stored.
    :return: A list of paths to the assembly files.
    """
    assembly_files = []

    # Get all directories and subdirectories
    all_dirs = [x[0] for x in os.walk(directory)]

    # Walk through the directory with a progress bar
    for root in tqdm(all_dirs, desc="Collecting files"):
        files = next(os.walk(root))[2]
        for file in files:
            if file.endswith(".S"):
                full_path = os.path.join(root, file)
                assembly_files.append(full_path)
            else:
                print("ERROR: No exist File!")
    return assembly_files

def collect_data(directory):
    """Collect and preprocess data from assembly files in a directory."""
    return preprocess_directory(directory)
