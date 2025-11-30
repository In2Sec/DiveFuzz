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

import os
import threading


class TempFileManager:
    """
    Manager for temporary files used during Spike simulation.

    This class handles registration and cleanup of temporary files created
    during the fuzzing process (e.g., temporary assembly files for Spike).

    Thread-safe implementation using locks for file operations.
    """

    def __init__(self):
        self._temp_files = set()
        self._lock = threading.Lock()

    def register_temp_file(self, filepath):
        """Register a temporary file for later cleanup."""
        with self._lock:
            self._temp_files.add(filepath)

    def remove_temp_file(self, filepath):
        """Remove a single temporary file."""
        with self._lock:
            try:
                os.unlink(filepath)
            except OSError:
                pass
            self._temp_files.discard(filepath)

    def remove_temp_files(self, filepaths):
        """Remove multiple temporary files."""
        with self._lock:
            for filepath in filepaths:
                try:
                    os.unlink(filepath)
                except OSError:
                    pass
                self._temp_files.discard(filepath)

    def cleanup_all_temp_files(self):
        """Clean up all registered temporary files."""
        with self._lock:
            for fp in list(self._temp_files):
                try:
                    if os.path.exists(fp):
                        os.unlink(fp)
                except OSError:
                    pass
                self._temp_files.discard(fp)


# Module-level singleton instance for temporary file management
temp_file_manager = TempFileManager()