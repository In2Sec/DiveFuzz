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

"""
Instruction Post Processor

Handles post-execution processing of instructions including:
- XOR value computation from register values
- Bug filtering based on known bug patterns
- XOR uniqueness checking within opcode groups

This module decouples the validation logic from spike_session,
making the architecture more modular and testable.
"""

from typing import Optional, List, Tuple

try:
    from ..bug_filter import bug_filter
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from bug_filter import bug_filter


def compute_xor(values: List[int]) -> int:
    """
    Compute XOR value from register values using shifted XOR.
    Replicates the C++ compute_xor algorithm.

    Formula: result = (values[0] << 0) ^ (values[1] << 1) ^ (values[2] << 2) ^ ...

    Args:
        values: List of register values (and optional immediate)

    Returns:
        Computed XOR value as uint64_t equivalent
    """
    result = 0
    for i, value in enumerate(values):
        result ^= (value << i)
    return result


class InstructionPostProcessor:
    """
    Post-processor for instruction validation results.

    Combines XOR computation and bug filtering in one place,
    decoupled from SpikeSession's execution logic.

    Usage:
        processor = InstructionPostProcessor(shared_xor_cache, architecture)

        # After executing instruction in spike:
        result = processor.process_result(
            opcode="add",
            source_values=[val1, val2],
            dest_values=[result_val]
        )

        if result.is_valid:
            # Instruction is unique and doesn't trigger bugs
            processor.confirm_xor(result.opcode, result.xor_value)
    """

    def __init__(self, shared_xor_cache, architecture: str = ""):
        """
        Initialize post processor.

        Args:
            shared_xor_cache: Manager.dict for cross-process XOR sharing
            architecture: Architecture name for bug filtering ('xs', 'nts', 'rkt', 'kmh')
        """
        self.confirmed_xor_values = shared_xor_cache

        # Initialize bug filter if architecture is specified
        if architecture:
            bug_filter.set_architecture(architecture)

    def compute_xor(self, source_values: List[int]) -> int:
        """
        Compute XOR value from source register values.

        Args:
            source_values: Source register values before execution

        Returns:
            Computed XOR value
        """
        return compute_xor(source_values)

    def check_known_bug(
        self,
        opcode: str,
        dest_values: List[int],
        source_values: List[int]
    ) -> Optional[str]:
        """
        Check if instruction triggers a known bug.

        Args:
            opcode: Instruction opcode (e.g., "add", "sc.w")
            dest_values: Destination register values after execution
            source_values: Source register values before execution

        Returns:
            Bug name if instruction matches a known bug pattern, None otherwise
        """
        return bug_filter.filter_known_bug(opcode, dest_values, source_values)

    def check_xor_uniqueness(self, opcode: str, xor_value: int) -> bool:
        """
        Check if XOR value is unique within its opcode group.

        Args:
            opcode: Instruction opcode
            xor_value: Computed XOR value

        Returns:
            True if unique, False if duplicate

        Raises:
            RuntimeError: If Manager connection fails after retries
        """
        max_retries = 3
        retry_delay = 0.01  # 10ms

        for retry in range(max_retries):
            try:
                if opcode not in self.confirmed_xor_values:
                    self.confirmed_xor_values[opcode] = []

                # Check uniqueness (list membership check)
                return xor_value not in self.confirmed_xor_values[opcode]

            except (TypeError, BrokenPipeError, EOFError) as e:
                if retry < max_retries - 1:
                    import time
                    time.sleep(retry_delay * (2 ** retry))
                    continue
                else:
                    raise RuntimeError(
                        f"Manager connection lost after {max_retries} retries. "
                        f"Opcode: {opcode}, Error: {e}"
                    )

        return False  # Should not reach here

    def process_result(
        self,
        opcode: str,
        source_values: List[int],
        dest_values: List[int]
    ) -> Tuple[Optional[int], bool, Optional[str]]:
        """
        Process instruction execution result.

        Performs XOR computation, uniqueness check, and bug filtering.

        Args:
            opcode: Instruction opcode
            source_values: Source register values before execution
            dest_values: Destination register values after execution

        Returns:
            Tuple of (xor_value, is_unique, bug_name):
            - xor_value: Computed XOR value
            - is_unique: True if XOR is unique within opcode group
            - bug_name: Bug name if triggers known bug, None otherwise
        """
        # 1. Compute XOR from source values
        xor_value = self.compute_xor(source_values)

        # 2. Check XOR uniqueness
        is_unique = self.check_xor_uniqueness(opcode, xor_value)

        if not is_unique:
            return xor_value, False, None

        # 3. Check for known bugs
        bug_name = self.check_known_bug(opcode, dest_values, source_values)

        return xor_value, True, bug_name

    def confirm_xor(self, opcode: str, xor_value: int):
        """
        Confirm an XOR value as accepted.

        Should be called after instruction is validated and accepted.

        Args:
            opcode: Instruction opcode
            xor_value: XOR value to add to confirmed list

        Raises:
            RuntimeError: If Manager connection fails after retries
        """
        max_retries = 3
        retry_delay = 0.01  # 10ms

        for retry in range(max_retries):
            try:
                if opcode not in self.confirmed_xor_values:
                    self.confirmed_xor_values[opcode] = []

                # Get current list, append value, then reassign to trigger sync
                current_list = list(self.confirmed_xor_values[opcode])
                current_list.append(xor_value)
                self.confirmed_xor_values[opcode] = current_list
                return

            except (TypeError, BrokenPipeError, EOFError) as e:
                if retry < max_retries - 1:
                    import time
                    time.sleep(retry_delay * (2 ** retry))
                    continue
                else:
                    raise RuntimeError(
                        f"Manager connection lost in confirm_xor after {max_retries} retries. "
                        f"Opcode: {opcode}, Error: {e}"
                    )


class ProcessResult:
    """
    Result of instruction post-processing.

    Attributes:
        xor_value: Computed XOR value
        is_unique: Whether XOR is unique within opcode group
        bug_name: Name of triggered bug, or None
        is_valid: True if instruction is unique and doesn't trigger bugs
    """

    def __init__(
        self,
        xor_value: int,
        is_unique: bool,
        bug_name: Optional[str] = None
    ):
        self.xor_value = xor_value
        self.is_unique = is_unique
        self.bug_name = bug_name

    @property
    def is_valid(self) -> bool:
        """Instruction is valid if unique and no bug triggered."""
        return self.is_unique and self.bug_name is None


if __name__ == "__main__":
    print("InstructionPostProcessor module")
    print("Provides XOR computation and bug filtering for instruction validation")
