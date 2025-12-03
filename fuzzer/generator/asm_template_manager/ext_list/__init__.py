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

from .allowed_ext import ALLOWED_EXT_PROFILES
from .special_probabilities import SPECIAL_PROB_PROFILES

class AllowedEXT:
    
    def __init__(self):
        self.EXT_NAMES = tuple(ALLOWED_EXT_PROFILES.keys())  # ('cva6', 'cva6_cascade', 'rv32', 'general', 'base', 'nutshell')
        self.special_probabilities = {}
        self.allowed_ext = []
    
    def _set_allowed_ext(self, allowed_ext_name: str):
        self.allowed_ext = ALLOWED_EXT_PROFILES[allowed_ext_name]

    def _set_special_probabilities(self, allowed_ext_name: str):
        self.special_probabilities = SPECIAL_PROB_PROFILES[allowed_ext_name]
        
    
    def setup_ext(self, allowed_ext_name: str):
        self._set_allowed_ext(allowed_ext_name)
        self._set_special_probabilities(allowed_ext_name)

allowed_ext = AllowedEXT()
