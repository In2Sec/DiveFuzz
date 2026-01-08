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
}
