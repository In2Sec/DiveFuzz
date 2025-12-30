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
Spike Debug Logger

Provides detailed debug output for spike_session instruction execution.
Records all registers (XPR, FPR), CSRs, and execution state to a file.

Usage:
    from spike_debug_logger import SpikeDebugLogger

    logger = SpikeDebugLogger("debug_output.log")
    logger.log_instruction_state(spike_session, instruction, is_before=True)
    # ... execute instruction ...
    logger.log_instruction_state(spike_session, instruction, is_before=False)
    logger.close()
"""

from typing import Optional, List, Dict, Tuple, TYPE_CHECKING
from pathlib import Path
import time
from datetime import datetime

if TYPE_CHECKING:
    from .spike_session import SpikeSession


# CSR name mapping (common CSRs)
CSR_NAMES = {
    # User-level CSRs
    0x001: "fflags",
    0x002: "frm",
    0x003: "fcsr",
    0x008: "vstart",
    0x009: "vxsat",
    0x00a: "vxrm",
    0x00f: "vcsr",
    0xc00: "cycle",
    0xc01: "time",
    0xc02: "instret",
    0xc20: "vl",
    0xc21: "vtype",
    0xc22: "vlenb",

    # Supervisor-level CSRs
    0x100: "sstatus",
    0x104: "sie",
    0x105: "stvec",
    0x106: "scounteren",
    0x10a: "senvcfg",
    0x140: "sscratch",
    0x141: "sepc",
    0x142: "scause",
    0x143: "stval",
    0x144: "sip",
    0x180: "satp",

    # Machine-level CSRs
    0x300: "mstatus",
    0x301: "misa",
    0x302: "medeleg",
    0x303: "mideleg",
    0x304: "mie",
    0x305: "mtvec",
    0x306: "mcounteren",
    0x310: "mstatush",
    0x340: "mscratch",
    0x341: "mepc",
    0x342: "mcause",
    0x343: "mtval",
    0x344: "mip",
    0x34a: "mtinst",
    0x34b: "mtval2",
    0x30a: "menvcfg",
    0x31a: "menvcfgh",

    # Machine Information Registers
    0xf11: "mvendorid",
    0xf12: "marchid",
    0xf13: "mimpid",
    0xf14: "mhartid",
    0xf15: "mconfigptr",

    # Performance counters
    0xb00: "mcycle",
    0xb02: "minstret",
    0xb03: "mhpmcounter3",
    0x323: "mhpmevent3",
}

# CSR groups for organized display
CSR_GROUPS = {
    'M-Mode': [0x300, 0x301, 0x302, 0x303, 0x304, 0x305, 0x306, 0x340, 0x341, 0x342, 0x343, 0x344],
    'S-Mode': [0x100, 0x104, 0x105, 0x140, 0x141, 0x142, 0x143, 0x144, 0x180],
    'Float': [0x001, 0x002, 0x003],
    'Vector': [0x008, 0x009, 0x00a, 0x00f, 0xc20, 0xc21, 0xc22],
}

# Key CSRs to always show in FULL mode (most commonly used)
KEY_CSRS = [0x300, 0x301, 0x305, 0x341, 0x342, 0x343, 0x003, 0xc20, 0xc21]

# XPR register names (ABI names)
XPR_NAMES = [
    "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
    "s0/fp", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
    "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
    "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6"
]

# FPR register names (ABI names)
FPR_NAMES = [
    "ft0", "ft1", "ft2", "ft3", "ft4", "ft5", "ft6", "ft7",
    "fs0", "fs1", "fa0", "fa1", "fa2", "fa3", "fa4", "fa5",
    "fa6", "fa7", "fs2", "fs3", "fs4", "fs5", "fs6", "fs7",
    "fs8", "fs9", "fs10", "fs11", "ft8", "ft9", "ft10", "ft11"
]


class SpikeDebugLogger:
    """
    Debug logger for Spike session instruction execution

    Records comprehensive state information including:
    - All 32 general-purpose registers (x0-x31)
    - All 32 floating-point registers (f0-f31)
    - Program counter (PC)
    - All accessible CSRs
    - Execution status (ACCEPTED/REJECTED/EXCEPTION)

    Output Modes:
    - FULL: Log all state before and after each instruction
    - DIFF: Log only changed registers/CSRs
    - SUMMARY: Log only instruction result and key registers
    """

    def __init__(
        self,
        filepath: str,
        mode: str = "FULL",
        log_csr: bool = True,
        log_fpr: bool = True,
        accepted_only: bool = False
    ):
        """
        Initialize debug logger

        Args:
            filepath: Path to output file
            mode: Output mode ("FULL", "DIFF", "SUMMARY")
            log_csr: Whether to log CSR values
            log_fpr: Whether to log FPR values
            accepted_only: If True, only log ACCEPTED instructions
        """
        self.filepath = Path(filepath)
        self.mode = mode.upper()
        self.log_csr = log_csr
        self.log_fpr = log_fpr
        self.accepted_only = accepted_only

        # State tracking
        self.instr_counter = 0
        self.last_xpr: Optional[List[int]] = None
        self.last_fpr: Optional[List[int]] = None
        self.last_csrs: Optional[Dict[int, int]] = None
        self.last_pc: Optional[int] = None

        # Pre-execution state (for DIFF mode)
        self.pre_xpr: Optional[List[int]] = None
        self.pre_fpr: Optional[List[int]] = None
        self.pre_csrs: Optional[Dict[int, int]] = None
        self.pre_pc: Optional[int] = None

        # Ensure parent directory exists
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        # Open file and write header
        self.file = open(filepath, 'w')
        self._write_header()

    def _write_header(self):
        """Write file header"""
        self.file.write("=" * 80 + "\n")
        self.file.write("  SPIKE DEBUG LOG\n")
        self.file.write(f"  Generated: {datetime.now().isoformat()}\n")
        self.file.write(f"  Mode: {self.mode}\n")
        self.file.write(f"  Log CSR: {self.log_csr}, Log FPR: {self.log_fpr}\n")
        self.file.write(f"  Filter: {'ACCEPTED only' if self.accepted_only else 'ALL'}\n")
        self.file.write("=" * 80 + "\n\n")

    def _format_xpr(self, xpr: List[int], changed_indices: Optional[List[int]] = None) -> str:
        """Format XPR registers"""
        lines = []
        for i in range(0, 32, 4):
            row = []
            for j in range(4):
                idx = i + j
                val = xpr[idx]
                name = f"x{idx:2d}/{XPR_NAMES[idx]:5s}"
                marker = "*" if (changed_indices and idx in changed_indices) else " "
                row.append(f"{marker}{name}: 0x{val:016x}")
            lines.append("  " + "  ".join(row))
        return "\n".join(lines)

    def _format_fpr(self, fpr: List[int], changed_indices: Optional[List[int]] = None) -> str:
        """Format FPR registers"""
        lines = []
        for i in range(0, 32, 4):
            row = []
            for j in range(4):
                idx = i + j
                val = fpr[idx]
                name = f"f{idx:2d}/{FPR_NAMES[idx]:5s}"
                marker = "*" if (changed_indices and idx in changed_indices) else " "
                row.append(f"{marker}{name}: 0x{val:016x}")
            lines.append("  " + "  ".join(row))
        return "\n".join(lines)

    def _format_csrs(self, csrs: Dict[int, int], changed_addrs: Optional[List[int]] = None) -> str:
        """Format CSR values in table format (similar to XPR/FPR)"""
        lines = []

        # Format CSRs by group, 3 per row (CSR names are longer than register names)
        for group_name, group_addrs in CSR_GROUPS.items():
            # Filter to only CSRs that exist in the dict
            valid_addrs = [addr for addr in group_addrs if addr in csrs]
            if not valid_addrs:
                continue

            lines.append(f"  [{group_name}]")
            for i in range(0, len(valid_addrs), 3):
                row = []
                for j in range(3):
                    if i + j < len(valid_addrs):
                        addr = valid_addrs[i + j]
                        val = csrs[addr]
                        name = CSR_NAMES.get(addr, f"0x{addr:03x}")
                        marker = "*" if (changed_addrs and addr in changed_addrs) else " "
                        row.append(f"{marker}{name:10s}: 0x{val:016x}")
                lines.append("  " + "  ".join(row))

        # Show other CSRs not in groups (if any non-zero)
        grouped_addrs = set()
        for addrs in CSR_GROUPS.values():
            grouped_addrs.update(addrs)

        other_addrs = [addr for addr in sorted(csrs.keys())
                       if addr not in grouped_addrs and csrs[addr] != 0]

        if other_addrs:
            lines.append("  [Other]")
            for i in range(0, len(other_addrs), 3):
                row = []
                for j in range(3):
                    if i + j < len(other_addrs):
                        addr = other_addrs[i + j]
                        val = csrs[addr]
                        name = CSR_NAMES.get(addr, f"0x{addr:03x}")
                        marker = "*" if (changed_addrs and addr in changed_addrs) else " "
                        row.append(f"{marker}{name:10s}: 0x{val:016x}")
                lines.append("  " + "  ".join(row))

        return "\n".join(lines) if lines else "  (no CSRs)"

    def _get_changed_indices(
        self,
        old_list: Optional[List[int]],
        new_list: List[int]
    ) -> List[int]:
        """Get indices where values changed"""
        if old_list is None:
            return []
        return [i for i in range(len(new_list)) if old_list[i] != new_list[i]]

    def _get_changed_csrs(
        self,
        old_csrs: Optional[Dict[int, int]],
        new_csrs: Dict[int, int]
    ) -> List[int]:
        """Get CSR addresses where values changed"""
        if old_csrs is None:
            return []
        changed = []
        for addr, val in new_csrs.items():
            if addr not in old_csrs or old_csrs[addr] != val:
                changed.append(addr)
        return changed

    def capture_pre_state(self, spike_session: 'SpikeSession'):
        """
        Capture state before instruction execution (for DIFF mode)

        Args:
            spike_session: Active SpikeSession instance
        """
        self.pre_xpr = spike_session.get_all_xpr()
        self.pre_pc = spike_session.get_current_pc()

        if self.log_fpr:
            self.pre_fpr = spike_session.get_all_fpr()

        if self.log_csr:
            self.pre_csrs = spike_session.get_all_csrs()

    def log_instruction(
        self,
        spike_session: 'SpikeSession',
        instruction: str,
        machine_codes: List[Tuple[int, int]],
        is_accepted: bool,
        source_regs: Optional[List[int]] = None,
        source_values: Optional[List[int]] = None,
        dest_regs: Optional[List[int]] = None,
        dest_values: Optional[List[int]] = None,
        xor_value: Optional[int] = None,
        reject_reason: Optional[str] = None,
        was_trapped: bool = False,
        trap_handler_steps: int = 0
    ):
        """
        Log instruction execution result with full state

        Args:
            spike_session: Active SpikeSession instance
            instruction: Assembly instruction string
            machine_codes: List of (machine_code, size) tuples
            is_accepted: Whether instruction was accepted
            source_regs: Source register indices (optional)
            source_values: Source register values (optional)
            dest_regs: Destination register indices (optional)
            dest_values: Destination register values (optional)
            xor_value: Computed XOR value (optional)
            reject_reason: Reason for rejection (optional)
            was_trapped: Whether the instruction triggered a trap/exception (optional)
            trap_handler_steps: Number of steps executed in trap handler (optional)
        """
        # Skip REJECTED if accepted_only mode
        if self.accepted_only and not is_accepted:
            return

        self.instr_counter += 1

        # Get current state
        curr_xpr = spike_session.get_all_xpr()
        curr_pc = spike_session.get_current_pc()
        curr_fpr = spike_session.get_all_fpr() if self.log_fpr else None
        curr_csrs = spike_session.get_all_csrs() if self.log_csr else None

        # Calculate changes (value-based detection)
        xpr_changed = self._get_changed_indices(self.pre_xpr, curr_xpr)
        fpr_changed = self._get_changed_indices(self.pre_fpr, curr_fpr) if curr_fpr else []
        csr_changed = self._get_changed_csrs(self.pre_csrs, curr_csrs) if curr_csrs else []

        # IMPORTANT: Also mark destination registers as "changed" even if value unchanged
        # This ensures the log matches spike --log-commits which records all writebacks
        # Register convention: 0-31 = XPR, 32-63 = FPR
        if dest_regs:
            for reg_idx in dest_regs:
                if reg_idx < 32:
                    # XPR register
                    if reg_idx not in xpr_changed and reg_idx != 0:  # x0 never changes
                        xpr_changed.append(reg_idx)
                else:
                    # FPR register (index - 32)
                    fpr_idx = reg_idx - 32
                    if fpr_idx not in fpr_changed:
                        fpr_changed.append(fpr_idx)

        # Write log entry
        f = self.file

        # Header with trap status
        status = "ACCEPTED" if is_accepted else "REJECTED"
        trap_suffix = ""
        if was_trapped:
            trap_suffix = f" [TRAPPED: {trap_handler_steps} steps]"
        f.write("-" * 80 + "\n")
        f.write(f"[#{self.instr_counter:06d}] [{status}]{trap_suffix} {instruction}\n")
        f.write("-" * 80 + "\n")

        # Machine code info
        if len(machine_codes) == 1:
            mc, sz = machine_codes[0]
            f.write(f"  Machine Code: 0x{mc:08x} (size={sz})\n")
        else:
            f.write(f"  Machine Code (expanded to {len(machine_codes)} instructions):\n")
            for i, (mc, sz) in enumerate(machine_codes):
                f.write(f"    [{i}] 0x{mc:08x} (size={sz})\n")

        # PC info
        if self.pre_pc is not None:
            f.write(f"  PC: 0x{self.pre_pc:016x} -> 0x{curr_pc:016x}\n")
        else:
            f.write(f"  PC: 0x{curr_pc:016x}\n")

        # Source/Dest registers (from validator)
        if source_regs and source_values:
            src_info = ", ".join([f"r{r}=0x{v:x}" for r, v in zip(source_regs, source_values)])
            f.write(f"  Source: [{src_info}]\n")

        if dest_regs and dest_values:
            dst_info = ", ".join([f"r{r}=0x{v:x}" for r, v in zip(dest_regs, dest_values)])
            f.write(f"  Dest:   [{dst_info}]\n")

        if xor_value is not None:
            f.write(f"  XOR Value: 0x{xor_value:016x}\n")

        if reject_reason:
            f.write(f"  Reject Reason: {reject_reason}\n")

        f.write("\n")

        # Full state based on mode
        if self.mode == "FULL":
            self._write_full_state(f, curr_xpr, curr_fpr, curr_csrs, xpr_changed, fpr_changed, csr_changed)
        elif self.mode == "DIFF":
            self._write_diff_state(f, curr_xpr, curr_fpr, curr_csrs, xpr_changed, fpr_changed, csr_changed)
        elif self.mode == "SUMMARY":
            self._write_summary_state(f, curr_xpr, xpr_changed)

        f.write("\n")
        f.flush()

        # Update last state
        self.last_xpr = curr_xpr
        self.last_fpr = curr_fpr
        self.last_csrs = curr_csrs
        self.last_pc = curr_pc

    def _write_full_state(
        self,
        f,
        xpr: List[int],
        fpr: Optional[List[int]],
        csrs: Optional[Dict[int, int]],
        xpr_changed: List[int],
        fpr_changed: List[int],
        csr_changed: List[int]
    ):
        """Write full state (FULL mode)"""
        f.write("  [Integer Registers (XPR)] (* = changed)\n")
        f.write(self._format_xpr(xpr, xpr_changed) + "\n\n")

        if fpr is not None:
            f.write("  [Floating-Point Registers (FPR)] (* = changed)\n")
            f.write(self._format_fpr(fpr, fpr_changed) + "\n\n")

        if csrs is not None:
            f.write("  [Control and Status Registers (CSR)] (* = changed)\n")
            f.write(self._format_csrs(csrs, csr_changed) + "\n")

    def _write_diff_state(
        self,
        f,
        xpr: List[int],
        fpr: Optional[List[int]],
        csrs: Optional[Dict[int, int]],
        xpr_changed: List[int],
        fpr_changed: List[int],
        csr_changed: List[int]
    ):
        """Write only changed state (DIFF mode) - compact format"""
        has_changes = False

        if xpr_changed:
            has_changes = True
            changes = []
            for idx in xpr_changed:
                old_val = self.pre_xpr[idx] if self.pre_xpr else 0
                new_val = xpr[idx]
                name = XPR_NAMES[idx]
                changes.append(f"{name}: {old_val:x}->{new_val:x}")
            f.write(f"  XPR: {', '.join(changes)}\n")

        if fpr_changed and fpr is not None:
            has_changes = True
            changes = []
            for idx in fpr_changed:
                old_val = self.pre_fpr[idx] if self.pre_fpr else 0
                new_val = fpr[idx]
                name = FPR_NAMES[idx]
                changes.append(f"{name}: {old_val:x}->{new_val:x}")
            f.write(f"  FPR: {', '.join(changes)}\n")

        if csr_changed and csrs is not None:
            has_changes = True
            changes = []
            for addr in csr_changed:
                old_val = self.pre_csrs.get(addr, 0) if self.pre_csrs else 0
                new_val = csrs[addr]
                name = CSR_NAMES.get(addr, f"0x{addr:03x}")
                changes.append(f"{name}: {old_val:x}->{new_val:x}")
            f.write(f"  CSR: {', '.join(changes)}\n")

        if not has_changes:
            f.write("  (no changes)\n")

    def _write_summary_state(self, f, xpr: List[int], xpr_changed: List[int]):
        """Write summary state (SUMMARY mode)"""
        # Only show key registers and changed ones
        key_regs = [0, 1, 2, 8, 10, 11]  # zero, ra, sp, s0, a0, a1
        show_regs = set(key_regs) | set(xpr_changed)

        f.write("  [Key Registers]\n")
        for idx in sorted(show_regs):
            name = f"x{idx}/{XPR_NAMES[idx]}"
            marker = "*" if idx in xpr_changed else " "
            f.write(f"  {marker}{name:12s}: 0x{xpr[idx]:016x}\n")

    def log_exception(self, instruction: str, exception: Exception):
        """Log exception during instruction execution"""
        self.instr_counter += 1

        f = self.file
        f.write("-" * 80 + "\n")
        f.write(f"[#{self.instr_counter:06d}] [EXCEPTION] {instruction}\n")
        f.write("-" * 80 + "\n")
        f.write(f"  Exception: {type(exception).__name__}: {exception}\n")
        f.write("\n")
        f.flush()

    def log_custom(self, message: str):
        """Log a custom message"""
        self.file.write(f"[INFO] {message}\n")
        self.file.flush()

    def get_stats(self) -> Dict[str, int]:
        """Get logging statistics"""
        return {
            "total_instructions": self.instr_counter,
        }

    def close(self):
        """Close the log file"""
        if self.file:
            self.file.write("\n" + "=" * 80 + "\n")
            self.file.write(f"  END OF LOG - Total instructions: {self.instr_counter}\n")
            self.file.write("=" * 80 + "\n")
            self.file.close()
            self.file = None

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Convenience function for quick debugging
def create_debug_session(
    output_path: str = "spike_debug.log",
    mode: str = "DIFF"
) -> SpikeDebugLogger:
    """
    Create a debug logger with common defaults

    Args:
        output_path: Path to output file
        mode: "FULL", "DIFF", or "SUMMARY"

    Returns:
        SpikeDebugLogger instance
    """
    return SpikeDebugLogger(
        filepath=output_path,
        mode=mode,
        log_csr=True,
        log_fpr=True,
        accepted_only=False
    )


if __name__ == "__main__":
    print("SpikeDebugLogger module")
    print("Usage:")
    print("  from spike_debug_logger import SpikeDebugLogger")
    print("  logger = SpikeDebugLogger('debug.log', mode='DIFF')")
    print("  logger.capture_pre_state(spike_session)")
    print("  # ... execute instruction ...")
    print("  logger.log_instruction(spike_session, instruction, ...)")
    print("  logger.close()")
