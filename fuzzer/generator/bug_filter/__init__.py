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

    def filter_known_bug(self, instr_op: str, source_values: List[int]) -> Optional[str]:
        """
        Check if an instruction triggers a known bug based on source register values

        Matches source register VALUES against bug patterns.
        Pattern format: (source_pattern1, source_pattern2, ...)

        This check is performed BEFORE instruction execution, using only source
        register values to filter out instructions that would trigger known bugs.

        Args:
            instr_op: Instruction opcode (e.g., "div", "sc.w", "csrrw")
            source_values: Source register VALUES before execution

        Returns:
            Bug name if instruction matches a known bug pattern, None otherwise

        Example:
            # Filter division by zero: div rd, rs1, rs2 where rs2=0
            add_bug(reg, 'div', 'div by zero', '*', '0')
            # source_values = [rs1_value, rs2_value]
            # Pattern matches if rs2_value == 0
        """
        return match_bug(self.registry, instr_op, source_values)

bug_filter = Filter()
