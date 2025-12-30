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

from ..asm_template_manager.ext_list import allowed_ext
from ..bug_filter import bug_filter
from ..asm_template_manager.riscv_asm_syntex import ArchConfig

# ISA strings for different extension profiles
# Key: allowed_ext_name, Value: (isa_with_c, isa_without_c)
ISA_PROFILES = {
    'cva6': (
        # CVA6: RV64GC + B + ZKN, NO Zfh/Zfhmin
        # NOTE: Use 'gc' (not 'g_c') - standard RISC-V ISA string format
        'rv{bits}gc_zicsr_zifencei_zba_zbb_zbc_zbs_zbkb_zbkc_zbkx_zkne_zknd_zknh',
        'rv{bits}g_zicsr_zifencei_zba_zbb_zbc_zbs_zbkb_zbkc_zbkx_zkne_zknd_zknh'
    ),
    'cva6_cascade': (
        'rv{bits}gc_zicsr_zifencei_zba_zbb_zbc_zbs_zbkb_zbkc_zbkx_zkne_zknd_zknh',
        'rv{bits}g_zicsr_zifencei_zba_zbb_zbc_zbs_zbkb_zbkc_zbkx_zkne_zknd_zknh'
    ),
    # Default profile with all extensions including zfh
    'default': (
        'rv{bits}gc_zicsr_zifencei_zfh_zba_zbb_zbkc_zbc_zbkb_zbs_zmmul_zknh_zkne_zknd_zbkx_zfa',
        'rv{bits}g_zicsr_zifencei_zfh_zba_zbb_zbkc_zbc_zbkb_zbs_zmmul_zknh_zkne_zknd_zbkx_zfa'
    )
}

MAX_MUTATE_TIME = 10
class Config:
    def __init__(self, args):
        self.mutation_enable = bool(args.mutation)
        self.generate_enable = bool(args.generate)
        self.eliminate_enable = bool(args.eliminate_enable)
        self.is_cva6 = bool(args.cva6)
        self.is_rv32 = bool(args.rv32)

        # Use command line arguments directly (no auto-override)
        # --allowed-ext-name: extension set (cva6, general, etc.)
        self.allowed_ext_name = str(args.allowed_ext_name)
        allowed_ext.setup_ext(self.allowed_ext_name)

        # --architecture: bug filter (xs, nts, rkt, cva6, etc.)
        self.architecture = str(args.architecture)
        bug_filter.set_architecture(self.architecture)

        # --template-type: template (xiangshan, cva6, nutshell, etc.)
        self.template_type = str(args.template_type)

        self.instr_number = int(args.instr_number)
        self.seed_times = int(args.seeds)
        self.max_workers = max(1, int(args.max_workers))

        self.directory_path = args.seed_dir.resolve()
        self.mutate_directory = (args.mutate_out or (self.directory_path / 'mutate')).resolve()
        self.out_dir = args.out_dir.resolve()

        self.enable_ext = bool(args.enable_ext)
        self.exclude_extensions = list(args.exclude_ext)

        # Debug configuration
        self.debug_enabled = bool(args.debug)
        self.debug_mode = str(args.debug_mode)
        # Default: only log ACCEPTED instructions (use --debug-all to log all)
        self.debug_accepted_only = not bool(args.debug_all)
        self.debug_log_csr = not bool(args.debug_no_csr)
        self.debug_log_fpr = not bool(args.debug_no_fpr)

        self.arch_bits = 32 if self.is_rv32 else 64

        # Build ISA string based on allowed_ext_name profile
        isa_profile = ISA_PROFILES.get(self.allowed_ext_name, ISA_PROFILES['default'])
        has_c_ext = any(ext in allowed_ext.allowed_ext for ext in ["RV64_C", "RV_C"])
        isa_template = isa_profile[0] if has_c_ext else isa_profile[1]
        self.isa = isa_template.format(bits=self.arch_bits)

        self.arch = ArchConfig(self.arch_bits, self.isa)
        self.mutate_time = getattr(args, "mutate_time", MAX_MUTATE_TIME)

def setup_config(args):
    return Config(args)
