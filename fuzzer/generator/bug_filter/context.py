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
Filter Context Module

Provides execution context for precision filters, including pre/post execution states,
instruction information, and convenient access to SpikeSession state query APIs.

Based on RISyn paper's three-level filtering conditions:
- Level 1: φ(s_pre, opcode, operand) - Pre-execution conditions
- Level 2: φ(s_pre, s_post) - State transition conditions
- Level 3: φ(s_pre, opcode, operand, s_post) - Complete four-tuple conditions
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..reg_analyzer.spike_session import SpikeSession


@dataclass
class PreExecutionState:
    """
    Snapshot of processor state before instruction execution.

    Captures all relevant state that may be needed for pre-execution filtering
    or as baseline for post-execution state comparison.
    """

    # Integer registers (x0-x31)
    xpr: List[int] = field(default_factory=lambda: [0] * 32)

    # Floating-point registers (f0-f31, stored as uint64)
    fpr: List[int] = field(default_factory=lambda: [0] * 32)

    # Program counter
    pc: int = 0

    # Current privilege level (0=U, 1=S, 3=M)
    privilege: int = 3

    # Virtualization mode (H extension)
    virtualization: bool = False

    # Load reservation state (for LR/SC atomic operations)
    reservation_valid: bool = False
    reservation_addr: int = 0

    # CSR values (addr -> value, only stores accessed CSRs)
    csrs: Dict[int, int] = field(default_factory=dict)

    # Vector state (None if V extension not enabled)
    vector_state: Optional[Any] = None


@dataclass
class PostExecutionState:
    """
    Snapshot of processor state after instruction execution.

    Captures state changes including side effects for post-execution filtering.
    """

    # Integer registers (x0-x31)
    xpr: List[int] = field(default_factory=lambda: [0] * 32)

    # Floating-point registers (f0-f31)
    fpr: List[int] = field(default_factory=lambda: [0] * 32)

    # Program counter
    pc: int = 0

    # Current privilege level
    privilege: int = 3

    # Virtualization mode
    virtualization: bool = False

    # Whether privilege changed during execution
    privilege_changed: bool = False

    # Whether virtualization mode changed
    virtualization_changed: bool = False

    # Trap information (if exception occurred)
    trap_occurred: bool = False
    trap_cause: int = 0
    trap_tval: int = 0
    trap_name: str = ""

    # Commit log (instruction side effects)
    reg_writes: List[tuple] = field(default_factory=list)  # [(reg_num, value), ...]
    mem_reads: List[tuple] = field(default_factory=list)  # [(addr, value, size), ...]
    mem_writes: List[tuple] = field(default_factory=list)  # [(addr, value, size), ...]

    # Load reservation state after execution
    reservation_valid: bool = False
    reservation_addr: int = 0

    # CSR values after execution
    csrs: Dict[int, int] = field(default_factory=dict)

    # Vector state after execution
    vector_state: Optional[Any] = None


@dataclass
class FilterContext:
    """
    Complete execution context for precision filters.

    This class provides all information needed by filter conditions:
    - Instruction details (opcode, operands, machine code)
    - Pre-execution state (s_pre)
    - Post-execution state (s_post, only available in post-filter phase)
    - Architecture and configuration info
    - Convenient helper methods for common queries

    Usage:
        # In pre-execution filter
        def my_pre_filter(ctx: FilterContext) -> FilterResult:
            if ctx.get_xpr(1) == 0:  # x1 == 0
                return FilterResult.reject("x1 is zero")
            return FilterResult.accept()

        # In post-execution filter
        def my_post_filter(ctx: FilterContext) -> FilterResult:
            if ctx.s_post.trap_occurred:
                return FilterResult.reject("Instruction caused trap")
            return FilterResult.accept()
    """

    # ==========================================================================
    # Spike Session Reference
    # ==========================================================================
    spike_session: Optional["SpikeSession"] = None

    # ==========================================================================
    # Instruction Information
    # ==========================================================================
    # Instruction opcode (e.g., "div", "sc.w", "csrrw")
    opcode: str = ""

    # Instruction operands as strings (e.g., ["x1", "x2", "x3"])
    operands: List[str] = field(default_factory=list)

    # Raw machine code
    machine_code: int = 0

    # Instruction size in bytes (2 for compressed, 4 for standard)
    instruction_size: int = 4

    # Original assembly string
    assembly: str = ""

    # ==========================================================================
    # Execution State
    # ==========================================================================
    # Pre-execution state snapshot
    s_pre: PreExecutionState = field(default_factory=PreExecutionState)

    # Post-execution state snapshot (None in pre-filter phase)
    s_post: Optional[PostExecutionState] = None

    # ==========================================================================
    # Configuration
    # ==========================================================================
    # Target architecture ('xs', 'nts', 'cva6', 'boom', 'rocket')
    architecture: str = ""

    # Whether targeting RV32 (vs RV64)
    is_rv32: bool = False

    # ==========================================================================
    # Convenience Methods for Pre-Execution State
    # ==========================================================================

    def get_xpr(self, idx: int) -> int:
        """
        Get integer register value from pre-execution state.

        Args:
            idx: Register index (0-31)

        Returns:
            Register value (0 if index out of range)
        """
        if 0 <= idx < 32:
            return self.s_pre.xpr[idx]
        return 0

    def get_fpr(self, idx: int) -> int:
        """
        Get floating-point register value from pre-execution state.

        Args:
            idx: Register index (0-31)

        Returns:
            Register value as uint64 (0 if index out of range)
        """
        if 0 <= idx < 32:
            return self.s_pre.fpr[idx]
        return 0

    def get_csr(self, addr: int) -> int:
        """
        Get CSR value from pre-execution state.

        Args:
            addr: CSR address (e.g., 0x300 for mstatus)

        Returns:
            CSR value (0 if not found)
        """
        return self.s_pre.csrs.get(addr, 0)

    def get_pc(self) -> int:
        """Get program counter from pre-execution state."""
        return self.s_pre.pc

    def get_privilege(self) -> int:
        """Get current privilege level (0=U, 1=S, 3=M)."""
        return self.s_pre.privilege

    def has_reservation(self) -> bool:
        """Check if load reservation is valid (for LR/SC)."""
        return self.s_pre.reservation_valid

    def get_reservation_addr(self) -> int:
        """Get load reservation address."""
        return self.s_pre.reservation_addr

    # ==========================================================================
    # Convenience Methods for Post-Execution State
    # ==========================================================================

    def get_post_xpr(self, idx: int) -> int:
        """
        Get integer register value from post-execution state.

        Args:
            idx: Register index (0-31)

        Returns:
            Register value (0 if index out of range or s_post is None)
        """
        if self.s_post is not None and 0 <= idx < 32:
            return self.s_post.xpr[idx]
        return 0

    def get_post_fpr(self, idx: int) -> int:
        """Get floating-point register value from post-execution state."""
        if self.s_post is not None and 0 <= idx < 32:
            return self.s_post.fpr[idx]
        return 0

    def get_post_csr(self, addr: int) -> int:
        """Get CSR value from post-execution state."""
        if self.s_post is not None:
            return self.s_post.csrs.get(addr, 0)
        return 0

    def did_privilege_change(self) -> bool:
        """Check if privilege level changed during execution."""
        return self.s_post.privilege_changed if self.s_post else False

    def did_virtualization_change(self) -> bool:
        """Check if virtualization mode changed during execution."""
        return self.s_post.virtualization_changed if self.s_post else False

    def was_trapped(self) -> bool:
        """Check if instruction caused a trap/exception."""
        return self.s_post.trap_occurred if self.s_post else False

    def get_trap_cause(self) -> int:
        """Get trap cause code (0 if no trap)."""
        return self.s_post.trap_cause if self.s_post else 0

    def get_trap_name(self) -> str:
        """Get human-readable trap name."""
        return self.s_post.trap_name if self.s_post else ""

    def get_reg_writes(self) -> List[tuple]:
        """
        Get list of register writes from commit log.

        Returns:
            List of (reg_num, value) tuples
            reg_num: 0-31 for XPR, 32-63 for FPR, >=4096 for CSR
        """
        return self.s_post.reg_writes if self.s_post else []

    def get_mem_writes(self) -> List[tuple]:
        """
        Get list of memory writes from commit log.

        Returns:
            List of (addr, value, size) tuples
        """
        return self.s_post.mem_writes if self.s_post else []

    def get_mem_reads(self) -> List[tuple]:
        """
        Get list of memory reads from commit log.

        Returns:
            List of (addr, value, size) tuples
        """
        return self.s_post.mem_reads if self.s_post else []

    # ==========================================================================
    # Operand Parsing Helpers
    # ==========================================================================

    def parse_register_operand(self, operand: str) -> Optional[int]:
        """
        Parse a register operand string to index.

        Args:
            operand: Register string (e.g., "x1", "a0", "ra", "f0")

        Returns:
            Register index (0-31) or None if not a register

        Examples:
            "x1" -> 1
            "a0" -> 10
            "ra" -> 1
            "f0" -> 0 (FPR, use FPR_OFFSET + 0 for unified indexing)
        """
        # ABI names mapping
        abi_map = {
            "zero": 0,
            "ra": 1,
            "sp": 2,
            "gp": 3,
            "tp": 4,
            "t0": 5,
            "t1": 6,
            "t2": 7,
            "s0": 8,
            "fp": 8,
            "s1": 9,
            "a0": 10,
            "a1": 11,
            "a2": 12,
            "a3": 13,
            "a4": 14,
            "a5": 15,
            "a6": 16,
            "a7": 17,
            "s2": 18,
            "s3": 19,
            "s4": 20,
            "s5": 21,
            "s6": 22,
            "s7": 23,
            "s8": 24,
            "s9": 25,
            "s10": 26,
            "s11": 27,
            "t3": 28,
            "t4": 29,
            "t5": 30,
            "t6": 31,
        }

        operand = operand.strip().rstrip(",").lower()

        # Check ABI name
        if operand in abi_map:
            return abi_map[operand]

        # Check xN format
        if operand.startswith("x") and operand[1:].isdigit():
            idx = int(operand[1:])
            if 0 <= idx <= 31:
                return idx

        # Check fN format (floating-point)
        if operand.startswith("f") and operand[1:].isdigit():
            idx = int(operand[1:])
            if 0 <= idx <= 31:
                return idx  # Caller should add FPR_OFFSET if needed

        return None

    def get_source_registers(self) -> List[int]:
        """
        Get indices of source registers from operands.

        Returns:
            List of register indices (typically rs1, rs2 for R-type)
        """
        # This is a simplified implementation
        # Real implementation would need to parse instruction format
        src_regs = []
        for i, op in enumerate(self.operands):
            # Skip first operand for most instructions (destination)
            if i == 0:
                continue
            idx = self.parse_register_operand(op)
            if idx is not None:
                src_regs.append(idx)
        return src_regs

    def get_destination_register(self) -> Optional[int]:
        """
        Get index of destination register from operands.

        Returns:
            Register index or None
        """
        if self.operands:
            return self.parse_register_operand(self.operands[0])
        return None
