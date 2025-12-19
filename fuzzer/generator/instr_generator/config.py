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

special_instr = [
                # Jump instructions are NOT in this list (they need to be generated naturally)
                # 'jal', 'beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu', 'c.j',
                # 'c.beqz', 'c.bnez', 'c.jal',
                # 'jalr', 'c.jr', 'c.jalr',
                # Compressed load/store instructions
                'c.sw', 'c.sd','c.fsw', 'c.fsd', \
                'c.lwsp', 'c.swsp', 'c.lw', 'c.sw', 'c.ldsp', 'c.sdsp', 'c.ld', \
                'c.sd', 'c.flw', 'c.flwsp', 'c.fldsp', 'c.fld', \
                #'pack', 'packw', 'packh'
                #'nop'
                #'pack', 'packh', 'packw'
                ]
                # Unknown instr
                # 'lui']

rv32_not_support_instr = ["c.addiw", "c.addw", "c.subw"]
rv32_not_support_csrs = ["senvcfg", "mcofigptr", "mseccfg","mcountinhibit","cycle","mcounteren"]
