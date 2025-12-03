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
Label Manager for Jump and Branch Instruction Generation

This module manages label generation and tracking for jump/branch instructions
in the DiveFuzz RISC-V assembly generator. It ensures:
1. Unique label names (fwd_0, fwd_1, loop_0, loop_1, etc.)
2. Prevention of nested jump generation
3. Tracking of jump sequence progress
"""

import random
from typing import Optional, Dict, Literal


class LabelManager:
    """
    Manages labels and jump generation state for RISC-V assembly generation.

    Supports three types of jumps:
    - Forward jumps: Jump over a small number of instructions (fwd_N labels)
    - Backward jumps: Loops that jump back to earlier labels (loop_N labels)
    - Indirect jumps: Register-based jumps (jalr, c.jr, c.jalr)
    """

    def __init__(self):
        """Initialize the label manager."""
        self.forward_label_counter = 0
        self.loop_label_counter = 0

        # Active jump state: None or dict with jump info
        self.active_jump: Optional[Dict] = None

    def generate_forward_label(self) -> str:
        """
        Generate a unique forward jump label.

        Returns:
            str: Label name like "fwd_0", "fwd_1", etc.
        """
        label = f"fwd_{self.forward_label_counter}"
        self.forward_label_counter += 1
        return label

    def generate_loop_label(self) -> str:
        """
        Generate a unique loop/backward jump label.

        Returns:
            str: Label name like "loop_0", "loop_1", etc.
        """
        label = f"loop_{self.loop_label_counter}"
        self.loop_label_counter += 1
        return label

    def generate_backward_label(self) -> str:
        """
        Generate a unique backward jump label.

        Returns:
            str: Label name like "bwd_0", "bwd_1", etc.
        """
        label = f"bwd_{self.loop_label_counter}"
        self.loop_label_counter += 1
        return label

    def is_jump_active(self) -> bool:
        """
        Check if a jump sequence is currently being generated.

        Returns:
            bool: True if a jump sequence is active, False otherwise.
        """
        return self.active_jump is not None

    def start_jump_sequence(
        self,
        jump_type: Literal['forward', 'backward'],
        label: str,
        target_distance: int,
        instruction: str = "",
        loop_counter_reg: Optional[str] = None
    ):
        """
        Start a new jump generation sequence.

        Args:
            jump_type: Type of jump ('forward', 'backward')
            label: The label name for this jump
            target_distance: Number of instructions between jump and label
            instruction: The jump instruction itself (for reference)
            loop_counter_reg: Loop counter register name (for backward jumps with loop counting)
        """
        if self.active_jump is not None:
            raise ValueError(f"Cannot start new jump sequence - already active: {self.active_jump}")

        self.active_jump = {
            'type': jump_type,
            'label': label,
            'target_distance': target_distance,
            'current_distance': 0,
            'instruction': instruction,
            'loop_counter_reg': loop_counter_reg
        }

    def end_jump_sequence(self):
        """End the current jump generation sequence."""
        if self.active_jump is None:
            raise ValueError("Cannot end jump sequence - no active jump")

        self.active_jump = None

    def get_active_jump_info(self) -> Optional[Dict]:
        """
        Get information about the currently active jump sequence.

        Returns:
            dict or None: Jump information dict or None if no jump is active.
        """
        return self.active_jump

    def get_current_label(self) -> Optional[str]:
        """
        Get the label of the currently active jump.

        For backward jumps, returns None (label is already inserted in entire_instrs).
        For forward jumps, returns the label name (to be appended during Spike verification).

        Returns:
            str or None: The active jump's label, or None for backward jumps.

        Raises:
            ValueError: If no jump is currently active.
        """
        if self.active_jump is None:
            return None

        # For backward jumps, label is already inserted, return None for Spike verification
        if self.active_jump['type'] == 'backward':
            return None

        return self.active_jump['label']

    def increment_distance(self):
        """Increment the current distance counter for the active jump."""
        if self.active_jump is None:
            raise ValueError("No active jump sequence")

        self.active_jump['current_distance'] += 1

    def get_current_distance(self) -> int:
        """
        Get the current distance (number of instructions inserted so far).

        Returns:
            int: Current distance.
        """
        if self.active_jump is None:
            raise ValueError("No active jump sequence")

        return self.active_jump['current_distance']

    def get_target_distance(self) -> int:
        """
        Get the target distance for the active jump.

        Returns:
            int: Target distance.
        """
        if self.active_jump is None:
            raise ValueError("No active jump sequence")

        return self.active_jump['target_distance']

    def should_finalize_jump(self) -> bool:
        """
        Check if the current jump sequence should be finalized.

        Returns:
            bool: True if current_distance >= target_distance.
        """
        if self.active_jump is None:
            return False

        return self.active_jump['current_distance'] >= self.active_jump['target_distance']

    def get_jump_type(self) -> Optional[str]:
        """
        Get the type of the currently active jump.

        Returns:
            str or None: 'forward', 'backward', 'indirect', or None.
        """
        if self.active_jump is None:
            raise ValueError("No active jump sequence")

        return self.active_jump['type']

    def get_jump_instruction(self) -> str:
        """
        Get the jump instruction saved in the active jump sequence.

        Returns:
            str or None: The jump instruction string, or None if no jump is active.
        """
        if self.active_jump is None:
            raise ValueError("No active jump sequence")

        return self.active_jump['instruction']

    def get_loop_counter_reg(self) -> str:
        """
        Get the loop counter register name for the active jump sequence.

        Returns:
            str or None: The loop counter register name, or None if no jump is active
                        or no loop counter is used.
        """
        if self.active_jump is None:
            raise ValueError("No active jump sequence")

        return self.active_jump['loop_counter_reg']
