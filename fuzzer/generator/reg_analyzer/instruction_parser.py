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

"""
Simplified RISC-V Instruction Parser

Parses RISC-V assembly instructions and extracts:
- Opcode
- Source register indices (for XOR computation before execution)
- Destination register indices (for bug filtering after execution)
- Immediate values

Design Philosophy:
- Direct parsing: One function returns all needed information
- No intermediate data structures
- Minimal abstraction layers
"""

from typing import Optional, Tuple, List
from enum import IntEnum

# Floating-point register index offset
# Register index convention:
# - 0-31: Integer registers (x0-x31)
# - 32-63: Floating-point registers (f0-f31, use FPR_OFFSET + reg_num)
FPR_OFFSET = 32


class InstructionType(IntEnum):
    """RISC-V instruction type enumeration for operand extraction"""
    ZERO_RS = 0          # Instructions with no source registers
    THREE_FRS = 1        # Instructions with three floating-point source registers
    DOUBLE_FRS = 2       # Instructions with two floating-point source registers
    SINGLE_FRS = 3       # Instructions with one floating-point source register (frd, frs)
    DOUBLE_RS = 4        # Instructions with two integer source registers
    SINGLE_RS_IMM = 5    # Instructions with one source register + immediate
    SINGLE_RS = 6        # Instructions with one integer source register
    SINGLE_CSR_RS = 7    # Instructions with one CSR + source register
    SINGLE_CSR_IMM = 8   # Instructions with one CSR + immediate
    SINGLE_IMM = 9       # Instructions with one immediate
    LOAD = 10            # Load instructions: rd, offset(rs1)
    STORE = 11           # Store instructions: rs2, offset(rs1)
    LOAD_FP = 12         # FP load instructions: frd, offset(rs1)
    STORE_FP = 13        # FP store instructions: frs2, offset(rs1)
    ATOMIC_LR = 14       # Load-Reserved: lr.w/lr.d rd, (rs1)
    ATOMIC_SC = 15       # Store-Conditional: sc.w/sc.d rd, rs2, (rs1)
    ATOMIC_AMO = 16      # Atomic Memory Operations: amo*.w/d rd, rs2, (rs1)
    FP_TO_INT = 17       # Float to Int conversion: rd (int), frs (float)
    INT_TO_FP = 18       # Int to Float conversion: frd (float), rs (int)


class InstructionParser:
    """Simplified RISC-V instruction parser"""

    # Instruction groups classified by type
    _INSTRUCTION_GROUPS = {
        InstructionType.ZERO_RS: [
            "frrm", "frflags"
        ],

        InstructionType.THREE_FRS: [
            "fmadd.s", "fmsub.s", "fnmadd.s", "fnmsub.s", "fmadd.d", "fmsub.d", "fnmadd.d", "fnmsub.d"
        ],

        InstructionType.DOUBLE_FRS: [
            "fadd.s", "fsub.s", "fmul.s", "fdiv.s", "fsgnj.s", "fsgnjn.s", "fsgnjx.s", "fmin.s", "fmax.s", "feq.s",
            "flt.s", "fle.s", "fadd.d", "fsub.d", "fmul.d", "fdiv.d", "fsgnj.d", "fsgnjn.d", "fsgnjx.d", "fmin.d",
            "fmax.d", "feq.d", "flt.d", "fle.d"
        ],

        InstructionType.SINGLE_FRS: [
            # frd, frs -> float to float operations
            "fsqrt.s", "fsqrt.d", "fcvt.s.d", "fcvt.d.s"
        ],

        InstructionType.FP_TO_INT: [
            # rd (int), frs (float) -> float to int conversion
            "fcvt.w.s", "fcvt.wu.s", "fcvt.l.s", "fcvt.lu.s",
            "fcvt.w.d", "fcvt.wu.d", "fcvt.l.d", "fcvt.lu.d",
            "fmv.x.w", "fmv.x.d",
            # fclass instructions also write to integer register
            "fclass.s", "fclass.d"
        ],

        InstructionType.INT_TO_FP: [
            # frd (float), rs (int) -> int to float conversion
            "fcvt.s.w", "fcvt.s.wu", "fcvt.s.l", "fcvt.s.lu",
            "fcvt.d.w", "fcvt.d.wu", "fcvt.d.l", "fcvt.d.lu",
            "fmv.w.x", "fmv.d.x"
        ],

        InstructionType.DOUBLE_RS: [
            "add", "sub", "sll", "slt", "sltu", "xor", "srl", "sra", "or", "and", "addw", "subw", "sllw", "srlw", "sraw",
            "c.add", "c.and", "c.or", "c.xor", "c.sub", "c.addw", "c.subw", "mul", "mulhsu", "mulhu", "div", "divu",
            "rem", "remu", "mulh", "mulw", "divw", "divuw", "remw", "remuw", "ror", "rol", "andn", "orn", "xnor", "pack",
            "packh", "rorw", "rolw", "packw", "clmul", "clmulh", "xperm8", "xperm4", "aes64es", "aes64esm",
            "aes64ks2", "aes64ds", "aes64dsm", "bclr", "bext", "binv", "bset", "slo", "sro", "grev", "gorc", "shfl", "unshfl",
            "sh1add", "sh2add", "sh3add", "min", "max", "maxu", "minu", "bcompress", "bdecompress", "bfp", "clmulr"
        ],

        InstructionType.SINGLE_RS_IMM: [
            "addi", "slti", "sltiu", "xori", "ori", "andi", "slli", "srli", "srai", "slliw", "srliw", "sraiw",
            "c.addi", "c.andi", "c.addiw", "c.slli", "c.srli", "c.srai", "rori", "roriw", "aes64ks1i"
        ],

        InstructionType.SINGLE_RS: [
            "fsrm", "fsflags", "c.mv", "aes64im", "sha512sig0", "sha512sig1",
            "sha512sum0", "sha512sum1", "sha256sig0", "sha256sig1", "sha256sum0", "sha256sum1", "sext.b", "sext.h",
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
        ],

        InstructionType.ATOMIC_LR: [
            "lr.w", "lr.d"
        ],

        InstructionType.ATOMIC_SC: [
            "sc.w", "sc.d"
        ],

        InstructionType.ATOMIC_AMO: [
            "amoswap.w", "amoswap.d", "amoadd.w", "amoadd.d",
            "amoxor.w", "amoxor.d", "amoand.w", "amoand.d",
            "amoor.w", "amoor.d", "amomin.w", "amomin.d",
            "amomax.w", "amomax.d", "amominu.w", "amominu.d",
            "amomaxu.w", "amomaxu.d"
        ]
    }

    # Build opcode to type mapping
    _OPCODE_TO_TYPE = {op: instr_type for instr_type, ops in _INSTRUCTION_GROUPS.items() for op in ops}

    # Register name to index mapping (integer registers)
    _REG_NAME_TO_INDEX = {
        'zero': 0, 'ra': 1, 'sp': 2, 'gp': 3, 'tp': 4,
        't0': 5, 't1': 6, 't2': 7,
        's0': 8, 'fp': 8, 's1': 9,
        'a0': 10, 'a1': 11, 'a2': 12, 'a3': 13, 'a4': 14, 'a5': 15, 'a6': 16, 'a7': 17,
        's2': 18, 's3': 19, 's4': 20, 's5': 21, 's6': 22, 's7': 23, 's8': 24, 's9': 25,
        's10': 26, 's11': 27,
        't3': 28, 't4': 29, 't5': 30, 't6': 31,
    }

    # Add x0-x31 and f0-f31 mappings
    for i in range(32):
        _REG_NAME_TO_INDEX[f'x{i}'] = i
        _REG_NAME_TO_INDEX[f'f{i}'] = i

    # Add floating-point register ABI names (ft0-ft11, fs0-fs11, fa0-fa7)
    _FPR_ABI_TO_INDEX = {
        'ft0': 0, 'ft1': 1, 'ft2': 2, 'ft3': 3, 'ft4': 4, 'ft5': 5, 'ft6': 6, 'ft7': 7,
        'fs0': 8, 'fs1': 9,
        'fa0': 10, 'fa1': 11,
        'fa2': 12, 'fa3': 13, 'fa4': 14, 'fa5': 15, 'fa6': 16, 'fa7': 17,
        'fs2': 18, 'fs3': 19, 'fs4': 20, 'fs5': 21, 'fs6': 22, 'fs7': 23,
        'fs8': 24, 'fs9': 25, 'fs10': 26, 'fs11': 27,
        'ft8': 28, 'ft9': 29, 'ft10': 30, 'ft11': 31,
    }
    # Add FPR ABI names to the main mapping (they use same 0-31 indices as f0-f31)
    _REG_NAME_TO_INDEX.update(_FPR_ABI_TO_INDEX)

    @staticmethod
    def _extract_base_register(addr_str: str) -> str:
        """Extract base register from address format like '12(t6)' -> 't6' or '(t6)' -> 't6'"""
        if '(' in addr_str and ')' in addr_str:
            start = addr_str.index('(') + 1
            end = addr_str.index(')')
            return addr_str[start:end]
        return addr_str

    @staticmethod
    def reg_name_to_index(reg_name: str) -> Optional[int]:
        """Convert register name to index (0-31)"""
        return InstructionParser._REG_NAME_TO_INDEX.get(reg_name.lower())

    @staticmethod
    def _is_float_register(reg_name: str) -> bool:
        """
        Determine if a register name is a floating-point register.

        Floating-point registers:
        - Numeric format: f0-f31
        - ABI names: ft0-ft7, fs0-fs11, fa0-fa7, ft8-ft11

        Note: 'fp' (frame pointer) is an INTEGER register (alias of s0/x8),
        not a floating-point register!

        Args:
            reg_name: Lowercase register name (e.g., 'ft4', 'x1', 'fp')

        Returns:
            True if floating-point register, False otherwise
        """
        # 'fp' is an integer register (s0/x8 alias), NOT a float register!
        if reg_name == 'fp':
            return False

        # Check if it's in the FPR ABI mapping (ft*, fs*, fa*)
        if reg_name in InstructionParser._FPR_ABI_TO_INDEX:
            return True

        # Check f0-f31 format: must be 'f' followed by a valid number
        if reg_name.startswith('f') and len(reg_name) >= 2:
            try:
                num = int(reg_name[1:])
                if 0 <= num <= 31:
                    return True
            except ValueError:
                pass

        return False

    @staticmethod
    def parse_instruction_full(instruction_str: str) -> Tuple[str, List[int], List[int], Optional[int]]:
        """
        Parse instruction and directly return all needed information

        This is the MAIN entry point - one function does everything:
        1. Parse opcode
        2. Classify instruction type
        3. Extract and convert register names to indices
        4. Separate source vs destination registers
        5. Extract immediate value

        Args:
            instruction_str: Assembly instruction like "sc.w s9, a7, (t6)" or "add t0, t1, t2"

        Returns:
            Tuple of (opcode, source_reg_indices, dest_reg_indices, immediate)
            immediate is None for instructions without immediate operand

        Examples:
            "add t0, t1, t2"      → ("add", [6, 7], [5], None)
            "sc.w s9, a7, (t6)"   → ("sc.w", [17, 31], [25], None)
            "lr.w s9, (t6)"       → ("lr.w", [31], [25], None)
            "addi t0, t1, 100"    → ("addi", [6], [5], 100)
            "addi t0, t1, 0"      → ("addi", [6], [5], 0)
            "sw t0, 12(t1)"       → ("sw", [5, 6], [], None)
            "lui t0, 0x1000"      → ("lui", [], [5], 4096)

        Note:
            For unknown instructions, returns ("unknown", [], [], None)
        """
        # Handle labels
        if ":" in instruction_str:
            _, instruction_str = instruction_str.split(':', 1)

        instruction_str = instruction_str.strip()
        parts = instruction_str.split()

        if not parts:
            return "", [], [], None

        opcode = parts[0]
        operands = [op.rstrip(',') for op in parts[1:]]

        # Normalize opcode: remove .aq/.rl/.aqrl suffixes for AMO instructions
        # e.g., "amoswap.d.rl" -> "amoswap.d", "amoadd.w.aqrl" -> "amoadd.w"
        opcode_normalized = opcode
        for suffix in ['.aqrl', '.aq', '.rl']:
            if opcode.endswith(suffix):
                opcode_normalized = opcode[:-len(suffix)]
                break

        # Get instruction type (use normalized opcode for lookup)
        instr_type = InstructionParser._OPCODE_TO_TYPE.get(opcode_normalized)
        if instr_type is None:
            # Unknown instruction, return empty
            return opcode, [], [], None

        # Extract immediate if present (for IMM type instructions)
        immediate = None
        if instr_type in [InstructionType.SINGLE_IMM, InstructionType.SINGLE_RS_IMM, InstructionType.SINGLE_CSR_IMM]:
            if operands:
                try:
                    immediate = int(operands[-1], 0)
                    operands = operands[:-1]  # Remove immediate from operands list
                except (ValueError, IndexError):
                    pass

        # Extract source and dest register indices based on instruction type
        source_indices, dest_indices = InstructionParser._extract_registers(instr_type, operands)

        return opcode, source_indices, dest_indices, immediate

    @staticmethod
    def _extract_registers(instr_type: InstructionType, operands: List[str]) -> Tuple[List[int], List[int]]:
        """
        Extract source and destination register indices based on instruction type

        Args:
            instr_type: Instruction type enum
            operands: List of operand strings (with immediate already removed for IMM types)

        Returns:
            (source_reg_indices, dest_reg_indices)
            Note: Floating-point registers use indices 32-63 (FPR_OFFSET + reg_num)
        """
        reg_to_idx = InstructionParser.reg_name_to_index

        # Helper to convert register name to index safely
        # Returns FPR_OFFSET + reg_num for floating-point registers
        def to_idx(reg_name: str) -> int:
            idx = reg_to_idx(reg_name)
            if idx is None:
                return 0
            # Check if this is a floating-point register
            # Note: 'fp' is an integer register (s0/x8 alias), NOT a float register!
            reg_lower = reg_name.strip().lower()
            if InstructionParser._is_float_register(reg_lower):
                return FPR_OFFSET + idx
            return idx

        if not operands:
            return [], []

        # Pattern matching for each instruction type
        # Format: (source_indices, dest_indices)

        if instr_type == InstructionType.ZERO_RS:
            # rd only (no source registers)
            return [], [to_idx(operands[0])] if operands else []

        elif instr_type in [InstructionType.THREE_FRS]:
            # frd, frs1, frs2, frs3 → sources=[frs1,frs2,frs3], dest=[frd]
            if len(operands) >= 4:
                return [to_idx(operands[1]), to_idx(operands[2]), to_idx(operands[3])], [to_idx(operands[0])]
            return [], []

        elif instr_type in [InstructionType.DOUBLE_FRS, InstructionType.DOUBLE_RS]:
            # rd, rs1, rs2 → sources=[rs1,rs2], dest=[rd]
            if len(operands) >= 3:
                return [to_idx(operands[1]), to_idx(operands[2])], [to_idx(operands[0])]
            return [], []

        elif instr_type in [InstructionType.SINGLE_FRS, InstructionType.SINGLE_RS, InstructionType.SINGLE_RS_IMM]:
            # rd, rs1, [imm] → sources=[rs1], dest=[rd]
            if len(operands) >= 2:
                return [to_idx(operands[1])], [to_idx(operands[0])]
            return [], []

        elif instr_type == InstructionType.FP_TO_INT:
            # rd (int), frs (float) → sources=[frs with FPR_OFFSET], dest=[rd without FPR_OFFSET]
            # e.g., fcvt.l.s t0, fs0 → sources=[40], dest=[5]
            if len(operands) >= 2:
                frs_idx = reg_to_idx(operands[1])
                rd_idx = reg_to_idx(operands[0])
                if frs_idx is not None and rd_idx is not None:
                    return [FPR_OFFSET + frs_idx], [rd_idx]
            return [], []

        elif instr_type == InstructionType.INT_TO_FP:
            # frd (float), rs (int) → sources=[rs without FPR_OFFSET], dest=[frd with FPR_OFFSET]
            # e.g., fcvt.s.l fs0, t0 → sources=[5], dest=[40]
            if len(operands) >= 2:
                rs_idx = reg_to_idx(operands[1])
                frd_idx = reg_to_idx(operands[0])
                if rs_idx is not None and frd_idx is not None:
                    return [rs_idx], [FPR_OFFSET + frd_idx]
            return [], []

        elif instr_type == InstructionType.SINGLE_CSR_RS:
            # rd, csr, rs1 → sources=[rs1], dest=[rd]
            # Note: CSR address is not included in source_regs (only used for encoding)
            if len(operands) >= 3:
                return [to_idx(operands[2])], [to_idx(operands[0])]
            return [], []

        elif instr_type == InstructionType.SINGLE_CSR_IMM:
            # rd, csr, imm → sources=[], dest=[rd]
            if len(operands) >= 2:
                return [], [to_idx(operands[0])]
            return [], []

        elif instr_type == InstructionType.SINGLE_IMM:
            # rd, imm → sources=[], dest=[rd]
            if len(operands) >= 1:
                return [], [to_idx(operands[0])]
            return [], []

        elif instr_type in [InstructionType.LOAD, InstructionType.LOAD_FP]:
            # rd, offset(base) → sources=[base], dest=[rd]
            if len(operands) >= 2:
                base_reg = InstructionParser._extract_base_register(operands[1])
                return [to_idx(base_reg)], [to_idx(operands[0])]
            return [], []

        elif instr_type in [InstructionType.STORE, InstructionType.STORE_FP]:
            # rs2, offset(base) → sources=[rs2, base], dest=[]
            if len(operands) >= 2:
                base_reg = InstructionParser._extract_base_register(operands[1])
                return [to_idx(operands[0]), to_idx(base_reg)], []
            return [], []

        elif instr_type == InstructionType.ATOMIC_LR:
            # lr.w rd, (rs1) → sources=[rs1], dest=[rd]
            if len(operands) >= 2:
                base_reg = InstructionParser._extract_base_register(operands[1])
                return [to_idx(base_reg)], [to_idx(operands[0])]
            return [], []

        elif instr_type in [InstructionType.ATOMIC_SC, InstructionType.ATOMIC_AMO]:
            # sc.w/amo*.w rd, rs2, (rs1) → sources=[rs2, rs1], dest=[rd]
            if len(operands) >= 3:
                base_reg = InstructionParser._extract_base_register(operands[2])
                return [to_idx(operands[1]), to_idx(base_reg)], [to_idx(operands[0])]
            return [], []

        # Default fallback
        return [], []
