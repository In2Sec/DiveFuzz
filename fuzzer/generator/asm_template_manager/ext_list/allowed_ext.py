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

# ========= 1) CVA6 =========
ALLOWED_EXT_CVA6 = [
    "RV_ZICSR", \
    "RV64_I", \
    "rv_zifencei", \
    "RV_I", \
    "RV64_I", \
    "RV_F", \
    "RV_D", \
    "RV64_F", \
    "RV64_D", \
    "RV_C", \
    "RV_C_D", \
    "RV32_C", \
    "RV_M", \
    "RV32_ZPN", \
    "RV64_M", \
    "RV_A", \
    "RV64_A", \
    "RV_ZBKB", \
    "RV64_ZBKB", \
    "RV_ZBKC", \
    "RV_ZBKX", \
    "RV64_ZK", \
    "RV_ZK", \
    "ROCC", \
    # "RV_F_ZFINX" # Zfinx/Zdinx/Zhinx{min} extensions conflict with 'F/D/Q/Zfh{min}' extensions
]

# ========= 2) CASCADE =========
ALLOWED_EXT_CVA6_CASCADE = [
    "RV_ZICSR", \
    "RV64_I", \
    "rv_zifencei", \
    "RV_I", \
    "RV64_I", \
    "RV_F", \
    "RV_D", \
    "RV64_F", \
    "RV64_D", \
    "RV_M", \
    "RV64_M", \
    # "RV_A", \
    # "RV64_A", \
    "RV_F_ZFINX" 
]

# ========= 3) RV32 =========
ALLOWED_EXT_RV32 = [
    "RV_ZICSR", \
    "rv_zifencei", \
    "RV_I", \
    "RV_M", \
    "RV32_ZPN", \
    "RV_ZBKB", \
    "RV_ZBKC", \
    "rv_32B",\
    "rv_zbs",\
    "ILL"
]

# ========= 4) General =========
ALLOWED_EXT_COMPARE = [
    "RV_ZICSR", \
    "RV64_I", \
    "rv_zifencei", \
    "RV_I", \
    "RV64_I", \
    "RV_F", \
    "RV_D", \
    "RV64_F", \
    "RV64_D", \
    "RV_C_D", \
    "RV32_C", \
    "RV_M", \
    "RV32_ZPN", \
    "RV64_M", \
    "RV_A", \
    "RV64_A", \
    "RV_ZBKB", \
    "RV64_ZBKB", \
    "RV_ZBKC", \
    "RV_ZBKX", \
    "RV64_ZK", \
    "RV_ZK", \
    "ROCC", \
    "ILL",
    "RV_F_ZFINX",
    # "RV_V"
]

ALLOWED_EXT_BASE = [
    "RV64_I", \
    "RV_I", \
    "RV_F", \
    "RV_D", \
    "RV64_F", \
    "RV64_D", \
    "RV_M", \
    "RV64_M", \
    "RV_A", \
    "RV64_A", \
]

# ========= 5) NutShell (RV64IMAC) =========
# NutShell is an educational RISC-V processor by OSCPU team
# Supports: I, M, A, C (optional), Zicsr, Zifencei
# Does NOT support: F, D (no FPU)
ALLOWED_EXT_NUTSHELL = [
    "RV_ZICSR",       # CSR instructions
    "rv_zifencei",    # FENCE.I instruction
    "RV_I",           # Base integer instructions
    "RV64_I",         # RV64 specific instructions (e.g., LD, SD, ADDIW)
    "RV_M",           # Multiplication extension
    "RV64_M",         # RV64 multiplication (e.g., MULW, DIVW)
    # "RV_A",           # Atomic extension
    # "RV64_A",         # RV64 atomic (e.g., LR.D, SC.D)
    "RV_C",           # Compressed extension (if EnableRVC is set)
    "RV32_C",         # RV32 compressed subset
]

# NutShell RV32 mode (without 64-bit instructions)
ALLOWED_EXT_NUTSHELL_RV32 = [
    "RV_ZICSR",
    "rv_zifencei",
    "RV_I",
    "RV_M",
    "RV_A",
    "RV_C",
    "RV32_C",
]

# ========= 6) BOOM (RV64GC) =========
# BOOM (Berkeley Out-of-Order Machine) - RV64IMAFDCG
# ISA string from Cospike: rv64imafdczicsr_zifencei_zihpm_zicntr
# Supports: I, M, A, F, D, C, Zicsr, Zifencei
# Does NOT support: V (vector), Zfh (half-precision FP), B (bit manipulation), ZK* (crypto)
ALLOWED_EXT_BOOM = [
    "RV_ZICSR",       # CSR instructions
    "rv_zifencei",    # FENCE.I instruction
    "RV_I",           # Base integer instructions
    "RV64_I",         # RV64 specific instructions (e.g., LD, SD, ADDIW)
    "RV_M",           # Multiplication extension
    "RV64_M",         # RV64 multiplication (e.g., MULW, DIVW)
    # "RV_A",           # Atomic extension
    # "RV64_A",         # RV64 atomic (e.g., LR.D, SC.D)
    "RV_F",           # Single-precision floating-point
    "RV64_F",         # RV64 FP (e.g., FCVT.L.S)
    "RV_D",           # Double-precision floating-point
    "RV64_D",         # RV64 double (e.g., FCVT.L.D)
    "RV_C",           # Compressed extension
    "RV_C_D",         # Compressed FP (double)
    "RV32_C",         # RV32 compressed subset
    "RV64_C"
    # Note: NO Zfh, B (Zba/Zbb/Zbs/Zbc), or ZK* extensions
]


# ========= 7) XiangShan (RV64GCBVH) =========
# XiangShan is an advanced high-performance RISC-V processor by BOSC/ICT
# Full ISA: RV64IMAFDC + Vector + Hypervisor + Bit Manipulation + Cryptography
# Key extensions: I, M, A, F, D, C, V, H, Zba, Zbb, Zbc, Zbs, Zfh, Zkn, Zksed, Zksh
# Source: Parameters.scala ISAExtensions and MisaBundle
#
# NOTE: Some extensions are disabled to avoid difftest false positives:
# - RV_ZBKX: xperm4/xperm8 instructions - Spike's DEFAULT_ISA lacks Zbkx
# - RV_ZK/RV64_ZK: AES instructions (aes64*) - Spike's DEFAULT_ISA lacks Zkne/Zknd
# To re-enable, modify Spike's platform.h DEFAULT_ISA to include these extensions
ALLOWED_EXT_XIANGSHAN = [
    "RV_ZICSR",       # CSR instructions (Zicsr)
    "rv_zifencei",    # FENCE.I instruction (Zifencei)
    "RV_I",           # Base integer instructions
    "RV64_I",         # RV64 specific instructions (LD, SD, ADDIW, etc.)
    "RV_M",           # Multiplication extension
    "RV64_M",         # RV64 multiplication (MULW, DIVW, etc.)
    # "RV_A",           # Atomic extension
    # "RV64_A",         # RV64 atomic (LR.D, SC.D, AMO*.D)
    "RV_F",           # Single-precision floating-point
    "RV64_F",         # RV64 FP (FCVT.L.S, etc.)
    "RV_D",           # Double-precision floating-point
    "RV64_D",         # RV64 double (FCVT.L.D, etc.)
    "RV_C",           # Compressed extension
    "RV_C_D",         # Compressed FP (double)
    "RV32_C",         # RV32 compressed subset (C.LW, C.SW, etc.)
    "RV64_C",         # RV64 compressed (C.LD, C.SD, etc.)
    # Bit Manipulation Extensions (Zba/Zbb/Zbc/Zbs)
    "rv_zbs",         # Single-bit manipulation (BCLR, BEXT, BINV, BSET)
    # Cryptographic Extensions (Zbkb/Zbkc/Zbkx/Zkn/Zksed/Zksh)
    "RV_ZBKB",        # Bitmanip for cryptography
    "RV64_ZBKB",      # RV64 bitmanip for crypto
    "RV_ZBKC",        # Carryless multiply for crypto (CLMUL, CLMULH)
    # === DISABLED: Causing difftest false positives (Spike lacks these extensions) ===
    # "RV_ZBKX",        # Crossbar permutation for crypto (xperm4, xperm8) - DISABLED: Spike lacks Zbkx
    # "RV_ZK",          # NIST Suite crypto (AES, SHA) - DISABLED: Spike lacks Zkne/Zknd
    # "RV64_ZK",        # RV64 crypto (AES64*, SHA512*) - DISABLED: Spike lacks Zkne/Zknd
    # Note: Vector extension (RV_V) supported by XiangShan but not yet in formats.py
    # Note: Half-precision FP (Zfh/Zfa) supported but not yet in formats.py
]

# ========= 8) Rocket (RV64GC) =========
# Rocket is the original in-order RISC-V processor from UC Berkeley
# Full ISA: RV64IMAFDCG (RV64GC) with Zicsr, Zifencei
# ISA string from CSR.scala: rv64imafdcsu_zicsr_zifencei
# Supports: I, M, A, F, D, C, Zicsr, Zifencei, S (supervisor), U (user mode)
# Optional: Zba, Zbb, Zbs (bit manipulation extensions in newer versions)
# Does NOT support: V (vector), Zfh (half-precision FP), ZK* (crypto) by default
#
# NOTE: All supported extensions are enabled (including atomics).
#       For seed generation only - differential testing filters disabled.
ALLOWED_EXT_ROCKET = [
    "RV_ZICSR",       # CSR instructions
    "rv_zifencei",    # FENCE.I instruction
    "RV_I",           # Base integer instructions
    "RV64_I",         # RV64 specific instructions (e.g., LD, SD, ADDIW)
    "RV_M",           # Multiplication extension
    "RV64_M",         # RV64 multiplication (e.g., MULW, DIVW)
    "RV_A",           # Atomic extension - ENABLED for seed generation
    "RV64_A",         # RV64 atomic (e.g., LR.D, SC.D) - ENABLED
    "RV_F",           # Single-precision floating-point
    "RV64_F",         # RV64 FP (e.g., FCVT.L.S)
    "RV_D",           # Double-precision floating-point
    "RV64_D",         # RV64 double (e.g., FCVT.L.D)
    "RV_C",           # Compressed extension
    "RV_C_D",         # Compressed FP (double)
    "RV32_C",         # RV32 compressed subset
    "RV64_C",         # RV64 compressed (e.g., C.LD, C.SD)
    # Note: Bit manipulation (Zba/Zbb/Zbs) available in some configs but not default
    # Note: NO Vector (V), Zfh, or ZK* extensions by default
]

# Rocket RV32 mode (without 64-bit instructions)
ALLOWED_EXT_ROCKET_RV32 = [
    "RV_ZICSR",
    "rv_zifencei",
    "RV_I",
    "RV_M",
    "RV_A",
    "RV_F",
    "RV_D",
    "RV_C",
    "RV32_C",
]

# Optional: provides a simple mapping that can be accessed externally by profile (without any logic)
ALLOWED_EXT_PROFILES = {
    "cva6": ALLOWED_EXT_CVA6,
    "cva6_cascade": ALLOWED_EXT_CVA6_CASCADE,
    "rv32": ALLOWED_EXT_RV32,
    "general": ALLOWED_EXT_COMPARE,
    "base": ALLOWED_EXT_BASE,
    "nutshell": ALLOWED_EXT_NUTSHELL,
    "nutshell_rv32": ALLOWED_EXT_NUTSHELL_RV32,
    "boom": ALLOWED_EXT_BOOM,
    "xiangshan": ALLOWED_EXT_XIANGSHAN,
    "rocket": ALLOWED_EXT_ROCKET,
    "rocket_rv32": ALLOWED_EXT_ROCKET_RV32,
}
