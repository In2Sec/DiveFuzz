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

# ------------------------------------------------------------------------------
# XiangShan mode Private Functions
# ------------------------------------------------------------------------------

def _xs_text_startup(p: AsmProgram) -> AsmProgram:
    """
    [XiangShan ] Build the startup sequence in .text (_start and early jumps):
    - Read mhartid/core ID
    - Jump to h0_start via jalr
    - Set MISA, kernel stack pointer, trap vector MTVEC, initial MEPC
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


def _xs_init(p: AsmProgram) -> AsmProgram:
    """
    [XiangShan] Mode basic initialization:
    - Write MSTATUS/MIE PMP/PMA
    - Enter init via mret
    """
    p.label(LBL_INIT_ENV)
    ms_val = random_mstatus_rv64_h()
    mpp = (ms_val >> 11) & 0b11  

    p.li("x26", f"0x{ms_val:016x}")
    p.csrw(CSR.MSTATUS, "x26", comment=f"MSTATUS (mode is {mpp})")
    # Build PMP (Physical Memory Protection) setup.
    # TODO support more PMP config
    if mpp != 3:
        p.la("x16", LBL_MAIN)
        p.csrw(0x3b0, "x16")
        p.li("x16", 0xf)
        p.csrw(0x3a0, "x16")

        p.instr("sfence.vma x0, x0")

    p.li("x26", "0x0")
    p.csrw(CSR.MIE, "x26", comment="MIE")
    p.mret()
    return p


def _xs_init_reg(p: AsmProgram) -> AsmProgram:
    """
    [XiangShan/Rocket] init: Initialize floating-point and general-purpose registers.
    """
    p.label(LBL_INIT)

    major_modes = [0, 1, 2, 3, 4]

    minor_modes = [5, 6, 7]

    if random.random() < 0.95:
        rm = random.choice(major_modes)
    else:
        rm = random.choice(minor_modes)

    p.instr("fsrmi", str(rm))

    # === General-purpose register initialization ===
    for r in range(16):
        
        rand_val = random.getrandbits(64)
        p.li(f"x{r}", f"0x{rand_val:016x}")
        op = random.choice(["fmv.h.x", "fmv.w.x", "fmv.d.x"])
        p.instr(op, f"f{r}", f"x{r}")

    p.li("t6", "4096")

    p.instr("j", LBL_MAIN)

    p.align(12)
    return p

 

def _nutshell_init_reg(p: AsmProgram) -> AsmProgram:
    """
    [XiangShan/Rocket] init: Initialize floating-point and general-purpose registers.
    """
    p.label(LBL_INIT)

    # === General-purpose register initialization ===
    for r in range(16):
        
        rand_val = random.getrandbits(64)
        p.li(f"x{r}", f"0x{rand_val:016x}")

    p.li("t6", "4096")

    p.instr("j", LBL_MAIN)

    p.align(12)
    return p



def _exception_vector(p: AsmProgram) -> AsmProgram:
    """
    [XiangShan/NutShell/Rocket] other_exp: Simple exception handling (increment mepc by 4, then mret).
    """
    p.label(LBL_OTHER_EXP)
    p.option("norvc")
    p.csrr("x13", CSR.MEPC)
    p.instr("addi", "x13", "x13", "4")
    p.csrw(CSR.MEPC, "x13")
    p.mret()
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
    [NutShell M-mode] Main section with csrrwi instruction after hook.
    """
    p.align(2)
    p.option("norvc")

    p.label(LBL_MAIN)
    p.hook(HOOK_MAIN)

    p.instr("csrrwi", "t0", "mhpmevent25", "1")
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
    """
    p.label(LBL_PMP_SETUP)
    p.la("x16", LBL_MAIN)
    p.csrw(0x3b0, "x16")
    p.li("x16", 0xf)
    p.csrw(0x3a0, "x16")
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
    """
    p.label(LBL_INIT)

    # FP register initialization
    p.li("x8", 2146959360);    p.instr("slli", "x8", "x8", "16"); p.instr("slli", "x8", "x8", "16")
    p.li("x5", 0);             p.instr("or", "x5", "x5", "x8");   p.instr("fmv.d.x", "f0", "x5")
    p.li("x8", 33088);         p.instr("fmv.h.x", "f1", "x8")
    p.li("x8", 490445);        p.instr("slli", "x8", "x8", "16"); p.instr("slli", "x8", "x8", "16")
    p.li("x5", 2820878163);    p.instr("or", "x5", "x5", "x8");   p.instr("fmv.d.x", "f2", "x5")
    p.li("x8", 31744);         p.instr("fmv.h.x", "f3", "x8")
    p.li("x8", 31743);         p.instr("fmv.h.x", "f4", "x8")
    p.li("x8", 2146435072);    p.instr("slli", "x8", "x8", "16"); p.instr("slli", "x8", "x8", "16")
    p.li("x5", 1);             p.instr("or", "x5", "x5", "x8");   p.instr("fmv.d.x", "f5", "x5")
    p.li("x8", 600638761);     p.instr("slli", "x8", "x8", "16"); p.instr("slli", "x8", "x8", "16")
    p.li("x5", 345061165);     p.instr("or", "x5", "x5", "x8");   p.instr("fmv.d.x", "f6", "x5")
    p.li("x8", 2146435072);    p.instr("slli", "x8", "x8", "16"); p.instr("slli", "x8", "x8", "16")
    p.li("x5", 1);             p.instr("or", "x5", "x5", "x8");   p.instr("fmv.d.x", "f7", "x5")
    p.li("x8", 192);           p.instr("fmv.h.x", "f8", "x8")
    p.li("x8", 4293918719);    p.instr("slli", "x8", "x8", "16"); p.instr("slli", "x8", "x8", "16")
    p.li("x5", 4294967295);    p.instr("or", "x5", "x5", "x8");   p.instr("fmv.d.x", "f9", "x5")
    p.li("x8", 64511);         p.instr("fmv.h.x", "f10", "x8")
    p.li("x8", 2480559614);    p.instr("slli", "x8", "x8", "16"); p.instr("slli", "x8", "x8", "16")
    p.li("x5", 265978380);     p.instr("or", "x5", "x5", "x8");   p.instr("fmv.d.x", "f11", "x5")
    p.li("x8", 835115);        p.instr("slli", "x8", "x8", "16"); p.instr("slli", "x8", "x8", "16")
    p.li("x5", 609019642);     p.instr("or", "x5", "x5", "x8");   p.instr("fmv.d.x", "f12", "x5")
    p.li("x8", 0);             p.instr("fmv.w.x", "f13", "x8")
    p.li("x8", 32256);         p.instr("fmv.h.x", "f14", "x8")
    p.li("x8", 2139095040);    p.instr("fmv.w.x", "f15", "x8")
    p.li("x8", 19);            p.instr("fmv.h.x", "f16", "x8")
    p.li("x8", 2150974470);    p.instr("fmv.w.x", "f17", "x8")
    p.li("x8", 1346398009);    p.instr("fmv.w.x", "f18", "x8")
    p.li("x8", 2143289344);    p.instr("fmv.w.x", "f19", "x8")
    p.li("x8", 31175);         p.instr("fmv.h.x", "f20", "x8")
    p.li("x8", 2146435072);    p.instr("slli", "x8", "x8", "16"); p.instr("slli", "x8", "x8", "16")
    p.li("x5", 1);             p.instr("or", "x5", "x5", "x8");   p.instr("fmv.d.x", "f21", "x5")
    p.li("x8", 2146435072);    p.instr("slli", "x8", "x8", "16"); p.instr("slli", "x8", "x8", "16")
    p.li("x5", 1);             p.instr("or", "x5", "x5", "x8");   p.instr("fmv.d.x", "f22", "x5")
    p.li("x8", 32768);         p.instr("fmv.h.x", "f23", "x8")
    p.li("x8", 31745);         p.instr("fmv.h.x", "f24", "x8")
    p.li("x8", 4293918719);    p.instr("slli", "x8", "x8", "16"); p.instr("slli", "x8", "x8", "16")
    p.li("x5", 4294967295);    p.instr("or", "x5", "x5", "x8");   p.instr("fmv.d.x", "f25", "x5")
    p.li("x8", 488043848);     p.instr("slli", "x8", "x8", "16"); p.instr("slli", "x8", "x8", "16")
    p.li("x5", 60684771);      p.instr("or", "x5", "x5", "x8");   p.instr("fmv.d.x", "f26", "x5")
    p.li("x8", 4286578688);    p.instr("fmv.w.x", "f27", "x8")
    p.li("x8", 3427503);       p.instr("fmv.w.x", "f28", "x8")
    p.li("x8", 2147658468);    p.instr("fmv.w.x", "f29", "x8")
    p.li("x8", 31744);         p.instr("fmv.h.x", "f30", "x8")
    p.li("x8", 2143289344);    p.instr("fmv.w.x", "f31", "x8")
    p.instr("fsrmi", "3")

    # GP register initialization
    p.li("x0",  "0xf20eafaf")
    p.li("x1",  "0xf1034be7")
    p.li("x2",  "0x80000000")
    p.li("x3",  "0x0")
    p.li("x4",  "0xf12beb63")
    p.li("x5",  "0xfc824cc8")
    p.li("x6",  "0x18ca07fa")
    p.li("x7",  "0xf")
    p.li("x8",  "0x6c66da25")
    p.li("x9",  "0x80000000")
    p.li("x10", "0x15fa294")
    p.li("x11", "0x6")
    p.li("x12", "0xf")
    p.li("x13", "0x0")
    p.li("x14", "0xc")
    p.li("x15", "0x80000000")
    p.li("x16", "0x0")
    p.li("x17", "0x0")
    p.li("x18", "0x0")
    p.li("x19", "0xf45ade45")
    p.li("x20", "0x3")
    p.li("x21", "0x0")
    p.li("x22", "0x101a400d")
    p.li("x23", "0x8225d371")
    p.li("x24", "0x98b685c8")
    p.li("x25", "0x0")
    p.li("x26", "0x1b23092d")
    p.li("x27", "0xffa21fa0")
    p.li("x29", "0xf6f9a8f2")
    p.comment("li x30, 0x80000000")
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

    p.label(SYM_KERNEL_STACK_END)
    p.data_8byte(0)

    p.section(".mem_region", flags="aw", sect_type="@progbits")
    p.align(4)
    p.label(SYM_MEM_REGION)
    p.data_space(8192)
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
    """
    p.label(LBL_PMP_SETUP)
    p.la("x29", LBL_MAIN)
    p.csrw(0x3b0, "x29")
    p.li("x29", 0xf)
    p.csrw(0x3a0, "x29")
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
    """
    p.label(LBL_INIT)

    p.li("x0",  "0xdfdb6f3b")
    p.li("x1",  "0x477b4a0f")
    p.li("x2",  "0xfd07d5c1")
    p.li("x3",  "0xf")
    p.li("x4",  "0x80000000")
    p.li("x5",  "0x0")
    p.li("x6",  "0xfceb8383")
    p.li("x7",  "0x75d8a2d8")
    p.li("x8",  "0x854e10aa")
    p.li("x9",  "0xf3acde09")
    p.li("x10", "0x9846fbc6")
    p.li("x11", "0xf042d4f4")
    p.li("x12", "0x4")
    p.li("x13", "0x0")
    p.li("x14", "0x7ab5f05c")
    p.li("x15", "0x80000000")
    p.li("x16", "0x0")
    p.li("x17", "0x0")
    p.li("x19", "0xf27aac6c")
    p.li("x20", "0xa2d87304")
    p.li("x21", "0xfcad8706")
    p.li("x22", "0x0")
    p.li("x23", "0x0")
    p.li("x24", "0x0")
    p.li("x25", "0x80000000")
    p.li("x26", "0x80585d40")
    p.li("x27", "0x80000000")
    p.li("x28", "0x49784ac")
    p.li("x29", "0xf6472a6f")
    p.li("x31", "0x0")

    p.la("x18", SYM_USER_STACK_END)
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

    p.label(SYM_KERNEL_STACK_END)
    p.data_8byte(0)

    p.label(SYM_USER_STACK_END)
    p.data_8byte(0)

    p.section(".mem_region", flags="aw", sect_type="@progbits")
    p.align(4)
    p.label(SYM_MEM_REGION)
    p.data_space(8192)
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
    xs = random.randint(0, 3)
    fs = random.randint(0, 3)
    vs = random.randint(0, 3)
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