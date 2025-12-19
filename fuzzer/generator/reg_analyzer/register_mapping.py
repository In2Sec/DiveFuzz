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
RISC-V Register Name to Number Mapping

Provides utilities to convert register names (e.g., 'x1', 'ra', 'f0', 'fa0')
to register numbers for use with SpikeEngine API.
"""

from typing import Dict, List, Optional

# RISC-V Integer (XPR) Register Mapping
# ABI names -> register numbers
_XPR_ABI_TO_NUM: Dict[str, int] = {
    # Standard ABI names
    "zero": 0,
    "ra": 1,
    "sp": 2,
    "gp": 3,
    "tp": 4,
    "t0": 5, "t1": 6, "t2": 7,
    "s0": 8, "fp": 8,  # s0 and fp are aliases
    "s1": 9,
    "a0": 10, "a1": 11,
    "a2": 12, "a3": 13, "a4": 14, "a5": 15, "a6": 16, "a7": 17,
    "s2": 18, "s3": 19, "s4": 20, "s5": 21, "s6": 22, "s7": 23,
    "s8": 24, "s9": 25, "s10": 26, "s11": 27,
    "t3": 28, "t4": 29, "t5": 30, "t6": 31,
}

# Floating-Point (FPR) Register Mapping
# ABI names -> register numbers
_FPR_ABI_TO_NUM: Dict[str, int] = {
    "ft0": 0, "ft1": 1, "ft2": 2, "ft3": 3, "ft4": 4, "ft5": 5, "ft6": 6, "ft7": 7,
    "fs0": 8, "fs1": 9,
    "fa0": 10, "fa1": 11,
    "fa2": 12, "fa3": 13, "fa4": 14, "fa5": 15, "fa6": 16, "fa7": 17,
    "fs2": 18, "fs3": 19, "fs4": 20, "fs5": 21, "fs6": 22, "fs7": 23,
    "fs8": 24, "fs9": 25, "fs10": 26, "fs11": 27,
    "ft8": 28, "ft9": 29, "ft10": 30, "ft11": 31,
}


class RegisterMapping:
    """Utility class for converting RISC-V register names to numbers"""

    @staticmethod
    def xpr_name_to_num(reg_name: str) -> Optional[int]:
        """
        Convert integer register name to register number.

        Supports:
        - Numeric format: 'x0' to 'x31'
        - ABI names: 'zero', 'ra', 'sp', 'gp', 'tp', 's0-s11', 'a0-a7', 't0-t6', 'fp'

        Args:
            reg_name: Register name (e.g., 'x1', 'ra', 't0')

        Returns:
            Register number (0-31), or None if invalid
        """
        reg_name = reg_name.strip().lower()

        # Handle x0-x31 format
        if reg_name.startswith('x'):
            try:
                num = int(reg_name[1:])
                if 0 <= num <= 31:
                    return num
            except ValueError:
                pass

        # Handle ABI names
        return _XPR_ABI_TO_NUM.get(reg_name)

    @staticmethod
    def fpr_name_to_num(reg_name: str) -> Optional[int]:
        """
        Convert floating-point register name to register number.

        Supports:
        - Numeric format: 'f0' to 'f31'
        - ABI names: 'ft0-ft11', 'fs0-fs11', 'fa0-fa7'

        Args:
            reg_name: Register name (e.g., 'f0', 'fa0', 'ft1')

        Returns:
            Register number (0-31), or None if invalid
        """
        reg_name = reg_name.strip().lower()

        # Handle f0-f31 format
        if reg_name.startswith('f') and len(reg_name) >= 2:
            # Try numeric format first
            try:
                num = int(reg_name[1:])
                if 0 <= num <= 31:
                    return num
            except ValueError:
                pass

        # Handle ABI names
        return _FPR_ABI_TO_NUM.get(reg_name)

    @staticmethod
    def is_float_register(reg_name: str) -> bool:
        """
        Determine if a register name is a floating-point register based on its prefix.

        Args:
            reg_name: Register name (e.g., 'ft4', 'x1', 'ra')

        Returns:
            True if floating-point register, False otherwise
        """
        reg_name = reg_name.strip().lower()

        # Floating-point registers start with 'f' or match FPR ABI names
        if reg_name.startswith('f'):
            return True

        # Check if it's in the FPR ABI mapping
        return reg_name in _FPR_ABI_TO_NUM

    @staticmethod
    def convert_register_name_smart(reg_name: str) -> Optional[int]:
        """
        Intelligently convert a register name to number based on its prefix.

        Automatically detects whether the register is integer or floating-point
        based on the register name itself (not the instruction type).

        Args:
            reg_name: Register name (e.g., 'ft4', 't6', 'fa0', 'sp')

        Returns:
            Register number (0-31), or None if invalid
        """
        if RegisterMapping.is_float_register(reg_name):
            return RegisterMapping.fpr_name_to_num(reg_name)
        else:
            return RegisterMapping.xpr_name_to_num(reg_name)

    @staticmethod
    def convert_register_names(reg_names: List[str], is_float: bool) -> Optional[List[int]]:
        """
        Convert a list of register names to register numbers.

        DEPRECATED: Use convert_register_names_smart() instead.
        This method assumes all registers are the same type (is_float),
        which is incorrect for mixed instructions like 'fsw ft4, 800(t6)'.

        Args:
            reg_names: List of register names
            is_float: True for floating-point registers, False for integer registers

        Returns:
            List of register numbers, or None if any conversion fails
        """
        converter = RegisterMapping.fpr_name_to_num if is_float else RegisterMapping.xpr_name_to_num

        result = []
        for reg_name in reg_names:
            reg_num = converter(reg_name)
            if reg_num is None:
                print(f"ERROR: Failed to convert register name '{reg_name}'")
                return None
            result.append(reg_num)

        return result

    @staticmethod
    def convert_register_names_smart(reg_names: List[str]) -> Optional[List[int]]:
        """
        Convert a list of register names to register numbers (smart mode).

        Automatically detects each register's type based on its name,
        correctly handling mixed instructions like 'fsw ft4, 800(t6)'.

        Args:
            reg_names: List of register names

        Returns:
            List of register numbers, or None if any conversion fails
        """
        result = []
        for reg_name in reg_names:
            reg_num = RegisterMapping.convert_register_name_smart(reg_name)
            if reg_num is None:
                print(f"ERROR: Failed to convert register name '{reg_name}'")
                return None
            result.append(reg_num)

        return result
