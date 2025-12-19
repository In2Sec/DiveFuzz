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

import argparse
import os
from pathlib import Path
from ..asm_template_manager.ext_list import allowed_ext
from ..asm_template_manager.constants import TemplateType

def create_parser():
    parser = argparse.ArgumentParser(
        description='Process some integers.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # --Mode switch: mutation/generation--
    parser.add_argument('--mutation', action='store_true',
                        help='Enable mutation process'
    )
    parser.add_argument('--generate', action='store_true',
                        help='Enable generate'
    )

    # —— Target Platform / Configuration ——
    parser.add_argument('--cva6', action='store_true',
                        help='CVA6 environments'
    )
    parser.add_argument('--rv32', action='store_true',
                        help='RV32 environments (RV32)'
    )
    parser.add_argument('-e', '--eliminate', dest='eliminate_enable', action='store_true',
                        help='Enable the constraint "Eliminate identical write-back data" (conflict avoidance)'
    )
    parser.add_argument('--architecture', type=str, default='xs',
                        help='Arch for bug filter(xs, nts, rkt).'
    )
    parser.add_argument('--allowed-ext-name', choices=allowed_ext.EXT_NAMES, default='general',
        help='Select the collection of allowed_ext.'
    )
    parser.add_argument('--template-type', type=str,
                        choices=[t.value for t in TemplateType],
                        default='xiangshan',
                        help='Template type for assembly generation'
    )

    # -- workload configuration --
    parser.add_argument(
        '--instr-number', type=int,
        default=200,
        metavar='N',
        help='Number of instructions to be generated per seed file'
    )
    parser.add_argument(
        '--seeds', type=int,
        default=10,
        metavar='K',
        help='Number of seed files generated (i.e., number of seed files)'
    )
    parser.add_argument(
        '--max-workers', type=int,
        default=os.cpu_count() or 20,
        help='Number of parallel processes'
    )

    # -- path configuration --
    parser.add_argument(
        '--seed-dir', type=Path,
        default=Path('out-seeds-2025-test'),
        help='Directory to read .S seed files in variant mode'
    )
    parser.add_argument(
        '--mutate-out', type=Path, 
        default=None,
        help='Mutation result output directory (default: <seed-dir>/mutate)'
    )
    parser.add_argument(
        '--out-dir', type=Path, 
        default=Path('out-seeds-2025-test'),
        help='Output seed file directory in generate mode (used in generate mode)'
    )

    # —— Additional options for mutation ——
    parser.add_argument(
        '--enable-ext', action='store_true',
        help='Mutation allows the introduction of the current file did not appear in the expansion of the instruction'
    )
    parser.add_argument(
        '--exclude-ext', nargs='*', 
        default=[],
        help='List of extensions (separated by spaces) to be excluded at mutation/generation time'
    )


    return parser

def parse_args():
    parser = create_parser()
    return parser.parse_args()
