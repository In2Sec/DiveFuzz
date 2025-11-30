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

def check_xor_and_execute(variable_content):
    for i, line in enumerate(variable_content):
        if 'different' in line:
            first_different_index = i
            break
    # Extract the right and wrong values from the variable content
    right_value = int(variable_content[first_different_index].split("right= ")[1].\
                                        split(",")[0], 16)
    wrong_value = int(variable_content[first_different_index].split("wrong = ")\
                                        [1], 16)
    # print(variable_content[first_different_index], '11111111')
    return right_value ^ wrong_value
    # Checking if the XOR of right and wrong values is 1
    # if right_value ^ wrong_value == 1:
    #     # If the condition is met, execute the code here
    #     # For demonstration, I'll just print a message
    #     print("XOR of right and wrong values is 1. Executing code...")
    #     return 
    #     # Place your code here
    # else:
    #     print("XOR of right and wrong values is not 1.")

# Used to further check the 5th specification requirement of NTS
def check_diff_csr(variable_content):
    different_lines = [line for line in variable_content if "different" in line]

    # CSRs required by NTS specification 5
    required_csr = {'mode', 'mstatus', 'mtval', 'mcause'}

    # Check whether the above CSRs are included
    found_csr = set()
    for line in different_lines:
        for csr in required_csr:
            if csr in required_csr:
                found_csr.add(csr)
    
    return found_csr == required_csr
