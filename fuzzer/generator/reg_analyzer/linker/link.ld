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


OUTPUT_ARCH( "riscv" )
ENTRY(_start)

SECTIONS
{
  . = 0x80000000;
  .text : { *(.text) }
  . = ALIGN(0x1000);
  .tohost : { *(.tohost) }
  . = ALIGN(0x1000);
  .page_table : { *(.page_table) }
  .data : { *(.data) }
  .bss : { *(.bss) }
  _end = .;
}
