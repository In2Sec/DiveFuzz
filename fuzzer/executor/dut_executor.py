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
import subprocess
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import glob
from config.logger_config import create_test_logger
from config.dut_config import Config, DUTTarget, DirSeedConfig, GeneratedSeedConfig, SeedConfigBase
from executor.divefuzz_adapter import setup_divefuzz, run_divefuzz
from utils.results_reporter import TestResult, ResultType, format_duration, generate_result_report, generate_summary_report

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def run_single_seed(seed_path: str, seed_name: str, dut_config: DUTTarget, seed_config_name: str, test_logger: logging.Logger) -> TestResult:
    """Run a single seed and return the result"""
    # Create path-safe seed name
    safe_seed_name = seed_name.replace(" ", "_").replace(os.sep, "_")
    # create logger for this seed
    with create_test_logger(
        test_name=safe_seed_name,
        config_filename=seed_config_name,
        enable_timestamp=False
    ) as (seed_logger, seed_log_path):
        try:
            command = dut_config.cmd.replace('$1', f'"{seed_path}"')
            test_logger.info(f"Starting seed: {seed_name}")
            test_logger.info(f"Seed file: {seed_path}")
            test_logger.info(f"Command: {command}")
            test_logger.info(f"Working directory: {dut_config.emu_path}")
            
            seed_logger.info("==== TEST OUTPUT BEGIN ====")
            result = subprocess.run(
                command, 
                shell=True,
                cwd=dut_config.emu_path,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=300
            )
            # Save output
            seed_logger.info(result.stdout)
            seed_logger.info("==== TEST OUTPUT END ====")
            
            # Parse result
            if result.returncode == 0:
                result_type = ResultType.SUCCESS
                summary = "No differences to reference and no errors"
            else:
                result_type = ResultType.FAILURE
                summary = f"Exited with code {result.returncode}"
            
            seed_logger.info(f"Test completed with status: {result_type.name}")
            test_logger.info(f"Seed completed: {seed_name} - Status: {result_type.name}")
            
            return TestResult(
                dut_name=dut_config.name,
                version=dut_config.version,
                diff_ref=dut_config.diff_ref,
                seed_name=seed_name,
                result_type=result_type,
                summary=summary,
                log_path=seed_log_path
            )
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"Test timed out after 300 seconds: {seed_name}"
            seed_logger.error(error_msg)
            return TestResult(
                dut_name=dut_config.name,
                version=dut_config.version,
                diff_ref=dut_config.diff_ref,
                seed_name=seed_name,
                result_type=ResultType.TIMEOUT,
                summary="Timeout expired (300s)",
                log_path=seed_log_path
            )
        except Exception as e:
            error_msg = f"Unexpected error during test execution: {e} - Seed: {seed_name}"
            seed_logger.exception(error_msg)
            return TestResult(
                dut_name=dut_config.name,
                version=dut_config.version,
                diff_ref=dut_config.diff_ref,
                seed_name=seed_name,
                result_type=ResultType.ERROR,
                summary=f"Unexpected error: {str(e)}",
                log_path=seed_log_path
            )
        finally:
            # Clean up logger handlers
            for hdlr in seed_logger.handlers[:]:
                hdlr.close()
                seed_logger.removeHandler(hdlr)


def run_single_test(dut_config: DUTTarget, seed_config: SeedConfigBase, config_filename: str, global_logger: logging.Logger = logger) -> list[TestResult]:
    """Execute a single test configuration with potential multiple seeds"""
    results = []
    
    with create_test_logger(seed_config.name, config_filename) as (test_logger, log_file_path):
        test_logger.info(f"Starting test: {dut_config.name} with seed config: {seed_config.name}")
        test_logger.info(f"DUT version: {dut_config.version}")
        test_logger.info(f"Diff reference: {dut_config.diff_ref}")
        
        # Collect all seed files for this configuration
        seed_files = []
        try:
            # Handle directory-based seeds
            if isinstance(seed_config, DirSeedConfig):
                test_logger.info(f"Seed mode: dir (path: {seed_config.path}, suffix: {seed_config.suffix})")
                suffix = f"*.{seed_config.suffix}" if seed_config.suffix else "*"
                pattern = os.path.join(seed_config.path, "**", suffix)
                seed_files = glob.glob(pattern, recursive=True)
                test_logger.info(f"Found {len(seed_files)} seed files in directory")
                
            # Handle generated seeds (like divefuzz)
            elif isinstance(seed_config, GeneratedSeedConfig):
                test_logger.info(f"Seed mode: {seed_config.input_type}")
                if seed_config.input_type == "divefuzz":
                    setup_divefuzz(seed_config, global_logger=test_logger)
                    seed_files = run_divefuzz(seed_config, test_logger)
                    test_logger.info(f"Generated {len(seed_files)} seed files via divefuzz")
                else:
                    test_logger.error(f"Unsupported seed input type: {seed_config.input_type}")
                    return []
            
            # Handle single seed file path
            else:
                test_logger.info(f"Seed mode: single file (path: {seed_config.path})")
                seed_files = [seed_config.path]
            
            if not seed_files:
                test_logger.warning("No seed files found for test configuration!")
                return []
                
        except Exception as e:
            global_logger.exception(f"Error preparing seeds: {e}")
            return []
        
        # Run seeds in parallel using ThreadPoolExecutor
        global_logger.info(f"Running {len(seed_files)} seed(s) with {dut_config.threads} threads")
        with ThreadPoolExecutor(max_workers=dut_config.threads) as executor:
            futures = {
                executor.submit(
                    run_single_seed,
                    seed_path,
                    f"{seed_config.name}_{os.path.basename(seed_path)}",
                    dut_config,
                    seed_config.name,
                    test_logger
                ): seed_path
                for seed_path in seed_files
            }
            
            for future in as_completed(futures):
                seed_path = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    generate_result_report(result, global_logger)
                except Exception as e:
                    error_msg = f"Unexpected error processing seed {seed_path}: {e}"
                    test_logger.exception(error_msg)
                    global_logger.exception(error_msg)
        
        return results


def run_dut_tests(config: Config, config_filename: str) -> list[TestResult]:
    """Run all tests defined in the configuration"""
    total_results = []
    
    logger.info(f"Starting tests for DUT: {config.dut_target.name}")
    logger.info(f"Number of seed configurations: {len(config.seeds)}")
    logger.info(f"Parallel threads per configuration: {config.dut_target.threads}")
    # Start time
    start_time = datetime.now()
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all seed configurations
    for seed_config in config.seeds:
        logger.info(f"Running seed configuration: {seed_config.name}")
        results = run_single_test(
            dut_config=config.dut_target,
            seed_config=seed_config,
            config_filename=config_filename,
            global_logger=logger
        )
        total_results.extend(results)
    
    # End time
    end_time = datetime.now()
    logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    # Format Duration
    duration_text = format_duration(start_time, end_time)
    
    # Generate summary report
    passed = sum(1 for r in total_results if r.result_type == ResultType.SUCCESS)
    failed = sum(1 for r in total_results if r.result_type == ResultType.FAILURE)
    timeouts = sum(1 for r in total_results if r.result_type == ResultType.TIMEOUT)
    errors = sum(1 for r in total_results if r.result_type == ResultType.ERROR)
    total = len(total_results)
    
    generate_summary_report(
        dut_name=f"{config.dut_target.name} ({config.dut_target.diff_ref}) {config.dut_target.version}",
        total_seeds=total,
        passed=passed,
        failed=failed,
        issues=timeouts + errors,
        logger=logger
    )
    
    logger.info(
        f"Testing completed: {passed} passed, {failed} failed, "
        f"{timeouts} timed out, {errors} errors. Total: {total}. Duration: {duration_text}"
    )
    
    return total_results
