# Copyright (c) 2024-2025 Institute of Information Engineering, Chinese Academy of Sciences
#
# DiveFuzz is licensed under Mulan PSL v2.
# See http://license.coscl.org.cn/MulanPSL2 for more details.

"""
Architecture-Specific Filters

Add filters using decorators in arch/<arch>_filters.py:

    from bug_filter import pre_execution_filter, FilterResult

    @pre_execution_filter(name="my_filter", opcodes=["div"])
    def my_filter(ctx):
        if condition:
            return FilterResult.reject("reason")
        return FilterResult.accept()

    def register_filters(registry):
        registry.register(my_filter)
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bug_filter import FilterRegistry


def register_architecture_filters(
    architecture: str, registry: "FilterRegistry"
) -> None:
    """Register all filters for an architecture."""
    arch = architecture.lower()

    if arch in ("xs", "xiangshan"):
        from . import xs_filters

        xs_filters.register_filters(registry)
    elif arch in ("nts", "nutshell"):
        from . import nts_filters

        nts_filters.register_filters(registry)
    elif arch == "cva6":
        from . import cva6_filters

        cva6_filters.register_filters(registry)
    elif arch == "boom":
        from . import boom_filters

        boom_filters.register_filters(registry)
    elif arch in ("rkt", "rocket"):
        from . import rocket_filters

        rocket_filters.register_filters(registry)


def get_supported_architectures() -> list:
    """Get list of supported architectures."""
    return ["xs", "nts", "cva6", "boom", "rocket"]


__all__ = [
    "register_architecture_filters",
    "get_supported_architectures",
]
