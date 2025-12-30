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
Bloom Filter based XOR Cache

Provides efficient XOR uniqueness checking for multi-process instruction generation
using shared memory Bloom filter with O(1) check and configurable false positive rate.

Usage:
    # Create cache with dynamic sizing (recommended)
    cache = XORCache.create_for_workload(num_seeds=10, instrs_per_seed=1000)
    cache.create()

    # Or create with explicit size
    cache = XORCache(size_mb=1.0)
    cache.create()

    # In each worker process
    cache.attach()
    if cache.check_and_add(opcode, xor_value):
        # XOR is unique, proceed
        pass
    else:
        # Duplicate, retry
        pass
"""

import hashlib
import math
import os
from multiprocessing import shared_memory
from typing import Optional


def compute_xor(values: list) -> int:
    """
    Compute XOR value from register values using shifted XOR.

    Each value is shifted by its index position before XOR-ing.
    This ensures different orderings produce different results:
        [A, B] -> A ^ (B << 1)
        [B, A] -> B ^ (A << 1)  (different result)
    """
    result = 0
    for i, value in enumerate(values):
        result ^= (value << i)
    return result


class XORCache:
    """
    Shared memory Bloom filter for fast XOR uniqueness checking across processes.

    A Bloom filter is a space-efficient probabilistic data structure that tests
    whether an element is a member of a set. It may have false positives
    (saying something exists when it doesn't) but never false negatives
    (if it says something doesn't exist, it definitely doesn't).

    For our use case:
    - False positive: We reject a unique XOR value (think it's duplicate)
      → Slightly reduces diversity, but safe
    - False negative: We accept a duplicate XOR value (think it's unique)
      → Never happens with Bloom filter

    Memory is shared across processes via multiprocessing.shared_memory,
    allowing all worker processes to check/add to the same filter.
    """

    def __init__(self, size_mb: float = 1.0, num_hashes: int = 7, name: str = None):
        """
        Initialize XOR cache with explicit size.

        Args:
            size_mb: Size in MB for Bloom filter (default 1MB = 8M bits)
            num_hashes: Number of hash functions (default 7)
            name: Shared memory name (auto-generated if None)
        """
        self._size_bits = int(size_mb * 8_000_000)
        self._size_bytes = (self._size_bits + 7) // 8
        self._num_hashes = num_hashes
        self._name = name or f"xor_bloom_{os.getpid()}"

        self._shm: Optional[shared_memory.SharedMemory] = None
        self._buffer: Optional[memoryview] = None
        self._owner = False

    @classmethod
    def create_for_workload(
        cls,
        num_seeds: int,
        instrs_per_seed: int,
        false_positive_rate: float = 0.01,
        safety_factor: float = 1.5,
        name: str = None
    ) -> 'XORCache':
        """
        Create XORCache with optimal size for the given workload.

        Uses mathematical formulas to calculate optimal Bloom filter size:
        - Size (bits): m = -n * ln(p) / (ln(2))^2
        - Hash count: k = (m/n) * ln(2)

        Where n = expected elements, p = false positive rate

        Args:
            num_seeds: Number of seed files to generate
            instrs_per_seed: Instructions per seed file
            false_positive_rate: Target false positive rate (default 1%)
            safety_factor: Multiply expected elements by this (default 1.5)
            name: Shared memory name (auto-generated if None)

        Returns:
            XORCache instance with optimal sizing
        """
        expected_elements = int(num_seeds * instrs_per_seed * safety_factor)

        # Calculate optimal size: m = -n * ln(p) / (ln(2))^2
        if expected_elements <= 0:
            expected_elements = 10000
        ln2_squared = math.log(2) ** 2
        bits_needed = -expected_elements * math.log(false_positive_rate) / ln2_squared

        # Apply bounds: 64KB minimum, 16MB maximum
        min_bits = 64 * 1024 * 8      # 64 KB
        max_bits = 16 * 1024 * 1024 * 8  # 16 MB
        size_bits = max(min_bits, min(int(bits_needed), max_bits))

        # Calculate optimal hash count: k = (m/n) * ln(2)
        optimal_k = (size_bits / expected_elements) * math.log(2)
        num_hashes = max(3, min(int(optimal_k + 0.5), 10))

        # Create instance
        instance = cls.__new__(cls)
        instance._size_bits = size_bits
        instance._size_bytes = (size_bits + 7) // 8
        instance._num_hashes = num_hashes
        instance._name = name or f"xor_bloom_{os.getpid()}"
        instance._shm = None
        instance._buffer = None
        instance._owner = False

        return instance

    def create(self):
        """
        Create shared memory region (call from main process only).

        This allocates the shared memory and initializes all bits to 0.
        Worker processes should call attach() instead.
        """
        # Clean up any existing shared memory with same name
        try:
            existing = shared_memory.SharedMemory(name=self._name)
            existing.close()
            existing.unlink()
        except FileNotFoundError:
            pass

        self._shm = shared_memory.SharedMemory(
            name=self._name,
            create=True,
            size=self._size_bytes
        )
        self._buffer = memoryview(self._shm.buf)
        self._owner = True

        # Clear all bits (initialize to empty)
        for i in range(self._size_bytes):
            self._buffer[i] = 0

    def attach(self):
        """
        Attach to existing shared memory (call from worker processes).

        Workers connect to the shared memory created by the main process.
        """
        self._shm = shared_memory.SharedMemory(name=self._name)
        self._buffer = memoryview(self._shm.buf)
        self._owner = False

    def _hash_positions(self, opcode: str, value: int) -> list:
        """
        Compute k bit positions for a (opcode, value) pair.

        Uses SHA256 with different salts to generate independent hash functions.
        Each hash maps to a position in the bit array.

        Args:
            opcode: Instruction opcode (e.g., "add", "sub")
            value: XOR value to hash

        Returns:
            List of k bit positions
        """
        positions = []
        key = f"{opcode}:{value}".encode()

        for i in range(self._num_hashes):
            # SHA256 with salt for different hash functions
            h = hashlib.sha256(key + i.to_bytes(1, 'little')).digest()
            # Use first 8 bytes as position, mod by filter size
            pos = int.from_bytes(h[:8], 'little') % self._size_bits
            positions.append(pos)

        return positions

    def _check(self, opcode: str, value: int) -> bool:
        """
        Check if value might exist in the filter.

        Returns True if ALL k bits are set (possibly exists).
        Returns False if ANY bit is 0 (definitely doesn't exist).
        """
        for pos in self._hash_positions(opcode, value):
            byte_idx = pos // 8
            bit_idx = pos % 8
            if not (self._buffer[byte_idx] & (1 << bit_idx)):
                return False  # At least one bit is 0 -> definitely not in set
        return True  # All bits set -> possibly in set

    def _add(self, opcode: str, value: int):
        """Set all k bits for the given value."""
        for pos in self._hash_positions(opcode, value):
            byte_idx = pos // 8
            bit_idx = pos % 8
            self._buffer[byte_idx] |= (1 << bit_idx)

    def check_and_add(self, opcode: str, xor_value: int) -> bool:
        """
        Check if XOR is unique and add it atomically.

        Returns:
            True if value was unique (added), False if possibly duplicate
        """
        if self._buffer is None:
            return True  # Not initialized, allow everything
        if self._check(opcode, xor_value):
            return False  # Possibly exists -> duplicate
        self._add(opcode, xor_value)
        return True  # Definitely new -> unique

    def is_unique(self, opcode: str, source_values: list) -> tuple:
        """
        Check if computed XOR value is unique.

        Convenience method that computes XOR from source values.

        Args:
            opcode: Instruction opcode
            source_values: Source register values

        Returns:
            Tuple of (xor_value, is_unique)
        """
        xor_value = compute_xor(source_values)
        is_unique = self.check_and_add(opcode, xor_value)
        return xor_value, is_unique

    @property
    def name(self) -> str:
        """Get shared memory name."""
        return self._name

    @property
    def size_kb(self) -> float:
        """Get filter size in KB."""
        return self._size_bits / 8 / 1024

    @property
    def size_mb(self) -> float:
        """Get filter size in MB."""
        return self._size_bits / 8 / 1024 / 1024

    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            'size_bits': self._size_bits,
            'size_kb': self.size_kb,
            'size_mb': self.size_mb,
            'num_hashes': self._num_hashes,
            'name': self._name
        }

    def close(self):
        """Close and cleanup shared memory."""
        if self._buffer:
            self._buffer.release()
            self._buffer = None
        if self._shm:
            self._shm.close()
            if self._owner:
                try:
                    self._shm.unlink()
                except FileNotFoundError:
                    pass
            self._shm = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.close()
        return False


if __name__ == "__main__":
    print("XOR Cache Module - Bloom Filter with Dynamic Sizing")
    print("=" * 60)

    # Test dynamic sizing calculations
    print("\n[1] Dynamic Size Calculation Examples:")
    test_cases = [
        (10, 100),      # Small: 10 seeds × 100 instrs = 1,000
        (10, 1000),     # Medium: 10 seeds × 1000 instrs = 10,000
        (100, 1000),    # Large: 100 seeds × 1000 instrs = 100,000
        (1000, 1000),   # XLarge: 1000 seeds × 1000 instrs = 1,000,000
    ]

    for num_seeds, instrs_per_seed in test_cases:
        cache = XORCache.create_for_workload(num_seeds, instrs_per_seed)
        print(f"  {num_seeds:4d} seeds × {instrs_per_seed:4d} instrs → "
              f"{cache.size_kb:7.1f} KB, {cache._num_hashes} hashes")

    # Test with context manager
    print("\n[2] Testing with context manager (auto cleanup)...")
    with XORCache.create_for_workload(num_seeds=10, instrs_per_seed=1000) as cache:
        cache.create()

        stats = cache.get_stats()
        print(f"  Created cache: {stats['size_kb']:.1f} KB, {stats['num_hashes']} hashes")

        # Add some values
        for i in range(1000):
            cache.check_and_add("add", i)

        # Check duplicates
        false_count = sum(1 for i in range(1000) if not cache.check_and_add("add", i))
        print(f"  Correctly identified {false_count}/1000 as duplicates")

        # Check new values
        new_count = sum(1 for i in range(1000, 2000) if cache.check_and_add("add", i))
        print(f"  Correctly identified {new_count}/1000 as new")

    print("  Cache automatically cleaned up on exit")
    print("\nDone!")
