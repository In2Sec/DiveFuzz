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

def fliter_known_bug(input_string):
    # Define the list of substrings to check
    bug_flag = '<--'
    bug_number = 0
    bug_1 = 'c.lui'
    bug_2 = 'c.jr'
    bug_3 = 'c.addiw'
    bug_4 = 'c.addi16sp'
    bug_5 = 'c.addi4spn'
    bug_6 = 'c.ldsp'
    bug_7 = 'c.lwsp'
    bug_set = ['c.lui','c.jr', 'c.addiw', 'c.addi16sp', 'c.addi4spn' ]
    # Check if any of the substrings exist
    # for bug_n in bug_set:
    #     if bug_n in bug_set:
    #         return 1
    if bug_1 in input_string:
        folder_name = "known_bug_1"
        return 1
    elif bug_2 in input_string:
        return 2
    elif bug_3 in input_string:
        return 3
    elif bug_4 in input_string:
        return 4
    elif bug_5 in input_string:
        return 5
    elif bug_6 in input_string:
        return 6
    elif bug_7 in input_string:
        return 7
    else:
        # If none of the substrings are found
        return 0

# Example usage
# input_string = "This is a test string containing abcd and other content"
# result = check_substrings(input_string)
# print(result)
