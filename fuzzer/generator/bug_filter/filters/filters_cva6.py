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
CVA6 Known Bug Filters

This module defines known bugs found in cva6 processor through DiveFuzz testing.
These filters can be enabled to avoid generating test cases that trigger known bugs.

"""

from . import add_bug, add_csr_blacklist, Registry, CSRBlacklist


def register(reg: Registry) -> None:
    pass


def register_csr_blacklist(blacklist: CSRBlacklist) -> None:
    pass

