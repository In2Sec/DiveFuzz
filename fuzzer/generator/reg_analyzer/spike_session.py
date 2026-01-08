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
Spike Session Manager

Manages spike_engine lifecycle and provides instruction execution API.
Uses checkpoint-based rollback for efficient instruction retry without recompilation.

Simplified API (v3.0):
- execute_sequence(): Unified method for all execution scenarios
- Python layer manually reads registers before/after execution for XOR validation
"""

import sys
from pathlib import Path
from typing import Optional, List, Tuple

# Add spike_engine path
SPIKE_ENGINE_PATH = Path(__file__).parent.parent.parent.parent / "ref" / "riscv-isa-sim-adapter" / "spike_engine"
sys.path.insert(0, str(SPIKE_ENGINE_PATH))

try:
    import spike_engine
    SPIKE_ENGINE_AVAILABLE = True
except ImportError as e:
    SPIKE_ENGINE_AVAILABLE = False
    spike_engine = None
    print(f"\n[WARNING] spike_engine import failed")
    print(f"  Import error: {e}")
    print(f"  Expected path: {SPIKE_ENGINE_PATH}")
    print(f"  Path exists: {SPIKE_ENGINE_PATH.exists()}")
    print(f"  Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    if SPIKE_ENGINE_PATH.exists():
        so_files = list(SPIKE_ENGINE_PATH.glob("spike_engine*.so"))
        print(f"  Found .so files: {len(so_files)}")
        for so in so_files:
            print(f"    - {so.name}")

        if not so_files:
            print(f"  → spike_engine not built. Run: cd {SPIKE_ENGINE_PATH} && make")
        else:
            expected_name = f"spike_engine.cpython-{sys.version_info.major}{sys.version_info.minor}"
            matching = [s for s in so_files if expected_name in s.name]
            if not matching:
                print(f"  → No .so file matches current Python {sys.version_info.major}.{sys.version_info.minor}")
                print(f"    Rebuild with: cd {SPIKE_ENGINE_PATH} && make clean && make")
    else:
        print(f"  → spike_engine directory not found")
        print(f"    Initialize submodule: git submodule update --init --recursive")
    print()


class SpikeSession:
    """
    Spike session manager with checkpoint support

    Manages spike_engine lifecycle and provides instruction execution API.

    Simplified Workflow (v3.0):
    1. Initialize: Load ELF with N nops, execute template initialization
    2. For each instruction:
       - Set checkpoint (save current state)
       - Read source register values (Python: get_xpr/get_fpr)
       - Execute instruction(s) via execute_sequence()
       - Read destination register values (Python: get_xpr/get_fpr)
       - Python computes XOR and checks uniqueness
       - If valid: confirm (keep state)
       - If invalid: restore checkpoint (rollback)
    3. Cleanup: Release resources

    Performance: O(n) instead of O(n^2) for n instructions
    """

    def __init__(self, elf_path: str, isa: str, num_instrs: int):
        """
        Create Spike session

        Args:
            elf_path: Path to ELF file with N nop instructions
            isa: ISA string (e.g., "rv64imafdcv_zicsr_zifencei")
            num_instrs: Number of instructions to generate

        Raises:
            RuntimeError: If spike_engine is not available
        """
        if not SPIKE_ENGINE_AVAILABLE:
            raise RuntimeError(
                "spike_engine not available. "
                "Build it at ref/riscv-isa-sim-checkpoint/spike_engine"
            )

        self.elf_path = elf_path
        self.isa = isa
        self.num_instrs = num_instrs

        # Spike engine instance
        self.engine: Optional[spike_engine.SpikeEngine] = None

        # State tracking
        self.checkpoint_set: bool = False
        self.initialized: bool = False

    def initialize(self) -> bool:
        """
        Initialize Spike engine and execute template initialization

        This loads the ELF, runs until the first nop, and prepares for
        instruction-by-instruction execution.

        Returns:
            True on success, False on error

        Side effects:
            - Creates spike_engine instance
            - Executes template initialization code (register setup, etc.)
            - Sets initialized flag to True
        """
        try:
            # Create engine (verbose=False for silent operation)
            self.engine = spike_engine.SpikeEngine(
                self.elf_path,
                self.isa,
                self.num_instrs,
                verbose=False
            )

            # Initialize (runs template init code until first nop)
            if not self.engine.initialize():
                error_msg = self.engine.get_last_error()
                print(f"[SpikeSession] Initialization failed: {error_msg}")
                return False

            self.initialized = True
            return True

        except Exception as e:
            print(f"[SpikeSession] Exception during initialization: {e}")
            import traceback
            traceback.print_exc()
            return False

    def execute_sequence(
        self,
        machine_codes: List[int],
        sizes: List[int],
        max_steps: int = 10000
    ) -> int:
        """
        Execute a sequence of instructions

        Unified execution method that handles all cases:
        - Single instruction: execute_sequence([code], [size])
        - Forward jump: execute_sequence([jump, middle...], [sizes...])
        - Backward loop: execute_sequence([init, body..., decr, branch], [sizes...])

        Args:
            machine_codes: List of machine codes to execute
            sizes: List of instruction sizes (2 or 4 bytes each)
            max_steps: Maximum execution steps (safety limit)

        Returns:
            Number of steps executed

        Raises:
            RuntimeError: If session not initialized or execution fails
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized. Call initialize() first.")

        try:
            return self.engine.execute_sequence(machine_codes, sizes, max_steps)
        except Exception as e:
            # Debug output for execution failures
            pc = self.engine.get_pc() if self.engine else 0
            print(f"\n[SpikeSession] execute_sequence FAILED:")
            print(f"  PC: 0x{pc:x}")
            print(f"  Codes: {[f'0x{c:08x}' for c in machine_codes]}")
            print(f"  Sizes: {sizes}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def execute_single(self, machine_code: int, size: Optional[int] = None) -> int:
        """
        Execute a single instruction (convenience method)

        Args:
            machine_code: 32-bit machine code
            size: Instruction size (auto-detected if None)

        Returns:
            Number of steps executed (typically 1)
        """
        if size is None:
            size = spike_engine.SpikeEngine.get_instruction_size(machine_code)
        return self.execute_sequence([machine_code], [size])

    def set_checkpoint(self):
        """
        Set checkpoint for current state

        Call this before executing instructions that may need to be rolled back.
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")
        try:
            self.engine.set_checkpoint()
            self.checkpoint_set = True
        except Exception as e:
            pc = self.engine.get_pc() if self.engine else 0
            print(f"\n[SpikeSession] set_checkpoint FAILED:")
            print(f"  PC: 0x{pc:x}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def confirm_instruction(self):
        """
        Confirm current instruction and prepare for next.

        Clears checkpoint flag so next operation will set new checkpoint if needed.
        """
        self.checkpoint_set = False

    def restore_checkpoint_and_reset(self):
        """
        Restore checkpoint and reset checkpoint_set flag

        This method should be called when rejecting an instruction
        (e.g., due to bug filter) to ensure proper state management.

        Side effects:
            - Restores processor state to last checkpoint
            - Resets checkpoint_set flag
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")

        try:
            self.engine.restore_checkpoint()
            self.checkpoint_set = False
        except Exception as e:
            pc = self.engine.get_pc() if self.engine else 0
            print(f"\n[SpikeSession] restore_checkpoint_and_reset FAILED:")
            print(f"  PC: 0x{pc:x}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def get_current_pc(self) -> int:
        """
        Get current program counter

        Returns:
            Current PC value

        Raises:
            RuntimeError: If session not initialized
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")
        return self.engine.get_pc()

    def get_xpr(self, reg_index: int) -> int:
        """
        Get general-purpose register value

        Args:
            reg_index: Register index (0-31)

        Returns:
            Register value

        Raises:
            RuntimeError: If session not initialized
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")
        return self.engine.get_xpr(reg_index)

    def get_fpr(self, reg_index: int) -> int:
        """
        Get floating-point register value

        Args:
            reg_index: Register index (0-31)

        Returns:
            Register value (as uint64)

        Raises:
            RuntimeError: If session not initialized
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")
        return self.engine.get_fpr(reg_index)

    def get_all_xpr(self) -> List[int]:
        """
        Get all general-purpose register values

        Returns:
            List of 32 register values (x0-x31)

        Raises:
            RuntimeError: If session not initialized
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")
        return list(self.engine.get_all_xpr())

    def get_all_fpr(self) -> List[int]:
        """
        Get all floating-point register values

        Returns:
            List of 32 register values (f0-f31)

        Raises:
            RuntimeError: If session not initialized
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")
        return list(self.engine.get_all_fpr())

    def get_csr(self, csr_addr: int) -> int:
        """
        Get CSR value by address

        Args:
            csr_addr: CSR address (e.g., 0x300 for mstatus)

        Returns:
            CSR value, or 0 if not found/accessible

        Raises:
            RuntimeError: If session not initialized
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")
        return self.engine.get_csr(csr_addr)

    def get_all_csrs(self) -> dict:
        """
        Get all accessible CSR values

        Returns:
            Dict mapping CSR address to value

        Raises:
            RuntimeError: If session not initialized
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")
        return dict(self.engine.get_all_csrs())

    def get_mem_region_info(self) -> Tuple[int, int]:
        """
        Get mem_region address information for testing memory operations

        Returns:
            Tuple of (start_address, size)

        Raises:
            RuntimeError: If session not initialized
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")
        return (self.engine.get_mem_region_start(), self.engine.get_mem_region_size())

    def read_memory(self, addr: int, size: int) -> bytes:
        """
        Read memory at specified address

        Args:
            addr: Memory address to read from
            size: Number of bytes to read

        Returns:
            Bytes read from memory

        Raises:
            RuntimeError: If session not initialized
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")
        return bytes(self.engine.read_mem(addr, size))

    def get_all_registers(self) -> dict:
        """
        Get all registers (XPR, FPR, PC) as a dictionary

        Returns:
            Dict with keys 'xpr' (list of 32 values), 'fpr' (list of 32 values), 'pc' (int)

        Raises:
            RuntimeError: If session not initialized
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")
        return {
            'xpr': self.get_all_xpr(),
            'fpr': self.get_all_fpr(),
            'pc': self.get_current_pc()
        }

    def was_last_execution_trapped(self) -> bool:
        """
        Check if the last executed instruction triggered a trap/exception.

        This is useful for logging - instructions that cause traps are handled
        by the exception handler (which skips them), but they are still "accepted"
        from the fuzzer's perspective.

        Returns:
            True if the last instruction triggered a trap, False otherwise

        Raises:
            RuntimeError: If session not initialized
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")
        return self.engine.was_last_execution_trapped()

    def get_last_trap_handler_steps(self) -> int:
        """
        Get the number of trap handler steps executed in the last execution.

        Returns 0 if no trap occurred.

        Returns:
            Number of steps executed in trap handler

        Raises:
            RuntimeError: If session not initialized
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")
        return self.engine.get_last_trap_handler_steps()

    def cleanup(self):
        """
        Cleanup resources

        Should be called when session is no longer needed.
        Note: With shared cache mode, no need to save cache (already in shared memory).
        """
        self.engine = None
        self.initialized = False
        self.checkpoint_set = False

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        self.cleanup()


if __name__ == "__main__":
    print("SpikeSession module")
    print(f"Spike engine available: {SPIKE_ENGINE_AVAILABLE}")
    if SPIKE_ENGINE_AVAILABLE:
        print(f"Version: {spike_engine.__version__}")
