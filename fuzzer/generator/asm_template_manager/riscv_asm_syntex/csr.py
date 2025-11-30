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
from enum import IntEnum

class CSR(IntEnum):
    """
    RISC-V CSR addresses (consolidated, spec-accurate).
    Groups mark the owning privilege level/extension; some CSRs are optional and
    appear only when the corresponding extension is implemented (e.g., V/H/Sstc/N).
    """

    # --------------------------
    # Machine-level (M) — core set
    # --------------------------
    MSTATUS     = 0x300
    MISA        = 0x301
    MIE         = 0x304
    MTVEC       = 0x305
    MCOUNTEREN  = 0x306
    MENVCFG     = 0x30A
    MSCRATCH    = 0x340
    MEPC        = 0x341
    MCAUSE      = 0x342
    MTVAL       = 0x343
    MIP         = 0x344
    MTINST      = 0x34A   # H extension added
    MTVAL2      = 0x34B   # H extension added

    # Machine information
    MVENDORID   = 0xF11
    MARCHID     = 0xF12
    MIMPID      = 0xF13
    MHARTID     = 0xF14
    MCONFIGPTR  = 0xF15

    # Machine delegate/enable
    MEDELEG     = 0x302
    MIDELEG     = 0x303

    # Machine performance counters / timers (Zicntr/Zihpm)
    MCOUNTINHIBIT = 0x320
    MCYCLE        = 0xB00
    MINSTRET      = 0xB02
    # RV32 high halves (appear on 32-bit harts)
    MCYCLEH       = 0xB80
    MINSTRETH     = 0xB82

    # Standard machine HPM counters (3..31)
    MHPMCOUNTER3  = 0xB03
    MHPMCOUNTER4  = 0xB04
    MHPMCOUNTER5  = 0xB05
    MHPMCOUNTER6  = 0xB06
    MHPMCOUNTER7  = 0xB07
    MHPMCOUNTER8  = 0xB08
    MHPMCOUNTER9  = 0xB09
    MHPMCOUNTER10 = 0xB0A
    MHPMCOUNTER11 = 0xB0B
    MHPMCOUNTER12 = 0xB0C
    MHPMCOUNTER13 = 0xB0D
    MHPMCOUNTER14 = 0xB0E
    MHPMCOUNTER15 = 0xB0F
    MHPMCOUNTER16 = 0xB10
    MHPMCOUNTER17 = 0xB11
    MHPMCOUNTER18 = 0xB12
    MHPMCOUNTER19 = 0xB13
    MHPMCOUNTER20 = 0xB14
    MHPMCOUNTER21 = 0xB15
    MHPMCOUNTER22 = 0xB16
    MHPMCOUNTER23 = 0xB17
    MHPMCOUNTER24 = 0xB18
    MHPMCOUNTER25 = 0xB19
    MHPMCOUNTER26 = 0xB1A
    MHPMCOUNTER27 = 0xB1B
    MHPMCOUNTER28 = 0xB1C
    MHPMCOUNTER29 = 0xB1D
    MHPMCOUNTER30 = 0xB1E
    MHPMCOUNTER31 = 0xB1F

    # RV32 high halves for HPM counters
    MHPMCOUNTER3H  = 0xB83
    MHPMCOUNTER4H  = 0xB84
    MHPMCOUNTER5H  = 0xB85
    MHPMCOUNTER6H  = 0xB86
    MHPMCOUNTER7H  = 0xB87
    MHPMCOUNTER8H  = 0xB88
    MHPMCOUNTER9H  = 0xB89
    MHPMCOUNTER10H = 0xB8A
    MHPMCOUNTER11H = 0xB8B
    MHPMCOUNTER12H = 0xB8C
    MHPMCOUNTER13H = 0xB8D
    MHPMCOUNTER14H = 0xB8E
    MHPMCOUNTER15H = 0xB8F
    MHPMCOUNTER16H = 0xB90
    MHPMCOUNTER17H = 0xB91
    MHPMCOUNTER18H = 0xB92
    MHPMCOUNTER19H = 0xB93
    MHPMCOUNTER20H = 0xB94
    MHPMCOUNTER21H = 0xB95
    MHPMCOUNTER22H = 0xB96
    MHPMCOUNTER23H = 0xB97
    MHPMCOUNTER24H = 0xB98  
    MHPMCOUNTER25H = 0xB99
    MHPMCOUNTER26H = 0xB9A
    MHPMCOUNTER27H = 0xB9B
    MHPMCOUNTER28H = 0xB9C
    MHPMCOUNTER29H = 0xB9D
    MHPMCOUNTER30H = 0xB9E
    MHPMCOUNTER31H = 0xB9F

    # HPM event selector（规范编号从 0x323 起）
    MHPMEVENT3   = 0x323
    MHPMEVENT4   = 0x324
    MHPMEVENT5   = 0x325
    MHPMEVENT6   = 0x326
    MHPMEVENT7   = 0x327
    MHPMEVENT8   = 0x328
    MHPMEVENT9   = 0x329
    MHPMEVENT10  = 0x32A
    MHPMEVENT11  = 0x32B
    MHPMEVENT12  = 0x32C
    MHPMEVENT13  = 0x32D
    MHPMEVENT14  = 0x32E
    MHPMEVENT15  = 0x32F
    MHPMEVENT16  = 0x330
    MHPMEVENT17  = 0x331
    MHPMEVENT18  = 0x332
    MHPMEVENT19  = 0x333
    MHPMEVENT20  = 0x334
    MHPMEVENT21  = 0x335
    MHPMEVENT22  = 0x336
    MHPMEVENT23  = 0x337
    MHPMEVENT24  = 0x338
    MHPMEVENT25  = 0x339
    MHPMEVENT26  = 0x33A
    MHPMEVENT27  = 0x33B
    MHPMEVENT28  = 0x33C
    MHPMEVENT29  = 0x33D
    MHPMEVENT30  = 0x33E
    MHPMEVENT31  = 0x33F

    # --------------------------
    # Supervisor-level (S)
    # --------------------------
    SSTATUS     = 0x100
    SEDELEG     = 0x102
    SIDELEG     = 0x103
    SIE         = 0x104
    STVEC       = 0x105
    SCOUNTEREN  = 0x106
    SENVCFG     = 0x10A
    SSCRATCH    = 0x140
    SEPC        = 0x141
    SCAUSE      = 0x142
    STVAL       = 0x143
    SIP         = 0x144
    SATP        = 0x180

    # --------------------------
    # SSTC (Supervisor timing comparison register) 
    # --------------------------
    STIMECMP    = 0x14D   # RV32
    STIMECMPH   = 0x15D
    # --------------------------
    # Hypervisor extension (H)
    # --------------------------
    HSTATUS     = 0x600
    HEDELEG     = 0x602
    HIDELEG     = 0x603
    HIE         = 0x604
    HCOUNTEREN  = 0x606
    HGEIE       = 0x607
    HENVCFG     = 0x60A
    HGATP       = 0x680
    HTVAL       = 0x643
    HIP         = 0x644
    HVIP        = 0x645
    HTINST      = 0x64A
    HGEIP       = 0xE12

    # --------------------------
    # VS (Virtual Supervisor)
    # --------------------------
    VSSTATUS    = 0x200
    VSIE        = 0x204
    VSTVEC      = 0x205
    VSSCRATCH   = 0x240
    VSEPC       = 0x241
    VSCAUSE     = 0x242
    VSTVAL      = 0x243
    VSIP        = 0x244
    VSATP       = 0x280

    # VS timing comparison (SSTC co-introduced with H extension) 
    VSTIMECMP   = 0x24D
    VSTIMECMPH  = 0x25D

    # --------------------------
    # User-level (U / N-Ext for user interrupts)
    # --------------------------
    USTATUS     = 0x000   # N/user interrupt-related capabilities must be implemented to exist
    UIE         = 0x004
    UTVEC       = 0x005
    USCRATCH    = 0x040
    UEPC        = 0x041
    UCAUSE      = 0x042
    UTVAL       = 0x043
    UIP         = 0x044

    # User Floating-Point CSRs（F/D）
    FFLAGS      = 0x001
    FRM         = 0x002
    FCSR        = 0x003

    # Vector Extension (V)
    VSTART      = 0x008
    VXSAT       = 0x009
    VXRM        = 0x00A
    VCSR        = 0x00F
    VL          = 0xC20
    VTYPE       = 0xC21
    VLENB       = 0xC22

    # User counters / timers (Zicntr/Zihpm)
    CYCLE       = 0xC00
    TIME        = 0xC01
    INSTRET     = 0xC02
    HPMCOUNTER3 = 0xC03
    HPMCOUNTER4 = 0xC04
    HPMCOUNTER5 = 0xC05
    HPMCOUNTER6 = 0xC06
    HPMCOUNTER7 = 0xC07
    HPMCOUNTER8 = 0xC08
    HPMCOUNTER9 = 0xC09
    HPMCOUNTER10= 0xC0A
    HPMCOUNTER11= 0xC0B
    HPMCOUNTER12= 0xC0C
    HPMCOUNTER13= 0xC0D
    HPMCOUNTER14= 0xC0E
    HPMCOUNTER15= 0xC0F
    HPMCOUNTER16= 0xC10
    HPMCOUNTER17= 0xC11
    HPMCOUNTER18= 0xC12
    HPMCOUNTER19= 0xC13
    HPMCOUNTER20= 0xC14
    HPMCOUNTER21= 0xC15
    HPMCOUNTER22= 0xC16
    HPMCOUNTER23= 0xC17
    HPMCOUNTER24= 0xC18
    HPMCOUNTER25= 0xC19
    HPMCOUNTER26= 0xC1A
    HPMCOUNTER27= 0xC1B
    HPMCOUNTER28= 0xC1C
    HPMCOUNTER29= 0xC1D
    HPMCOUNTER30= 0xC1E
    HPMCOUNTER31= 0xC1F

    # RV32 high halves for user counters
    CYCLEH      = 0xC80
    TIMEH       = 0xC81
    INSTRETH    = 0xC82
    
    # --------------------------
    # PMP (Machine)
    # --------------------------
    PMPCFG0     = 0x3A0
    PMPCFG1     = 0x3A1
    PMPCFG2     = 0x3A2
    PMPADDR0    = 0x3B0
    PMPADDR1    = 0x3B1
    PMPADDR2    = 0x3B2

    # --------------------------
    # Debug CSRs
    # --------------------------
    DCSR        = 0x7B0
    DPC         = 0x7B1
    DSCRATCH0   = 0x7B2
    DSCRATCH1   = 0x7B3
