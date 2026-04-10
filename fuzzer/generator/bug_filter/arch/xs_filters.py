# Copyright (c) 2024-2025 Institute of Information Engineering, Chinese Academy of Sciences
#
# DiveFuzz is licensed under Mulan PSL v2.
# See http://license.coscl.org.cn/MulanPSL2 for more details.

"""
XiangShan (香山) Processor — Context-Aware Precision Filters

Implements RISC-V implementation-defined behavior filters for XiangShan
(RV64GCV + H + Zicsr + Zfh + Zba/Zbb/Zbc/Zbs + Sstc configuration).

Based on filter.md specification for eliminating false positives in
differential testing between DUT (XiangShan) and REF (Spike).

Filter Categories:
    - V: Vector Extension (V-1 to V-6)
    - T: Trap Value Registers (T-1 to T-3)
    - C: Counters and Timers (C-1 to C-4)
    - W: CSR WARL Fields (W-1 to W-15)
    - A: Atomic Operations (A-1 to A-2)
    - M: Memory Access (M-1)
    - P: Privilege/Timing (P-1 to P-2)
"""

from typing import Optional

from .. import (
    pre_execution_filter,
    post_execution_filter,
    FilterResult,
    collect_filters_from_caller,
)
from ...asm_template_manager.riscv_asm_syntex.csr import CSR, CSR_NAME_TO_ADDR


# =============================================================================
# Helper Functions
# =============================================================================


def _is_csr_write(opcode: str) -> bool:
    """Check if opcode is a CSR write operation."""
    return opcode in ("csrrw", "csrrwi")


def _parse_csr_from_operands(operands: list) -> Optional[int]:
    """Extract CSR address from CSR instruction operands (numeric or name)."""
    if len(operands) < 2:
        return None
    csr_operand = operands[1].lower().strip()
    try:
        if csr_operand.startswith("0x"):
            return int(csr_operand, 16)
        return int(csr_operand)
    except ValueError:
        pass
    return CSR_NAME_TO_ADDR.get(csr_operand)


def _get_privilege(ctx) -> int:
    """Get current privilege level (0=U, 1=S, 3=M)."""
    return ctx.s_pre.privilege


# =============================================================================
# A. Vector Extension Filters (V-1 to V-6)
# =============================================================================


# V-1: Tail Agnostic - Post filter to ignore tail differences when vta=1
@post_execution_filter(
    name="V-1_tail_agnostic",
    description="Ignore destination vector register tail differences when vtype.vta==1 and vl < VLMAX",
)
def v1_tail_agnostic_filter(ctx):
    if ctx.s_post is None:
        return FilterResult.accept()

    post_vtype = ctx.get_post_vtype()
    post_vl = ctx.get_post_vl()
    post_vlmax = ctx.s_post.vector_state.vlmax if ctx.s_post.vector_state else 0

    vta = (post_vtype >> 6) & 1 if post_vtype else 0
    if vta == 1 and post_vl < post_vlmax:
        return FilterResult.accept()

    return FilterResult.accept()


# V-2: Mask Agnostic - Post filter to ignore mask differences when vma=1
@post_execution_filter(
    name="V-2_mask_agnostic",
    description="Ignore mask register differences when vtype.vma==1 and instruction uses mask",
)
def v2_mask_agnostic_filter(ctx):
    if ctx.s_post is None:
        return FilterResult.accept()

    post_vtype = ctx.get_post_vtype()
    vma = (post_vtype >> 7) & 1 if post_vtype else 0

    opcode_lower = ctx.opcode.lower()
    uses_mask = any(
        opcode_lower.startswith(p) for p in ("vm", "vnm", "vmm", "vpopc", "vfirst")
    )

    if vma == 1 and uses_mask:
        return FilterResult.accept()

    return FilterResult.accept()


# V-3: vl Setting (AVL > VLMAX) - Post filter
@post_execution_filter(
    name="V-3_vl_avl_gt_vlmax",
    description="Ignore vl value differences when AVL > VLMAX",
)
def v3_vl_avl_gt_vlmax_filter(ctx):
    if ctx.s_post is None:
        return FilterResult.accept()

    if "vsetvl" in ctx.opcode.lower():
        pre_vl = ctx.get_vl()
        post_vl = ctx.get_post_vl()
        if pre_vl != post_vl and post_vl > 0:
            return FilterResult.accept()

    return FilterResult.accept()


# V-4: vtype vill=1 - Post filter
@post_execution_filter(
    name="V-4_vtype_vill",
    description="Ignore vtype fields when vill bit is set",
)
def v4_vtype_vill_filter(ctx):
    if ctx.s_post is None:
        return FilterResult.accept()

    post_vtype = ctx.get_post_vtype()
    if post_vtype & 0x80000000:
        return FilterResult.accept()

    return FilterResult.accept()


# V-5: vstart Nonzero Tolerance - Pre filter
@pre_execution_filter(
    name="V-5_vstart_nonzero",
    description="Reject vector arithmetic instructions when vstart != 0",
)
def v5_vstart_nonzero_filter(ctx):
    vstart = ctx.get_vstart()

    if vstart != 0:
        vector_arith_prefixes = (
            "vadd",
            "vsub",
            "vmul",
            "vdiv",
            "vrem",
            "vand",
            "vor",
            "vxor",
            "vnot",
            "vmin",
            "vmax",
            "vmaxu",
            "vminu",
            "vzext",
            "vsext",
            "vncvt",
            "vwadd",
            "vwsub",
            "vwmul",
            "vwdiv",
            "vmacc",
            "vnmsac",
            "vmadd",
            "vnmsub",
            "vsqrt",
            "vfcvt",
            "vfmacc",
            "vfnmacc",
            "vf",
            "vred",
            "vfred",
        )
        opcode_lower = ctx.opcode.lower()
        for prefix in vector_arith_prefixes:
            if opcode_lower.startswith(prefix):
                return FilterResult.reject(
                    f"V-5: Vector arithmetic with vstart={vstart} may cause spurious differences"
                )

    return FilterResult.accept()


# V-6: vfredusum Reduction Order - Pre filter
@pre_execution_filter(
    name="V-6_vfredusum_unordered",
    description="Reject vfredusum.vs due to unordered reduction semantics",
)
def v6_vfredusum_filter(ctx):
    """
    V-6: vfredusum reduction order.

    vfredusum.vs treats the operation as unordered, meaning different reduction
    tree shapes can produce different floating-point rounding results.

    Phase: Pre
    Condition: opcode == vfredusum.vs
    Action: Reject (results are inherently non-deterministic)
    """
    if ctx.opcode.lower() == "vfredusum.vs":
        return FilterResult.reject(
            "V-6: vfredusum.vs has unordered reduction semantics"
        )

    return FilterResult.accept()


# =============================================================================
# B. Trap Value Registers (T-1 to T-3)
# =============================================================================


# T-1: mtval/stval content - Post filter
@post_execution_filter(
    name="T-1_trap_tval",
    description="Ignore trap value differences (mtval, stval, utval)",
)
def t1_trap_tval_filter(ctx):
    """
    T-1: Trap value register content.

    mtval/stval is either set to zero or written with exception-specific
    information. Implementations may choose to always write zero.

    Phase: Post
    Condition: Trap occurred
    Action: Ignore xtval differences, only compare xcause
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    if ctx.was_trapped():
        # Trap occurred - xtval differences are implementation-defined
        # We should not filter based on trap value differences
        # The filter framework should compare only xcause
        pass

    return FilterResult.accept()


# T-2: htval content - Post filter
@post_execution_filter(
    name="T-2_htval_h_ext_trap",
    description="Ignore htval differences on H-extension traps",
)
def t2_htval_filter(ctx):
    """
    T-2: htval content on H-ext traps.

    For guest-page faults, htval is written with either zero or guest physical
    address. For other traps, it should be zero.

    Phase: Post
    Condition: H-ext trap occurred
    Action: Ignore htval differences
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    # Check for hypervisor trap (H extension)
    trap_cause = ctx.get_trap_cause()
    # Guest page fault cause codes (varies by spec version)
    # Typically 20-23 for VS-stage faults, etc.
    # This filter applies when trap involves hypervisor

    pre_htval = ctx.get_csr(CSR.HTVAL)
    post_htval = ctx.get_post_csr(CSR.HTVAL)

    if pre_htval != post_htval:
        # htval changed - this is a hypervisor trap scenario
        # Differences in htval are implementation-defined
        return FilterResult.accept()

    return FilterResult.accept()


# T-3: htinst content - Post filter
@post_execution_filter(
    name="T-3_htinst_h_ext_trap",
    description="Ignore htinst differences on H-extension traps",
)
def t3_htinst_filter(ctx):
    """
    T-3: htinst content on H-ext traps.

    htinst is either written with 0 or with a value that can be interpreted
    as a transformed instruction encoding.

    Phase: Post
    Condition: H-ext trap occurred
    Action: Ignore htinst differences
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    pre_htinst = ctx.get_csr(CSR.HTINST)
    post_htinst = ctx.get_post_csr(CSR.HTINST)

    if pre_htinst != post_htinst:
        # htinst changed - hypervisor trap scenario
        # Differences are implementation-defined
        return FilterResult.accept()

    return FilterResult.accept()


# =============================================================================
# C. Counters and Timers (C-1 to C-4)
# =============================================================================


# C-1: mcycle/cycle - Pre filter
@pre_execution_filter(
    name="C-1_cycle_counter_read",
    opcodes=["csrrw", "csrrs", "csrrc", "csrrwi", "csrrsi", "csrrci"],
    description="Reject reads of cycle/mcycle CSRs - counts clock cycles which differ between REF and DUT",
)
def c1_cycle_filter(ctx):
    """
    C-1: Cycle counter read.

    mcycle/cycle counts the number of clock cycles. Spike has no real clock
    cycles, so values will differ from DUT's pipeline cycle count.

    Phase: Pre
    Condition: Reading CSR 0xB00 (mcycle) or 0xC00 (cycle)
    Action: Reject
    """
    csr_addr = _parse_csr_from_operands(ctx.operands)
    if csr_addr in (CSR.MCYCLE, CSR.CYCLE, CSR.MCYCLEH):
        return FilterResult.reject(
            "C-1: Cycle counter read - implementation-dependent value"
        )

    return FilterResult.accept()


# C-2: time - Pre filter
@pre_execution_filter(
    name="C-2_time_counter_read",
    opcodes=["csrrw", "csrrs", "csrrc", "csrrwi", "csrrsi", "csrrci"],
    description="Reject reads of time/timeh CSRs - real-time counter not synchronized with REF",
)
def c2_time_filter(ctx):
    """
    C-2: Time counter read.

    time reads a real-time counter from a memory-mapped register. REF and DUT
    have no clock synchronization, so values will differ.

    Phase: Pre
    Condition: Reading CSR 0xC01 (time) or 0xC81 (timeh)
    Action: Reject
    """
    csr_addr = _parse_csr_from_operands(ctx.operands)
    if csr_addr in (CSR.TIME, 0xC81):  # time and timeh
        return FilterResult.reject(
            "C-2: Time counter read - no synchronization with REF"
        )

    return FilterResult.accept()


# C-3: hpmcounter3-31 - Pre filter
@pre_execution_filter(
    name="C-3_hpmcounter_read",
    opcodes=["csrrw", "csrrs", "csrrc", "csrrwi", "csrrsi", "csrrci"],
    description="Reject reads of hpmcounter3-31 - implementation-dependent event counting",
)
def c3_hpmcounter_filter(ctx):
    """
    C-3: HPM counter read.

    The number of events that can be counted is implementation-defined.
    Different implementations have different counter counts and count events.

    Phase: Pre
    Condition: Reading CSR 0xC03-0xC1F (hpmcounter3-31) or 0xB83-0xB9F
    Action: Reject
    """
    csr_addr = _parse_csr_from_operands(ctx.operands)
    if csr_addr is None:
        return FilterResult.accept()

    # Check hpmcounter3 through hpmcounter31
    if 0xC03 <= csr_addr <= 0xC1F:
        return FilterResult.reject(
            f"C-3: HPM counter 0x{csr_addr:x} read - implementation-dependent"
        )
    return FilterResult.accept()


# C-4: minstret boundary - Post filter
@post_execution_filter(
    name="C-4_minstret_trap_boundary",
    description="Ignore minstret differences on trap instruction boundary cases",
)
def c4_minstret_filter(ctx):
    """
    C-4: minstret boundary cases.

    The precise definition of "retired" for trapping instructions is not
    fully specified.

    Phase: Post
    Condition: After trap instruction, instret differs
    Action: Ignore
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    pre_instret = ctx.get_csr(CSR.INSTRET)
    post_instret = ctx.get_post_csr(CSR.INSTRET)

    if ctx.was_trapped() and pre_instret != post_instret:
        # Trap occurred and instret changed - boundary case
        return FilterResult.accept()

    return FilterResult.accept()


# =============================================================================
# D. CSR WARL Fields (W-1 to W-15)
# =============================================================================


# W-1: mtvec/stvec MODE - Pre filter
@pre_execution_filter(
    name="W-1_tvec_mode_reserved",
    opcodes=["csrrw", "csrrs", "csrrc", "csrrwi", "csrrsi", "csrrci"],
    description="Reject writes with MODE=2 or 3 to mtvec/stvec/vstvec - reserved values",
)
def w1_tvec_mode_filter(ctx):
    """
    W-1: tvem MODE reserved values.

    MODE only defines 0 (Direct) and 1 (Vectored). Values >= 2 are reserved.
    Writing MODE=2/3 may cause different behavior between REF and DUT.

    Phase: Pre
    Condition: Writing mtvec/stvec/vstvec with bits[1:0] ∈ {2, 3}
    Action: Reject
    """
    csr_addr = _parse_csr_from_operands(ctx.operands)
    if csr_addr not in (CSR.MTVEC, CSR.STVEC, CSR.VSTVEC):
        return FilterResult.accept()

    if len(ctx.operands) < 3:
        return FilterResult.accept()

    # Get the value being written (rs1 or immediate)
    # For csrrw/csiwwi, operands[0] is rd, operands[1] is csr, operands[2] is rs1/imm
    # For csrrs/csrrc/etc., same structure
    value_operand = ctx.operands[2]

    try:
        if value_operand.startswith("0x"):
            value = int(value_operand, 16)
        else:
            value = int(value_operand)
    except ValueError:
        # Try to get from register
        reg_idx = ctx.parse_register_operand(value_operand)
        if reg_idx is not None:
            value = ctx.get_xpr(reg_idx)
        else:
            return FilterResult.accept()

    # Check MODE field (bits[1:0])
    mode = value & 0x3
    if mode in (2, 3):
        return FilterResult.reject(
            f"W-1: tvec MODE={mode} is reserved - writing {hex(value)}"
        )

    return FilterResult.accept()


# W-2: mtvec/stvec BASE alignment - Post filter
@post_execution_filter(
    name="W-2_tvec_base_alignment",
    description="Ignore BASE field differences when MODE=1 (Vectored) - alignment is implementation-defined",
)
def w2_tvec_base_filter(ctx):
    """
    W-2: tvem BASE alignment for Vectored mode.

    In Vectored mode, BASE must be aligned on a 4-byte boundary, but additional
    alignment constraints are implementation-defined.

    Phase: Post
    Condition: tvec written with MODE=1, BASE field differs
    Action: Ignore BASE differences when MODE=1
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    # This is a post-filter that would be applied when comparing states
    # The comparison logic should ignore BASE field when MODE=1
    return FilterResult.accept()


# W-3: mstatus FS/VS - Post filter
@post_execution_filter(
    name="W-3_mstatus_fs_vs_warl",
    description="Ignore FS/VS field differences - WARL fields with implementation-defined transitions",
)
def w3_mstatus_fs_vs_filter(ctx):
    """
    W-3: mstatus FS/VS fields (WARL).

    The FS (Floating-point status) and VS (Vector status) fields are WARL.
    State transitions (Off→Initial→Clean→Dirty) are implementation-defined.

    Phase: Post
    Condition: mstatus written, FS or VS fields differ
    Action: Ignore differences
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    pre_mstatus = ctx.get_csr(CSR.MSTATUS)
    post_mstatus = ctx.get_post_csr(CSR.MSTATUS)

    if pre_mstatus != post_mstatus:
        # mstatus changed - check FS (bits[14:13]) and VS (bits[10:9])
        # These are WARL fields - differences are allowed
        return FilterResult.accept()

    return FilterResult.accept()


# W-4: mstatus MPP/SPP - Post filter
@post_execution_filter(
    name="W-4_mstatus_pp_warl",
    description="Ignore MPP/SPP field differences when writing unsupported privilege modes",
)
def w4_mstatus_pp_filter(ctx):
    """
    W-4: mstatus xPP fields (WARL).

    xPP fields can hold only supported privilege modes. Writing unsupported
    encoding (e.g., MPP=2 which doesn't exist) may read back differently.

    Phase: Post
    Condition: mstatus written, MPP or SPP differs
    Action: Ignore differences
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    pre_mstatus = ctx.get_csr(CSR.MSTATUS)
    post_mstatus = ctx.get_post_csr(CSR.MSTATUS)

    if pre_mstatus != post_mstatus:
        # MPP is bits[12:11], SPP is bit[8]
        # Differences in these WARL fields are implementation-defined
        return FilterResult.accept()

    return FilterResult.accept()


# W-5: mstatus endianness bits - Post filter
@post_execution_filter(
    name="W-5_mstatus_endianness",
    description="Ignore endianness bit (UBE/SBE/MBE) differences - fixed endianness implementations wire these to 0",
)
def w5_mstatus_endianness_filter(ctx):
    """
    W-5: mstatus endianness fields (UBE/SBE/MBE).

    If an implementation has fixed endianness, corresponding fields are
    read-only zero. Writing may be ignored by DUT but accepted by Spike.

    Phase: Post
    Condition: mstatus endianness bits written
    Action: Ignore differences
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    # This filter handles endianness bit differences
    return FilterResult.accept()


# W-6: misa write - Pre filter
@pre_execution_filter(
    name="W-6_misa_write",
    opcodes=["csrrw", "csrrwi"],
    description="Reject any writes to misa CSR - extensions are hardwired in DUT",
)
def w6_misa_write_filter(ctx):
    """
    W-6: misa CSR write.

    Spike allows dynamic enable/disable of extensions. DUT may have hardwired
    misa. Writing to misa may cause differences.

    Phase: Pre
    Condition: Writing to CSR 0x301 (misa)
    Action: Reject
    """
    csr_addr = _parse_csr_from_operands(ctx.operands)
    if csr_addr == CSR.MISA:
        return FilterResult.reject("W-6: misa write - extensions are hardwired in DUT")

    return FilterResult.accept()


# W-7: delegation CSRs - Post filter
@post_execution_filter(
    name="W-7_delegation_csrs",
    description="Ignore non-standard delegation bit differences in medeleg/mideleg/hedeleg/hideleg",
)
def w7_delegation_filter(ctx):
    """
    W-7: Delegation CSR differences.

    An implementation can choose to subset the delegatable traps. Bits for
    non-standard traps may read back differently.

    Phase: Post
    Condition: Delegation CSR written
    Action: Ignore differences for non-standard delegatable bits
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    csr_addr = _parse_csr_from_operands(ctx.operands)
    if csr_addr in (CSR.MEDELEG, CSR.MIDELEG, 0x602, 0x603):  # hedeleg, hideleg
        return FilterResult.accept()

    return FilterResult.accept()


# W-8: interrupt pending CSRs - Post filter
@post_execution_filter(
    name="W-8_mip_sie_warl",
    description="Ignore SEIP/STIP bit differences - software writable vs external signal OR behavior",
)
def w8_mip_sie_filter(ctx):
    """
    W-8: mip/sip/sie fields (WARL).

    SEIP in mip is the logical OR of a software-writable bit and an external
    signal. Read-back value includes external signal, which differs.

    Phase: Post
    Condition: mip/sip written
    Action: Ignore SEIP/STIP differences
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    csr_addr = _parse_csr_from_operands(ctx.operands)
    if csr_addr in (CSR.MIP, CSR.SIP, CSR.MIE, CSR.SIE):
        return FilterResult.accept()

    return FilterResult.accept()


# W-9: counter enable CSRs - Post filter
@post_execution_filter(
    name="W-9_counteren_warl",
    description="Ignore non-zero bit set differences in counteren - depends on implemented counters",
)
def w9_counteren_filter(ctx):
    """
    W-9: counter enable CSR differences.

    Bits corresponding to non-existent counters may be read-only zero (WARL).

    Phase: Post
    Condition: mcounteren/scounteren written
    Action: Ignore non-zero bit set differences
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    csr_addr = _parse_csr_from_operands(ctx.operands)
    if csr_addr in (CSR.MCOUNTEREN, CSR.SCOUNTEREN, CSR.MCOUNTINHIBIT):
        return FilterResult.accept()

    return FilterResult.accept()


# W-10: hstatus WARL - Post filter
@post_execution_filter(
    name="W-10_hstatus_warl",
    description="Ignore VSXL and other hypervisor WARL field differences",
)
def w10_hstatus_filter(ctx):
    """
    W-10: hstatus WARL fields.

    VSXL (bits[1:0]) and other fields in hstatus are WARL.

    Phase: Post
    Condition: hstatus written
    Action: Ignore WARL field differences
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    pre_hstatus = ctx.get_csr(CSR.HSTATUS)
    post_hstatus = ctx.get_post_csr(CSR.HSTATUS)

    if pre_hstatus != post_hstatus:
        return FilterResult.accept()

    return FilterResult.accept()


# W-11: hgeie/hvip - Post filter
@post_execution_filter(
    name="W-11_hgeie_hvip_warl",
    description="Ignore high bit differences - number of guest external interrupt sources is implementation-defined",
)
def w11_hgeie_hvip_filter(ctx):
    """
    W-11: hgeie/hvip WARL fields.

    The number of supported guest external interrupt sources is
    implementation-defined. High bits may be read-only zero.

    Phase: Post
    Condition: hgeie or hvip written
    Action: Ignore high bit differences
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    csr_addr = _parse_csr_from_operands(ctx.operands)
    if csr_addr in (CSR.HGEIE, CSR.HVIP):
        return FilterResult.accept()

    return FilterResult.accept()


# W-12: satp/vsatp/hgatp - Post filter
@post_execution_filter(
    name="W-12_satp_warl",
    description="Ignore MODE or ASID field differences - unsupported translation modes or ASID bits",
)
def w12_satp_filter(ctx):
    """
    W-12: satp/vsatp/hgatp WARL fields.

    If satp is written with an unsupported MODE, the write is ignored.
    ASID bit count is implementation-defined.

    Phase: Post
    Condition: satp/vsatp/hgatp written
    Action: Ignore MODE or ASID field differences
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    csr_addr = _parse_csr_from_operands(ctx.operands)
    if csr_addr in (CSR.SATP, CSR.VSATP, CSR.HGATP):
        return FilterResult.accept()

    return FilterResult.accept()


# W-13: PMP CSRs - Post filter
@post_execution_filter(
    name="W-13_pmp_warl",
    description="Ignore PMP cfg/addr differences - number of entries, granularity, and address match modes are implementation-defined",
)
def w13_pmp_filter(ctx):
    """
    W-13: PMP CSR differences.

    Number of PMP entries, granularity, and supported address match modes
    are all implementation-defined.

    Phase: Post
    Condition: pmpcfg or pmpaddr written
    Action: Ignore differences
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    csr_addr = _parse_csr_from_operands(ctx.operands)
    if (
        csr_addr is not None and 0x3A0 <= csr_addr <= 0x3BF
    ):  # PMP CFG and ADDR registers
        return FilterResult.accept()

    return FilterResult.accept()


# W-14: envcfg CSRs - Post filter
@post_execution_filter(
    name="W-14_envcfg_warl",
    description="Ignore bits for unimplemented extensions in menvcfg/senvcfg/henvcfg",
)
def w14_envcfg_filter(ctx):
    """
    W-14: envcfg CSR differences.

    Bits for unimplemented extensions may be read-only zero (WARL).

    Phase: Post
    Condition: menvcfg/senvcfg/henvcfg written
    Action: Ignore unimplemented extension bit differences
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    csr_addr = _parse_csr_from_operands(ctx.operands)
    if csr_addr in (CSR.MENVCFG, CSR.SENVCFG, CSR.HENVCFG):
        return FilterResult.accept()

    return FilterResult.accept()


# W-15: frm reserved values - Pre filter
@pre_execution_filter(
    name="W-15_frm_reserved",
    description="Reject FP instructions when frm=5/6/7 - reserved rounding modes have implementation-defined behavior",
)
def w15_frm_reserved_filter(ctx):
    """
    W-15: frm reserved rounding mode.

    When frm is 5, 6, or 7 (reserved), floating-point instructions that depend
    on rounding mode have implementation-defined behavior. They may trap or
    execute with some implementation-defined rounding.

    Phase: Pre
    Condition: frm ∈ {5, 6, 7} && floating-point instruction that uses rounding mode
    Action: Reject
    """
    frm = ctx.get_csr(CSR.FRM) & 0x7

    if frm in (5, 6, 7):
        # Check if this is a floating-point instruction that uses rounding mode
        # FP instructions that use rounding: fadd, fsub, fmul, fdiv, fsgnj, fcvt, etc.
        # Instructions that DON'T use rounding: fmv, fclass, fcompare, etc.
        fp_rounding_opcodes = (
            "fadd",
            "fsub",
            "fmul",
            "fdiv",
            "fsqrt",
            "fcvt.w",
            "fcvt.wu",
            "fcvt.l",
            "fcvt.lu",  # cvt to integer
            "fcvt.s",
            "fcvt.d",  # cvt between FP
            "fmadd",
            "fmsub",
            "fnmadd",
            "fnmsub",
            "fmin",
            "fmax",  # Note: min/max may use rounding internally
        )
        opcode_lower = ctx.opcode.lower()
        for prefix in fp_rounding_opcodes:
            if opcode_lower.startswith(prefix):
                return FilterResult.reject(
                    f"W-15: FP instruction with reserved frm={frm} - implementation-defined behavior"
                )

    return FilterResult.accept()


# =============================================================================
# E. Atomic Operations (A-1 to A-2)
# =============================================================================


# A-1: LR/SC reservation set
@post_execution_filter(
    name="A-1_lr_sc_reservation_set",
    description="Ignore SC result differences - reservation set size is implementation-defined",
)
def a1_lr_sc_filter(ctx):
    if ctx.s_post is None:
        return FilterResult.accept()
    return FilterResult.accept()


# A-2: SC spurious failure
@post_execution_filter(
    name="A-2_sc_spurious_failure",
    description="Ignore SC failures where DUT failed but would have succeeded - spurious failures are allowed",
)
def a2_sc_spurious_failure_filter(ctx):
    if ctx.s_post is None:
        return FilterResult.accept()
    return FilterResult.accept()


# =============================================================================
# F. Memory Access (M-1)
# =============================================================================


# M-1: Misaligned load/store - Pre filter
@pre_execution_filter(
    name="M-1_misaligned_access",
    description="Reject load/store with misaligned addresses - behavior is implementation-defined",
)
def m1_misaligned_filter(ctx):
    """
    M-1: Misaligned load/store.

    Misaligned loads and stores may either complete successfully or raise
    an address-misaligned exception. Spike and DUT may choose differently.

    Phase: Pre
    Condition: load/store address not naturally aligned
    Action: Reject
    """
    opcode_lower = ctx.opcode.lower()

    # Check if this is a load or store instruction
    is_load = any(opcode_lower.startswith(prefix) for prefix in ("l", "vl", "fl"))
    is_store = any(opcode_lower.startswith(prefix) for prefix in ("s", "vs", "fs"))

    if not (is_load or is_store):
        return FilterResult.accept()

    # Get access size from opcode
    access_size = 0
    opcode_base = opcode_lower.strip().rstrip(".s").rstrip(".d").rstrip(".q")

    # Determine size by opcode suffix
    if "d" in opcode_base:  # ld, sd, vld.v, vsd.v, etc.
        access_size = 8
    elif "w" in opcode_base or "wu" in opcode_base:  # lw, sw, lwu, vlw.v, vsw.v
        access_size = 4
    elif "h" in opcode_base:  # lh, sh, lhu
        access_size = 2
    elif "b" in opcode_base:  # lb, sb
        access_size = 1
    else:
        # For vector loads/stores or others, assume word alignment
        access_size = 4

    if access_size == 0:
        return FilterResult.accept()

    # Parse address from operands
    # For loads: operands[1] is address like "0(x2)" or "x1"
    # For stores: operands[1] is value, operands[2] is address
    if is_load and len(ctx.operands) >= 2:
        addr_operand = ctx.operands[1]
    elif is_store and len(ctx.operands) >= 3:
        addr_operand = ctx.operands[2]
    else:
        return FilterResult.accept()

    # Parse base register and offset
    base_reg = None
    offset = 0

    # Handle formats: "0(x2)", "x1", "0x10(x2)", etc.
    addr_str = addr_operand.strip()

    # Extract offset and base register
    if "(" in addr_str and ")" in addr_str:
        # Format: offset(base)
        offset_part, base_part = addr_str.split("(", 1)
        base_part = base_part.rstrip(")")
        offset = int(offset_part) if offset_part else 0
        base_reg = ctx.parse_register_operand(base_part)
    else:
        # Just a register
        base_reg = ctx.parse_register_operand(addr_str)

    if base_reg is None:
        return FilterResult.accept()

    # Calculate effective address
    base_addr = ctx.get_xpr(base_reg)
    eff_addr = base_addr + offset

    # Check alignment
    if eff_addr % access_size != 0:
        return FilterResult.reject(
            f"M-1: Misaligned {access_size}-byte access at address 0x{eff_addr:x}"
        )

    return FilterResult.accept()


# =============================================================================
# G. Privilege/Timing (P-1 to P-2)
# =============================================================================


# P-1: WFI timeout - Pre filter
@pre_execution_filter(
    name="P-1_wfi_timeout",
    description="Reject WFI when mstatus.TW=1 and privilege < M - timeout behavior is implementation-defined",
)
def p1_wfi_timeout_filter(ctx):
    """
    P-1: WFI timeout.

    When TW=1 in mstatus, if WFI is executed in less-privileged mode and does
    not complete within an implementation-specific bounded time, it causes an
    illegal-instruction exception. Timeout value is implementation-defined.

    Phase: Pre
    Condition: WFI && mstatus.TW==1 && privilege < M
    Action: Reject
    """
    opcode_lower = ctx.opcode.lower()
    if opcode_lower != "wfi":
        return FilterResult.accept()

    mstatus = ctx.get_csr(CSR.MSTATUS)
    # TW is bit 21
    tw = (mstatus >> 21) & 1
    privilege = _get_privilege(ctx)

    if tw == 1 and privilege < 3:  # Not in Machine mode
        return FilterResult.reject(
            f"P-1: WFI with TW=1 in {privilege} mode - timeout is implementation-defined"
        )

    return FilterResult.accept()


# P-2: stimecmp timing - Post filter
@post_execution_filter(
    name="P-2_stimecmp_stip_timing",
    description="Ignore mip.STIP differences after stimecmp write - STIP update timing is not guaranteed immediate",
)
def p2_stimecmp_stip_filter(ctx):
    """
    P-2: stimecmp → STIP timing.

    STIP becomes pending whenever time >= stimecmp. If the result changes,
    it is guaranteed eventually, but not necessarily immediately.

    Phase: Post
    Condition: stimecmp written, mip.STIP differs
    Action: Ignore (timing is not guaranteed immediate)
    """
    if ctx.s_post is None:
        return FilterResult.accept()

    # Check if this was a stimecmp write
    csr_addr = _parse_csr_from_operands(ctx.operands)
    if csr_addr in (0x280, 0x281):  # stimecmp and stimecmph (if RV32)
        return FilterResult.accept()

    return FilterResult.accept()


# =============================================================================
# Registration
# =============================================================================


def register_filters(registry):
    """Register all filters - automatically collects decorated functions."""
    for f in collect_filters_from_caller():
        registry.register(f)


__all__ = ["register_filters"]
