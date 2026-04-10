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
RISC-V Register Name Mappings — Single Source of Truth

All XPR and FPR name<->number mappings live here.
Other modules import from here instead of defining their own copies.
"""

from typing import Dict, List, Optional

# =============================================================================
# Integer (XPR) registers
# =============================================================================

# ABI name → register number (0-31)
XPR_ABI_TO_NUM: Dict[str, int] = {
    "zero": 0,
    "ra": 1,
    "sp": 2,
    "gp": 3,
    "tp": 4,
    "t0": 5, "t1": 6, "t2": 7,
    "s0": 8, "fp": 8,   # s0 and fp are aliases for x8
    "s1": 9,
    "a0": 10, "a1": 11,
    "a2": 12, "a3": 13, "a4": 14, "a5": 15, "a6": 16, "a7": 17,
    "s2": 18, "s3": 19, "s4": 20, "s5": 21, "s6": 22, "s7": 23,
    "s8": 24, "s9": 25, "s10": 26, "s11": 27,
    "t3": 28, "t4": 29, "t5": 30, "t6": 31,
}

# Register number → canonical ABI name (index 8 = "s0", not "fp")
XPR_NAMES: List[str] = [
    "zero", "ra",  "sp",  "gp",  "tp",  "t0",  "t1",  "t2",
    "s0",   "s1",  "a0",  "a1",  "a2",  "a3",  "a4",  "a5",
    "a6",   "a7",  "s2",  "s3",  "s4",  "s5",  "s6",  "s7",
    "s8",   "s9",  "s10", "s11", "t3",  "t4",  "t5",  "t6",
]

# =============================================================================
# Floating-point (FPR) registers
# =============================================================================

# ABI name → register number (0-31)
FPR_ABI_TO_NUM: Dict[str, int] = {
    "ft0": 0,  "ft1": 1,  "ft2": 2,  "ft3": 3,
    "ft4": 4,  "ft5": 5,  "ft6": 6,  "ft7": 7,
    "fs0": 8,  "fs1": 9,
    "fa0": 10, "fa1": 11,
    "fa2": 12, "fa3": 13, "fa4": 14, "fa5": 15, "fa6": 16, "fa7": 17,
    "fs2": 18, "fs3": 19, "fs4": 20, "fs5": 21, "fs6": 22, "fs7": 23,
    "fs8": 24, "fs9": 25, "fs10": 26, "fs11": 27,
    "ft8": 28, "ft9": 29, "ft10": 30, "ft11": 31,
}

# Register number → canonical ABI name
FPR_NAMES: List[str] = [
    "ft0",  "ft1",  "ft2",  "ft3",  "ft4",  "ft5",  "ft6",  "ft7",
    "fs0",  "fs1",  "fa0",  "fa1",  "fa2",  "fa3",  "fa4",  "fa5",
    "fa6",  "fa7",  "fs2",  "fs3",  "fs4",  "fs5",  "fs6",  "fs7",
    "fs8",  "fs9",  "fs10", "fs11", "ft8",  "ft9",  "ft10", "ft11",
]


# =============================================================================
# Helper utilities
# =============================================================================

class RegisterMapping:
    """Utility class for converting RISC-V register names to numbers."""

    @staticmethod
    def xpr_name_to_num(reg_name: str) -> Optional[int]:
        """
        Convert integer register name to number (0-31).
        Accepts x0-x31 format and ABI names (zero/ra/sp/…/t6/fp).
        """
        reg_name = reg_name.strip().lower()
        if reg_name.startswith('x'):
            try:
                num = int(reg_name[1:])
                if 0 <= num <= 31:
                    return num
            except ValueError:
                pass
        return XPR_ABI_TO_NUM.get(reg_name)

    @staticmethod
    def fpr_name_to_num(reg_name: str) -> Optional[int]:
        """
        Convert floating-point register name to number (0-31).
        Accepts f0-f31 format and ABI names (ft0-ft11/fs0-fs11/fa0-fa7).
        """
        reg_name = reg_name.strip().lower()
        if reg_name.startswith('f') and len(reg_name) >= 2:
            try:
                num = int(reg_name[1:])
                if 0 <= num <= 31:
                    return num
            except ValueError:
                pass
        return FPR_ABI_TO_NUM.get(reg_name)

    @staticmethod
    def is_float_register(reg_name: str) -> bool:
        """
        Return True if the name refers to a floating-point register.

        Note: 'fp' is an INTEGER register alias (s0/x8), not float!
        """
        reg_name = reg_name.strip().lower()
        if reg_name == 'fp':
            return False
        if reg_name in FPR_ABI_TO_NUM:
            return True
        if reg_name.startswith('f') and len(reg_name) >= 2:
            try:
                num = int(reg_name[1:])
                return 0 <= num <= 31
            except ValueError:
                pass
        return False

    @staticmethod
    def convert_register_name_smart(reg_name: str) -> Optional[int]:
        """Convert register name to number, auto-detecting XPR vs FPR."""
        if RegisterMapping.is_float_register(reg_name):
            return RegisterMapping.fpr_name_to_num(reg_name)
        return RegisterMapping.xpr_name_to_num(reg_name)

    @staticmethod
    def convert_register_names(reg_names: List[str], is_float: bool) -> Optional[List[int]]:
        """
        Convert a list of register names to numbers.
        DEPRECATED: use convert_register_names_smart() for mixed instructions.
        """
        converter = RegisterMapping.fpr_name_to_num if is_float else RegisterMapping.xpr_name_to_num
        result = []
        for name in reg_names:
            num = converter(name)
            if num is None:
                print(f"ERROR: Failed to convert register name '{name}'")
                return None
            result.append(num)
        return result

    @staticmethod
    def convert_register_names_smart(reg_names: List[str]) -> Optional[List[int]]:
        """Convert a list of register names, auto-detecting each register's type."""
        result = []
        for name in reg_names:
            num = RegisterMapping.convert_register_name_smart(name)
            if num is None:
                print(f"ERROR: Failed to convert register name '{name}'")
                return None
            result.append(num)
        return result
