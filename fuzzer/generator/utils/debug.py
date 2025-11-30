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

# For debugging purposes
def write_freq_analysis_to_file(instruction_freq, output_filename):
    with open(output_filename, 'w') as file:
        for instr, count in instruction_freq.items():
            file.write(f"{instr}: {count}\n")
            
            
# For debugging purposes
def write_queue_to_file(queue, output_filename):
    with open(output_filename, 'w') as file:
        for instr in queue:
            file.write(f"{instr}\n")
