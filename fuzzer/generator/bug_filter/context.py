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

"""
Filter Context Module

Provides execution context for precision filters, including pre/post execution states,
instruction information, and convenient access to SpikeSession state query APIs.

Based on RISyn paper's three-level filtering conditions:
- Level 1: φ(s_pre, opcode, operand) - Pre-execution conditions
- Level 2: φ(s_pre, s_post) - State transition conditions
- Level 3: φ(s_pre, opcode, operand, s_post) - Complete four-tuple conditions
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from ..reg_analyzer.register_mapping import XPR_ABI_TO_NUM

if TYPE_CHECKING:
    from ..reg_analyzer.spike_session import SpikeSession


class _LazyPreState:
    __slots__ = (
        "_ss",
        "_xpr",
        "_xpr_loaded",
        "_fpr",
        "_fpr_loaded",
        "_pc",
        "_privilege",
        "_virtualization",
        "_priv_loaded",
        "_reservation_valid",
        "_reservation_addr",
        "_res_loaded",
        "_csrs",
        "_csr_cache",
        "_vector_state",
        "_vec_loaded",
    )

    def __init__(self, spike_session: "SpikeSession"):
        self._ss = spike_session
        self._xpr: List[Optional[int]] = []
        self._xpr_loaded: bool = False
        self._fpr: List[Optional[int]] = []
        self._fpr_loaded: bool = False
        self._pc: Optional[int] = None
        self._privilege: Optional[int] = None
        self._virtualization: Optional[bool] = None
        self._priv_loaded: bool = False
        self._reservation_valid: Optional[bool] = None
        self._reservation_addr: Optional[int] = None
        self._res_loaded: bool = False
        self._csrs: Optional[Dict[int, int]] = None
        self._csr_cache: Dict[int, int] = {}
        self._vector_state: Any = None
        self._vec_loaded: bool = False

    def get_xpr(self, idx: int) -> int:
        if not self._xpr_loaded:
            self._xpr = [None] * 32
            self._xpr_loaded = True
        cached = self._xpr[idx]
        if cached is None:
            val = self._ss.get_xpr(idx)
            self._xpr[idx] = val
            return val
        return cached

    def get_fpr(self, idx: int) -> int:
        if not self._fpr_loaded:
            self._fpr = [None] * 32
            self._fpr_loaded = True
        cached = self._fpr[idx]
        if cached is None:
            val = self._ss.get_fpr(idx)
            self._fpr[idx] = val
            return val
        return cached

    def get_csr(self, addr: int) -> int:
        if addr in self._csr_cache:
            return self._csr_cache[addr]
        val = self._ss.get_csr(addr)
        self._csr_cache[addr] = val
        return val

    @property
    def pc(self) -> int:
        if self._pc is None:
            self._pc = self._ss.get_current_pc()
        return self._pc

    @property
    def privilege(self) -> int:
        if not self._priv_loaded:
            ps = self._ss.get_privilege_state()
            self._privilege = ps.prv
            self._virtualization = ps.v
            self._priv_loaded = True
        return self._privilege  # type: ignore[return-value]

    @property
    def virtualization(self) -> bool:
        if not self._priv_loaded:
            ps = self._ss.get_privilege_state()
            self._privilege = ps.prv
            self._virtualization = ps.v
            self._priv_loaded = True
        return self._virtualization  # type: ignore[return-value]

    @property
    def reservation_valid(self) -> bool:
        if not self._res_loaded:
            rs = self._ss.get_reservation_state()
            self._reservation_valid = rs.valid
            self._reservation_addr = rs.address
            self._res_loaded = True
        return self._reservation_valid  # type: ignore[return-value]

    @property
    def reservation_addr(self) -> int:
        if not self._res_loaded:
            rs = self._ss.get_reservation_state()
            self._reservation_valid = rs.valid
            self._reservation_addr = rs.address
            self._res_loaded = True
        return self._reservation_addr  # type: ignore[return-value]

    @property
    def vector_state(self) -> Any:
        if not self._vec_loaded:
            if self._ss.is_vector_enabled():
                self._vector_state = self._ss.get_vector_state(include_regfile=False)
            self._vec_loaded = True
        return self._vector_state

    @property
    def csrs(self) -> Dict[int, int]:
        if self._csrs is None:
            self._csrs = dict(self._ss.get_all_csrs())
            self._csr_cache.update(self._csrs)
        return self._csrs


class _LazyPostState:
    __slots__ = (
        "_ss",
        "_xpr",
        "_xpr_loaded",
        "_fpr",
        "_fpr_loaded",
        "_pc",
        "_privilege",
        "_virtualization",
        "_privilege_changed",
        "_virtualization_changed",
        "_priv_loaded",
        "_trap_occurred",
        "_trap_cause",
        "_trap_tval",
        "_trap_name",
        "_trap_loaded",
        "_reg_writes",
        "_mem_reads",
        "_mem_writes",
        "_commit_loaded",
        "_reservation_valid",
        "_reservation_addr",
        "_res_loaded",
        "_csr_cache",
        "_csrs",
        "_vector_state",
        "_vec_loaded",
    )

    def __init__(self, spike_session: "SpikeSession"):
        self._ss = spike_session
        self._xpr: List[Optional[int]] = []
        self._xpr_loaded: bool = False
        self._fpr: List[Optional[int]] = []
        self._fpr_loaded: bool = False
        self._pc: Optional[int] = None
        self._privilege: Optional[int] = None
        self._virtualization: Optional[bool] = None
        self._privilege_changed: Optional[bool] = None
        self._virtualization_changed: Optional[bool] = None
        self._priv_loaded: bool = False
        self._trap_occurred: Optional[bool] = None
        self._trap_cause: Optional[int] = None
        self._trap_tval: Optional[int] = None
        self._trap_name: Optional[str] = None
        self._trap_loaded: bool = False
        self._reg_writes: Optional[List[tuple]] = None
        self._mem_reads: Optional[List[tuple]] = None
        self._mem_writes: Optional[List[tuple]] = None
        self._commit_loaded: bool = False
        self._reservation_valid: Optional[bool] = None
        self._reservation_addr: Optional[int] = None
        self._res_loaded: bool = False
        self._csr_cache: Dict[int, int] = {}
        self._csrs: Optional[Dict[int, int]] = None
        self._vector_state: Any = None
        self._vec_loaded: bool = False

    def get_xpr(self, idx: int) -> int:
        if not self._xpr_loaded:
            self._xpr = [None] * 32
            self._xpr_loaded = True
        cached = self._xpr[idx]
        if cached is None:
            val = self._ss.get_xpr(idx)
            self._xpr[idx] = val
            return val
        return cached

    def get_fpr(self, idx: int) -> int:
        if not self._fpr_loaded:
            self._fpr = [None] * 32
            self._fpr_loaded = True
        cached = self._fpr[idx]
        if cached is None:
            val = self._ss.get_fpr(idx)
            self._fpr[idx] = val
            return val
        return cached

    def get_csr(self, addr: int) -> int:
        if addr in self._csr_cache:
            return self._csr_cache[addr]
        val = self._ss.get_csr(addr)
        self._csr_cache[addr] = val
        return val

    def _load_trap(self):
        ti = self._ss.get_last_trap_info()
        self._trap_occurred = ti.occurred
        self._trap_cause = ti.cause
        self._trap_tval = ti.tval
        self._trap_name = ti.name if ti.name else ""
        self._trap_loaded = True

    @property
    def trap_occurred(self) -> bool:
        if not self._trap_loaded:
            self._load_trap()
        return self._trap_occurred  # type: ignore[return-value]

    @property
    def trap_cause(self) -> int:
        if not self._trap_loaded:
            self._load_trap()
        return self._trap_cause  # type: ignore[return-value]

    @property
    def trap_tval(self) -> int:
        if not self._trap_loaded:
            self._load_trap()
        return self._trap_tval  # type: ignore[return-value]

    @property
    def trap_name(self) -> str:
        if not self._trap_loaded:
            self._load_trap()
        return self._trap_name  # type: ignore[return-value]

    def _load_commit_log(self):
        cl = self._ss.get_commit_log()
        self._reg_writes = [(rw.reg_num, rw.value) for rw in cl.reg_writes]
        self._mem_reads = [(ma.addr, ma.value, ma.size) for ma in cl.mem_reads]
        self._mem_writes = [(ma.addr, ma.value, ma.size) for ma in cl.mem_writes]
        self._commit_loaded = True

    @property
    def reg_writes(self) -> List[tuple]:
        if not self._commit_loaded:
            self._load_commit_log()
        return self._reg_writes  # type: ignore[return-value]

    @property
    def mem_reads(self) -> List[tuple]:
        if not self._commit_loaded:
            self._load_commit_log()
        return self._mem_reads  # type: ignore[return-value]

    @property
    def mem_writes(self) -> List[tuple]:
        if not self._commit_loaded:
            self._load_commit_log()
        return self._mem_writes  # type: ignore[return-value]

    def _load_privilege(self):
        ps = self._ss.get_privilege_state()
        self._privilege = ps.prv
        self._virtualization = ps.v
        self._privilege_changed = ps.prv_changed
        self._virtualization_changed = ps.v_changed
        self._priv_loaded = True

    @property
    def privilege(self) -> int:
        if not self._priv_loaded:
            self._load_privilege()
        return self._privilege  # type: ignore[return-value]

    @property
    def virtualization(self) -> bool:
        if not self._priv_loaded:
            self._load_privilege()
        return self._virtualization  # type: ignore[return-value]

    @property
    def privilege_changed(self) -> bool:
        if not self._priv_loaded:
            self._load_privilege()
        return self._privilege_changed  # type: ignore[return-value]

    @property
    def virtualization_changed(self) -> bool:
        if not self._priv_loaded:
            self._load_privilege()
        return self._virtualization_changed  # type: ignore[return-value]

    @property
    def pc(self) -> int:
        if self._pc is None:
            self._pc = self._ss.get_current_pc()
        return self._pc

    def _load_reservation(self):
        rs = self._ss.get_reservation_state()
        self._reservation_valid = rs.valid
        self._reservation_addr = rs.address
        self._res_loaded = True

    @property
    def reservation_valid(self) -> bool:
        if not self._res_loaded:
            self._load_reservation()
        return self._reservation_valid  # type: ignore[return-value]

    @property
    def reservation_addr(self) -> int:
        if not self._res_loaded:
            self._load_reservation()
        return self._reservation_addr  # type: ignore[return-value]

    @property
    def csrs(self) -> Dict[int, int]:
        if self._csrs is None:
            self._csrs = dict(self._ss.get_all_csrs())
            self._csr_cache.update(self._csrs)
        return self._csrs

    @property
    def vector_state(self) -> Any:
        if not self._vec_loaded:
            if self._ss.is_vector_enabled():
                self._vector_state = self._ss.get_vector_state(include_regfile=False)
            self._vec_loaded = True
        return self._vector_state


# ---------------------------------------------------------------------------
# Backward-compatible type aliases (dataclass fields are replaced by proxies
# but external code using PreExecutionState / PostExecutionState as type hints
# still works because isinstance checks are rarely used on these objects).
# ---------------------------------------------------------------------------

PreExecutionState = _LazyPreState
PostExecutionState = _LazyPostState


@dataclass
class FilterContext:
    spike_session: Optional["SpikeSession"] = None

    opcode: str = ""
    operands: List[str] = field(default_factory=list)
    machine_code: int = 0
    instruction_size: int = 4
    assembly: str = ""

    s_pre: Optional[_LazyPreState] = None
    s_post: Optional[_LazyPostState] = None

    is_rv32: bool = False

    # ------------------------------------------------------------------
    # Pre-execution helpers — delegate to _LazyPreState for on-demand queries
    # ------------------------------------------------------------------

    def get_xpr(self, idx: int) -> int:
        if 0 <= idx < 32 and self.s_pre is not None:
            return self.s_pre.get_xpr(idx)
        return 0

    def get_fpr(self, idx: int) -> int:
        if 0 <= idx < 32 and self.s_pre is not None:
            return self.s_pre.get_fpr(idx)
        return 0

    def get_csr(self, addr: int) -> int:
        if self.s_pre is not None:
            return self.s_pre.get_csr(addr)
        return 0

    def get_pc(self) -> int:
        return self.s_pre.pc if self.s_pre is not None else 0

    def get_privilege(self) -> int:
        return self.s_pre.privilege if self.s_pre is not None else 3

    def has_reservation(self) -> bool:
        return self.s_pre.reservation_valid if self.s_pre is not None else False

    def get_reservation_addr(self) -> int:
        return self.s_pre.reservation_addr if self.s_pre is not None else 0

    # ------------------------------------------------------------------
    # Post-execution helpers — delegate to _LazyPostState for on-demand queries
    # ------------------------------------------------------------------

    def get_post_xpr(self, idx: int) -> int:
        if self.s_post is not None and 0 <= idx < 32:
            return self.s_post.get_xpr(idx)
        return 0

    def get_post_fpr(self, idx: int) -> int:
        if self.s_post is not None and 0 <= idx < 32:
            return self.s_post.get_fpr(idx)
        return 0

    def get_post_csr(self, addr: int) -> int:
        if self.s_post is not None:
            return self.s_post.get_csr(addr)
        return 0

    def did_privilege_change(self) -> bool:
        return self.s_post.privilege_changed if self.s_post else False

    def did_virtualization_change(self) -> bool:
        return self.s_post.virtualization_changed if self.s_post else False

    def was_trapped(self) -> bool:
        return self.s_post.trap_occurred if self.s_post else False

    def get_trap_cause(self) -> int:
        return self.s_post.trap_cause if self.s_post else 0

    def get_trap_name(self) -> str:
        return self.s_post.trap_name if self.s_post else ""

    def get_reg_writes(self) -> List[tuple]:
        return self.s_post.reg_writes if self.s_post else []

    def get_mem_writes(self) -> List[tuple]:
        return self.s_post.mem_writes if self.s_post else []

    def get_mem_reads(self) -> List[tuple]:
        return self.s_post.mem_reads if self.s_post else []

    # ------------------------------------------------------------------
    # Operand parsing
    # ------------------------------------------------------------------

    def parse_register_operand(self, operand: str) -> Optional[int]:
        operand = operand.strip().rstrip(",").lower()
        if operand in XPR_ABI_TO_NUM:
            return XPR_ABI_TO_NUM[operand]
        if operand.startswith("x") and operand[1:].isdigit():
            idx = int(operand[1:])
            if 0 <= idx <= 31:
                return idx
        if operand.startswith("f") and operand[1:].isdigit():
            idx = int(operand[1:])
            if 0 <= idx <= 31:
                return idx
        return None

    def get_source_registers(self) -> List[int]:
        src_regs = []
        for i, op in enumerate(self.operands):
            if i == 0:
                continue
            idx = self.parse_register_operand(op)
            if idx is not None:
                src_regs.append(idx)
        return src_regs

    def get_destination_register(self) -> Optional[int]:
        if self.operands:
            return self.parse_register_operand(self.operands[0])
        return None

    # ------------------------------------------------------------------
    # Vector helpers (lazy — trigger _LazyPreState.vector_state only when needed)
    # ------------------------------------------------------------------

    def get_vl(self) -> int:
        vs = self.s_pre.vector_state if self.s_pre is not None else None
        if vs is not None:
            return getattr(vs, "vl", 0)
        return self.s_pre.get_csr(0xC20) if self.s_pre is not None else 0

    def get_vtype(self) -> int:
        vs = self.s_pre.vector_state if self.s_pre is not None else None
        if vs is not None:
            return getattr(vs, "vtype", 0)
        return self.s_pre.get_csr(0xC21) if self.s_pre is not None else 0

    def get_vstart(self) -> int:
        vs = self.s_pre.vector_state if self.s_pre is not None else None
        if vs is not None:
            return getattr(vs, "vstart", 0)
        return self.s_pre.get_csr(0x008) if self.s_pre is not None else 0

    def get_vta(self) -> int:
        vtype = self.get_vtype()
        return (vtype >> 6) & 1 if vtype else 0

    def get_vma(self) -> int:
        vtype = self.get_vtype()
        return (vtype >> 7) & 1 if vtype else 0

    def get_vlmax(self) -> int:
        vs = self.s_pre.vector_state if self.s_pre is not None else None
        return getattr(vs, "vlmax", 0) if vs is not None else 0

    def get_vsew(self) -> int:
        vs = self.s_pre.vector_state if self.s_pre is not None else None
        return getattr(vs, "vsew", 0) if vs is not None else 0

    def get_post_vl(self) -> int:
        if self.s_post is None:
            return 0
        vs = self.s_post.vector_state
        if vs is not None:
            return getattr(vs, "vl", 0)
        return self.s_post.get_csr(0xC20)

    def get_post_vtype(self) -> int:
        if self.s_post is None:
            return 0
        vs = self.s_post.vector_state
        if vs is not None:
            return getattr(vs, "vtype", 0)
        return self.s_post.get_csr(0xC21)

    def get_post_vstart(self) -> int:
        if self.s_post is None:
            return 0
        vs = self.s_post.vector_state
        if vs is not None:
            return getattr(vs, "vstart", 0)
        return self.s_post.get_csr(0x008)
