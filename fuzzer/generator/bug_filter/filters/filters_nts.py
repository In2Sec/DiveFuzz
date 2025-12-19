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
NutShell Known Bug Filters

This module defines known bugs found in NutShell processor through DiveFuzz testing.
These filters can be enabled to avoid generating test cases that trigger known bugs.

Reference: Bug analysis from 2025-12-14 testing
"""

from . import add_bug, Registry


def register(reg: Registry) -> None:
    """
    Register NutShell known bugs to the filter registry.
    """
    pass
