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
        
    def filter_known_bug(self, instr_op: str, register_values: List[int]) -> Optional[str]:
        return match_bug(self.registry, instr_op, register_values)
    
bug_filter = Filter()
