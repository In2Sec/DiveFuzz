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

from enum import Enum, auto

# ------------------------------------------------------------------------------
# Template Type Enumeration
# ------------------------------------------------------------------------------
class TemplateType(Enum):
    """Enumeration of supported template types."""
    # XiangShan templates
    XIANGSHAN = 'xiangshan'   # xiangshan - M/S/VX/U... mode

    # NutShell templates
    NUTSHELL = 'nutshell'     # nutshell - Machine mode with mtvec handler

    # Rocket templates
    ROCKET = 'rocket'

    # CVA6 templates
    CVA6 = 'cva6'             # CVA6 - RV64GC with B/ZKN, no Zfh

    # BOOM templates
    BOOM = 'boom'             # BOOM - RV64GC, no Zfh/B/ZK

    # TESTXS_U_MODE = 'testxs_u_mode'         # testxs/u_mode.S - User mode with complex page tables


# ------------------------------------------------------------------------------
# Hook Constants
# ------------------------------------------------------------------------------
HOOK_MAIN                  = "MAIN_BODY_HOOK"
HOOK_OTHER_EXP_M           = "HOOK_OTHER_EXP_M"
HOOK_OTHER_EXP_S           = "HOOK_OTHER_EXP_S"

LBL_STVEC_HANDLER          = "stvec_handler"
LBL_SMODE_EXC_HANDLER      = "smode_exception_handler"
LBL_OTHER_EXP_S            = "other_exp_s"
LBL_MTVEC_HANDLER          = "mtvec_handler"
LBL_MMODE_EXC_HANDLER      = "mmode_exception_handler"
LBL_OTHER_EXP_M            = "other_exp_m"   # Existing M mode exception label, but this is for S template only
LBL_PAGE_TABLE_SEC         = ".page_table"
LBL_PAGE_TABLE_0           = "page_table_0"

# Label constants (can be uniformly modified/reused)
LBL_START             = "_start"
LBL_H0_START          = "h0_start"
LBL_KERNEL_SP         = "kernel_sp"
LBL_TRAP_VEC_INIT     = "trap_vec_init"
LBL_MEPC_SETUP        = "mepc_setup"
LBL_CUSTOM_CSR_SETUP  = "custom_csr_setup"
LBL_INIT_ENV          = "init_env"
LBL_INIT              = "init"
LBL_OTHER_EXP         = "other_exp"
LBL_TEST_DONE         = "test_done"
LBL_MAIN              = "main"
LBL_MAIN_G            = "main_g"
LBL_WRITE_TOHOST      = "write_tohost"
LBL_EXIT              = "_exit"
LBL_DEBUG_ROM         = "debug_rom"
LBL_DEBUG_EXC         = "debug_exception"
LBL_INSTR_END         = "instr_end"

# Data symbols
SYM_TOHOST            = "tohost"
SYM_FROMHOST          = "fromhost"
SYM_USER_STACK_END    = "user_stack_end"
SYM_KERNEL_STACK_END  = "kernel_stack_end"
SYM_REGION0           = "region_0"
SYM_AMO0              = "amo_0"
SYM_MEM_REGION        = "mem_region"
SYM_MEM_REGION_END    = "mem_region_end"

# Additional labels for S-mode and U-mode templates
LBL_PMP_SETUP         = "pmp_setup"
LBL_PROCESS_PT        = "process_pt"
LBL_INIT_SUPERVISOR   = "init_supervisor_mode"
LBL_INIT_USER         = "init_user_mode"
LBL_KERNEL_INSTR_START = "kernel_instr_start"
LBL_KERNEL_INSTR_END  = "kernel_instr_end"
LBL_KERNEL_DATA_START = "kernel_data_start"

# Page table labels (for multi-level page tables)
LBL_PAGE_TABLE_1      = "page_table_1"
LBL_PAGE_TABLE_2      = "page_table_2"
LBL_PAGE_TABLE_3      = "page_table_3"
LBL_PAGE_TABLE_4      = "page_table_4"
LBL_PAGE_TABLE_5      = "page_table_5"
LBL_PAGE_TABLE_6      = "page_table_6"

# Exception handler labels for U-mode templates
LBL_SMODE_INTR_HANDLER = "smode_intr_handler"
LBL_MMODE_INTR_HANDLER = "mmode_intr_handler"
LBL_ECALL_HANDLER      = "ecall_handler"
LBL_EBREAK_HANDLER     = "ebreak_handler"
LBL_ILLEGAL_INSTR_HANDLER = "illegal_instr_handler"
LBL_INSTR_FAULT_HANDLER = "instr_fault_handler"
LBL_LOAD_FAULT_HANDLER = "load_fault_handler"
LBL_STORE_FAULT_HANDLER = "store_fault_handler"
LBL_PT_FAULT_HANDLER   = "pt_fault_handler"
