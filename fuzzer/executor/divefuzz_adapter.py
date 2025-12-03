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


import os
from pathlib import Path
import subprocess
from config.dut_config import GeneratedSeedConfig

from config.divefuzz_config import DiveFuzzArgConfig
from generator.core.mutator import mutate_instructions_parallel
from utils.elf_to_img import process_assembly_files
from generator.core.generator import generate_instructions_parallel
from generator.config.config_manager import setup_config

# Module-level variable to store the Config object
_divefuzz_config = None


def setup_divefuzz(seed_config: GeneratedSeedConfig, global_logger):
    global _divefuzz_config
    # make sure `riscv64-unknown-elf-as`, `riscv64-unknown-elf-gcc`,
    # `riscv64-unknown-elf-ld` and `riscv64-unknown-elf-objcopy` are specified in the environment
    riscv_toolchain = [
        'riscv64-unknown-elf-as', 'riscv64-unknown-elf-gcc', 'riscv64-unknown-elf-ld', 'riscv64-unknown-elf-objcopy'
    ]
    for tool in riscv_toolchain:
        try:
            subprocess.run([tool, '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            raise Exception(f"{tool} not found in environment, DiveFuzz will not work.")
    
    # fetch `spike` path
    if 'spike' not in os.environ:
        global_logger.warning("spike not found in environment")
    else:
        spike_path = os.environ['spike']
        
        # check `spike` path contain `DiveFuzz`
        if 'DiveFuzz' not in spike_path:
            global_logger.warning("Your spike path does not contain `DiveFuzz`. Diversity function will not work.")
     
    divefuzz_config = DiveFuzzArgConfig(
        mutation=seed_config.divefuzz.mode == "mutate",
        generate=seed_config.divefuzz.mode == "generate",
        eliminate_enable=seed_config.divefuzz.dive_enable,
        cva6=seed_config.divefuzz.is_cva6,
        rv32=seed_config.divefuzz.is_rv32,
        instr_number=seed_config.divefuzz.ins_num,
        seeds=seed_config.divefuzz.seeds_num,
        max_workers=seed_config.divefuzz.threads,
        seed_dir=Path(seed_config.divefuzz.seeds_output),
        mutate_out=Path(seed_config.divefuzz.mutate_input) if seed_config.divefuzz.mutate_input else Path.cwd(),
        out_dir=Path(seed_config.divefuzz.seeds_output),
        enable_ext=seed_config.divefuzz.enable_extension,
        exclude_ext=seed_config.divefuzz.exclude_extension if seed_config.divefuzz.exclude_extension else [],
        template_type=seed_config.divefuzz.template_type,
    )
    _divefuzz_config = setup_config(divefuzz_config)


def run_divefuzz(seed_config: GeneratedSeedConfig, seed_config_logger) -> list:
    global _divefuzz_config
    assert(_divefuzz_config is not None)
    # handle generate
    if seed_config.divefuzz.mode == "generate":
        generate_instructions_parallel(
            instr_number=seed_config.divefuzz.ins_num,
            seed_times=seed_config.divefuzz.seeds_num,
            eliminate_enable=seed_config.divefuzz.dive_enable,
            is_cva6=seed_config.divefuzz.is_cva6,
            is_rv32=seed_config.divefuzz.is_rv32,
            max_workers=seed_config.divefuzz.threads,
            arch=_divefuzz_config.arch,
            template_type=seed_config.divefuzz.template_type
        )

    elif seed_config.divefuzz.mode == "mutate":
        mutate_instructions_parallel(
            directory_path=Path(seed_config.divefuzz.mutate_input) if seed_config.divefuzz.mutate_input else Path.cwd(),
            mutate_directory=Path(seed_config.divefuzz.seeds_output),
            max_workers=seed_config.divefuzz.threads,
            enable_ext=seed_config.divefuzz.enable_extension,
            exclude_extensions=seed_config.divefuzz.exclude_extension if seed_config.divefuzz.exclude_extension else [],
            eliminate_enable=seed_config.divefuzz.dive_enable,
            arch=_divefuzz_config.arch,
            template_type=seed_config.divefuzz.template_type
        )
    else:
        raise ValueError(f"Unknown mode: {seed_config.divefuzz.mode}")

    return process_divefuzz_asm(seed_config, seed_config_logger)
        


def process_divefuzz_asm(seed_config: GeneratedSeedConfig, seed_config_logger):

    # Generator outputs to cwd/out-seeds by default
    generator_output_dir = Path.cwd() / 'out-seeds'

    # convert img/elf
    seed_config_logger.info("Converting assembly to elf files...")
    process_assembly_files(str(generator_output_dir))

    # find elf
    elf_dir = generator_output_dir / 'elf_file'
    if not elf_dir.exists():
        seed_config_logger.error(f"ELF directory not found: {elf_dir}")
        return []

    seed_files = []
    for file in os.listdir(elf_dir):
        if file.endswith(".elf"):
            seed_files.append(os.path.join(elf_dir, file))

    seed_config_logger.info(
        f"Found {len(seed_files)} generated seed files")

    return seed_files
