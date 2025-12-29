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

/*
 * Memory Layout:
 *   0x80000000 - 0x800FFFFF : Code and data sections (.text.init, .text, .tohost, .page_table, .data, .bss)
 *   0x80100000 - 0x80101FFF : Fixed mem_region for AMO/load/store testing (8KB)
 *
 * IMPORTANT: mem_region is placed at a FIXED address (0x80100000) to ensure
 * consistency between template ELF (used by spike_engine during generation)
 * and final ELF (used by standalone spike for verification).
 * This prevents address mismatch issues caused by varying code section sizes.
 *
 * NOTE: .text.init is placed first for CVA6 compatibility. CVA6's Verilator
 * testbench preloads memory starting from 0x80000000, so the startup code
 * must be at the beginning. Both .text.init and .text are merged here.
 */

SECTIONS
{
  . = 0x80000000;
  .text : { *(.text.init) *(.text) }
  . = ALIGN(0x1000);
  .tohost : { *(.tohost) }
  . = ALIGN(0x1000);
  .page_table : { *(.page_table) }
  .data : { *(.data) }
  .bss : { *(.bss) }

  /* Place mem_region at fixed absolute address to ensure consistency */
  . = 0x80100000;
  .mem_region : { *(.mem_region) }
  _end = .;
}
