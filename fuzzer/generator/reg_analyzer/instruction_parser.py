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

from typing import Dict, List, Optional, Tuple
from enum import IntEnum
from dataclasses import dataclass

class InstructionType(IntEnum):
    """RISC-V instruction type enumeration"""
    ZERO_RS = 0          # Instructions with no source registers
    THREE_FRS = 1        # Instructions with three floating-point source registers
    DOUBLE_FRS = 2       # Instructions with two floating-point source registers
    SINGLE_FRS = 3       # Instructions with one floating-point source register
    DOUBLE_RS = 4        # Instructions with two integer source registers
    SINGLE_RS_IMM = 5    # Instructions with one source register + immediate
    SINGLE_RS = 6        # Instructions with one integer source register
    SINGLE_CSR_RS = 7    # Instructions with one CSR + source register
    SINGLE_CSR_IMM = 8   # Instructions with one CSR + immediate
    SINGLE_IMM = 9       # Instructions with one immediate
    LOAD = 10            # Load instructions: rd, offset(rs1) - read base register
    STORE = 11           # Store instructions: rs2, offset(rs1) - read base + data registers
    LOAD_FP = 12         # FP load instructions: frd, offset(rs1) - read base register
    STORE_FP = 13        # FP store instructions: frs2, offset(rs1) - read base + data registers
    
@dataclass
class InstructionInfo:
    """Instruction information data class"""
    op_name: str
    oprd_names: List[str]
    type: InstructionType
    imm: Optional[int] = None
    
class InstructionParser:
    """RISC-V instruction parser"""
    
    # Define various types of instructions
    # TODO Consider rounding mode later
    _INSTRUCTION_GROUPS = {
        InstructionType.ZERO_RS: [
            "frrm", "frflags"
        ],
        
        InstructionType.THREE_FRS: [
            "fmadd.s", "fmsub.s", "fnmadd.s", "fnmsub.s", "fmadd.d", "fmsub.d", "fnmadd.d", "fnmsub.d"
        ],
        
        InstructionType.DOUBLE_FRS: [
            "fadd.s", "fsub.s", "fmul.s", "fdiv.s", "fsgnj.s", "fsgnjn.s", "fsgnjx.s", "fmin.s", "fmax.s", "feq.s",\
            "flt.s", "fle.s", "fadd.d", "fsub.d", "fmul.d", "fdiv.d", "fsgnj.d", "fsgnjn.d", "fsgnjx.d", "fmin.d",\
            "fmax.d", "feq.d", "flt.d", "fle.d"
        ],
        
        InstructionType.SINGLE_FRS: [
            "fsqrt.s", "fcvt.w.s", "fcvt.wu.s", "fmv.x.w", "fclass.s", "fsqrt.d", "fcvt.w.d", "fcvt.wu.d", "fclass.d",\
            "fcvt.d.w", "fcvt.d.wu", "fcvt.s.d", "fcvt.d.s", "fcvt.l.s", "fcvt.lu.s", "fcvt.s.l", "fcvt.s.lu",\
            "fcvt.l.d", "fcvt.lu.d", "fmv.x.d", "fcvt.d.l", "fcvt.d.lu", "fmv.d.x"
        ],
        
        InstructionType.DOUBLE_RS: [
            "add", "sub", "sll", "slt", "sltu", "xor", "srl", "sra", "or", "and", "addw", "subw", "sllw", "srlw", "sraw",\
            "c.add", "c.and", "c.or", "c.xor", "c.sub", "c.addw", "c.subw", "mul", "mulhsu", "mulhu", "div", "divu",\
            "rem", "remu", "mulh", "mulw", "divw", "divuw", "remw", "remuw", "ror", "rol", "andn", "orn", "xnor", "pack",\
            "packh", "rorw", "rolw", "packw", "clmul", "clmulh", "xperm8", "xperm4", "aes64es", "aes64es", "aes64esm",\
            "aes64ks2", "aes64ds", "aes64dsm","bclr", "bext", "binv", "bset", "slo","sro", "grev", "gorc", "shfl","unshfl",\
            "sh1add", "sh2add", "sh3add", "min", "max", "maxu", "minu", "bcompress", "bdecompress", "bfp", "clmulr"
        ],
        
        InstructionType.SINGLE_RS_IMM: [
            "addi", "slti", "sltiu", "xori", "ori", "andi", "slli", "srli", "srai", "slliw", "srliw", "sraiw",\
            "c.addi", "c.andi", "c.addiw", "c.slli", "c.srli", "c.srai", "rori", "roriw", "aes64ks1i"
        ],
        
        InstructionType.SINGLE_RS: [
            "fsrm","fsflags", "fcvt.s.w", "fcvt.s.wu", "fmv.w.x", "c.mv",  "aes64im", "sha512sig0", "sha512sig1",\
            "sha512sum0", "sha512sum1", "sha256sig0", "sha256sig1", "sha256sum0", "sha256sum1", "sext.b", "sext.h",\
            "ctz", "crc32.b", "crc32.h", "crc32.w", "crc32c.b", "crc32c.w", "cpop"
        ],
        
        InstructionType.SINGLE_CSR_RS: [
            "csrrw", "csrrs", "csrrc"
        ],
        
        InstructionType.SINGLE_CSR_IMM: [
            "csrrwi", "csrrsi", "csrrci"
        ],
        
        InstructionType.SINGLE_IMM: [
            "lui", "auipc", "li", "c.li", "c.lui", "c.addi16sp", "c.addi4spn"
        ],

        InstructionType.LOAD: [
            "lb", "lh", "lw", "ld", "lbu", "lhu", "lwu"
        ],

        InstructionType.STORE: [
            "sb", "sh", "sw", "sd"
        ],

        InstructionType.LOAD_FP: [
            "flw", "fld"
        ],

        InstructionType.STORE_FP: [
            "fsw", "fsd"
        ]
    }
    
    _OPCODE_TO_TYPE = {op: instr_type for instr_type, ops in _INSTRUCTION_GROUPS.items() for op in ops}
    
    @staticmethod
    def _get_instruction_type(opcode: str) -> Optional[InstructionType]:
        """Get instruction type"""
        return InstructionParser._OPCODE_TO_TYPE.get(opcode)
    
    @staticmethod
    def parse_instruction(instruction_str: str) -> Tuple[str, Optional[InstructionInfo]]:
        """Parse instruction string"""
        # Handle possible labels, Remove segment identifiers
        if ":" in instruction_str:
            _, instruction_str = instruction_str.split(':', 1)
        
        instruction_str = instruction_str.strip()
        # Remove leading and trailing white space characters
        parts = instruction_str.split()
        if not parts:
            return instruction_str, None
            
        opcode = parts[0]
        operands = [op.rstrip(',') for op in parts[1:]]
        
        instr_type = InstructionParser._get_instruction_type(opcode)
        if instr_type is None:
            return instruction_str, None
            
        if instr_type in [InstructionType.SINGLE_IMM, InstructionType.SINGLE_RS_IMM, InstructionType.SINGLE_CSR_IMM]:
            imm = int(operands[-1], 0)
            operands = operands[:-1]
        else:
            imm = None  
            
        return instruction_str, InstructionInfo(op_name=opcode, oprd_names=operands, type=instr_type, imm=imm)

    # Helper function to extract base register from "offset(base)" format
    @staticmethod
    def _extract_base_register(addr_str: str) -> str:
        """Extract base register from address format like '12(t6)' -> 't6'"""
        if '(' in addr_str and ')' in addr_str:
            start = addr_str.index('(') + 1
            end = addr_str.index(')')
            return addr_str[start:end]
        return addr_str  # Fallback if no parentheses

    # Source register extractors - return list of register names (excluding destination register)
    _EXTRACTORS = {
        InstructionType.ZERO_RS: lambda a: [a[-1]],                   # rd only, for reading result
        InstructionType.THREE_FRS: lambda a: [a[-3], a[-2], a[-1]],   # frd, frs1, frs2, frs3 -> get last 3
        InstructionType.DOUBLE_FRS: lambda a: [a[-2], a[-1]],         # frd, frs1, frs2 -> get last 2
        InstructionType.SINGLE_FRS: lambda a: [a[-1]],                # frd, frs1 -> get last 1
        InstructionType.DOUBLE_RS: lambda a: [a[-2], a[-1]],          # rd, rs1, rs2 -> get last 2
        InstructionType.SINGLE_RS_IMM: lambda a: [a[-1]],             # rd, rs1, imm -> get last 1 (imm already removed)
        InstructionType.SINGLE_RS: lambda a: [a[-1]],                 # rd, rs1 -> get last 1
        InstructionType.SINGLE_CSR_RS: lambda a: [a[-1]],             # rd, csr, rs1 -> get last 1 (only rs1 value matters)
        InstructionType.SINGLE_CSR_IMM: lambda a: [],                 # rd, csr, imm -> no register to read
        InstructionType.SINGLE_IMM: lambda a: [],                     # rd, imm -> no register to read
        # Load: rd, offset(rs1) -> extract base register rs1
        InstructionType.LOAD: lambda a: [InstructionParser._extract_base_register(a[-1])],
        # Store: rs2, offset(rs1) -> extract both rs2 (data) and rs1 (base)
        InstructionType.STORE: lambda a: [a[0], InstructionParser._extract_base_register(a[-1])],
        # FP Load: frd, offset(rs1) -> extract base register rs1
        InstructionType.LOAD_FP: lambda a: [InstructionParser._extract_base_register(a[-1])],
        # FP Store: frs2, offset(rs1) -> extract both frs2 (data) and rs1 (base)
        InstructionType.STORE_FP: lambda a: [a[0], InstructionParser._extract_base_register(a[-1])],
    }

    @staticmethod
    def get_source_registers(instructionInfo: InstructionInfo) -> Optional[List[str]]:
        """Extract source register names from instruction.

        Returns:
            List of source register names, e.g., ['s4', 's5'] for 'add t0, s4, s5'
            Empty list if no source registers to read
            None if instruction type not recognized
        """
        extractor = InstructionParser._EXTRACTORS.get(instructionInfo.type)
        if extractor is None:
            print("No matched instruction type.")
            return None

        return extractor(instructionInfo.oprd_names)

    @staticmethod
    def is_float_instruction(instructionInfo: InstructionInfo) -> bool:
        """Check if instruction uses floating-point registers"""
        return instructionInfo.type in [
            InstructionType.THREE_FRS,
            InstructionType.DOUBLE_FRS,
            InstructionType.SINGLE_FRS
        ]
