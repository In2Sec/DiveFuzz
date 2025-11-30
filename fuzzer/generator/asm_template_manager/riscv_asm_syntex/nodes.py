# -*- coding: utf-8 -*-

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

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence, Optional

class AsmNode:
    """Assembly syntax tree base class"""
    def render(self) -> str:
        raise NotImplementedError

@dataclass
class Comment(AsmNode):
    """Comment lines (output with '#')"""
    text: str
    def render(self) -> str:
        return f"# {self.text}".rstrip()

@dataclass
class Blank(AsmNode):
    """blank line"""
    def render(self) -> str:
        return ""

@dataclass
class Label(AsmNode):
    """Tags, for example main: / _start: / 0:"""
    name: str
    def render(self) -> str:
        return f"{self.name}:"

@dataclass
class Directive(AsmNode):
    """
    Assembler directives (e.g., .section/.globl/.align/.word/...)
    - name:  name without the dot prefix (e.g., 'section')
    - args:  sequence of arguments, rendered as '.name arg1, arg2, ...'
    - raw:   if provided, outputs raw string (overrides name/args)
    """
    name: str
    args: Sequence[str] = field(default_factory=list)
    raw: Optional[str] = None

    def render(self) -> str:
        if self.raw is not None:
            return self.raw.rstrip()
        arg_str = ", ".join(self.args)
        if arg_str:
            return f".{self.name} {arg_str}".rstrip()
        return f".{self.name}".rstrip()

@dataclass
class Instruction(AsmNode):
    """Machine/Pseudo instruction line: mnemonic + operands + optional comment"""
    mnemonic: str
    operands: Sequence[str] = field(default_factory=list)
    comment: Optional[str] = None

    def render(self) -> str:
        ops = ", ".join(self.operands)
        s = f"  {self.mnemonic}" + (f" {ops}" if ops else "")
        if self.comment:
            s += f" # {self.comment}"
        return s.rstrip()

@dataclass
class Hook(AsmNode):
    """
    Named placeholder (for instrumentation points), outputs a reminder comment if not replaced during rendering.
    """
    name: str
    def render(self) -> str:
        return f"# <HOOK name='{self.name}' (no content yet)>"
