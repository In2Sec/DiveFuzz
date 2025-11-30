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
import logging
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List
from .data_collector import collect_data
from .mutate_instructions import process_content
from ...asm_template_manager.riscv_asm_syntex import ArchConfig

logger = logging.getLogger(__name__)

def mutate_instructions_parallel(directory_path: Path,
                                 mutate_directory: Path,
                                 max_workers: int,
                                 enable_ext: bool = False,
                                 exclude_extensions: List[str] = [],
                                 eliminate_enable: bool = False,
                                 arch: ArchConfig = None):
    """
    Mutate instructions in parallel across multiple processes.

    Each process creates its own template instance with random type and values,
    ensuring each mutated file gets independent random content.

    Args:
        directory_path: Path to directory containing seed files
        mutate_directory: Path to output directory for mutated files
        max_workers: Maximum number of parallel processes
        enable_ext: Allow introducing new extension instructions
        exclude_extensions: Extensions to exclude from mutation
        eliminate_enable: Enable conflict elimination via Spike
        arch: Architecture configuration for template creation
    """
    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"Error {directory_path} NOT exist!")
    else:
        processed_data = collect_data(directory_path)
    mutate_directory.mkdir(parents=True, exist_ok=True)

    print("---Start mutation instrs---")
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                process_content,
                file_path,
                content,
                directory_path,
                mutate_directory,
                enable_ext,
                exclude_extensions,
                eliminate_enable,
                arch
            ) for file_path, content in processed_data.items()
        ]

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing files"):
            try:
                result = future.result()
            except Exception as exc:
                print(f'File processing mutation an exception: {exc}')
