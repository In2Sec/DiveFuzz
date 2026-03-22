# Copyright (c) 2024-2025 Institute of Information Engineering, Chinese Academy of Sciences
#
# DiveFuzz is licensed under Mulan PSL v2.
# See http://license.coscl.org.cn/MulanPSL2 for more details.

"""
XiangShan (香山) Processor Filters

Simply use @pre_execution_filter or @post_execution_filter decorators.
All decorated filters are automatically collected.

Example:
    from bug_filter import pre_execution_filter, FilterResult

    @pre_execution_filter(name="my_filter", opcodes=["div"])
    def my_filter(ctx):
        if ctx.get_xpr(1) == 0:
            return FilterResult.reject("Division by zero")
        return FilterResult.accept()

    # No need to manually register - collect_filters_from_caller() handles it!
"""

from .. import (
    pre_execution_filter,
    post_execution_filter,
    FilterResult,
    collect_filters_from_caller,
)


def _parse_csr(ctx):
    """Extract CSR address from instruction context."""
    for op in reversed(ctx.operands):
        op_clean = str(op).strip().rstrip(",")
        if op_clean.isdigit():
            return int(op_clean)
        if op_clean.startswith("0x") or op_clean.startswith("0X"):
            try:
                return int(op_clean, 16)
            except ValueError:
                pass
    return None


# =============================================================================
# CSR Filters (Pre-execution)
# =============================================================================


@pre_execution_filter(
    name="xs_csr_hstatus",
    opcodes=["csrrw", "csrrwi", "csrrs", "csrrsi", "csrrc", "csrrci"],
)
def filter_hstatus(ctx):
    """Filter hstatus CSR (0x600) - WARL fields."""
    csr = _parse_csr(ctx)
    if csr == 0x600:
        return FilterResult.reject("CSR hstatus has WARL fields")
    return FilterResult.accept()


@pre_execution_filter(
    name="xs_csr_vstvec",
    opcodes=["csrrw", "csrrwi", "csrrs", "csrrsi", "csrrc", "csrrci"],
)
def filter_vstvec(ctx):
    """Filter vstvec CSR (0x205) - MODE field implementation-defined."""
    csr = _parse_csr(ctx)
    if csr == 0x205:
        return FilterResult.reject("CSR vstvec MODE field is implementation-defined")
    return FilterResult.accept()


@pre_execution_filter(
    name="xs_csr_stvec",
    opcodes=["csrrw", "csrrwi", "csrrs", "csrrsi", "csrrc", "csrrci"],
)
def filter_stvec(ctx):
    """Filter stvec CSR (0x105) - MODE field implementation-defined."""
    csr = _parse_csr(ctx)
    if csr == 0x105:
        return FilterResult.reject("CSR stvec MODE field is implementation-defined")
    return FilterResult.accept()


@pre_execution_filter(
    name="xs_csr_stimecmp",
    opcodes=["csrrw", "csrrwi", "csrrs", "csrrsi", "csrrc", "csrrci"],
)
def filter_stimecmp(ctx):
    """Filter stimecmp/stimecmph CSRs (0x14D, 0x15D)."""
    csr = _parse_csr(ctx)
    if csr in (0x14D, 0x15D):
        return FilterResult.reject("CSR stimecmp timing is implementation-defined")
    return FilterResult.accept()


# =============================================================================
# Post-execution Filters
# =============================================================================


@post_execution_filter(name="xs_sc_no_reservation", opcodes=["sc.w", "sc.d"])
def filter_sc_reservation(ctx):
    """Filter SC without valid reservation."""
    if not ctx.s_pre.reservation_valid:
        return FilterResult.reject("SC without valid reservation")
    return FilterResult.accept()


@post_execution_filter(name="xs_unexpected_privilege_change")
def filter_privilege_change(ctx):
    """Filter unexpected privilege changes."""
    if not ctx.did_privilege_change():
        return FilterResult.accept()
    expected = {"ecall", "ebreak", "sret", "mret", "uret"}
    if ctx.opcode.lower() not in expected:
        return FilterResult.reject("Unexpected privilege change")
    return FilterResult.accept()


# =============================================================================
# Registration (Auto-collect)
# =============================================================================


def register_filters(registry):
    """Register all filters - automatically collects decorated functions."""
    for f in collect_filters_from_caller():
        registry.register(f)


__all__ = ["register_filters"]
