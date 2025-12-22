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

Note: XOR computation and bug filtering have been moved to InstructionPostProcessor
for better separation of concerns.
"""

import sys
import os
from pathlib import Path
from typing import Optional, List, Tuple

# Add spike_engine path
SPIKE_ENGINE_PATH = Path(__file__).parent.parent.parent.parent / "ref" / "riscv-isa-sim-adapter" / "spike_engine"
sys.path.insert(0, str(SPIKE_ENGINE_PATH))

try:
    import spike_engine
    SPIKE_ENGINE_AVAILABLE = True
    IMMEDIATE_NOT_PRESENT = spike_engine.IMMEDIATE_NOT_PRESENT
except ImportError as e:
    SPIKE_ENGINE_AVAILABLE = False
    spike_engine = None
    IMMEDIATE_NOT_PRESENT = -(2**63)  # Fallback value
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

    Workflow:
    1. Initialize: Load ELF with N nops, execute template initialization
    2. For each instruction:
       - Set checkpoint (save current state)
       - Execute instruction and get register values
       - External: compute XOR, check uniqueness, check bugs (InstructionPostProcessor)
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
            # print(f"[SpikeSession] Initialized successfully")
            # print(f"  ELF: {self.elf_path}")
            # print(f"  ISA: {self.isa}")
            # print(f"  Num instrs: {self.num_instrs}")
            # print(f"  Initial PC: {hex(self.engine.get_pc())}")

            return True

        except Exception as e:
            print(f"[SpikeSession] Exception during initialization: {e}")
            import traceback
            traceback.print_exc()
            return False

    def execute_instruction(
        self,
        machine_code: int,
        source_regs: List[int],
        dest_regs: List[int],
        immediate: int = IMMEDIATE_NOT_PRESENT
    ) -> Tuple[List[int], List[int]]:
        """
        Execute an instruction and return register values.

        This method:
        1. Sets checkpoint if not already set
        2. Executes instruction with spike_engine
        3. Returns (source_values, dest_values)

        Note: XOR computation and uniqueness checking are handled by
        InstructionPostProcessor.

        Args:
            machine_code: 32-bit machine code
            source_regs: List of source register indices (read before execution)
            dest_regs: List of destination register indices (read after execution)
            immediate: Immediate value (default: 0)

        Returns:
            Tuple of (source_values, dest_values):
            - source_values: Source register values before execution
            - dest_values: Destination register values after execution

        Raises:
            RuntimeError: If session not initialized or execution fails
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized. Call initialize() first.")

        try:
            # Set checkpoint if not already set
            # (First instruction or after confirm_instruction)
            if not self.checkpoint_set:
                self.engine.set_checkpoint()
                self.checkpoint_set = True

            # Execute instruction and get execution result
            execution_result = self.engine.execute_instruction(
                machine_code,
                source_regs,
                dest_regs,
                immediate
            )

            # Extract values from execution result
            source_values = list(execution_result.source_values_before)
            dest_values = list(execution_result.dest_values_after)

            return source_values, dest_values

        except Exception as e:
            # Print detailed exception information
            import traceback
            print(f"[SpikeSession] Exception in execute_instruction:")
            print(f"  Exception type: {type(e).__name__}")
            print(f"  Exception message: {str(e)}")
            print(f"  Machine code: 0x{machine_code:08x}")
            print(f"  Source regs: {source_regs}")
            print(f"  Dest regs: {dest_regs}")
            print(f"  Immediate: {immediate}")
            traceback.print_exc()
            # Try to restore checkpoint on error
            try:
                if self.checkpoint_set:
                    self.engine.restore_checkpoint()
            except:
                pass
            raise

    def confirm_instruction(self):
        """
        Confirm current instruction and prepare for next.

        Clears checkpoint flag so next execute_instruction will set new checkpoint.
        """
        self.checkpoint_set = False

    def restore_checkpoint_and_reset(self):
        """
        Restore checkpoint and reset checkpoint_set flag

        This method should be called when rejecting an instruction
        (e.g., due to bug filter) to ensure proper state management.

        Side effects:
            - Restores processor state to last checkpoint
            - Resets checkpoint_set flag so next try_instruction will set new checkpoint
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized")

        self.engine.restore_checkpoint()
        self.checkpoint_set = False

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

    def execute_jump_sequence(
        self,
        machine_codes: List[int],
        sizes: List[int]
    ) -> int:
        """
        Execute a jump sequence (forward jump with middle instructions)

        This method executes a pre-compiled sequence of instructions without
        XOR validation. Used for jump sequences where labels have been
        resolved to offsets.

        Args:
            machine_codes: List of machine codes to execute
            sizes: List of instruction sizes (2 or 4 bytes)

        Returns:
            Number of instructions executed

        Raises:
            RuntimeError: If session not initialized or execution fails
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized. Call initialize() first.")

        try:
            # Clear checkpoint since we're executing a sequence
            self.checkpoint_set = False

            # Execute the sequence
            executed = self.engine.execute_instruction_sequence(machine_codes, sizes)

            return executed

        except Exception as e:
            import traceback
            print(f"[SpikeSession] Exception in execute_jump_sequence:")
            print(f"  Exception: {e}")
            traceback.print_exc()
            raise

    def execute_loop_sequence(
        self,
        init_code: int,
        init_size: int,
        loop_body_codes: List[int],
        loop_body_sizes: List[int],
        decr_code: int,
        decr_size: int,
        branch_code: int,
        branch_size: int,
        max_iterations: int = 100
    ) -> int:
        """
        Execute a backward loop sequence

        Executes: init + (loop_body + decr + branch)* until branch falls through.
        No XOR validation is performed.

        Args:
            init_code: Initialization instruction code (e.g., li s11, 5)
            init_size: Size of init instruction
            loop_body_codes: List of loop body instruction codes
            loop_body_sizes: List of loop body instruction sizes
            decr_code: Decrement instruction code (e.g., addi s11, s11, -1)
            decr_size: Size of decrement instruction
            branch_code: Branch instruction code (e.g., bne s11, zero, offset)
            branch_size: Size of branch instruction
            max_iterations: Maximum iterations (safety limit)

        Returns:
            Actual number of iterations executed

        Raises:
            RuntimeError: If session not initialized or execution fails
        """
        if not self.initialized:
            raise RuntimeError("Session not initialized. Call initialize() first.")

        try:
            # Clear checkpoint since we're executing a sequence
            self.checkpoint_set = False

            # Execute the loop
            iterations = self.engine.execute_loop_sequence(
                init_code, init_size,
                loop_body_codes, loop_body_sizes,
                decr_code, decr_size,
                branch_code, branch_size,
                max_iterations
            )

            return iterations

        except Exception as e:
            import traceback
            print(f"[SpikeSession] Exception in execute_loop_sequence:")
            print(f"  Exception: {e}")
            traceback.print_exc()
            raise

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
