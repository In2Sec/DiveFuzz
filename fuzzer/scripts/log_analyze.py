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


# This script is used to analyze the logs of a specific CPU version.
import sys
import os
def remove_lines_and_count(input_file, output_file):

    prefixes = ['[>', 'This', '	But','Timeout','[=']
  
    patterns = ['spec issue 2', 'spec issue 1', 'spec issue 3',\
                        'spec issue 4', 'spec issue 6',\
                        'PASSED','Bug','Timeout',\
  
                        'Strange',\
 
                        'known_bug_1','known_bug_2','known_bug_3','known_bug_4','known_bug_5']
    pattern_counts = {pattern: 0 for pattern in patterns}
    following_word_counts = {}

    with open(input_file, 'r') as file:
        lines = file.readlines()


    for i in range(len(lines)):
 
        for pattern in patterns:
            if pattern in lines[i]:
                pattern_counts[pattern] += 1
       
        if lines[i].strip().startswith('Bug'):
            if i+1 < len(lines): 
                following_line = lines[i+1].strip()
                if following_line:  
                    first_word = following_line.split()[0]
                    if first_word not in following_word_counts:
                        following_word_counts[first_word] = 0
                    following_word_counts[first_word] += 1
    
    filtered_lines = [line for line in lines \
            if not any(line.startswith(prefix) \
            for prefix in prefixes) and line.strip()]
    
    with open(output_file, 'w') as file:
        file.writelines(filtered_lines)
       
        file.write("\n--- Pattern Counts in the Entire File ---\n")
        for pattern, count in pattern_counts.items():
            file.write(f"\t'{pattern}' count: {count}\n")
        
        file.write("\n--- First Word Counts Following 'Bug' Lines ---\n")
        for word, count in following_word_counts.items():
            file.write(f"\t'{word}' count: {count}\n")
