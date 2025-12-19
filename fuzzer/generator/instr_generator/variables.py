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
#     # mybe lead mret addr error
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
#     # 'senvcfg', # SPIKE not write it ,To test cva6
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