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

# Define the range of RISC-V general-purpose integer registers
reg_range = [
    "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2", "s0", "s1", 
    "a0",  
    "a1",
    "a2", "a3", "a4", "a5", "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
    "s8", "s9", "s10", "s11", "t3", "t4"
]

# Define the range of RISC-V floating-point registers
float_range = [
    "ft0", "ft1", "ft2", "ft3", "ft4", "ft5", "ft6", "ft7",
    "fs0", "fs1", "fa0", "fa1", "fa2", "fa3", "fa4", "fa5",
    "fa6", "fa7", "fs2", "fs3", "fs4", "fs5", "fs6", "fs7",
    "fs8", "fs9", "fs10", "fs11", "ft8", "ft9", "ft10", "ft11"
]

rvc_reg_range = [
    "s0", "s1", 
    "a0",  # FOR CVA6
    "a1", "a2", "a3", "a4", "a5"
]

rvc_reg_range_zero = [
    "s0", "s1", 
    "a0", # FOR CVA6
    "a1", "a2", "a3", "a4", "a5",
    "zero" # Used to test HINT-type instructions
]

rvc_float_range = [
    "fs0", "fs1", "fa0", "fa1", "fa2", "fa3", "fa4", "fa5"
]




# Define the range of Control and Status Registers (CSR)
csr_range = [
# M-Mode
#     'fcsr',
#     'frm',
#     'dpc',
#     #'mconfigptr',
#     'mstatus',
#     #'mstatush',
#     'dscratch0',
#     'dscratch1',
#     'mhpmevent4',
#     'mhpmevent5',
#     'mhpmevent6',
#     'mhpmevent7','mhpmevent8','mhpmevent9','mhpmevent10','mcycle','mcycleh','mhpmcounter3h','mhpmcounter4h','mhpmcounter5h',
#     #'cpuctrlsts',#'secureseed',
#     #rv32 end

#     'mvendorid', 'marchid', 'mimpid', 'mhartid',
#     #'mtvec', 
#     'mideleg', 
#     #'mip', 'mcounteren', 'mcountinhibit',
#     'mscratch', 
#     # 会导致异常返回地址错误
#     #'mepc', 
#     'mcause', 'mtval',
#     #'medeleg', 'mie', 'mstatus', 'misa'

#     # S-Mode
#     'sstatus', 'stvec', 'sip', 'scounteren', 'sscratch', 'sepc', 'scause',
#     'stval', 'sie', 
#     #'satp',
#     # NEW ADD
#     #'instret', #rv32 # TODO delete
#     'time','cycle', 'minstret', 'minstreth',
# #     'vstart', 'vxsat', 'vxsat', 'vxrm', 'vcsr', 
# #     'ssp', 
# #     'seed', 
# #     'jvt', 
# #     'vl', 'vtype',
# #     'vlenb', 'sedeleg', 'sideleg', 'sstateen0', 'sstateen1', 
# #     'scountinhibit',
# #     'stimecmp',
# #     'siselect', 'sireg', 'stopei', 
# #     'srmcfg', 
# #     'scontext', 
# #     'vstimecmp', 'vsiselect','vsireg',
# #     'hstatus', 
# #     'hedlege', 
# #     'scountovf', 'stopi', 
# #     'utvt', 
# #     'unxti',
# #     'uintstatus',
# #     'stvt', 
# #     'snxti',
# #     'mtvt', 'mnxti', 
# #     'minstatus', 
# #     'mscratchcsw', 
# #     'mscratchcswl', 
# #    'mvien', 'mvip', 'menvcfg',
# #     'mstateen0', 'mtinst', 'miselect','mireg', 'mcontext', 
# #     'mscountext',
#     'dcsr', 
#     #'mcyclecfg',
#     #'minstretcfg', 
#     'mhpmevent3', 'mimpid', 'mvendorid', 'cycleh', 'timeh',
#     #'mieh', 'mviph', 
#     #'mncause', 
#     # CVA6
#     #'hpmcounter3','hpmcounter4','hpmcounter5','hpmcounter6',
#     # VS-Mode
#     # TODO Currently not supported by Rocket
#     #'vsstatus', 'vstvec', 'vsip', 'vsie', 'vsscratch', 'vsepc', 'vscause', 'vsatp', 'vstval',

#     # Unknown

#     #'mtimecmp', 


#     # TODO for generate rv32
#     #'mconfigptr', 
#     # 'senvcfg', #SPIKE not write it ,To test cva6
#     # 'mseccfg', 


#     #'mtime',
#     # 'menvcfg', 'mstatush', 'menvcfgh'


### For test KMH #################################################

### add new

  'stimecmp',
  'vstimecmp',

# User Trap Setup
  'ustatus',
  'uie',
  'utvec',

  # User Trap Handling
  'uscratch',
  'uepc',
  'ucause',
  'utval',
  'uip',

  # User Floating-Point CSRs (not implemented)
  'fflags',
  'frm',
  'fcsr',

  # Vector Extension CSRs
  'vstart',
  'vxsat',
  'vxrm',
  'vcsr',
  'vl',
  'vtype',
  'vlenb',

  # User Counter/Timers
  'cycle',
  'time',
  'instret',
  'hpmcounter3',
  'hpmcounter4',
  'hpmcounter5',
  'hpmcounter6',
  'hpmcounter7',
  'hpmcounter8',
  'hpmcounter9',
  'hpmcounter10',
  'hpmcounter11',
  'hpmcounter12',
  'hpmcounter13',
  'hpmcounter14',
  'hpmcounter15',
  'hpmcounter16',
  'hpmcounter17',
  'hpmcounter18',
  'hpmcounter19',
  'hpmcounter20',
  'hpmcounter21',
  'hpmcounter22',
  'hpmcounter23',
  'hpmcounter24',
  'hpmcounter25',
  'hpmcounter26',
  'hpmcounter27',
  'hpmcounter28',
  'hpmcounter29',
  'hpmcounter30',
  'hpmcounter31',

  # Supervisor Trap Setup
  'sstatus',
  'sedeleg',
  'sideleg',
  'sie',
  'stvec',
  'scounteren',

  # Supervisor Configuration
  'senvcfg',

  # Supervisor Trap Handling
  'sscratch',
  'sepc',
  'scause',
  'stval',
  'sip',

  # Supervisor Protection and Translation
  'satp',

  # Supervisor Custom Read/Write
#   'sbpctl',
#   'spfctl',
#   'slvpredctl',
#   'smblockctl',
#   'srnctl',
#   'scachebase',

  # Supervisor Custom Read/Write
  #'sfetchctl',

  # Hypervisor Trap Setup
  'hstatus',
  'hedeleg',
  'hideleg',
  'hie',
  'hcounteren',
  'hgeie',

  # Hypervisor Trap Handling
  'htval',
  'hip',
  'hvip',
  'htinst',
  'hgeip',

  # Hypervisor Configuration
  'henvcfg',

  # Hypervisor Protection and Translation
  'hgatp',

  # Hypervisor Counter/Timer Virtualization Registers
  #'htimedelta',

  # Virtual Supervisor Registers
  'vsstatus',
  'vsie',
  'vstvec',
  'vsscratch',
  'vsepc',
  'vscause',
  'vstval',
  'vsip',
  'vsatp',

  # Machine Information Registers
  'mvendorid',
  'marchid',
  'mimpid',
  'mhartid',
  'mconfigptr',

  # Machine Trap Setup
  #'mstatus',   # Opening resulted in an interrupt: exception interrupt #7, epc 0x0000000080001354, unable to return.
  'misa',
  'medeleg',
  'mideleg',
  'mie',
  #'mtvec',
  'mcounteren',

  # Machine Trap Handling
  'mscratch',
  #'mepc',
  'mcause',
  'mtval',
  'mtinst',
  'mtval2',

  # Machine Configuration
  'menvcfg',

  # Machine Memory Protection
  # TBD
  'pmpcfg0',
  'pmpaddr0',

   'pmpcfg1',
  'pmpaddr1',
   'pmpcfg2',
  'pmpaddr2',
  # Machine level PMA
#   'pmacfg0',
#   'pmaaddr0', # 64 entry at most

  # Machine Counter/Timers
  # Currently, we uses perfcnt csr set instead of standard Machine Counter/Timers
  # 0xB80 - 0x89F are also used as perfcnt csr
  'mcycle',
  'minstret',

  'mhpmcounter3',
  'mhpmcounter4',
  'mhpmcounter5',
  'mhpmcounter6',
  'mhpmcounter7',
  'mhpmcounter8',
  'mhpmcounter9',
  'mhpmcounter10',
  'mhpmcounter11',
  'mhpmcounter12',
  'mhpmcounter13',
  'mhpmcounter14',
  'mhpmcounter15',
  'mhpmcounter16',
  'mhpmcounter17',
  'mhpmcounter18',
  'mhpmcounter19',
  'mhpmcounter20',
  'mhpmcounter21',
  'mhpmcounter22',
  'mhpmcounter23',
  'mhpmcounter24',
  'mhpmcounter25',
  'mhpmcounter26',
  'mhpmcounter27',
  'mhpmcounter28',
  'mhpmcounter29',
  'mhpmcounter30',
  'mhpmcounter31',

  'mcountinhibit',
  # difftest does not support
#   'mhpmevent3',
#   'mhpmevent4',
#   'mhpmevent5',
#   'mhpmevent6',
#   'mhpmevent7',
#   'mhpmevent8',
#   'mhpmevent9',
#   'mhpmevent10',
#   'mhpmevent11',
#   'mhpmevent12',
#   'mhpmevent13',
#   'mhpmevent14',
#   'mhpmevent15',
#   'mhpmevent16',
#   'mhpmevent17',
#   'mhpmevent18',
#   'mhpmevent19',
#   'mhpmevent20',
#   'mhpmevent21',
#   'mhpmevent22',
#   'mhpmevent23',
#   'mhpmevent24',
#   'mhpmevent25',
#   'mhpmevent26',
#   'mhpmevent27',
#   'mhpmevent28',
#   'mhpmevent29',
#   'mhpmevent30',
#   'mhpmevent31'
]

csr_range_cva6=[



]

# ============================================================================
# NutShell-specific CSR range for M-mode fuzzing
# ============================================================================
# IMPORTANT: NutShell DOES implement S-mode (CSR.scala:426-442), but tests run
# in M-mode only environment (template: nutshell M-mode). S-mode CSRs are
# excluded because testing them requires S-mode privilege context.
#
# Evidence sources: dut/NutShell/src/main/scala/nutcore/backend/fu/CSR.scala
# ============================================================================

excluded_csrs_nts = []

# ----------------------------------------------------------------------------
# Category 1: Floating-Point CSRs (NOT IMPLEMENTED)
# Evidence: CSR.scala:50 comment "User Floating-Point CSRs (not implemented)"
#           CSR.scala:415-418 all FP CSRs are commented out
# Reason: NutShell does not implement F/D extensions
# ----------------------------------------------------------------------------
excluded_csrs_nts += ['fflags', 'frm', 'fcsr']

# ----------------------------------------------------------------------------
# Category 2: Read-Only Information CSRs (IMPLEMENTED but exclude from fuzzing)
# Evidence: CSR.scala:444-447 - MaskedRegMap with Unwritable flag
# Reason: Read-only CSRs cause difftest failures when attempting writes
#         Values differ between NutShell and NEMU implementations
# ----------------------------------------------------------------------------
excluded_csrs_nts += ['mvendorid', 'marchid', 'mimpid', 'mhartid']

# ----------------------------------------------------------------------------
# Category 3: Write-Sensitive CSRs (IMPLEMENTED but exclude from fuzzing)
# Evidence:
#   - misa: CSR.scala:452 - MaskedRegMap with mask=0x0 (Unwritable)
#   - mcycle: CSR.scala:759 - perfCnt(0), auto-increment counter
#   - minstret: CSR.scala:760 - perfCnt(2), auto-increment counter
# Reason:
#   - misa: Read-only in NutShell
#   - mcycle/minstret: Auto-increment counters cause non-deterministic difftest
#                      NEMU and NutShell may have different cycle counts
# ----------------------------------------------------------------------------
excluded_csrs_nts += ['misa', 'mcycle', 'minstret']

# ----------------------------------------------------------------------------
# Category 4: PMP CSRs (IMPLEMENTED but exclude from fuzzing)
# Evidence: CSR.scala:467-474 - pmpcfg0-3 and pmpaddr0-3 all implemented
# Reason: PMP configuration changes during fuzzing may cause:
#         - Memory access permission violations
#         - Instruction fetch failures
#         - Unpredictable difftest behavior
#         Better to keep PMP disabled for fuzzing stability
# ----------------------------------------------------------------------------
excluded_csrs_nts += ['pmpcfg0', 'pmpcfg1', 'pmpcfg2', 'pmpcfg3',
                  'pmpaddr0', 'pmpaddr1', 'pmpaddr2', 'pmpaddr3']

# ----------------------------------------------------------------------------
# Category 5: Standard Performance Counters (NOT IMPLEMENTED)
# Evidence: CSR.scala uses custom perfCnt range 0xb00-0xb7f (lines 397-398)
#           Standard hpmcounter*/mhpmcounter* addresses NOT registered
# Reason: NutShell uses non-standard performance counter addresses
#         Accessing standard addresses causes illegal instruction exceptions
# ----------------------------------------------------------------------------
excluded_csrs_nts += [f'hpmcounter{i}' for i in range(3, 32)]
excluded_csrs_nts += [f'mhpmcounter{i}' for i in range(3, 32)]

# ----------------------------------------------------------------------------
# Category 6: Hypervisor Extension CSRs (NOT IMPLEMENTED)
# Evidence: No h* CSR definitions in CSR.scala
#           ModeH not defined (only ModeM, ModeS, ModeU at lines 123-125)
# Reason: NutShell does not implement hypervisor extension
# ----------------------------------------------------------------------------
excluded_csrs_nts += ['hstatus', 'hedeleg', 'hideleg', 'hie', 'hcounteren', 'hgeie',
                  'htval', 'hip', 'hvip', 'htinst', 'hgeip', 'henvcfg', 'hgatp',
                  'vstimecmp']

# ----------------------------------------------------------------------------
# Category 7: VS-mode CSRs (Virtual Supervisor - NOT IMPLEMENTED)
# Evidence: No vs* CSR definitions in CSR.scala
# Reason: Part of hypervisor extension, not supported by NutShell
# ----------------------------------------------------------------------------
excluded_csrs_nts += ['vsstatus', 'vsie', 'vstvec', 'vsscratch', 'vsepc', 'vscause',
                  'vstval', 'vsip', 'vsatp']

# ----------------------------------------------------------------------------
# Category 8: S-mode CSRs (IMPLEMENTED but exclude from M-mode testing)
# Evidence: CSR.scala:426-442 - All S-mode CSRs ARE implemented:
#   - sstatus (0x100) - line 426: MaskedRegMap(Sstatus, mstatus, sstatusWmask, ...)
#   - sie (0x104) - line 430: MaskedRegMap(Sie, mie, sieMask, ...)
#   - stvec (0x105) - line 431: MaskedRegMap(Stvec, stvec)
#   - scounteren (0x106) - line 432: MaskedRegMap(Scounteren, scounteren)
#   - sscratch (0x140) - line 435: MaskedRegMap(Sscratch, sscratch)
#   - sepc (0x141) - line 436: MaskedRegMap(Sepc, sepc)
#   - scause (0x142) - line 437: MaskedRegMap(Scause, scause)
#   - stval (0x143) - line 438: MaskedRegMap(Stval, stval)
#   - sip (0x144) - line 439: MaskedRegMap(Sip, mip.asUInt, sipMask, Unwritable)
#   - satp (0x180) - line 442: MaskedRegMap(Satp, satp)
#   - sedeleg, sideleg - lines 428-429: Commented out (not implemented)
#   - senvcfg, stimecmp - Not defined (newer spec)
#
# Reason for exclusion: Tests run in M-mode only environment (template: nutshell)
#   - While M-mode CAN access S-mode CSRs, testing S-mode CSRs without S-mode
#     privilege context provides limited value
#   - S-mode CSR behaviors (delegation, traps, etc.) only meaningful in S-mode
#   - Template does not switch to S-mode (uses M-mode mret only)
# ----------------------------------------------------------------------------
excluded_csrs_nts += ['sstatus', 'sie', 'stvec', 'scounteren', 'sscratch', 'sepc',
                  'scause', 'stval', 'sip', 'satp',
                  'sedeleg', 'sideleg',  # These two are NOT implemented (commented out)
                  'senvcfg', 'stimecmp']  # Newer spec, not in NutShell

# ----------------------------------------------------------------------------
# Category 9: U-mode CSRs (NOT IMPLEMENTED)
# Evidence: CSR.scala:404-413 - All U-mode CSRs commented out
# Reason: NutShell does not implement user-mode CSRs
# ----------------------------------------------------------------------------
excluded_csrs_nts += ['ustatus', 'uie', 'utvec', 'uscratch', 'uepc', 'ucause',
                  'utval', 'uip']

# ----------------------------------------------------------------------------
# Category 10: Vector Extension CSRs (NOT IMPLEMENTED)
# Evidence: No vector CSR definitions in CSR.scala
#           No V extension support in NutShell ISA files
# Reason: NutShell does not implement RISC-V V extension
# ----------------------------------------------------------------------------
excluded_csrs_nts += ['vstart', 'vxsat', 'vxrm', 'vcsr', 'vl', 'vtype', 'vlenb']

# ----------------------------------------------------------------------------
# Category 11: Newer Privilege Spec CSRs (NOT IMPLEMENTED)
# Evidence: CSR.scala does not define these CSRs (searched entire file)
# Reason: NutShell based on older privilege spec, these CSRs added in v1.12+
#   - mcountinhibit (0x320): Counter inhibit - not in NutShell
#   - menvcfg (0x30a): Environment configuration - not in NutShell
#   - mconfigptr: Configuration pointer - not in NutShell
#   - mtinst (0x34a): Trap instruction - not in NutShell
#   - mtval2 (0x34b): Second trap value - not in NutShell
# Verified: grep search returned no matches
# ----------------------------------------------------------------------------
excluded_csrs_nts += ['mcountinhibit', 'menvcfg', 'mconfigptr', 'mtinst', 'mtval2']

# ----------------------------------------------------------------------------
# Category 12: User-Mode Counter Pseudo-Instructions (NOT IMPLEMENTED)
# Evidence: CSR.scala:421-423 - cycle, time, instret all commented out
# Reason: These are user-mode readable counters (addresses 0xc00-0xc02)
#         NutShell only implements M-mode accessible mcycle/minstret
#         Accessing these causes illegal instruction exceptions
# Note: DO NOT confuse with mcycle/minstret (M-mode versions at 0xb00/0xb02)
# ----------------------------------------------------------------------------
excluded_csrs_nts += ['cycle', 'time', 'instret']

# ----------------------------------------------------------------------------
# Category 13: Dangerous CSRs (IMPLEMENTED but exclude from random fuzzing)
# Evidence & Reasoning:
#
# mstatus (0x300): IMPLEMENTED (CSR.scala:451)
#   - Reason for exclusion: variables.py:282 comment "resulted in interrupt #7"
#   - Random writes can corrupt privilege/interrupt state causing hangs
#   - Template initializes it safely; random fuzzing is dangerous
#
# mepc (0x341): IMPLEMENTED (CSR.scala:461)
#   - Reason for exclusion: variables.py:292 commented out in csr_range
#   - Exception return address; random writes cause control flow chaos
#   - Can jump to invalid addresses after trap
#
# mtvec (0x305): IMPLEMENTED (CSR.scala:456)
#   - Reason for exclusion: variables.py:287 commented out in csr_range
#   - Trap vector base; random writes redirect exceptions to invalid handlers
#   - Template sets it correctly; fuzzing breaks exception handling
#
# mip (0x344): IMPLEMENTED (CSR.scala:463) as READ-ONLY
#   - Reason for exclusion: Hardware-controlled interrupt pending register
#   - Writing has no effect (Unwritable), wastes fuzzing effort
# ----------------------------------------------------------------------------
excluded_csrs_nts += ['mstatus', 'mepc', 'mtvec', 'mip']

# Result: csr_range_nutshell contains only safe, testable M-mode CSRs
csr_range_nutshell = [reg for reg in csr_range if reg not in excluded_csrs_nts]

# XiangShan-specific CSR range (M-mode with FP and Vector support)
# XiangShan is a high-performance processor supporting:
# - M-mode (Machine mode) for testing environment
# - F/D extensions (Floating-point) - includes FP CSRs
# - V extension (Vector) - includes Vector CSRs
# - Additional extensions (A, C, ZK, etc.)
#
# Unlike NutShell, XiangShan supports FP and Vector, so we keep those CSRs.
# However, we still exclude S/H/U-mode CSRs since tests run in M-mode only.
excluded_csrs_xs = []

# Exclude dangerous CSRs that cause processor hangs (already commented in csr_range but be explicit)
excluded_csrs_xs += ['mstatus', 'mepc', 'mtvec']

# Exclude read-only info CSRs that may cause difftest failures
excluded_csrs_xs += ['mvendorid', 'marchid', 'mimpid', 'mhartid', 'mconfigptr']

# Exclude write-sensitive CSRs
excluded_csrs_xs += ['misa', 'mcycle', 'minstret']

# Exclude PMP CSRs (may cause memory access permission issues)
excluded_csrs_xs += ['pmpcfg0', 'pmpcfg1', 'pmpcfg2',
                     'pmpaddr0', 'pmpaddr1', 'pmpaddr2']

# Exclude performance counters (cause difftest mismatches)
excluded_csrs_xs += [f'hpmcounter{i}' for i in range(3, 32)]
excluded_csrs_xs += [f'mhpmcounter{i}' for i in range(3, 32)]

# Exclude Hypervisor extension CSRs (not confirmed supported in M-mode test environment)
excluded_csrs_xs += ['hstatus', 'hedeleg', 'hideleg', 'hie', 'hcounteren', 'hgeie',
                     'htval', 'hip', 'hvip', 'htinst', 'hgeip', 'henvcfg', 'hgatp',
                     'vstimecmp']

# Exclude VS-mode CSRs (Virtual Supervisor)
excluded_csrs_xs += ['vsstatus', 'vsie', 'vstvec', 'vsscratch', 'vsepc', 'vscause',
                     'vstval', 'vsip', 'vsatp']

# Exclude S-mode CSRs (tests run in M-mode only)
# Particularly 'satp' which causes cache inconsistency (see generator.py:264)
excluded_csrs_xs += ['sstatus', 'sedeleg', 'sideleg', 'sie', 'stvec', 'scounteren',
                     'senvcfg', 'sscratch', 'sepc', 'scause', 'stval', 'sip',
                     'satp', 'stimecmp']

# Exclude U-mode CSRs (tests run in M-mode only)
excluded_csrs_xs += ['ustatus', 'uie', 'utvec', 'uscratch', 'uepc', 'ucause',
                     'utval', 'uip']

# Create XiangShan CSR range (keeps FP and Vector CSRs, excludes problematic ones)
csr_range_xiangshan = [reg for reg in csr_range if reg not in excluded_csrs_xs]

reg_sp= ['sp']
reg_t6= ['t6']

reg_v = ['v1','v2', 'v3' ,'v4','v5','v6','v7','v8','v9','v10','v11','v12','v13','v14','v15','v16','v17','v18','v19','v20','v21'
        ,'v22','v23','v24','v25','v26','v27','v28','v29','v30','v31']
reg_vm = ['v0.t', '']
# TODO surpport NF bit
reg_nf = ['']


variable_range = {
    'RD': reg_range,
    'RS1': reg_range,
    'RS2': reg_range,
    'RS3': reg_range,
    'FRD': float_range,
    'FRS1': float_range,
    'FRS2': float_range,
    'FRS3': float_range,
    'CSR': csr_range, 
    'RD_RS1': reg_range,
    'C_RS2': reg_range,
    'RS1_P': rvc_reg_range,
    'RS2_P': rvc_reg_range,
    'RD_RS1_P': rvc_reg_range,
    'RD_RS1_N': rvc_reg_range_zero,# To test hint
    'RD_P': rvc_reg_range,
    'RD_RS1_N0': [reg for reg in reg_range if reg not in ['zero']],
    'RD_N0': [reg for reg in reg_range if reg not in ['zero']],
    'RD_SP': [reg for reg in reg_range if reg not in ['sp']],# 用来测试HINT
    'C_RS1_N0': [reg for reg in reg_range if reg not in ['zero']],
    'RS1_N0': [reg for reg in reg_range if reg not in ['zero']],
    'C_RS2_N0': [reg for reg in reg_range if reg not in ['zero']],
    'RD_N2': [reg for reg in reg_range if reg not in ['zero', 'sp']],
    'FRD_P': rvc_float_range,
    'FRS2_P': rvc_float_range,
    'C_FRS2': float_range,
    #'L_TYPE': l_type_range,
    #'MAGIC_ADDR': magic_addr_range,
    #'MAGIC_ADDR_A': magic_addr_a_range,
    #'EXTENSION': extension_range,
    #'CATEGORY': category_range,
    'IMM': None,
    'LABEL': None,
    'SP': reg_sp,
    # Used to store values that are valid addresses
    'T6': reg_t6,
    'VD': reg_v,
    'VS1': reg_v,
    'VS2': reg_v,
    'VS3': reg_v,
    'VM' : reg_vm,
    'NF' : reg_nf
}
