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

import logging
import sys
import os
import time
from pathlib import Path
from contextlib import contextmanager

def setup_logging(log_file=None, level=logging.INFO, console=True):
    """
    Configure global root logger.

    Args:
        log_file (str): Path to the global log file (optional)
        level (int): Logging level
        console (bool): Enable console output
    """
    # Clear existing handlers to avoid duplication
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove all existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Setup formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Add console handler if needed
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

    # Add file handler if log_file is specified
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

def create_output_dir():
    """Create output directory for test logs"""
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    return output_dir

@contextmanager
def create_test_logger(test_name, config_filename, enable_timestamp=False):
    """
    Create a dedicated test logger with file handler (context manager).
    
    Args:
        test_name: Name of the test 
        config_filename: Configuration file name
        enable_timestamp: Enable timestamp in log file name
    
    Yields:
        Tuple: (logger_object, log_file_path)
    """
    config_stem = Path(config_filename).stem
    safe_test_name = test_name.replace(" ", "_").replace(os.sep, "_")
    if enable_timestamp:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_filename = f"{config_stem}-{safe_test_name}-{timestamp}.log"
    else:
        log_filename = f"{config_stem}-{safe_test_name}.log"
    output_dir = create_output_dir()
    log_path = output_dir / log_filename
    
    # Create unique test logger (not root)
    logger = logging.getLogger(f"test.{safe_test_name}")
    logger.setLevel(logging.DEBUG)
    
    # File handler only for this logger
    file_handler = logging.FileHandler(log_path, mode='w')
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Prevent propagation to avoid double logging
    logger.propagate = False 
    logger.addHandler(file_handler)
    
    try:
        yield logger, str(log_path)
    finally:
        # Cleanup handler to release resources
        logger.removeHandler(file_handler)
        file_handler.close()

def get_global_logger(name=None):
    """Get global logger instance"""
    return logging.getLogger(name or "global")
