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



def show_progress(current, total, bar_length=50):
    fraction_completed = current / total
    arrow = int(fraction_completed * bar_length - 1) * '=' + '>'
    padding = (bar_length - len(arrow)) * ' '
    percentage = 100 * fraction_completed
    progress_bar = f"[{arrow}{padding}] {current}/{total} ({percentage:.2f}%)\n"
    print(f"\r{progress_bar}", end='')
