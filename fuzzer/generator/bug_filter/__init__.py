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
DiveFuzz Precision Filter Module

Two-phase filtering with runtime state inspection.

Usage:
    from bug_filter import (
        FilterRegistry, FilterResult,
        pre_execution_filter, post_execution_filter
    )

    # Create registry
    registry = FilterRegistry()
    registry.set_architecture('xs')

    # Add filter using decorator
    @pre_execution_filter(name="my_filter", opcodes=["div"])
    def my_filter(ctx):
        if ctx.get_xpr(1) == 0:
            return FilterResult.reject("Division by zero")
        return FilterResult.accept()

    registry.register(my_filter)
"""

from typing import List, Optional, Set

# Legacy System
from .filters import get_known_bugs, match_bug


class Filter:
    """Legacy bug filter using pattern matching."""

    def __init__(self):
        self.registry = {}
        self.csr_blacklist: Set[str] = set()

    def set_architecture(self, architecture: str) -> None:
        self.registry, self.csr_blacklist = get_known_bugs(architecture)

    def filter_known_bug(self, opcode: str, source_values: List[int]) -> Optional[str]:
        return match_bug(self.registry, opcode, source_values)

    def is_csr_blacklisted(self, csr_name: str) -> bool:
        return csr_name.lower() in self.csr_blacklist

    def get_csr_blacklist(self) -> Set[str]:
        return self.csr_blacklist


bug_filter = Filter()


# Precision Filter System
from .context import (
    FilterContext,
    PreExecutionState,
    PostExecutionState,
)

from .base import (
    FilterPhase,
    FilterResult,
    PrecisionFilter,
    PreExecutionFilter,
    PostExecutionFilter,
    FunctionFilter,
    pre_execution_filter,
    post_execution_filter,
    collect_filters_from_caller,
)

from .registry import (
    FilterRegistry,
    create_registry_for_architecture,
)


__all__ = [
    # Legacy
    "Filter",
    "bug_filter",
    # Core
    "FilterContext",
    "PreExecutionState",
    "PostExecutionState",
    "FilterPhase",
    "FilterResult",
    "PrecisionFilter",
    "PreExecutionFilter",
    "PostExecutionFilter",
    "FunctionFilter",
    "FilterRegistry",
    "create_registry_for_architecture",
    # Decorators
    "pre_execution_filter",
    "post_execution_filter",
    "collect_filters_from_caller",
]
