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
Filter Registry Module

Manages registration and execution of precision filters.
Supports two-phase filtering (pre/post execution) with efficient lookup.

Usage:
    # Create registry
    registry = FilterRegistry()
    registry.set_architecture('xs')

    # Register filters
    registry.register(MyPreFilter())
    registry.register(MyPostFilter())

    # Pre-execution check
    reason = registry.check_pre_execution(ctx)
    if reason:
        # Reject instruction

    # Post-execution check
    reason = registry.check_post_execution(ctx)
    if reason:
        # Rollback via checkpoint
"""

from typing import List, Optional, Dict
from collections import defaultdict

from .base import (
    PrecisionFilter,
    PreExecutionFilter,
    PostExecutionFilter,
    FilterPhase,
    FilterResult,
)
from .context import FilterContext


class FilterRegistry:
    """
    Central registry for managing precision filters.

    Features:
    - Two-phase filter execution (pre/post)
    - Architecture-aware filtering
    - Priority-based execution order
    - Filter enable/disable control
    - Efficient lookup by phase

    Thread Safety:
        This class is NOT thread-safe. Each worker process should have
        its own registry instance.
    """

    def __init__(self):
        # Separate lists for each phase for efficient access
        self._pre_filters: List[PreExecutionFilter] = []
        self._post_filters: List[PostExecutionFilter] = []

        # Filter name to filter mapping (for quick lookup)
        self._name_to_filter: Dict[str, PrecisionFilter] = {}

    # =========================================================================
    # Registration
    # =========================================================================

    def register(self, filter: PrecisionFilter) -> "FilterRegistry":
        """
        Register a filter with the registry.

        Filters are automatically sorted by phase and priority.

        Args:
            filter: Filter instance to register

        Returns:
            self (for chaining)

        Raises:
            ValueError: If filter with same name already exists
        """
        # Check for duplicate
        if filter.name in self._name_to_filter:
            raise ValueError(f"Filter with name '{filter.name}' already registered")

        # Add to appropriate list
        if filter.phase == FilterPhase.PRE_EXECUTION:
            self._pre_filters.append(filter)
        else:
            self._post_filters.append(filter)

        # Add to name mapping
        self._name_to_filter[filter.name] = filter

        return self

    def register_all(self, filters: List[PrecisionFilter]) -> "FilterRegistry":
        """
        Register multiple filters at once.

        Args:
            filters: List of filters to register

        Returns:
            self (for chaining)
        """
        for f in filters:
            self.register(f)
        return self

    def unregister(self, name: str) -> Optional[PrecisionFilter]:
        """
        Remove a filter by name.

        Args:
            name: Filter name to remove

        Returns:
            Removed filter, or None if not found
        """
        filter = self._name_to_filter.pop(name, None)
        if filter is None:
            return None

        # Remove from phase-specific list
        if filter.phase == FilterPhase.PRE_EXECUTION:
            self._pre_filters = [f for f in self._pre_filters if f.name != name]
        else:
            self._post_filters = [f for f in self._post_filters if f.name != name]

        return filter

    # =========================================================================
    # Filter Control
    # =========================================================================

    def enable_filter(self, name: str) -> bool:
        """
        Enable a filter by name.

        Args:
            name: Filter name

        Returns:
            True if filter was found and enabled
        """
        filter = self._name_to_filter.get(name)
        if filter:
            filter.enable()
            return True
        return False

    def disable_filter(self, name: str) -> bool:
        """
        Disable a filter by name.

        Args:
            name: Filter name

        Returns:
            True if filter was found and disabled
        """
        filter = self._name_to_filter.get(name)
        if filter:
            filter.disable()
            return True
        return False

    def get_filter(self, name: str) -> Optional[PrecisionFilter]:
        """Get a filter by name"""
        return self._name_to_filter.get(name)

    def get_all_filters(self) -> List[PrecisionFilter]:
        """Get all registered filters"""
        return list(self._name_to_filter.values())

    def get_pre_filters(self) -> List[PreExecutionFilter]:
        """Get all pre-execution filters"""
        return list(self._pre_filters)

    def get_post_filters(self) -> List[PostExecutionFilter]:
        """Get all post-execution filters"""
        return list(self._post_filters)

    # =========================================================================
    # Execution
    # =========================================================================

    def check_pre_execution(self, ctx: FilterContext) -> Optional[str]:
        """
        Execute all applicable pre-execution filters.

        Filters are executed in priority order until one rejects
        or all pass.

        Args:
            ctx: Execution context (s_post will be None)

        Returns:
            Rejection reason if instruction should be filtered, None if accepted
        """
        for filter in self._pre_filters:
            # Check if filter applies
            if not filter.should_apply(ctx):
                continue

            # Execute filter
            result = filter.check(ctx)

            # Return on first rejection
            if result.should_filter:
                return result.reason or filter.name

        return None

    def check_post_execution(self, ctx: FilterContext) -> Optional[str]:
        """
        Execute all applicable post-execution filters.

        Filters are executed in priority order until one rejects
        or all pass.

        Args:
            ctx: Execution context (s_post should be populated)

        Returns:
            Rejection reason if instruction should be filtered, None if accepted
        """
        for filter in self._post_filters:
            # Check if filter applies
            if not filter.should_apply(ctx):
                continue

            # Execute filter
            result = filter.check(ctx)

            # Return on first rejection
            if result.should_filter:
                return result.reason or filter.name

        return None

    def check_all(
        self, ctx: FilterContext, include_post: bool = False
    ) -> Optional[str]:
        """
        Execute all applicable filters (both phases).

        This is a convenience method for contexts where both phases
        need to be checked together.

        Args:
            ctx: Execution context
            include_post: Whether to include post-execution filters

        Returns:
            Rejection reason if instruction should be filtered, None if accepted
        """
        # Pre-execution checks
        reason = self.check_pre_execution(ctx)
        if reason:
            return reason

        # Post-execution checks (if requested)
        if include_post:
            reason = self.check_post_execution(ctx)
            if reason:
                return reason

        return None

    # =========================================================================
    # Statistics and Debugging
    # =========================================================================

    def get_stats(self) -> Dict:
        """
        Get statistics about registered filters.

        Returns:
            Dictionary with filter counts and configuration
        """
        enabled_pre = sum(1 for f in self._pre_filters if f.enabled)
        enabled_post = sum(1 for f in self._post_filters if f.enabled)

        return {
            "total_filters": len(self._name_to_filter),
            "pre_filters": {
                "total": len(self._pre_filters),
                "enabled": enabled_pre,
                "disabled": len(self._pre_filters) - enabled_pre,
            },
            "post_filters": {
                "total": len(self._post_filters),
                "enabled": enabled_post,
                "disabled": len(self._post_filters) - enabled_post,
            },
        }

    def __len__(self) -> int:
        """Total number of registered filters"""
        return len(self._name_to_filter)

    def __repr__(self) -> str:
        return (
            f"FilterRegistry("
            f"pre={len(self._pre_filters)}, "
            f"post={len(self._post_filters)})"
        )


# =============================================================================
# Global Registry Instance
# =============================================================================

# Global registry for convenience (used by default in InstructionValidator)
# Each worker process should create its own registry via FilterRegistry()
global_registry = FilterRegistry()


def get_global_registry() -> FilterRegistry:
    """
    Get the global filter registry.

    Note: In multiprocessing environments, each process should
    create its own registry instance instead of using this global.
    """
    return global_registry


def create_registry_for_architecture(architecture: str) -> FilterRegistry:
    """
    Create a new registry for a specific architecture.

    The architecture parameter is used by the caller to register
    the appropriate filters via register_architecture_filters().

    Args:
        architecture: Target architecture (passed to register_architecture_filters)

    Returns:
        New FilterRegistry instance
    """
    return FilterRegistry()
