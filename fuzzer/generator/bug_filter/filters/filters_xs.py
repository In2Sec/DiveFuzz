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


from . import add_bug, add_csr_blacklist, Registry, CSRBlacklist

# This feature should be enabled manually !
def register(reg: Registry) -> None:
    pass
    # During testing, known bugs can be avoided; for example, a division by zero error can be avoided.
    # add_bug(reg, 'div',  'div by zero',      '*', '0')
    # add_bug(*, 'wfi',  'wfi is disabled')
    # add_bug(reg, 'fsqrt', 'INF', '0x7f7fffff')


def register_csr_blacklist(blacklist: CSRBlacklist) -> None:
    """
    Register CSRs that cause false positives in differential testing.

    These CSRs have implementation-defined behavior where XiangShan and Spike
    may legitimately differ, leading to false positive bug reports.
    """
    # =========================================================================
    # Hypervisor Extension CSRs (H-extension)
    # These CSRs have WARL (Write Any, Read Legal) fields with implementation-
    # defined behavior. XiangShan and Spike may handle reserved/undefined bits
    # differently.
    # =========================================================================

    # hstatus: Hypervisor status register
    # - Contains WARL fields like VSXL, VTSR, VTW, VTVM
    # - Implementation-defined behavior for reserved bits
    add_csr_blacklist(blacklist, 'hstatus')

    # vstvec: Virtual supervisor trap vector base address
    # - MODE field (bit[1:0]) only defines values 0 and 1
    # - Reserved values (2, 3) have implementation-defined behavior
    # - Spike preserves bit[0], XiangShan clears MODE to 0
    add_csr_blacklist(blacklist, 'vstvec')

    # hgeie: Hypervisor guest external interrupt enable
    # - Implementation-defined which bits are writable
    add_csr_blacklist(blacklist, 'hgeie')

    # hvip: Hypervisor virtual interrupt pending
    # - Implementation-defined behavior for virtual interrupt bits
    add_csr_blacklist(blacklist, 'hvip')

    # =========================================================================
    # Supervisor-level CSRs with implementation-defined behavior
    # =========================================================================

    # stvec: Supervisor trap vector base address
    # - Same MODE field issue as vstvec
    # - Reserved MODE values have implementation-defined behavior
    add_csr_blacklist(blacklist, 'stvec')

    # =========================================================================
    # Sstc Extension CSRs (Supervisor Timer Compare)
    # These CSRs interact with mip.STIP in implementation-defined ways
    # regarding timing of interrupt pending bit updates.
    # =========================================================================

    # stimecmp: Supervisor timer compare register
    # - When time >= stimecmp, STIP should be set
    # - Timing of STIP update is implementation-defined
    # - XiangShan sets immediately, Spike may delay
    add_csr_blacklist(blacklist, 'stimecmp')
    add_csr_blacklist(blacklist, 'stimecmph')  # Upper 32 bits for RV32
