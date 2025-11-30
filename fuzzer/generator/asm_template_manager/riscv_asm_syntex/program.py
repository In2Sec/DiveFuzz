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
from typing import Dict, Iterable, List, Optional, Sequence, Union

from .arch import ArchConfig
from .nodes import AsmNode, Instruction, Directive, Label, Comment, Blank, Hook

NodeLike = Union[AsmNode, str, Sequence[str], tuple, list]

def _hex_or_str(v: Union[int, str]) -> str:
    """
    Formats the integer as the hexadecimal of the 0x prefix; returns directly if it is already str.
    """
    return v if isinstance(v, str) else hex(v)
    
@dataclass
class AsmProgram:
    """
    Assembly program container: holds a linear node list and provides Builder-style API.
    - arch:     ArchConfig, controls data width/rendering details
    - nodes:    syntax nodes
    """
    arch: ArchConfig = field(default_factory=ArchConfig)
    nodes: List[AsmNode] = field(default_factory=list)
    hook_map: Dict[str, List[int]] = field(default_factory=dict, repr=False)
    
    def fork(self) -> "AsmProgram":
        """
        Generate a shallow copy: shares arch, but creates a new list for nodes.
        Suitable for concurrent scenarios: base template remains unchanged, child copies can safely use fill_hook.
        """
        return AsmProgram(arch=self.arch, nodes=list(self.nodes))
    
    # ---------------- Basic Structure and Convenience Methods ----------------

    def add(self, node: AsmNode) -> "AsmProgram":
        self.nodes.append(node)
        return self

    def extend(self, nodes: Iterable[AsmNode]) -> "AsmProgram":
        self.nodes.extend(nodes)
        return self

    def comment(self, text: str) -> "AsmProgram":
        return self.add(Comment(text))

    def blank(self) -> "AsmProgram":
        return self.add(Blank())

    def label(self, name: str) -> "AsmProgram":
        return self.add(Label(name))

    def directive(self, name: str, *args: str, raw: Optional[str] = None) -> "AsmProgram":
        return self.add(Directive(name, list(args), raw=raw))

    def option(self, opt: str) -> "AsmProgram":
        return self.directive("option", opt)

    def align(self, n: int) -> "AsmProgram":
        return self.directive("align", str(n))

    def globl(self, symbol: str) -> "AsmProgram":
        return self.directive("globl", symbol)

    def section(self, name: str, flags: Optional[str] = None, sect_type: Optional[str] = None) -> "AsmProgram":
        """
        Switch sections (supports the format .section .region_0,"aw",@progbits)
        """
        if flags is None and sect_type is None:
            return self.directive("section", name)
        parts = [name]
        if flags is not None: parts.append(f"\"{flags}\"")
        if sect_type is not None: parts.append(sect_type)
        return self.directive("section", ", ".join(parts))

    def instr(self, mnemonic: str, *operands: str, comment: Optional[str] = None) -> "AsmProgram":
        return self.add(Instruction(mnemonic, list(operands), comment=comment))

    def hook(self, name: str) -> "AsmProgram":
        idx = len(self.nodes)
        self.hook_map.setdefault(name, []).append(idx)
        return self.add(Hook(name))

    # ---------------- Instruction Wrappers (including common pseudo-instructions) ----------------

    def li(self, rd: str, imm: Union[int, str]) -> "AsmProgram":
        return self.instr("li", rd, _hex_or_str(imm))

    def la(self, rd: str, symbol: str) -> "AsmProgram":
        return self.instr("la", rd, symbol)

    def mv(self, rd: str, rs: str) -> "AsmProgram":
        return self.instr("mv", rd, rs)

    def auipc(self, rd: str, imm20: Union[int, str]) -> "AsmProgram":
        return self.instr("auipc", rd, _hex_or_str(imm20))

    def lui(self, rd: str, imm20: Union[int, str]) -> "AsmProgram":
        return self.instr("lui", rd, _hex_or_str(imm20))

    def jalr(self, rd: str, rs: str, imm: Union[int, str]) -> "AsmProgram":
        return self.instr("jalr", rd, rs, _hex_or_str(imm))

    def beq(self, rs1: str, rs2: str, target: str) -> "AsmProgram":
        return self.instr("beq", rs1, rs2, target)

    def fence(self) -> "AsmProgram":
        return self.instr("fence")

    def mret(self) -> "AsmProgram":
        return self.instr("mret")

    def dret(self) -> "AsmProgram":
        return self.instr("dret")

    def wfi(self) -> "AsmProgram":
        return self.instr("wfi")

    # ---- CSR Convenience ----
    def csrr(self, rd: str, csr: Union[int, str]) -> "AsmProgram":
        return self.instr("csrr", rd, _hex_or_str(csr))

    def csrw(self, csr: Union[int, str], rs: str, comment: Optional[str] = None) -> "AsmProgram":
        return self.instr("csrw", _hex_or_str(csr), rs, comment=comment)

    # ---- Convenient memory access (expandable as needed) ----
    def lw(self, rd: str, offset_rs1: str) -> "AsmProgram":
        return self.instr("lw", rd, offset_rs1)

    def sw(self, rs2: str, offset_rs1: str) -> "AsmProgram":
        return self.instr("sw", rs2, offset_rs1)

    def ld(self, rd: str, offset_rs1: str) -> "AsmProgram":
        return self.instr("ld", rd, offset_rs1)

    def sd(self, rs2: str, offset_rs1: str) -> "AsmProgram":
        return self.instr("sd", rs2, offset_rs1)

    # ---------------- Data Pseudo-Instructions ----------------

    def data_byte(self, *values: Union[int, str]) -> "AsmProgram":
        vs = [_hex_or_str(v) for v in values]
        return self.directive("byte", ", ".join(vs))

    def data_word(self, *values: Union[int, str]) -> "AsmProgram":
        vs = [_hex_or_str(v) for v in values]
        return self.directive("word", ", ".join(vs))

    def data_dword(self, value: Union[int, str]) -> "AsmProgram":
        return self.directive("dword", _hex_or_str(value))

    def data_8byte(self, value: Union[int, str]) -> "AsmProgram":
        return self.directive("8byte", _hex_or_str(value))

    def data_zero(self, n: int) -> "AsmProgram":
        """Equivalent to .zero n: Outputs n bytes of zero values."""
        return self.directive("zero", str(n))

    def data_space(self, n: int) -> "AsmProgram":
        """Equivalent to .space n: reserves n uninitialized bytes"""
        return self.directive("space", str(n))

    def fourbyte(self, value: Union[int, str]) -> "AsmProgram":
        return self.directive("4byte", _hex_or_str(value))

    # ---- Pointer-width aware write helpers ----
    def label_ptr_zero(self, label_name: str) -> "AsmProgram":
        """
        Declare a pointer-sized 0-value object (RV64: .8byte 0; RV32: two .word 0s).
        """
        self.label(label_name)
        if self.arch.is_rv64():
            self.data_8byte(0x0)
        else:
            self.data_word(0x0, 0x0)
        return self

    # ---------------- Hook Content Filling ----------------

    def fill_hook(self, name: str, nodes: Iterable[NodeLike]) -> "AsmProgram":
        """
        Replace the Hook named `name` with the given nodes.

        Supported:

        - Instances of AsmNode subclasses

        - tuple/list: (mnemonic, *operands)

        - str: Characters starting with '.' or '#' are treated as plain text/comments; otherwise, they are treated as comments.
        """
        prepared: List[AsmNode] = []
        for n in nodes:
            if isinstance(n, AsmNode):
                prepared.append(n)
            elif isinstance(n, (tuple, list)) and len(n) >= 1:
                mnemonic = str(n[0])
                operands = [str(x) for x in n[1:]]
                prepared.append(Instruction(mnemonic, operands))
            elif isinstance(n, str):
                s = n.strip()
                if s.startswith(".") or s.startswith("#"):
                    prepared.append(Directive(name="raw", raw=n))
                else:
                    prepared.append(Comment(n))
            else:
                raise TypeError(f"Unsupported node type in fill_hook: {type(n)}")

        # Search and replace all hooks with the same name
        i, replaced = 0, False
        while i < len(self.nodes):
            node = self.nodes[i]
            if isinstance(node, Hook) and node.name == name:
                self.nodes = self.nodes[:i] + prepared + self.nodes[i+1:]
                replaced = True
                i += len(prepared)
                continue
            i += 1

        if not replaced:
            raise KeyError(f"Hook '{name}' not found.")
        return self

    def get_hook_idx(self, name: str, occurrence: int = 0) -> int:
        """Return the index of the occurrence-th Hook (default first occurrence)."""
        lst = self.hook_map.get(name)
        if not lst or occurrence >= len(lst):
            raise KeyError(f"Hook '{name}' not found (occurrence={occurrence}).")
        return lst[occurrence]
    
    # ---------------- Rendering and Writing ----------------
    def render(self) -> str:
        lines = [node.render() for node in self.nodes]
        return "\n".join(lines).rstrip() + "\n"

    def write(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.render())
    
    def render_slice(self, start: int, end: int) -> str:
        """Render the nodes[start:end] slice, useful for step-by-step rendering."""
        lines = [n.render() for n in self.nodes[start:end]]
        return "\n".join(lines).rstrip() + "\n" if lines else ""
