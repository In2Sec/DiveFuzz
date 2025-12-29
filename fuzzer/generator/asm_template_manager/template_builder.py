# -*- coding: utf-8 -*-

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

from __future__ import annotations

from .riscv_asm_syntex import AsmProgram, ArchConfig, CSR, Instruction, Comment, Hook
from .constants import *
from .template_instance import TemplateInstance
from .constants import TemplateType, HOOK_MAIN
import random
# ==============================================================================
# Private Helper Functions (Internal Use Only)
# ==============================================================================


def _init_random_mem_region(p: AsmProgram, total_bytes: int = 8192, random_bytes: int = 1024) -> AsmProgram:
    """
    Initialize memory region with random data for fuzzing diversity.

    Args:
        p: AsmProgram to add data to
        total_bytes: Total size of memory region (default 8192 = 8KB)
        random_bytes: Number of bytes to randomize (default 1024 = 1KB)
                     The rest will be zero-initialized for efficiency.

    The random portion provides diversity for Load/Store operations,
    while the zero portion keeps file size manageable.
    """
    # Generate random 32-bit words for the random portion
    random_words = random_bytes // 4  # 4 bytes per word
    for i in range(0, random_words, 8):
        # Generate 8 words at a time for more compact output
        batch_size = min(8, random_words - i)
        words = [f"0x{random.getrandbits(32):08x}" for _ in range(batch_size)]
        p.data_word(*words)

    # Fill remaining with zeros
    remaining_bytes = total_bytes - random_bytes
    if remaining_bytes > 0:
        p.data_zero(remaining_bytes)

    return p


# ------------------------------------------------------------------------------
# XiangShan mode Private Functions
# ------------------------------------------------------------------------------

def _xs_text_startup(p: AsmProgram) -> AsmProgram:
    """
    [XiangShan ] Build the startup sequence in .text (_start and early jumps):
    - Read mhartid/core ID
    - Jump to h0_start via jalr
    - Set MISA, kernel stack pointer, trap vector MTVEC/STVEC, initial MEPC
    """
    p.globl(LBL_START).section(".text")

    p.label(LBL_START)

    p.li("x13", "0x800000000084112d")
    p.csrw(CSR.MISA, "x13")


    p.label(LBL_TRAP_VEC_INIT)
    p.la("x13", LBL_OTHER_EXP)
    p.csrw(CSR.MTVEC, "x13", comment="MTVEC")
    p.la("x13", LBL_OTHER_EXP_S)
    p.csrw(CSR.STVEC, "x13", comment="STVEC")

    p.label(LBL_MEPC_SETUP)
    p.la("x13", LBL_INIT)
    p.csrw(CSR.MEPC, "x13")


    return p


def _xs_init(p: AsmProgram) -> AsmProgram:
    """
    [XiangShan] Mode basic initialization:
    - Write MSTATUS/MIE PMP/PMA
    - Enter init via mret
    """
    p.label(LBL_INIT_ENV)
    ms_val = random_mstatus_rv64_h()
    mpp = (ms_val >> 11) & 0b11  
    # mode_map = {
    #     0: "U-mode",
    #     1: "S-mode",
    #     3: "M-mode",
    # }
    # ret_mode = mode_map.get(mpp, "RESERVED")
    # Load and write MSTATUS
    p.li("x26", f"0x{ms_val:016x}")
    p.csrw(CSR.MSTATUS, "x26", comment=f"MSTATUS (mode is {mpp})")
    # Build PMP (Physical Memory Protection) setup.
    # Use NAPOT mode to cover entire address space (including mem_region for AMO instructions)
    # pmpaddr0 = ~0 (all 1s) with NAPOT mode covers the entire address space
    # pmpcfg0 = 0x1f means: A=NAPOT(0b11), R=1, W=1, X=1
    if mpp != 3:
        p.li("x16", -1)  # All 1s = 0xffffffffffffffff
        p.csrw(0x3b0, "x16")  # pmpaddr0
        p.li("x16", 0x1f)  # NAPOT + RWX
        p.csrw(0x3a0, "x16")  # pmpcfg0

        p.instr("sfence.vma x0, x0")

    p.li("x26", "0x0")
    p.csrw(CSR.MIE, "x26", comment="MIE")
    p.mret()
    return p


def _xs_init_reg(p: AsmProgram) -> AsmProgram:
    """
    [XiangShan/Rocket] init: Initialize floating-point and general-purpose registers.

    This function initializes ALL registers to ensure deterministic behavior
    across different simulators/processors for differential testing:
    - x1-x31: General-purpose registers (x0 is hardwired to 0)
    - f0-f31: Floating-point registers
    """
    p.label(LBL_INIT)

    # Large probability group: valid rounding modes 0~4
    major_modes = [0, 1, 2, 3, 4]

    # Small probability group: reserved modes 5~7
    minor_modes = [5, 6, 7]

    # Choose group (e.g., 95% vs 5%)
    if random.random() < 0.95:
        rm = random.choice(major_modes)
    else:
        rm = random.choice(minor_modes)

    p.instr("fsrmi", str(rm))

    # === General-purpose and floating-point register initialization ===
    # Initialize ALL x1-x31 and f0-f31 for deterministic testing
    # Note: x0 is hardwired to 0, no need to initialize

    # Phase 1: Initialize x1-x31 with random values
    # We use a specific pattern to ensure all registers get initialized
    for r in range(1, 32):
        rand_val = random.getrandbits(64)
        p.li(f"x{r}", f"0x{rand_val:016x}")

    # Phase 2: Initialize f0-f31 using the initialized x registers
    # Use x5 (t0) as temp since it's already initialized
    for r in range(32):
        rand_val = random.getrandbits(64)
        p.li("x5", f"0x{rand_val:016x}")  # Use t0 as temp register
        # choose a random fmv instruction: h.x / w.x / d.x
        op = random.choice(["fmv.h.x", "fmv.w.x", "fmv.d.x"])
        p.instr(op, f"f{r}", "x5")

    # To Store/Load - use valid memory region address
    # Point t6 to the MIDDLE of mem_region (offset by 4096 bytes = half of 8KB)
    # This allows both positive and negative offsets to access valid memory
    p.la("t6", SYM_MEM_REGION)
    p.li("t5", "4096")
    p.instr("add", "t6", "t6", "t5")

    p.instr("j", LBL_MAIN)

    p.align(12)
    return p


def _nutshell_init_reg(p: AsmProgram) -> AsmProgram:
    """
    [NutShell M-mode] init: Initialize general-purpose registers.

    NutShell typically runs in M-mode without floating-point extensions,
    so only GPRs are initialized here. All x1-x31 are initialized to
    ensure deterministic behavior across different environments.
    """
    p.label(LBL_INIT)

    # === General-purpose register initialization ===
    # Initialize ALL x1-x31 (x0 is hardwired to 0)
    for r in range(1, 32):
        rand_val = random.getrandbits(64)
        p.li(f"x{r}", f"0x{rand_val:016x}")

    # To Store/Load - use valid memory region address
    # Point t6 to the MIDDLE of mem_region (offset by 4096 bytes = half of 8KB)
    # This allows both positive and negative offsets to access valid memory
    p.la("t6", SYM_MEM_REGION)
    p.li("t5", "4096")
    p.instr("add", "t6", "t6", "t5")

    p.instr("j", LBL_MAIN)

    p.align(12)
    return p


def _exception_vector(p: AsmProgram) -> AsmProgram:
    """
    [XiangShan/NutShell/Rocket] Exception handlers for M-mode and S-mode.
    - other_exp: M-mode handler (increment mepc by 4, then mret)
    - other_exp_s: S-mode handler (increment sepc by 4, then sret)
    """
    # M-mode trap handler
    p.label(LBL_OTHER_EXP)
    p.option("norvc")
    p.csrr("x13", CSR.MEPC)
    p.instr("addi", "x13", "x13", "4")
    p.csrw(CSR.MEPC, "x13")
    p.mret()
    p.option("rvc")

    # S-mode trap handler
    p.label(LBL_OTHER_EXP_S)
    p.option("norvc")
    p.csrr("x13", CSR.SEPC)
    p.instr("addi", "x13", "x13", "4")
    p.csrw(CSR.SEPC, "x13")
    p.instr("sret")
    p.option("rvc")
    return p


def _init_data_sections(p: AsmProgram) -> AsmProgram:
    """
    [XiangShan/NutShell/Rocket] Data area and custom sections.
    """
    p.section(".data")
    p.directive("align", "6"); p.directive("global", SYM_TOHOST); p.label(SYM_TOHOST)
    if p.arch.is_rv64(): p.data_dword(0)
    else:                p.data_word(0, 0)

    p.directive("align", "6"); p.directive("global", SYM_FROMHOST); p.label(SYM_FROMHOST)
    if p.arch.is_rv64(): p.data_dword(0)
    else:                p.data_word(0, 0)

    p.section(".region_0", flags="aw", sect_type="@progbits")
    p.label(SYM_REGION0)
    rand_words = [f"0x{random.getrandbits(32):08x}" for _ in range(8)]
    p.data_word(*rand_words)

    # Add mem_region for NutShell compatibility
    p.section(".mem_region", flags="aw", sect_type="@progbits")
    p.align(4)
    p.label(SYM_MEM_REGION)
    _init_random_mem_region(p)  # Initialize with random data for fuzzing diversity
    p.label(SYM_MEM_REGION_END)

    return p


# ------------------------------------------------------------------------------
# NutShell M-mode Private Functions (_nutshell_m_*)
# ------------------------------------------------------------------------------

def _nutshell_m_text_startup(p: AsmProgram) -> AsmProgram:
    """
    [NutShell M-mode] Build the startup sequence. Uses mtvec_handler instead of other_exp.
    """
    p.globl(LBL_START).section(".text")

    p.label(LBL_START)

    p.li("x13", "0x800000000084112d")
    p.csrw(CSR.MISA, "x13")


    p.label(LBL_TRAP_VEC_INIT)
    p.la("x13", LBL_OTHER_EXP)
    p.csrw(CSR.MTVEC, "x13", comment="MTVEC")

    p.label(LBL_MEPC_SETUP)
    p.la("x13", LBL_INIT)
    p.csrw(CSR.MEPC, "x13")
    return p


def _nutshell_m_machine_mode_init(p: AsmProgram) -> AsmProgram:
    """
    [NutShell M-mode] Machine mode initialization (different MSTATUS value).
    """
    p.label(LBL_INIT_ENV)
    # TODO support more MSTATUS
    p.li("x26", "0xa00101800")
    p.csrw(CSR.MSTATUS, "x26", comment="MSTATUS")
    p.li("x26", "0x0")
    p.csrw(CSR.MIE, "x26", comment="MIE")
    p.mret()
    return p



def _nutshell_m_main_with_hook(p: AsmProgram) -> AsmProgram:
    """
    [NutShell M-mode] Main section with hook.
    """
    p.align(2)
    p.option("norvc")

    p.label(LBL_MAIN)
    p.hook(HOOK_MAIN)
    p.fourbyte("0x0000006b")

    p.option("rvc")
    return p


# ------------------------------------------------------------------------------
# S-mode Private Functions (_s_mode_*)
# ------------------------------------------------------------------------------

def _s_mode_text_startup(p: AsmProgram) -> AsmProgram:
    """
    [S-mode] Build startup sequence. Sets up both STVEC and MTVEC.
    """
    p.globl(LBL_START).section(".text")
    p.label(LBL_START)
    p.csrr("x5", 0xF14)
    p.li("x6", 0)
    p.beq("x5", "x6", "0f")

    p.label("0")
    p.la("x16", LBL_H0_START)
    p.jalr("x0", "x16", 0)

    p.label(LBL_H0_START)
    p.li("x8", "0x800000000084112d")
    p.csrw(CSR.MISA, "x8")

    p.label(LBL_KERNEL_SP)
    p.la("x28", SYM_KERNEL_STACK_END)

    p.label(LBL_TRAP_VEC_INIT)
    p.la("x8", LBL_STVEC_HANDLER)
    p.csrw(CSR.STVEC, "x8", comment="STVEC")
    p.la("x8", LBL_MTVEC_HANDLER)
    p.csrw(CSR.MTVEC, "x8", comment="MTVEC")
    return p


def _s_mode_pmp_setup(p: AsmProgram) -> AsmProgram:
    """
    [S-mode] Build PMP (Physical Memory Protection) setup.
    Use NAPOT mode to cover entire address space (including mem_region for AMO instructions).
    """
    p.label(LBL_PMP_SETUP)
    p.li("x16", -1)  # All 1s = 0xffffffffffffffff
    p.csrw(0x3b0, "x16")  # pmpaddr0
    p.li("x16", 0x1f)  # NAPOT + RWX
    p.csrw(0x3a0, "x16")  # pmpcfg0
    p.instr("sfence.vma")
    return p


def _s_mode_mepc_setup(p: AsmProgram) -> AsmProgram:
    """
    [S-mode] Build MEPC setup.
    """
    p.label(LBL_MEPC_SETUP)
    p.la("x8", LBL_INIT)
    p.csrw(CSR.MEPC, "x8")

    p.label(LBL_CUSTOM_CSR_SETUP)
    p.instr("nop")
    return p


def _s_mode_supervisor_init(p: AsmProgram) -> AsmProgram:
    """
    [S-mode] Build supervisor mode initialization with SATP and page table setup.
    """
    p.label(LBL_INIT_SUPERVISOR)
    p.li("x8", "0x8000000000000000")
    p.csrw(CSR.SATP, "x8", comment="satp")
    p.la("x8", LBL_PAGE_TABLE_0)
    p.instr("srli", "x8", "x8", "12")
    p.li("x5", "0xfffffffffff")
    p.instr("and", "x8", "x8", "x5")
    p.instr("csrs", hex(CSR.SATP), "x8", comment="satp")

    p.li("x8", "0xa000c2800")
    p.csrw(CSR.MSTATUS, "x8", comment="MSTATUS")
    p.li("x8", "0x0")
    p.csrw(CSR.MIE, "x8", comment="MIE")
    p.li("x8", "0x200042000")
    p.csrw(CSR.SSTATUS, "x8", comment="SSTATUS")
    p.li("x8", "0x0")
    p.csrw(CSR.SIE, "x8", comment="SIE")
    p.mret()
    return p


def _s_mode_init_sequence(p: AsmProgram) -> AsmProgram:
    """
    [S-mode] Build init sequence with FP and GP register initialization.

    All registers are initialized with random values for fuzzing diversity.
    """
    p.label(LBL_INIT)

    # Set random floating-point rounding mode
    major_modes = [0, 1, 2, 3, 4]
    minor_modes = [5, 6, 7]
    if random.random() < 0.95:
        rm = random.choice(major_modes)
    else:
        rm = random.choice(minor_modes)
    p.instr("fsrmi", str(rm))

    # === General-purpose register initialization with random values ===
    # Initialize x1-x31 (x0 is hardwired to 0)
    for r in range(1, 32):
        rand_val = random.getrandbits(64)
        p.li(f"x{r}", f"0x{rand_val:016x}")

    # === Floating-point register initialization with random values ===
    # Use x5 (t0) as temp register for loading values
    for r in range(32):
        rand_val = random.getrandbits(64)
        p.li("x5", f"0x{rand_val:016x}")
        op = random.choice(["fmv.h.x", "fmv.w.x", "fmv.d.x"])
        p.instr(op, f"f{r}", "x5")

    # Setup memory region pointer for Store/Load operations
    p.la("t6", SYM_MEM_REGION)
    p.li("t5", "4096")
    p.instr("add", "t6", "t6", "t5")
    p.instr("j", LBL_MAIN)
    return p


def _s_mode_exception_vector(p: AsmProgram) -> AsmProgram:
    """
    [S-mode] Build exception vectors for both STVEC and MTVEC handlers.
    """
    # STVEC handler
    p.align(12)
    p.label(LBL_STVEC_HANDLER)
    p.option("norvc")
    p.instr("j", LBL_SMODE_EXC_HANDLER)
    p.option("rvc")

    p.label(LBL_SMODE_EXC_HANDLER)
    p.option("norvc")
    p.csrr("x21", 0x343)
    p.label("1")
    p.la("x8", LBL_OTHER_EXP_S)
    p.jalr("x1", "x8", 0)
    p.option("rvc")

    p.label(LBL_OTHER_EXP_S)
    p.option("norvc")
    p.csrr("x13", "sepc")
    p.instr("addi", "x13", "x13", "4")
    p.csrw("sepc", "x13")
    p.instr("sret")
    p.option("rvc")

    # MTVEC handler
    p.align(12)
    p.label(LBL_MTVEC_HANDLER)
    p.option("norvc")
    p.instr("j", LBL_MMODE_EXC_HANDLER)
    p.option("rvc")

    p.label(LBL_MMODE_EXC_HANDLER)
    p.csrr("x21", 0x343)
    p.label("1")
    p.la("x8", LBL_OTHER_EXP_M)
    p.jalr("x1", "x8", 0)

    p.label(LBL_OTHER_EXP_M)
    p.option("norvc")
    p.csrr("x13", CSR.MEPC)
    p.instr("addi", "x13", "x13", "4")
    p.csrw(CSR.MEPC, "x13")
    p.mret()
    p.option("rvc")
    return p


def _s_mode_main_with_hook(p: AsmProgram) -> AsmProgram:
    """
    [S-mode] Main section.
    """
    p.label(LBL_TEST_DONE)
    p.wfi()

    p.align(2)
    p.option("norvc")
    p.label(LBL_MAIN)
    p.hook(HOOK_MAIN)
    p.fourbyte("0x0000006b")
    p.option("rvc")
    return p


def _s_mode_data_sections(p: AsmProgram) -> AsmProgram:
    """
    [S-mode] Build data sections including page table.
    """
    p.section(".data")
    p.directive("align", "6"); p.directive("global", SYM_TOHOST); p.label(SYM_TOHOST)
    if p.arch.is_rv64(): p.data_dword(0)
    else:                p.data_word(0, 0)

    p.directive("align", "6"); p.directive("global", SYM_FROMHOST); p.label(SYM_FROMHOST)
    if p.arch.is_rv64(): p.data_dword(0)
    else:                p.data_word(0, 0)

    # Allocate stack space for exception handling
    # Stack grows downward, so we allocate space BEFORE the _end label
    p.comment("Kernel stack space (512 bytes)")
    p.data_zero(512)
    p.label(SYM_KERNEL_STACK_END)

    p.section(".mem_region", flags="aw", sect_type="@progbits")
    p.align(4)
    p.label(SYM_MEM_REGION)
    _init_random_mem_region(p)  # Initialize with random data for fuzzing diversity
    p.label(SYM_MEM_REGION_END)

    p.section(LBL_PAGE_TABLE_SEC, flags="aw", sect_type="@progbits")
    p.align(12)
    p.label(LBL_PAGE_TABLE_0)
    page_entries = [
        "0x1", "0x1", "0x200000cf", "0x300000cf", "0x400000cf", "0x500000cf", "0x600000cf", "0x700000cf",
        "0x800000cf", "0x900000cf", "0xa00000cf", "0xb00000cf", "0xc00000cf", "0xd00000cf", "0xe00000cf", "0xf00000cf",
        "0x1000000cf", "0x1100000cf", "0x1200000cf", "0x1300000cf", "0x1400000cf", "0x1500000cf", "0x1600000cf", "0x1700000cf",
        "0x1800000cf", "0x1900000cf", "0x1a00000cf", "0x1b00000cf", "0x1c00000cf", "0x1d00000cf", "0x1e00000cf", "0x1f00000cf",
        "0x2000000cf", "0x2100000cf", "0x2200000cf", "0x2300000cf", "0x2400000cf", "0x2500000cf", "0x2600000cf", "0x2700000cf",
    ]
    for i in range(0, len(page_entries), 8):
        p.directive("dword", ", ".join(page_entries[i:i+8]))
    return p


# ------------------------------------------------------------------------------
# U-mode Private Functions (_u_mode_*)
# ------------------------------------------------------------------------------

def _u_mode_text_startup(p: AsmProgram) -> AsmProgram:
    """
    [U-mode] Build startup sequence. Uses x29, x27 registers.
    """
    p.globl(LBL_START).section(".text")
    p.label(LBL_START)
    p.csrr("x5", 0xF14)
    p.li("x6", 0)
    p.beq("x5", "x6", "0f")

    p.label("0")
    p.la("x29", LBL_H0_START)
    p.jalr("x0", "x29", 0)

    p.label(LBL_H0_START)
    p.li("x27", "0x800000000084112d")
    p.csrw(CSR.MISA, "x27")

    p.label(LBL_KERNEL_SP)
    p.la("x30", SYM_KERNEL_STACK_END)

    p.label(LBL_TRAP_VEC_INIT)
    p.la("x27", LBL_STVEC_HANDLER)
    p.instr("slli", "x27", "x27", "44")
    p.instr("srli", "x27", "x27", "44")
    p.instr("ori", "x27", "x27", "0")
    p.csrw(CSR.STVEC, "x27", comment="STVEC")
    p.la("x27", LBL_MTVEC_HANDLER)
    p.instr("ori", "x27", "x27", "0")
    p.csrw(CSR.MTVEC, "x27", comment="MTVEC")
    return p


def _u_mode_pmp_setup(p: AsmProgram) -> AsmProgram:
    """
    [U-mode] Build PMP setup.
    Use NAPOT mode to cover entire address space (including mem_region for AMO instructions).
    """
    p.label(LBL_PMP_SETUP)
    p.li("x29", -1)  # All 1s = 0xffffffffffffffff
    p.csrw(0x3b0, "x29")  # pmpaddr0
    p.li("x29", 0x1f)  # NAPOT + RWX
    p.csrw(0x3a0, "x29")  # pmpcfg0
    return p


def _u_mode_process_page_tables(p: AsmProgram) -> AsmProgram:
    """
    [U-mode] Build complex page table processing. Links multiple levels.
    """
    p.label(LBL_PROCESS_PT)

    p.la("x8", f"{LBL_PAGE_TABLE_0}+2048")
    p.ld("x13", "-2048(x8)")
    p.la("x27", LBL_PAGE_TABLE_1)
    p.instr("srli", "x27", "x27", "2")
    p.instr("or", "x13", "x27", "x13")
    p.sd("x13", "-2048(x8)")

    p.ld("x13", "-2040(x8)")
    p.la("x27", LBL_PAGE_TABLE_2)
    p.instr("srli", "x27", "x27", "2")
    p.instr("or", "x13", "x27", "x13")
    p.sd("x13", "-2040(x8)")

    p.la("x8", f"{LBL_PAGE_TABLE_1}+2048")
    p.ld("x13", "-2048(x8)")
    p.la("x27", LBL_PAGE_TABLE_3)
    p.instr("srli", "x27", "x27", "2")
    p.instr("or", "x13", "x27", "x13")
    p.sd("x13", "-2048(x8)")

    p.ld("x13", "-2040(x8)")
    p.la("x27", LBL_PAGE_TABLE_4)
    p.instr("srli", "x27", "x27", "2")
    p.instr("or", "x13", "x27", "x13")
    p.sd("x13", "-2040(x8)")

    p.la("x8", f"{LBL_PAGE_TABLE_2}+2048")
    p.ld("x13", "-2048(x8)")
    p.la("x27", LBL_PAGE_TABLE_5)
    p.instr("srli", "x27", "x27", "2")
    p.instr("or", "x13", "x27", "x13")
    p.sd("x13", "-2048(x8)")

    p.ld("x13", "-2040(x8)")
    p.la("x27", LBL_PAGE_TABLE_6)
    p.instr("srli", "x27", "x27", "2")
    p.instr("or", "x13", "x27", "x13")
    p.sd("x13", "-2040(x8)")

    p.la("x27", LBL_KERNEL_INSTR_START)
    p.la("x8", LBL_KERNEL_INSTR_END)
    p.instr("slli", "x27", "x27", "34")
    p.instr("srli", "x27", "x27", "46")
    p.instr("slli", "x27", "x27", "6")
    p.instr("slli", "x8", "x8", "34")
    p.instr("srli", "x8", "x8", "46")
    p.instr("slli", "x8", "x8", "6")
    p.la("x13", LBL_PAGE_TABLE_3)
    p.instr("add", "x27", "x13", "x27")
    p.instr("add", "x8", "x13", "x8")
    p.li("x13", "0xffffffffffffffef")
    p.label("1")
    p.ld("x28", "0(x27)")
    p.instr("and", "x28", "x28", "x13")
    p.sd("x28", "0(x27)")
    p.instr("addi", "x27", "x27", "8")
    p.instr("ble", "x27", "x8", "1b")

    p.la("x27", LBL_KERNEL_DATA_START)
    p.instr("slli", "x27", "x27", "34")
    p.instr("srli", "x27", "x27", "46")
    p.instr("slli", "x27", "x27", "6")
    p.la("x13", LBL_PAGE_TABLE_3)
    p.instr("add", "x27", "x13", "x27")
    p.li("x13", "0xffffffffffffffef")
    p.instr("addi", "x8", "x8", "160")
    p.label("2")
    p.ld("x28", "0(x27)")
    p.instr("and", "x28", "x28", "x13")
    p.sd("x28", "0(x27)")
    p.instr("addi", "x27", "x27", "8")
    p.instr("ble", "x27", "x8", "2b")

    p.instr("sfence.vma")
    return p


def _u_mode_mepc_setup(p: AsmProgram) -> AsmProgram:
    """
    [U-mode] Build MEPC setup with address masking.
    """
    p.label(LBL_MEPC_SETUP)
    p.la("x27", LBL_INIT)
    p.instr("slli", "x27", "x27", "52")
    p.instr("srli", "x27", "x27", "52")
    p.csrw(CSR.MEPC, "x27")

    p.label(LBL_CUSTOM_CSR_SETUP)
    p.instr("nop")
    return p


def _u_mode_user_init(p: AsmProgram) -> AsmProgram:
    """
    [U-mode] Build user mode initialization with SATP setup.
    """
    p.label(LBL_INIT_USER)
    p.li("x27", "0x8000000000000000")
    p.csrw(CSR.SATP, "x27", comment="satp")
    p.la("x27", LBL_PAGE_TABLE_0)
    p.instr("srli", "x27", "x27", "12")
    p.li("x8", "0xfffffffffff")
    p.instr("and", "x27", "x27", "x8")
    p.instr("csrs", hex(CSR.SATP), "x27", comment="satp")
    p.li("x27", "0xa001c0000")
    p.csrw(CSR.MSTATUS, "x27", comment="MSTATUS")
    p.li("x27", "0x0")
    p.csrw(CSR.MIE, "x27", comment="MIE")
    p.mret()
    return p


def _u_mode_init_sequence(p: AsmProgram) -> AsmProgram:
    """
    [U-mode] Build init sequence (GP registers).

    All registers are initialized with random values for fuzzing diversity.
    IMPORTANT: x30 must NOT be randomized - it's the stack pointer for exception handling!
    Note: x18 is set to user_stack_end at the end (required for U-mode operation).
    """
    p.label(LBL_INIT)

    # === General-purpose register initialization with random values ===
    # Initialize x1-x29 and x31 (x0 is hardwired to 0)
    # SKIP x30: it's the stack pointer, must keep pointing to kernel_stack_end
    for r in range(1, 30):
        rand_val = random.getrandbits(64)
        p.li(f"x{r}", f"0x{rand_val:016x}")

    # x31 can be randomized (it will be overwritten by t6 later anyway)
    rand_val = random.getrandbits(64)
    p.li("x31", f"0x{rand_val:016x}")

    # x18 must point to user stack for U-mode exception handling
    p.la("x18", SYM_USER_STACK_END)
    # Setup memory region pointer for Store/Load operations
    p.la("t6", SYM_MEM_REGION)
    p.li("t5", "4096")
    p.instr("add", "t6", "t6", "t5")
    p.instr("j", LBL_MAIN)
    return p


def _u_mode_stvec_handler(p: AsmProgram) -> AsmProgram:
    """
    [U-mode] Build STVEC handler with register save and cause dispatch.
    """
    p.align(12)
    p.label(LBL_STVEC_HANDLER)

    p.instr("addi", "x30", "x30", "-8")
    p.sd("x18", "(x30)")
    p.instr("add", "x18", "x30", "zero")
    p.instr("addi", "x18", "x18", "-256")
    for i in range(1, 32):
        p.sd(f"x{i}", f"{i*8}(x18)")
    p.instr("add", "x30", "x18", "zero")

    p.csrr("x27", CSR.SSTATUS)
    p.csrr("x27", CSR.SCAUSE)
    p.instr("srli", "x27", "x27", "63")
    p.instr("bne", "x27", "x0", LBL_SMODE_INTR_HANDLER)

    p.label(LBL_SMODE_EXC_HANDLER)
    p.csrr("x27", CSR.SEPC)
    p.csrr("x27", CSR.SCAUSE)
    p.li("x8", "0x3"); p.instr("beq", "x27", "x8", LBL_EBREAK_HANDLER)
    p.li("x8", "0x8"); p.instr("beq", "x27", "x8", LBL_ECALL_HANDLER)
    p.li("x8", "0x9"); p.instr("beq", "x27", "x8", LBL_ECALL_HANDLER)
    p.li("x8", "0xb"); p.instr("beq", "x27", "x8", LBL_ECALL_HANDLER)
    p.li("x8", "0x1"); p.instr("beq", "x27", "x8", LBL_INSTR_FAULT_HANDLER)
    p.li("x8", "0x5"); p.instr("beq", "x27", "x8", LBL_LOAD_FAULT_HANDLER)
    p.li("x8", "0x7"); p.instr("beq", "x27", "x8", LBL_STORE_FAULT_HANDLER)
    p.li("x8", "0xc"); p.instr("beq", "x27", "x8", LBL_PT_FAULT_HANDLER)
    p.li("x8", "0xd"); p.instr("beq", "x27", "x8", LBL_PT_FAULT_HANDLER)
    p.li("x8", "0xf"); p.instr("beq", "x27", "x8", LBL_PT_FAULT_HANDLER)
    p.li("x8", "0x2"); p.instr("beq", "x27", "x8", LBL_ILLEGAL_INSTR_HANDLER)
    p.csrr("x8", CSR.STVAL)
    p.label("1")
    p.la("x29", LBL_TEST_DONE)
    p.jalr("x1", "x29", 0)
    return p


def _u_mode_mtvec_handler(p: AsmProgram) -> AsmProgram:
    """
    [U-mode] Build MTVEC handler with register save and cause dispatch.
    """
    p.align(12)
    p.label(LBL_MTVEC_HANDLER)

    p.instr("addi", "x30", "x30", "-8")
    p.sd("x18", "(x30)")
    p.instr("add", "x18", "x30", "zero")
    p.instr("addi", "x18", "x18", "-256")
    for i in range(1, 32):
        p.sd(f"x{i}", f"{i*8}(x18)")
    p.instr("add", "x30", "x18", "zero")

    p.csrr("x27", CSR.MSTATUS)
    p.csrr("x27", CSR.MCAUSE)
    p.instr("srli", "x27", "x27", "63")
    p.instr("bne", "x27", "x0", LBL_MMODE_INTR_HANDLER)

    p.label(LBL_MMODE_EXC_HANDLER)
    p.csrr("x27", CSR.MEPC)
    p.csrr("x27", CSR.MCAUSE)
    p.li("x8", "0x3"); p.instr("beq", "x27", "x8", LBL_EBREAK_HANDLER)
    p.li("x8", "0x8"); p.instr("beq", "x27", "x8", LBL_ECALL_HANDLER)
    p.li("x8", "0x9"); p.instr("beq", "x27", "x8", LBL_ECALL_HANDLER)
    p.li("x8", "0xb"); p.instr("beq", "x27", "x8", LBL_ECALL_HANDLER)
    p.li("x8", "0x1"); p.instr("beq", "x27", "x8", LBL_INSTR_FAULT_HANDLER)
    p.li("x8", "0x5"); p.instr("beq", "x27", "x8", LBL_LOAD_FAULT_HANDLER)
    p.li("x8", "0x7"); p.instr("beq", "x27", "x8", LBL_STORE_FAULT_HANDLER)
    p.li("x8", "0xc"); p.instr("beq", "x27", "x8", LBL_PT_FAULT_HANDLER)
    p.li("x8", "0xd"); p.instr("beq", "x27", "x8", LBL_PT_FAULT_HANDLER)
    p.li("x8", "0xf"); p.instr("beq", "x27", "x8", LBL_PT_FAULT_HANDLER)
    p.li("x8", "0x2"); p.instr("beq", "x27", "x8", LBL_ILLEGAL_INSTR_HANDLER)
    p.csrr("x8", CSR.MTVAL)
    p.label("1")
    p.la("x29", LBL_TEST_DONE)
    p.jalr("x1", "x29", 0)
    return p


def _u_mode_exception_handlers(p: AsmProgram) -> AsmProgram:
    """
    [U-mode] Build exception handlers (ecall, ebreak, faults).
    """
    p.label(LBL_ECALL_HANDLER)
    p.la("x27", LBL_START)
    p.csrw(CSR.MEPC, "x27")
    p.mret()

    p.label(LBL_EBREAK_HANDLER)
    p.csrr("x27", CSR.MEPC)
    p.instr("addi", "x27", "x27", "4")
    p.csrw(CSR.MEPC, "x27")
    p.mret()

    p.label(LBL_ILLEGAL_INSTR_HANDLER)
    p.csrr("x27", CSR.MEPC)
    p.instr("addi", "x27", "x27", "4")
    p.csrw(CSR.MEPC, "x27")
    p.mret()

    p.label(LBL_INSTR_FAULT_HANDLER)
    p.csrr("x27", CSR.MEPC)
    p.instr("addi", "x27", "x27", "4")
    p.csrw(CSR.MEPC, "x27")
    p.mret()

    p.label(LBL_LOAD_FAULT_HANDLER)
    p.csrr("x27", CSR.MEPC)
    p.instr("addi", "x27", "x27", "4")
    p.csrw(CSR.MEPC, "x27")
    p.mret()

    p.label(LBL_STORE_FAULT_HANDLER)
    p.csrr("x27", CSR.MEPC)
    p.instr("addi", "x27", "x27", "4")
    p.csrw(CSR.MEPC, "x27")
    p.mret()

    p.label(LBL_PT_FAULT_HANDLER)
    p.csrr("x27", CSR.MEPC)
    p.instr("addi", "x27", "x27", "4")
    p.csrw(CSR.MEPC, "x27")
    p.mret()

    p.label(LBL_SMODE_INTR_HANDLER)
    p.instr("j", LBL_TEST_DONE)

    p.label(LBL_MMODE_INTR_HANDLER)
    p.instr("j", LBL_TEST_DONE)
    return p


def _u_mode_data_sections(p: AsmProgram) -> AsmProgram:
    """
    [U-mode] Build data sections with multi-level page tables.
    """
    p.section(".data")
    p.directive("align", "6"); p.directive("global", SYM_TOHOST); p.label(SYM_TOHOST)
    if p.arch.is_rv64(): p.data_dword(0)
    else:                p.data_word(0, 0)

    p.directive("align", "6"); p.directive("global", SYM_FROMHOST); p.label(SYM_FROMHOST)
    if p.arch.is_rv64(): p.data_dword(0)
    else:                p.data_word(0, 0)

    # Allocate stack space for exception handling
    # Stack grows downward, so we allocate space BEFORE the _end label
    # Exception handler saves 31 registers * 8 bytes = 248 bytes, plus some margin
    p.comment("Kernel stack space (512 bytes)")
    p.data_zero(512)
    p.label(SYM_KERNEL_STACK_END)

    p.comment("User stack space (512 bytes)")
    p.data_zero(512)
    p.label(SYM_USER_STACK_END)

    p.section(".mem_region", flags="aw", sect_type="@progbits")
    p.align(4)
    p.label(SYM_MEM_REGION)
    _init_random_mem_region(p)  # Initialize with random data for fuzzing diversity
    p.label(SYM_MEM_REGION_END)

    p.label(LBL_KERNEL_INSTR_START)
    p.label(LBL_KERNEL_INSTR_END)
    p.label(LBL_KERNEL_DATA_START)

    p.section(LBL_PAGE_TABLE_SEC, flags="aw", sect_type="@progbits")

    p.align(12)
    p.label(LBL_PAGE_TABLE_0)
    p.directive("dword", "0x1, 0x1")
    for i in range(2, 40):
        p.directive("dword", f"0x{i:x}00000cf")

    p.align(12)
    p.label(LBL_PAGE_TABLE_1)
    p.directive("dword", "0x1, 0x1")
    for i in range(2, 512):
        p.directive("dword", "0x0")

    p.align(12)
    p.label(LBL_PAGE_TABLE_2)
    p.directive("dword", "0x1, 0x1")
    for i in range(2, 512):
        p.directive("dword", "0x0")

    p.align(12)
    p.label(LBL_PAGE_TABLE_3)
    for i in range(512):
        p.directive("dword", f"0x{i:x}000cf")

    p.align(12)
    p.label(LBL_PAGE_TABLE_4)
    for i in range(512):
        p.directive("dword", f"0x{0x200 + i:x}000cf")

    p.align(12)
    p.label(LBL_PAGE_TABLE_5)
    for i in range(512):
        p.directive("dword", f"0x{0x400 + i:x}000cf")

    p.align(12)
    p.label(LBL_PAGE_TABLE_6)
    for i in range(512):
        p.directive("dword", f"0x{0x600 + i:x}000cf")

    return p


# ------------------------------------------------------------------------------
# CVA6 Private Functions (_cva6_*)
# CVA6 Config: RV64GC + B + ZKN, NO Zfh/Zfhmin (no fmv.h.x)
# ------------------------------------------------------------------------------

def _cva6_text_startup(p: AsmProgram) -> AsmProgram:
    """
    [CVA6] Build the startup sequence in .text.init.
    CVA6 uses standard RISC-V privilege architecture.

    NOTE: We use .text.init instead of .text because CVA6's linker script
    places .text.init at 0x80000000 first, then .text after alignment.
    This ensures correct memory preloading in CVA6's Verilator testbench.
    """
    p.globl(LBL_START).section(".text.init")

    p.label(LBL_START)

    # CVA6 doesn't need MISA write (it's read-only in CVA6)
    # Just setup trap vectors
    p.label(LBL_TRAP_VEC_INIT)
    p.la("x13", LBL_OTHER_EXP)
    p.csrw(CSR.MTVEC, "x13", comment="MTVEC")
    p.la("x13", LBL_OTHER_EXP_S)
    p.csrw(CSR.STVEC, "x13", comment="STVEC")

    p.label(LBL_MEPC_SETUP)
    p.la("x13", LBL_INIT)
    p.csrw(CSR.MEPC, "x13")

    return p


def _cva6_init(p: AsmProgram) -> AsmProgram:
    """
    [CVA6] Mode initialization:
    - Write MSTATUS/MIE/PMP
    - Enter init via mret

    CVA6 supports M/S/U modes with SV39 MMU.
    """
    p.label(LBL_INIT_ENV)

    # Generate random MSTATUS for CVA6 (RV64, no H extension)
    ms_val = _random_mstatus_cva6()
    mpp = (ms_val >> 11) & 0b11

    # Load and write MSTATUS
    p.li("x26", f"0x{ms_val:016x}")
    p.csrw(CSR.MSTATUS, "x26", comment=f"MSTATUS (MPP={mpp})")

    # PMP setup for non-M-mode execution
    # CVA6 has 8 PMP entries
    # Use NAPOT mode to cover entire address space (including mem_region for AMO instructions)
    if mpp != 3:
        p.li("x16", -1)  # All 1s = 0xffffffffffffffff
        p.csrw(0x3b0, "x16")  # pmpaddr0
        p.li("x16", 0x1f)  # NAPOT + RWX
        p.csrw(0x3a0, "x16")  # pmpcfg0
        p.instr("sfence.vma", "x0", "x0")

    # Disable interrupts
    p.li("x26", "0x0")
    p.csrw(CSR.MIE, "x26", comment="MIE")
    p.mret()

    return p


def _cva6_init_reg(p: AsmProgram) -> AsmProgram:
    """
    [CVA6] Initialize floating-point and general-purpose registers.

    IMPORTANT: CVA6 does NOT support Zfh extension, so we only use:
    - fmv.w.x (single precision, F extension)
    - fmv.d.x (double precision, D extension)

    NO fmv.h.x (half precision, Zfh extension)!

    This function initializes ALL registers to ensure deterministic behavior:
    - x1-x31: General-purpose registers (x0 is hardwired to 0)
    - f0-f31: Floating-point registers
    """
    p.label(LBL_INIT)

    # Set floating-point rounding mode
    major_modes = [0, 1, 2, 3, 4]
    minor_modes = [5, 6, 7]

    if random.random() < 0.95:
        rm = random.choice(major_modes)
    else:
        rm = random.choice(minor_modes)

    p.instr("fsrmi", str(rm))

    # === General-purpose and floating-point register initialization ===
    # CVA6 only supports F and D extensions, NOT Zfh
    # So we only use fmv.w.x (32-bit) and fmv.d.x (64-bit)

    # Phase 1: Initialize ALL x1-x31 (x0 is hardwired to 0)
    for r in range(1, 32):
        rand_val = random.getrandbits(64)
        p.li(f"x{r}", f"0x{rand_val:016x}")

    # Phase 2: Initialize ALL f0-f31 using x5 (t0) as temp
    for r in range(32):
        rand_val = random.getrandbits(64)
        p.li("x5", f"0x{rand_val:016x}")  # Use t0 as temp register
        # CVA6: Only use fmv.w.x or fmv.d.x (NO fmv.h.x!)
        op = random.choice(["fmv.w.x", "fmv.d.x"])
        p.instr(op, f"f{r}", "x5")

    # Setup memory region pointer for Store/Load operations
    # Point t6 to the MIDDLE of mem_region (offset by 4096 bytes = half of 8KB)
    # This allows both positive and negative offsets to access valid memory
    p.la("t6", SYM_MEM_REGION)
    p.li("t5", "4096")
    p.instr("add", "t6", "t6", "t5")

    p.instr("j", LBL_MAIN)

    p.align(12)
    return p


def _random_mstatus_cva6():
    """
    Generate random MSTATUS value for CVA6.

    CVA6 Config:
    - RV64 (XLEN=64)
    - No H extension (RVH=0)
    - Supports M/S/U modes
    - Has MMU (SV39)
    """
    val = 0

    # SD(63) - derived by hardware, keep 0

    # SXL[1:0] (35-34) & UXL[1:0] (33-32)
    # For RV64: 2 means 64-bit
    sxl = 2  # Always 64-bit for CVA6
    uxl = 2
    val |= (sxl << 34)
    val |= (uxl << 32)

    # TSR(22), TW(21), TVM(20), MXR(19), SUM(18), MPRV(17)
    for bit in [22, 21, 20, 19, 18, 17]:
        val |= (random.randint(0, 1) << bit)

    # XS[1:0] (16-15), FS[1:0] (14-13)
    # CVA6 has F/D extensions, so FS can be non-zero
    # IMPORTANT: FS must NOT be 0, otherwise FP instructions cause illegal instruction exceptions
    # FS=0 (Off): FP disabled, all FP instructions trap
    # FS=1 (Initial): FP enabled, initial state
    # FS=2 (Clean): FP enabled, no modifications
    # FS=3 (Dirty): FP enabled, state modified
    xs = random.randint(0, 3)
    fs = random.randint(1, 3)  # Never Off, always enable FP
    val |= (xs << 15)
    val |= (fs << 13)

    # VS[1:0] (10-9) - CVA6 has no V extension
    vs = 0
    val |= (vs << 9)

    # MPP[1:0] (12-11): legal values 0 (U), 1 (S), 3 (M)
    mpp = random.choice([0, 1, 3])
    val |= (mpp << 11)

    # SPP(8), MPIE(7), UBE(6), SPIE(5), MIE(3), SIE(1)
    for bit in [8, 7, 5, 3, 1]:
        val |= (random.randint(0, 1) << bit)

    # UBE(6) - CVA6 is little-endian, keep 0
    # val |= (0 << 6)

    return val & ((1 << 64) - 1)


def _cva6_exception_vector(p: AsmProgram) -> AsmProgram:
    """
    [CVA6] Exception handlers for M-mode and S-mode.
    Similar to XiangShan but adapted for CVA6.
    """
    # M-mode trap handler
    p.label(LBL_OTHER_EXP)
    p.option("norvc")
    p.csrr("x13", CSR.MEPC)
    p.instr("addi", "x13", "x13", "4")
    p.csrw(CSR.MEPC, "x13")
    p.mret()
    p.option("rvc")

    # S-mode trap handler
    p.label(LBL_OTHER_EXP_S)
    p.option("norvc")
    p.csrr("x13", CSR.SEPC)
    p.instr("addi", "x13", "x13", "4")
    p.csrw(CSR.SEPC, "x13")
    p.instr("sret")
    p.option("rvc")

    return p


def _cva6_data_sections(p: AsmProgram) -> AsmProgram:
    """
    [CVA6] Data area and custom sections.
    """
    p.section(".data")
    p.directive("align", "6")
    p.directive("global", SYM_TOHOST)
    p.label(SYM_TOHOST)
    if p.arch.is_rv64():
        p.data_dword(0)
    else:
        p.data_word(0, 0)

    p.directive("align", "6")
    p.directive("global", SYM_FROMHOST)
    p.label(SYM_FROMHOST)
    if p.arch.is_rv64():
        p.data_dword(0)
    else:
        p.data_word(0, 0)

    p.section(".region_0", flags="aw", sect_type="@progbits")
    p.label(SYM_REGION0)
    rand_words = [f"0x{random.getrandbits(32):08x}" for _ in range(8)]
    p.data_word(*rand_words)

    # Memory region for load/store operations
    p.section(".mem_region", flags="aw", sect_type="@progbits")
    p.align(4)
    p.label(SYM_MEM_REGION)
    _init_random_mem_region(p)  # Initialize with random data for fuzzing diversity
    p.label(SYM_MEM_REGION_END)

    return p


# ------------------------------------------------------------------------------
# Common Private Functions (_common_*)
# ------------------------------------------------------------------------------

# def _common_test_done(p: AsmProgram) -> AsmProgram:
#     """
#     [Common] test_done: End with wfi.
#     """
#     p.label(LBL_TEST_DONE)
#     p.wfi()
#     return p


def _common_main_with_hook(p: AsmProgram) -> AsmProgram:
    """
    [Common] main section with hook insertion point.
    """
    p.align(2)
    p.option("norvc")
    p.label(LBL_MAIN)
    p.hook(HOOK_MAIN)
    p.fourbyte("0x0000006b")
    p.option("rvc")
    return p


def _common_support_routines(p: AsmProgram) -> AsmProgram:
    """
    [Common] Helper routines: write_tohost/_exit, debug_rom/debug_exception/instr_end.
    """
    p.label(LBL_WRITE_TOHOST)
    p.la("t1", SYM_TOHOST)
    p.li("t2", 1)
    p.sw("t2", "0(t1)")

    p.label(LBL_EXIT)
    p.instr("j", LBL_WRITE_TOHOST)

    p.label(LBL_DEBUG_ROM); p.dret()
    p.label(LBL_DEBUG_EXC); p.dret()
    p.label(LBL_INSTR_END); p.instr("nop")
    return p


# ==============================================================================
# Public Template Build Functions
# ==============================================================================

def build_template_xiangshan(arch: ArchConfig) -> AsmProgram:
    """
    Build complete XiangShan template.

    This template runs in mode only with simple exception handling.
    """
    p = AsmProgram(arch=arch)

    _xs_text_startup(p)
    _xs_init(p)
    _xs_init_reg(p)
    _exception_vector(p)
    # _common_test_done(p)
    _common_main_with_hook(p)
    _common_support_routines(p)
    _init_data_sections(p)

    return p


def build_template_nutshell(arch: ArchConfig) -> AsmProgram:
    """
    Build complete NutShell M-mode template.

    Similar to XiangShan M-mode but uses mtvec_handler routing and different MSTATUS.
    """
    p = AsmProgram(arch=arch)

    _nutshell_m_text_startup(p)
    _nutshell_m_machine_mode_init(p)
    _nutshell_init_reg(p)  
    _exception_vector(p)
    # _common_test_done(p)
    _nutshell_m_main_with_hook(p)
    _common_support_routines(p)
    _init_data_sections(p)  

    return p


def build_template_rocket(arch: ArchConfig) -> AsmProgram:
    """
    Build complete XiangShan S-mode template.

    This template runs in supervisor mode with virtual memory (SATP/page tables).
    """
    p = AsmProgram(arch=arch)

    if random.random() < 0:
        _xs_text_startup(p)
        _s_mode_pmp_setup(p)
        _s_mode_mepc_setup(p)
        _s_mode_supervisor_init(p)
        _s_mode_init_sequence(p)
        _exception_vector(p)
        _s_mode_main_with_hook(p)
        _common_support_routines(p)
        _s_mode_data_sections(p)
    else:
        _xs_text_startup(p)
        _xs_init(p)
        _xs_init_reg(p)
        _exception_vector(p)
        _common_main_with_hook(p)
        _common_support_routines(p)
        _init_data_sections(p)


    return p




def build_template_testxs_u_mode(arch: ArchConfig) -> AsmProgram:
    """
    Build complete TestXS U-mode template.

    This template runs in user mode with complex multi-level page tables
    and detailed exception handling.
    """
    p = AsmProgram(arch=arch)

    _u_mode_text_startup(p)
    _u_mode_pmp_setup(p)
    _u_mode_process_page_tables(p)
    _u_mode_mepc_setup(p)
    _u_mode_user_init(p)
    _u_mode_init_sequence(p)
    _u_mode_stvec_handler(p)
    _u_mode_mtvec_handler(p)
    _u_mode_exception_handlers(p)
    # _common_test_done(p)
    _common_main_with_hook(p)
    _common_support_routines(p)
    _u_mode_data_sections(p)

    return p


def build_template_cva6(arch: ArchConfig) -> AsmProgram:
    """
    Build complete CVA6 template.

    CVA6 (formerly Ariane) is a 6-stage, single issue, in-order CPU
    implementing the 64-bit RISC-V instruction set.

    Supported extensions: RV64GC + B (Zba/Zbb/Zbs/Zbc) + ZKN (crypto)
    NOT supported: Zfh/Zfhmin (half-precision FP), V (vector), H (hypervisor)

    This template runs in M/S/U modes with simple exception handling.
    """
    p = AsmProgram(arch=arch)

    # Startup sequence (trap vector setup, MEPC setup)
    _cva6_text_startup(p)

    # Mode initialization (MSTATUS, PMP, MIE)
    _cva6_init(p)

    # Register initialization (NO fmv.h.x!)
    _cva6_init_reg(p)

    # Exception handlers
    _cva6_exception_vector(p)

    # Main section with hook
    _common_main_with_hook(p)

    # Support routines (write_tohost, debug_rom, etc.)
    _common_support_routines(p)

    # Data sections
    _cva6_data_sections(p)

    return p


def random_mstatus_rv64_h():
    val = 0

    # --- High position retention / SD ---
    # SD(63) is derived from FS/XS/VS by the implementation, 
    # and is kept at 0 here, so that it is more reasonable to let the hardware set it itself.

    # --- MPV(39), GVA(38), MBE(37), SBE(36) ---
    for bit in [39, 38, 37, 36]:
        val |= (random.randint(0, 1) << bit)

    # --- SXL[1:0] (35–34) & UXL[1:0] (33–32) ---
    # For RV64, a valid encoding is typically 1 (32-bit) or 2 (64-bit).
    sxl = random.choice([1, 2])
    uxl = random.choice([1, 2])
    val |= (sxl << 34)
    val |= (uxl << 32)

    # --- TSR(22), TW(21), TVM(20), MXR(19), SUM(18), MPRV(17) ---
    for bit in [22, 21, 20, 19, 18, 17]:
        val |= (random.randint(0, 1) << bit)

    # --- XS[1:0] (16–15), FS[1:0] (14–13), VS[1:0] (10–9) ---
    # IMPORTANT: FS and VS must NOT be 0, otherwise FP/Vector instructions trap
    # FS/VS=0 (Off): unit disabled, instructions cause illegal instruction exception
    # FS/VS=1 (Initial): unit enabled, initial state
    # FS/VS=2 (Clean): unit enabled, no modifications
    # FS/VS=3 (Dirty): unit enabled, state modified
    xs = random.randint(0, 3)
    fs = random.randint(1, 3)  # Never Off, always enable FP
    vs = random.randint(1, 3)  # Never Off, always enable Vector
    val |= (xs << 15)
    val |= (fs << 13)
    val |= (vs << 9)

    # --- MPP[1:0] (12–11) legal：0,1,3 ---
    mpp = random.choice([0, 1, 3])
    val |= (mpp << 11)

    # --- SPP(8), MPIE(7), UBE(6), SPIE(5), MIE(3), SIE(1) ---
    for bit in [8, 7, 6, 5, 3, 1]:
        val |= (random.randint(0, 1) << bit)

    # The remaining WPRI bits remain 0
    return val & ((1 << 64) - 1)


# ==============================================================================
# Template Factory Function
# ==============================================================================

def build_template(template_type: TemplateType, arch: ArchConfig) -> AsmProgram:
    """
    Factory function to build template based on type.

    Args:
        template_type: The type of template to build (from TemplateType enum)
        arch: Architecture configuration (RV32/RV64, ISA extensions)

    Returns:
        AsmProgram with the complete template

    Raises:
        ValueError: If template_type is unknown
    """

    builders = {
        TemplateType.XIANGSHAN: build_template_xiangshan,
        TemplateType.NUTSHELL: build_template_nutshell,
        TemplateType.ROCKET: build_template_rocket,
        TemplateType.CVA6: build_template_cva6,
        # TemplateType.TESTXS_U_MODE: build_template_testxs_u_mode,
    }

    builder = builders.get(template_type, None)
    if builder is None:
        raise ValueError(f"Unknown template type: {template_type}")

    return builder(arch)


# ==============================================================================
# Template Instance Factory Function
# ==============================================================================

def create_template_instance(
    arch: ArchConfig,
    template_type: str
) -> TemplateInstance:
    """
    Factory function to create a fresh template instance with random values.

    Each call triggers new random generation (MSTATUS, register initialization, etc.).
    This ensures each seed gets independent random content.

    Args:
        arch: Architecture configuration (RV32/RV64, ISA extensions)
        template_type: Type of template to use. If None, randomly selects from all 5 types.

    Returns:
        TemplateInstance ready for use with independently generated random content
    """


    template_type_enum = TemplateType(template_type)

    program = build_template(template_type_enum, arch)
    hook_idx = program.get_hook_idx(HOOK_MAIN)

    return TemplateInstance(
        header = program.render_slice(0, hook_idx),
        footer = program.render_slice(hook_idx + 1, len(program.nodes)),
        template_type = template_type_enum,
        isa = arch.get_isa(),
        arch_bits = arch.get_arch_bits()
    )
