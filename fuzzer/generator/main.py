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
import time
import logging
from .config.cli_parser import parse_args
from .config.config_manager import setup_config
from .core.generator import generate_instructions_parallel
from .core.mutator import mutate_instructions_parallel

logger = logging.getLogger(__name__)


def write_isa_info(out_dir: str, isa: str, arch_bits: int):
    """
    Write ISA information to a file for downstream tools (e.g., spike runner).

    This ensures consistency between the generator and spike execution.
    """
    isa_file = os.path.join(out_dir, ".isa_info")
    with open(isa_file, 'w') as f:
        f.write(f"ISA={isa}\n")
        f.write(f"ARCH_BITS={arch_bits}\n")

# When processing a large number of files and performing compute-intensive operations 
# on the file contents (such as instruction counting, probability calculation, etc.), 
# the optimal choice is usually to use multiprocessing to parallelize the work, 
# in order to fully utilize the computational power of multi-core processors. 
# This is because Python's Global Interpreter Lock (GIL) restricts only one thread 
# from executing Python bytecode at a time. Therefore, for compute-intensive tasks, 
# multithreading does not provide significant performance improvements. 
# In contrast, using multiprocessing can bypass the GIL limitation, 
# since each Python process has its own interpreter and memory space, 
# thus enabling true parallel execution of tasks.



def main():
    args = parse_args()
    config = setup_config(args)

    if config.generate_enable:
        # Build debug configuration if debug mode is enabled
        debug_config = None
        if config.debug_enabled:
            debug_config = {
                'enabled': True,
                'output_dir': str(config.out_dir),
                'mode': config.debug_mode,
                'accepted_only': config.debug_accepted_only,
                'log_csr': config.debug_log_csr,
                'log_fpr': config.debug_log_fpr,
            }
            filter_str = "ACCEPTED only" if config.debug_accepted_only else "ALL"
            print(f"# Debug mode enabled: mode={config.debug_mode}, filter={filter_str}")
            print(f"#   Output: {config.out_dir}/spike_debug_seed_*.log")

        generate_instructions_parallel(
            config.instr_number,
            config.seed_times,
            config.eliminate_enable,
            config.is_rv32,
            config.max_workers,
            config.arch,
            config.template_type,
            str(config.out_dir),
            config.architecture,
            debug_config
        )

        # Write ISA info for downstream tools (e.g., spike runner)
        write_isa_info(str(config.out_dir), config.isa, config.arch_bits)

    # Whether to enable out-of-order mutation, considering previously unseen extension instructions
    if config.mutation_enable:
        mutate_instructions_parallel(
            config.directory_path,
            config.mutate_directory,
            config.max_workers,
            config.enable_ext,
            config.exclude_extensions,
            config.eliminate_enable,
            config.arch,
            config.template_type
        )



def test_main():
    start_time = time.time()
    main()
    end_time = time.time()
    print("# Execution time: %.2f seconds" % (end_time - start_time))

if __name__ == "__main__":
    test_main()
