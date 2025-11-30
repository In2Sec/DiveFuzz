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


import sys
import os
import re
class Logger:
    def __init__(self, filename="program_log.txt", path="."):
        self.terminal = sys.stdout
        full_path = os.path.join(path, filename)
        print(f"Logging to: {full_path}")  # Print the full path of the log file
        try:
            self.log = open(full_path, "a")
        except Exception as e:
            self.terminal.write(f"Failed to open log file: {e}\n")
        # succ
        self.ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
    def write(self, message):
        self.terminal.write(message)
        clean_message = self.ansi_escape.sub('', message)
        self.log.write(clean_message)
        self.log.flush()  

    def flush(self):
        self.terminal.flush()
        self.log.flush()
