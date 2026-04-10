# Copyright (c) 2024-2025 Institute of Information Engineering, Chinese Academy of Sciences
#
# DiveFuzz is licensed under Mulan PSL v2.
# See http://license.coscl.org.cn/MulanPSL2 for more details.

"""
CVA6 Processor Filters

Add filters using decorators - they are automatically collected:

    from bug_filter import pre_execution_filter, FilterResult

    @pre_execution_filter(name="my_filter", opcodes=["div"])
    def my_filter(ctx):
        if condition:
            return FilterResult.reject("reason")
        return FilterResult.accept()
"""

from .. import (
    pre_execution_filter,
    post_execution_filter,
    FilterResult,
    collect_filters_from_caller,
)


def register_filters(registry):
    """Register all filters - automatically collects decorated functions."""
    for f in collect_filters_from_caller():
        registry.register(f)


__all__ = ["register_filters"]
