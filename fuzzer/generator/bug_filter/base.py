# Copyright (c) 2024-2025 Institute of Information Engineering, Chinese Academy of Sciences
#
# DiveFuzz is licensed under Mulan PSL v2.
# See http://license.coscl.org.cn/MulanPSL2 for more details.

"""
Filter Base Classes

Two-phase filtering:
- Pre-execution (Level 1): φ(s_pre, opcode, operand)
- Post-execution (Level 2/3): φ(s_pre, s_post) or φ(s_pre, opcode, operand, s_post)

Usage:
    from bug_filter import pre_execution_filter, post_execution_filter, FilterResult

    @pre_execution_filter(name="div_by_zero", opcodes=["div"])
    def check_div(ctx):
        if ctx.get_xpr(1) == 0:
            return FilterResult.reject("Division by zero")
        return FilterResult.accept()
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Callable, List
from dataclasses import dataclass
import sys

from .context import FilterContext


class FilterPhase(Enum):
    PRE_EXECUTION = "pre"
    POST_EXECUTION = "post"


@dataclass(frozen=True)
class FilterResult:
    """Filter check result."""

    should_filter: bool
    reason: Optional[str]

    @classmethod
    def accept(cls) -> "FilterResult":
        return cls(should_filter=False, reason=None)

    @classmethod
    def reject(cls, reason: str) -> "FilterResult":
        return cls(should_filter=True, reason=reason)


class PrecisionFilter(ABC):
    """Base class for precision filters."""

    def __init__(
        self,
        name: str,
        phase: FilterPhase,
        architectures: Optional[List[str]] = None,
        opcodes: Optional[List[str]] = None,
        description: str = "",
        priority: int = 100,
        enabled: bool = True,
    ):
        self.name = name
        self.phase = phase
        self.architectures = architectures or []
        self.opcodes = opcodes or []
        self.description = description
        self.priority = priority
        self.enabled = enabled

    @abstractmethod
    def check(self, ctx: FilterContext) -> FilterResult:
        pass

    def applies_to_architecture(self, architecture: str) -> bool:
        if not self.architectures:
            return True
        return architecture.lower() in [a.lower() for a in self.architectures]

    def applies_to_opcode(self, opcode: str) -> bool:
        if not self.opcodes:
            return True
        opcode_lower = opcode.lower()
        for pattern in self.opcodes:
            pattern_lower = pattern.lower()
            if pattern_lower == "*":
                return True
            if pattern_lower.endswith("*"):
                if opcode_lower.startswith(pattern_lower[:-1]):
                    return True
            else:
                if opcode_lower == pattern_lower:
                    return True
        return False

    def should_apply(self, ctx: FilterContext) -> bool:
        if not self.enabled:
            return False
        if not self.applies_to_architecture(ctx.architecture):
            return False
        if not self.applies_to_opcode(ctx.opcode):
            return False
        return True


class FunctionFilter(PrecisionFilter):
    """Function-based filter wrapper."""

    def __init__(
        self,
        name: str,
        phase: FilterPhase,
        check_func: Callable[[FilterContext], FilterResult],
        architectures: Optional[List[str]] = None,
        opcodes: Optional[List[str]] = None,
        description: str = "",
        priority: int = 100,
        enabled: bool = True,
    ):
        super().__init__(
            name=name,
            phase=phase,
            architectures=architectures,
            opcodes=opcodes,
            description=description,
            priority=priority,
            enabled=enabled,
        )
        self._check_func = check_func

    def check(self, ctx: FilterContext) -> FilterResult:
        return self._check_func(ctx)


# =============================================================================
# Decorators
# =============================================================================


def pre_execution_filter(
    name: str,
    architectures: Optional[List[str]] = None,
    opcodes: Optional[List[str]] = None,
    description: str = "",
    priority: int = 100,
):
    """Decorator for pre-execution filters."""

    def decorator(func: Callable[[FilterContext], FilterResult]) -> FunctionFilter:
        return FunctionFilter(
            name=name,
            phase=FilterPhase.PRE_EXECUTION,
            check_func=func,
            architectures=architectures,
            opcodes=opcodes,
            description=description,
            priority=priority,
        )

    return decorator


def post_execution_filter(
    name: str,
    architectures: Optional[List[str]] = None,
    opcodes: Optional[List[str]] = None,
    description: str = "",
    priority: int = 100,
):
    """Decorator for post-execution filters."""

    def decorator(func: Callable[[FilterContext], FilterResult]) -> FunctionFilter:
        return FunctionFilter(
            name=name,
            phase=FilterPhase.POST_EXECUTION,
            check_func=func,
            architectures=architectures,
            opcodes=opcodes,
            description=description,
            priority=priority,
        )

    return decorator


# =============================================================================
# Auto-Collection
# =============================================================================


def collect_filters_from_caller() -> List[PrecisionFilter]:
    """
    Collect all filter instances from the calling module.

    Scans the module for all PrecisionFilter instances (including FunctionFilter).
    Use this in register_filters() to auto-register decorated filters.

    Example:
        @pre_execution_filter(name="my_filter", opcodes=["div"])
        def my_filter(ctx):
            return FilterResult.accept()

        # my_filter is now a FunctionFilter instance at module level

        def register_filters(registry):
            for f in collect_filters_from_caller():
                registry.register(f)
    """
    # Get the calling module (skip this module)
    frame = sys._getframe(1)
    module_name = frame.f_globals.get("__name__")

    if not module_name:
        return []

    # Import the calling module
    import importlib

    try:
        module = importlib.import_module(module_name)
    except:
        return []

    # Collect all PrecisionFilter instances
    filters = []
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, PrecisionFilter):
            filters.append(obj)

    return filters


# =============================================================================
# Convenience Subclasses (for type-level distinction)
# =============================================================================


class PreExecutionFilter(PrecisionFilter):
    """
    Base class for pre-execution filters (Level 1: φ(s_pre, opcode, operand)).

    Subclass this when implementing a pre-execution filter as a class.
    For simple cases, prefer the @pre_execution_filter decorator.

    Example:
        class DivByZeroFilter(PreExecutionFilter):
            def __init__(self):
                super().__init__(name="div_by_zero", opcodes=["div"])

            def check(self, ctx) -> FilterResult:
                if ctx.get_xpr(2) == 0:
                    return FilterResult.reject("Division by zero")
                return FilterResult.accept()
    """

    def __init__(self, name: str, **kwargs):
        super().__init__(name, FilterPhase.PRE_EXECUTION, **kwargs)


class PostExecutionFilter(PrecisionFilter):
    """
    Base class for post-execution filters (Level 2/3: φ(s_pre, s_post) or
    φ(s_pre, opcode, operand, s_post)).

    Subclass this when implementing a post-execution filter as a class.
    For simple cases, prefer the @post_execution_filter decorator.

    Example:
        class TrapFilter(PostExecutionFilter):
            def __init__(self):
                super().__init__(name="trap_filter")

            def check(self, ctx) -> FilterResult:
                if ctx.was_trapped():
                    return FilterResult.reject("Instruction caused trap")
                return FilterResult.accept()
    """

    def __init__(self, name: str, **kwargs):
        super().__init__(name, FilterPhase.POST_EXECUTION, **kwargs)


__all__ = [
    "FilterPhase",
    "FilterResult",
    "PrecisionFilter",
    "PreExecutionFilter",
    "PostExecutionFilter",
    "FunctionFilter",
    "pre_execution_filter",
    "post_execution_filter",
    "collect_filters_from_caller",
]
