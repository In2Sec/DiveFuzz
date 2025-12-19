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


from . import add_bug, Registry

# This feature should be enabled manually !
def register(reg: Registry) -> None:
    pass
    # During testing, known bugs can be avoided; for example, a division by zero error can be avoided.
    # add_bug(reg, 'div',  'div by zero',      '*', '0')
    # add_bug(*, 'wfi',  'wfi is disabled')
    # add_bug(reg, 'fsqrt', 'INF', '0x7f7fffff')
