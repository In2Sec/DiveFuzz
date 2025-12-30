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
import json
from multiprocessing import Manager
from concurrent.futures import ProcessPoolExecutor, as_completed, TimeoutError
from tqdm import tqdm
from .generate_instrs import generate_instructions
from ...asm_template_manager.riscv_asm_syntex import ArchConfig

def generate_instructions_parallel(instr_number: int,
                                   seed_times: int,
                                   eliminate_enable: bool,
                                   is_cva6: bool,
                                   is_rv32: bool,
                                   max_workers: int,
                                   arch: ArchConfig,
                                   template_type: str,
                                   out_dir: str = "out-seeds-2025-test",
                                   architecture: str = 'xs',
                                   debug_config: dict = None):
    """
    Generate random RISC-V instructions in parallel across multiple processes.

    Each process creates its own template instance with random type and values,
    ensuring each seed gets independent random content.

    Args:
        instr_number: Number of instructions per seed
        seed_times: Number of seeds to generate
        eliminate_enable: Enable conflict elimination via Spike
        is_cva6: Target CVA6 processor
        is_rv32: Use RV32 architecture
        max_workers: Maximum number of parallel processes
        arch: Architecture configuration for template creation
        template_type: Template type name
        out_dir: Output directory for seeds and XOR cache
        architecture: Architecture for bug filtering ('xs', 'nts', 'rkt', 'kmh')
        debug_config: Debug configuration dict with keys:
            - enabled: bool - Enable debug mode
            - output_dir: str - Debug output directory
            - mode: str - 'FULL', 'DIFF', or 'SUMMARY'
            - accepted_only: bool - Only log ACCEPTED instructions
            - log_csr: bool - Log CSR values
            - log_fpr: bool - Log FPR values
    """
    resolve_duplicates = 0
    resolve_duplicates_fail = 0
    timeout_count = 0

    # The timeout period = the number of instructions * 0.8 seconds
    timeout_seconds = instr_number * 0.8
    # Maximum retry count to prevent unlimited retries
    max_retries = 5

    print("---Start generate instrs---")
    print(f"# Timeout per seed: {timeout_seconds}s")

    # Create Manager for shared XOR cache (real-time cross-process sharing)
    # IMPORTANT: Use context manager to ensure Manager stays alive until all processes complete
    with Manager() as manager:
        shared_xor_cache = manager.dict()

        # Load existing cache from file if available
        cache_file = os.path.join(out_dir, 'xor_cache.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    for opcode, xor_list in data.items():
                        # Convert list to Manager.list for thread-safe operations
                        shared_xor_cache[opcode] = manager.list(xor_list)
                    print(f"# Loaded initial XOR cache from {cache_file}")
                    print(f"  Total opcodes: {len(shared_xor_cache)}")
                    total_xors = sum(len(v) for v in shared_xor_cache.values())
                    print(f"  Total XOR values: {total_xors}")
            except Exception as e:
                print(f"# Warning: Failed to load cache: {e}")
                print(f"  Starting with empty cache")

        # The list of seed indexes to be generated
        pending_seeds = list(range(seed_times))
        completed_count = 0
        retry_round = 0

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            while pending_seeds and retry_round < max_retries:
                if retry_round > 0:
                    print(f"# Retry round {retry_round}/{max_retries} for {len(pending_seeds)} timed out seeds")


                futures = {}
                for seed_idx in pending_seeds:
                    future = executor.submit(
                        generate_instructions,
                        instr_number,
                        seed_idx,
                        eliminate_enable,
                        is_cva6,
                        is_rv32,
                        arch,
                        template_type,
                        out_dir,
                        shared_xor_cache,  # Pass shared cache to each process
                        architecture,  # Pass architecture for bug_filter initialization in subprocess
                        debug_config  # Pass debug configuration
                    )
                    futures[future] = seed_idx

                # Clear the pending list and get ready to collect the failed tasks
                pending_seeds = []

                # collect results
                for future in tqdm(as_completed(futures), total=len(futures),
                                 desc="# Generating instructions"):
                    seed_idx = futures[future]
                    try:
                        result1, result2 = future.result(timeout=timeout_seconds)
                        resolve_duplicates += result1
                        resolve_duplicates_fail += result2
                        completed_count += 1
                    except TimeoutError:
                        timeout_count += 1
                        print(f"# Seed {seed_idx} timed out ({timeout_seconds}s)")
                        pending_seeds.append(seed_idx)
                    except RuntimeError as e:
                        # Manager connection error - retry this seed
                        if "Manager connection lost" in str(e):
                            print(f"# Seed {seed_idx} failed due to Manager connection issue, will retry")
                            pending_seeds.append(seed_idx)
                        else:
                            print(f"# Error generating seed {seed_idx}: {e}")
                    except Exception as e:
                        print(f"# Error generating seed {seed_idx}: {e}")

                retry_round += 1

            if pending_seeds:
                print(f"# {len(pending_seeds)} seeds failed after {max_retries} retry rounds, skipping")

        # Save shared XOR cache to file for persistence (inside Manager context)
        try:
            os.makedirs(out_dir, exist_ok=True)
            temp_file = cache_file + '.tmp'
            with open(temp_file, 'w') as f:
                # Convert Manager.dict and Manager.list to regular dict/list for JSON
                data = {opcode: sorted(list(xor_list)) for opcode, xor_list in shared_xor_cache.items()}
                json.dump(data, f, indent=2)
            os.replace(temp_file, cache_file)
            total_xors = sum(len(v) for v in shared_xor_cache.values())
            print(f"# Saved XOR cache to {cache_file}")
            print(f"  Total opcodes: {len(shared_xor_cache)}")
            print(f"  Total XOR values: {total_xors}")
        except Exception as e:
            print(f"# Warning: Failed to save cache: {e}")

        print(f"# Successfully generated: {completed_count}/{seed_times} seeds")
        print(f"# Total timeouts: {timeout_count}")
        print(f"# Total conflict avoidances: {resolve_duplicates}")
        print(f"# Total failed conflict avoidances: {resolve_duplicates_fail}")
