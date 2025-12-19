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

import yaml
import os
from dataclasses import dataclass
from typing import List, Optional, Union, Dict
from config.logger_config import get_global_logger


config_logger = get_global_logger(__name__)
# DUT target config
@dataclass
class DUTTarget:
    name: str
    version: str
    diff_ref: str
    emu_path: str
    cmd: str
    threads: int = 0
    
    def __post_init__(self):
        self.emu_path = os.path.expanduser(self.emu_path)
        if self.threads == 0:
            config_logger.warning("DUT target config warning: threads is not specified, default to 1 thread")
            self.threads = 1
            

# seed input config
@dataclass
class DiveFuzzConfig:
    gen_only: bool
    threads: int
    dive_enable: bool
    mode: str
    seeds_output: str

    template_type: str
    mutate_input: Optional[str] = None
    enable_extension: bool = True
    exclude_extension: Optional[List[str]] = None
    # Specify which extension set to use: 'nutshell', 'general', 'cva6', etc.
    allowed_ext_name: str = 'base'
    # Architecture for bug filtering: 'xs' (XiangShan), 'nts' (NutShell), 'rkt' (Rocket), 'kmh' (Kunminghu)
    architecture: str = 'xs'

    # generate mode fields
    seeds_num: int = 10
    ins_num: int = 200
    is_cva6: bool = False
    is_rv32: bool = False
    
    def __post_init__(self):
        self.seeds_output = os.path.expanduser(self.seeds_output)
        if self.mutate_input:
            self.mutate_input = os.path.expanduser(self.mutate_input)

# base class for seed config
@dataclass
class SeedConfigBase:
    name: str

# predefined seed config
@dataclass
class PredefinedSeedConfig(SeedConfigBase):
    path: str
    
    def __post_init__(self):
        self.path = os.path.expanduser(self.path)

# directory seed input config
@dataclass
class DirSeedConfig(PredefinedSeedConfig):
   
    suffix: str

# runtime generated seed config
@dataclass
class GeneratedSeedConfig(SeedConfigBase):
    input_type: str
    divefuzz: DiveFuzzConfig

# main config parser
@dataclass
class Config:
    dut_target: DUTTarget
    seeds: List[Union[PredefinedSeedConfig, GeneratedSeedConfig]]
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'Config':
        """ create a Config object from a dictionary """
        dut_target = DUTTarget(**config_dict['dut_target'][0])
        
        seeds = []
        for seed_cfg in config_dict.get('seeds', []):
            if 'path' in seed_cfg:
                # is a predefined seed
                if 'input' in seed_cfg:
                    if 'dir' == seed_cfg['input']:
                        # allow `suffix` to be empty
                        seeds.append(DirSeedConfig(
                            name=seed_cfg['name'],
                            path=seed_cfg['path'],
                            suffix=seed_cfg.get('suffix', '')
                        ))
                else:
                    seeds.append(PredefinedSeedConfig(
                        name=seed_cfg['name'],
                        path=seed_cfg['path']
                    ))
            elif 'divefuzz' in seed_cfg:
                seeds.append(GeneratedSeedConfig(
                    name=seed_cfg['name'],
                    input_type=seed_cfg['input'],
                    divefuzz=DiveFuzzConfig(**seed_cfg['divefuzz'])
                ))
        return cls(dut_target=dut_target, seeds=seeds)
    
    @classmethod
    def from_yaml(cls, file_path: str) -> 'Config':
        """ create a Config object from a yaml file """
        with open(file_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls.from_dict(config_dict)
