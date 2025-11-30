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

from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ArchConfig:
    """
    Architecture/ABI configuration:
    - arch_bits: word width (32/64)
    - isa:      -march, such as 'rv64gc' / 'rv32gc'
    - abi:      -mabi, such as 'lp64d' / 'ilp32d'
    """
    arch_bits: int = 64
    isa: str = "rv64gc"

    def is_rv64(self) -> bool:
        return self.arch_bits == 64

    def is_rv32(self) -> bool:
        return self.arch_bits == 32
    
    def get_arch_bits(self) -> int:
        return self.arch_bits
    
    def get_isa(self) -> str:
        return self.isa
