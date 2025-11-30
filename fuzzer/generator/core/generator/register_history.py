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

class RegisterHistory:
    def __init__(self, capacity=6):
        self.history = []
        self.capacity = capacity

    def use_register(self, register):
        if register in self.history:
            # If the register already exists in the history, remove the old record
            self.history.remove(register)
        if len(self.history) >= self.capacity:
            # If the capacity limit is reached, remove the farthest register record (the right end of the queue)
            self.history.pop()
        # Add the newly used register to the left end of the list
        self.history.insert(0, register)

    def get_history(self):
        return self.history
