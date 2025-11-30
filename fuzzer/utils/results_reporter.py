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

from datetime import datetime
from enum import Enum, auto
import re
import logging
import sys


class ResultType(Enum):
    SUCCESS = auto()
    FAILURE = auto()
    TIMEOUT = auto()
    ERROR = auto()

# ANSI Color Codes


class TermColor:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'

    @staticmethod
    def colorize(text, color_code):
        """Add color to text (if supported)"""
        # Check if running in a terminal (to avoid using colors in file output)
        if sys.stdout.isatty():
            return f"{color_code}{text}{TermColor.ENDC}"
        return text

    @staticmethod
    def success(text):
        return TermColor.colorize(text, TermColor.GREEN + TermColor.BOLD)

    @staticmethod
    def warning(text):
        return TermColor.colorize(text, TermColor.YELLOW + TermColor.BOLD)

    @staticmethod
    def error(text):
        return TermColor.colorize(text, TermColor.RED + TermColor.BOLD)

    @staticmethod
    def info(text):
        return TermColor.colorize(text, TermColor.BLUE)

    @staticmethod
    def header(text):
        return TermColor.colorize(text, TermColor.HEADER + TermColor.BOLD)

    @staticmethod
    def underline(text):
        return TermColor.colorize(text, TermColor.UNDERLINE)

    @staticmethod
    def dim(text):
        return TermColor.colorize(text, TermColor.DIM)


def strip_ansi_codes(s) -> str:
    """Remove ANSI color codes from a string"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', s)


class TestResult:
    def __init__(self, dut_name, version, diff_ref, seed_name,
                 result_type, summary, log_path):
        self.dut_name = dut_name
        self.version = version
        self.diff_ref = diff_ref
        self.seed_name = seed_name
        self.result_type = result_type
        self.summary = summary
        self.log_path = log_path


def generate_report_block(content_lines, color):
    """Generate a complete report block with borders"""
    MAX_WIDTH = 78

    # Ensure that all lines do not exceed the maximum width
    stripped_lines = [(strip_ansi_codes(line) if isinstance(
        line, str) else line) for line in content_lines]
    max_line_len = max((len(strip_ansi_codes(str(line)))
                       for line in stripped_lines), default=0)

    # Calculate actual width (ensure it doesn't exceed MAX_WIDTH)
    box_width = min(MAX_WIDTH, max_line_len + 4)

    # Create borders
    top_border = color(f"+{'-' * (box_width - 2)}+")
    bottom_border = color(f"+{'-' * (box_width - 2)}+")

    # Build content lines
    box_lines = []
    for line in content_lines:
        # Ensure content is in the correct position
        visible_len = len(strip_ansi_codes(str(line)))
        # Subtract | and the spaces on both sides
        padding_len = box_width - visible_len - 4
        if padding_len < 0:
            # If the content is too long, truncate it
            if isinstance(line, str):
                line = line[:padding_len - 4] + "..."
            else:
                line = str(line)[:padding_len - 4] + "..."
            visible_len = len(strip_ansi_codes(line))
            padding_len = box_width - visible_len - 4

        box_line = color("| ") + str(line) + (" " * padding_len) + color(" |")
        box_lines.append(box_line)

    # Add top and bottom borders
    return [top_border] + box_lines + [bottom_border]


def generate_result_report(test_result, logger):
    # Determine color based on result type
    color_map = {
        ResultType.SUCCESS: TermColor.success,
        ResultType.FAILURE: TermColor.error,
        ResultType.TIMEOUT: TermColor.warning,
        ResultType.ERROR: TermColor.error
    }

    # Get the result color function
    colorize = color_map.get(test_result.result_type, TermColor.info)

    # Create the content block
    content_lines = [
        TermColor.header(test_result.dut_name),
        f"   Version: {TermColor.info(test_result.version)}",
        f"   Ref: \"{TermColor.info(test_result.diff_ref)}\"",
        "=" * 72,
    ]

    # Symbols and status text
    if test_result.result_type == ResultType.SUCCESS:
        symbol = "✓"
        status = f"{symbol} Passed!"
        status_line = TermColor.success(status)
    elif test_result.result_type == ResultType.TIMEOUT:
        symbol = "⚠"
        status = f"{symbol} Timeout!"
        status_line = TermColor.warning(status)
    else:  # FAILURE or ERROR
        symbol = "✗"
        status = f"{symbol} Failed!"
        status_line = TermColor.error(status)

    result_lines = [
        status_line,
    ]

    # Add summary and log
    if test_result.summary:
        result_lines.append(f"  {test_result.summary}")

    result_lines.extend([
        "",
        f"  Log: {TermColor.underline(test_result.log_path)}"
    ])

    # Merge all lines
    all_lines = content_lines + result_lines

    # Generate report block
    report_lines = generate_report_block(all_lines, colorize)
    report = "\n".join(report_lines)

    # Output report using the global logger
    logger.info(f"\n{report}")

    # Log the detailed log path based on the test result type
    level = logging.INFO if test_result.result_type == ResultType.SUCCESS else logging.ERROR
    logger.log(
        level, f"Detailed log saved to: {TermColor.underline(test_result.log_path)}")


def generate_summary_report(dut_name, total_seeds, passed, failed, issues, logger):
    """
    Generate a test summary report

    Args:
        dut_name: Name of the DUT
        total_seeds: Total number of seeds
        passed: Number of passed tests
        failed: Number of failed tests
        issues: Number of issues (timeouts, errors, etc.)
        logger: Logger for logging the report
    """
    # Calculate percentage
    pass_percent = (passed / total_seeds) * 100 if total_seeds > 0 else 0

    # Create progress bar
    progress_width = 50
    
    if total_seeds == 0:
        passed_width = 0
    else:
        passed_width = int(progress_width * passed / total_seeds)
    
    if total_seeds == 0:
        failed_width = 0
    else:
        failed_width = int(progress_width * failed / total_seeds)
    issues_width = progress_width - passed_width - failed_width

    progress_bar = (
        TermColor.success('=' * passed_width) +
        TermColor.error('=' * failed_width) +
        TermColor.warning('=' * issues_width)
    )

    # Create content block
    title = TermColor.header(f"TEST SUMMARY")

    dut_info = TermColor.info(f"DUT: {dut_name}")
    progress = f"[{progress_bar}] {pass_percent:.1f}% ({passed}/{total_seeds})"

    # Statistics lines
    stats_lines = [
        f"Testing completed:",
        f"  {TermColor.success(str(passed) + ' passed')}, ",
        f"  {TermColor.error(str(failed) + ' failed')}, ",
        f"  {TermColor.warning(str(issues) + ' with issues')}."
    ]

    # Add icons
    if failed > 0 or issues > 0:
        icon = TermColor.error("✗")
        overall_result = "Some tests failed or had issues"
    elif total_seeds == 0:
        icon = TermColor.warning("⚠")
        overall_result = "No tests were executed"
    else:
        icon = TermColor.success("✓")
        overall_result = "All tests passed successfully"

    # Overall result line
    overall_line = f"{icon} Overall: {overall_result}"

    # All content lines
    content_lines = [
        "",
        title,
        "",
        dut_info,
        "",
        progress,
        "",
        *stats_lines,
        "",
        overall_line
    ]

    # Generate report block
    report_lines = generate_report_block(content_lines, TermColor.header)
    report = "\n".join(report_lines)

    # Output report and add separator empty lines
    logger.info("")
    logger.info('\n' + report)
    logger.info("")

def format_duration(start_time: datetime, end_time: datetime) -> str:
    duration = end_time - start_time
    milliseconds = duration.microseconds // 1000
    seconds = duration.seconds
    duration_text = f"{seconds}.{milliseconds:03d} s"
    
    if seconds >= 60:
        # Convert to minutes and seconds
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        duration_text = f"{minutes} min {remaining_seconds}.{milliseconds:03d} s"
        
        if minutes >= 60:
            # Convert to hours, minutes and seconds
            hours = minutes // 60
            remaining_minutes = minutes % 60
            duration_text = f"{hours} h {remaining_minutes} min {remaining_seconds}.{milliseconds:03d} s"
    
    return duration_text
