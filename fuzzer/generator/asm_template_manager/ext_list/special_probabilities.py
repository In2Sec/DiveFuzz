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


# You can adjust the frequency of any instruction extension you want to test.

# ========= 1) CVA6 =========
# CVA6 Config: RV64GC + B (Zba/Zbb/Zbs/Zbc) + ZKN (crypto)
# NOTE: Must match ALLOWED_EXT_CVA6 exactly to avoid probability calculation errors
SPECIAL_PROB_CVA6 = {
    'RV_ZICSR': 0.0423, 'rv_zifencei': 0.0042, 'RV_I': 0.1652,
    'RV64_I': 0.0635, 'RV_F': 0.0084, 'RV_D': 0.1101,
    'RV64_F': 0.0209, 'RV64_D': 0.0254,
    'RV_C': 0.0974, 'RV_C_D': 0.0169, 'RV32_C': 0.0042,
    'RV_M': 0.0296, 'RV32_ZPN': 0.0042, 'RV64_M': 0.0211,
    'RV_A': 0.0476, 'RV64_A': 0.0466,
    'RV_ZBKB': 0.0796, 'RV64_ZBKB': 0.0811, 'RV_ZBKC': 0.0284, 'RV_ZBKX': 0.0384,
    'RV64_ZK': 0.0466, 'RV_ZK': 0.0169,
    'ROCC': 0.0042
    # NOTE: RV_F_ZFINX excluded (conflicts with F/D extensions)
    # NOTE: RV64_C and RV32_C_F not in ALLOWED_EXT_CVA6
}

# ========= 2) CVA6_CASCADE =========
SPECIAL_PROB_CVA6_CASCADE = {
    'RV_ZICSR': 0.0423, 'rv_zifencei': 0.0042, 'RV_I': 0.1652, \
    'RV64_I': 0.0635, 'RV_F_ZFINX': 0.1016, 'RV_F': 0.0084, 'RV_D': 0.1101, \
    'RV64_F': 0.0209, 'RV64_D': 0.0254, \
    #'RV_C': 0.0974, 'RV64_C': 0.0423,\ {'RV_ZICSR': 0.0423728813559322, 'rv_zifencei': 0.00423728813559322, 'RV_I': 0.1652542372881356, 
    # 'RV64_I': 0.0635593220338983, 'RV_F_ZFINX': 0.1016949152542373, 'RV_F': 0.00847457627118644, 'RV_D': 0.11016949152542373, 
    # 'RV64_F': 0.01694915254237288, 'RV64_D': 0.025423728813559324, 'RV_C': 0.09745762711864407, 'RV64_C': 0.0423728813559322,
    # 'RV32_C_F': 0.01694915254237288, 'RV_C_D': 0.01694915254237288, 'RV32_C': 0.00423728813559322, 'RV_M': 0.029661016949152543,
    # 'RV32_ZPN': 0.00423728813559322, 'RV64_M': 0.0211864406779661, 'RV_A': 0.046610169491525424, 'RV64_A': 0.046610169491525424, 
    # 'RV_ZBKB': 0.029661016949152543, 'RV64_ZBKB': 0.0211864406779661, 'RV_ZBKC': 0.00847457627118644, 'RV_ZBKX': 0.00847457627118644, 
    # 'RV64_ZK': 0.046610169491525424, 'RV_ZK': 0.01694915254237288, 'ROCC': 0.00423728813559322}
    'RV_C': 0, 'RV64_C': 0,\
    #'RV32_C_F': 0.0169, \
    'RV32_C_F': 0, \
    #'RV_C_D': 0.0169, \
    'RV_C_D': 0, \
    #'RV32_C': 0.0042, \
    'RV32_C': 0, \
    'RV_M': 0.0296,\
    #'RV32_ZPN': 0.0042, 
    'RV64_M': 0.0211, \
    #'RV_A': 0.0476, 'RV64_A': 0.0466, \
    'RV_A': 0, 'RV64_A': 0, \
    'RV_ZBKB': 0, 'RV64_ZBKB': 0, 'RV_ZBKC': 0, 'RV_ZBKX': 0, \
    'RV64_ZK': 0, 'RV_ZK': 0, 'ILL':0
}

# ========= 3) RV32 =========
SPECIAL_PROB_RV32 = {
    'RV_ZICSR': 0.023, 'rv_zifencei': 0.001, \
    # 'RV_I': 0.1652, \
    # 'RV_F': 0.0084,
    # 'RV_C': 0.004, 
    # 'RV_M': 0.0296,\
    # 'RV_A': 0.004, \
    #'rv_zbs':0.14,\
    #'RV_ZBKB': 0.17,\
    #'rv_32B':0.2,\
    #'RV_ZBKX': 0.2,
    'ILL':0.001
}

# ========= 4) GENERAL =========
SPECIAL_PROB_GENERAL = {
    # 'RV_ZICSR': 0.023, 'rv_zifencei': 0.001, \
    #  'RV_I': 0.2, \
    # 'RV_F': 0.0004,
    # 'RV_F_ZFINX':0.36,
    # 'RV_C': 0.004, 
    # 'RV_M': 0.0296,\
    'RV_A': 0.004, \
    'rv_zbs':0.14,\
    'RV_ZBKB': 0.17,\
    'rv_32B':0.05,\
    'RV_ZBKX': 0.02,\
    # 'RV_V': 0.3
    # 'ILL':0.8
}
ALLOWED_EXT_BASE = {

}

SPECIAL_PROB_PROFILES = {
    "cva6": SPECIAL_PROB_CVA6,
    "cva6_cascade": SPECIAL_PROB_CVA6_CASCADE,
    "rv32": SPECIAL_PROB_RV32,
    "general": SPECIAL_PROB_GENERAL,
    "base": ALLOWED_EXT_BASE,
}
