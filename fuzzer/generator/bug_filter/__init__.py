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

from .filters import get_known_bugs, match_bug
from typing import List, Optional

class Filter:
    def __init__(self):
        self.registry = {}

    def set_architecture(self, architecture: str) -> None:
        self.registry = get_known_bugs(architecture)

    def filter_known_bug(self, instr_op: str, dest_values: List[int], source_values: List[int]) -> Optional[str]:
        """
        Check if an instruction triggers a known bug based on register values

        Matches actual register VALUES (not indices) against bug patterns.
        Pattern format: (dest_pattern, source_pattern1, source_pattern2, ...)

        Args:
            instr_op: Instruction opcode (e.g., "sc.w", "csrrw")
            dest_values: Destination register VALUES after execution (usually 1 element)
            source_values: Source register VALUES before execution

        Returns:
            Bug name if instruction matches a known bug pattern, None otherwise
        """
        # Combine dest and source values for pattern matching
        # Pattern format: (dest1, dest2, ..., src1, src2, ...)
        all_values = dest_values + source_values
        return match_bug(self.registry, instr_op, all_values)

bug_filter = Filter()
