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
StatefulXORCache - Context-aware XOR deduplicator

Extends XORCache with execution context awareness to prevent hash collisions
caused by XOR's commutativity when different contexts produce same XOR values.

Design:
    - Bloom Filter: Inherited from XORCache
    - Context extraction: Query SpikeSession for relevant state
    - Structured combination: (operand_hash << 32) | context_hash using OR
    - Backward compatible: Falls back to XORCache behavior when context not needed
"""

from enum import Enum
from typing import List, Tuple, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .spike_session import SpikeSession

from .xor_cache import (
    XORCache,
    _fnv1a_hash,
    _MASK_64,
)
from ..asm_template_manager.riscv_asm_syntex.csr import CSR

_CONTEXT_WEIGHTS = {
    "frm": 0x9E3779B97F4A7C15,
    "vl": 0x517CC1B727220A95,
    "vsew": 0xBF58476D1CE4E5B9,
    "vflmul": 0x94D049BB133111EB,
    "vta": 0xC4CEB9FE1A85EC53,
    "vma": 0x87C37B91114253D5,
    "vill": 0x4CF5AD432745937F,
    "res_valid": 0x2B7B1516EAE0C1C3,
    "res_addr": 0xBB40E64E2C5B3C7D,
    "prv": 0x9B6DB7C1A3D4E5F7,
    "v": 0x4A7C8B2D1E3F5A6C,
}

_FRM_CSR_ADDR = CSR.FRM


class InstructionContext(Enum):
    GENERAL = 0
    FLOAT = 1
    VECTOR = 2
    ATOMIC_SC = 3
    CSR = 4
    SYSTEM = 5
    MEMORY = 6


_CATEGORY_TO_CONTEXT = {
    "FLOAT": InstructionContext.FLOAT,
    "FLOAT_LOAD": InstructionContext.FLOAT,
    "FLOAT_STORE": InstructionContext.FLOAT,
    "FLOAT_MOVE": InstructionContext.FLOAT,
    "FLOAT_COMPARE": InstructionContext.FLOAT,
    "FLOAT_CONVERT": InstructionContext.FLOAT,
    "FLOAT_ARITH": InstructionContext.FLOAT,
    "VECTOR": InstructionContext.VECTOR,
    "VECTOR_LOAD": InstructionContext.VECTOR,
    "VECTOR_STORE": InstructionContext.VECTOR,
    "VECTOR_ARITH": InstructionContext.VECTOR,
    "VECTOR_LOGIC": InstructionContext.VECTOR,
    "VECTOR_SHIFT": InstructionContext.VECTOR,
    "VECTOR_MOVE": InstructionContext.VECTOR,
    "AMO_STORE": InstructionContext.ATOMIC_SC,
    "CSR": InstructionContext.CSR,
    "CSR_READ": InstructionContext.CSR,
    "CSR_WRITE": InstructionContext.CSR,
    "CSR_SWAP": InstructionContext.CSR,
    "CSR_SET": InstructionContext.CSR,
    "CSR_CLEAR": InstructionContext.CSR,
    "SYSTEM": InstructionContext.SYSTEM,
    "TRAP": InstructionContext.SYSTEM,
    "INTERRUPT": InstructionContext.SYSTEM,
    "SFENCE": InstructionContext.SYSTEM,
    "LOAD": InstructionContext.MEMORY,
    "STORE": InstructionContext.MEMORY,
    "LOAD_FP": InstructionContext.MEMORY,
    "STORE_FP": InstructionContext.MEMORY,
    "LOAD_SP": InstructionContext.MEMORY,
    "STORE_SP": InstructionContext.MEMORY,
    "PREFETCH": InstructionContext.MEMORY,
}


def extract_float_context(spike_session: "SpikeSession") -> List[Tuple[str, int]]:
    frm = spike_session.get_csr(_FRM_CSR_ADDR)
    return [("frm", frm & 0x7)]


def extract_vector_context(spike_session: "SpikeSession") -> List[Tuple[str, int]]:
    if not spike_session.is_vector_enabled():
        return []
    vs = spike_session.get_vector_state(include_regfile=False)
    context = []
    context.append(("vl", vs.vl & 0xFFFFFFFF))
    context.append(("vsew", vs.vsew & 0x7))
    vflmul_encoded = _encode_vflmul(vs.vflmul)
    context.append(("vflmul", vflmul_encoded))
    context.append(("vta", vs.vta & 0x1))
    context.append(("vma", vs.vma & 0x1))
    context.append(("vill", vs.vill & 0x1))
    return context


def _encode_vflmul(vflmul: float) -> int:
    vflmul_map = {
        0.125: 0,
        0.25: 1,
        0.5: 2,
        1.0: 3,
        2.0: 4,
        4.0: 5,
        8.0: 6,
    }
    return vflmul_map.get(vflmul, 7)


def extract_atomic_context(spike_session: "SpikeSession") -> List[Tuple[str, int]]:
    res = spike_session.get_reservation_state()
    context = []
    context.append(("res_valid", 1 if res.valid else 0))
    context.append(("res_addr", res.address & 0xFFF))
    return context


def extract_privilege_context(spike_session: "SpikeSession") -> List[Tuple[str, int]]:
    priv = spike_session.get_privilege_state()
    context = []
    context.append(("prv", priv.prv & 0x3))
    context.append(("v", 1 if priv.v else 0))
    return context


def extract_memory_context(spike_session: "SpikeSession") -> List[Tuple[str, int]]:
    return extract_privilege_context(spike_session)


def extract_context(
    context_type: InstructionContext, spike_session: "SpikeSession"
) -> List[Tuple[str, int]]:
    if context_type == InstructionContext.FLOAT:
        return extract_float_context(spike_session)
    elif context_type == InstructionContext.VECTOR:
        return extract_vector_context(spike_session)
    elif context_type == InstructionContext.ATOMIC_SC:
        return extract_atomic_context(spike_session)
    elif context_type == InstructionContext.CSR:
        return extract_privilege_context(spike_session)
    elif context_type == InstructionContext.SYSTEM:
        return extract_privilege_context(spike_session)
    elif context_type == InstructionContext.MEMORY:
        return extract_memory_context(spike_session)
    else:
        return []


def compute_context_hash(context_fields: List[Tuple[str, int]]) -> int:
    if not context_fields:
        return 0
    result = 0
    for field_name, value in context_fields:
        weight = _CONTEXT_WEIGHTS.get(field_name, _fnv1a_hash(field_name))
        name_hash = _fnv1a_hash(field_name)
        field_contribution = ((name_hash ^ value) * weight) & _MASK_64
        result ^= field_contribution
    return result


_opcode_context_cache: Dict[str, InstructionContext] = {}


def get_instruction_context(opcode: str) -> InstructionContext:
    global _opcode_context_cache
    if opcode in _opcode_context_cache:
        return _opcode_context_cache[opcode]
    try:
        from ..instr_generator import get_instruction_format

        fmt = get_instruction_format(opcode)
        if fmt:
            categories = fmt.get("category", [])
            if isinstance(categories, str):
                categories = [categories]
            for cat in categories:
                if cat in _CATEGORY_TO_CONTEXT:
                    ctx = _CATEGORY_TO_CONTEXT[cat]
                    _opcode_context_cache[opcode] = ctx
                    return ctx
    except Exception:
        pass
    ctx = InstructionContext.GENERAL
    _opcode_context_cache[opcode] = ctx
    return ctx


class StatefulXORCache(XORCache):
    def __init__(
        self, size_mb: float = 1.0, num_hashes: int = 7, name: Optional[str] = None
    ):
        super().__init__(size_mb=size_mb, num_hashes=num_hashes, name=name)

    @classmethod
    def create_for_workload(
        cls,
        num_seeds: int,
        instrs_per_seed: int,
        false_positive_rate: float = 0.001,
        safety_factor: float = 1.5,
        name: Optional[str] = None,
    ) -> "StatefulXORCache":
        instance = super().create_for_workload(
            num_seeds=num_seeds,
            instrs_per_seed=instrs_per_seed,
            false_positive_rate=false_positive_rate,
            safety_factor=safety_factor,
            name=name,
        )
        instance.__class__ = cls
        return instance  # type: ignore[return-value]

    def extract_context_for_instruction(
        self, opcode: str, spike_session: "SpikeSession"
    ) -> List[Tuple[str, int]]:
        ctx = get_instruction_context(opcode)
        return extract_context(ctx, spike_session)

    def compute_combined_hash(self, xor_value: int, context_hash: int) -> int:
        return ((xor_value & 0xFFFFFFFF) << 32) | (context_hash & 0xFFFFFFFF)

    def check_and_add_stateful(
        self,
        opcode: str,
        xor_value: int,
        spike_session: "SpikeSession",
        context_type: Optional[InstructionContext] = None,
    ) -> bool:
        if context_type is None:
            context_type = get_instruction_context(opcode)
        context_fields = extract_context(context_type, spike_session)
        context_hash = compute_context_hash(context_fields)
        combined_value = self.compute_combined_hash(xor_value, context_hash)
        return self.check_and_add(opcode, combined_value)

    def get_state_for_worker(self) -> Dict[str, Any]:
        state = super().get_state_for_worker()
        state["is_stateful"] = True
        return state

    @classmethod
    def from_worker_state(cls, state: Dict[str, Any]) -> "StatefulXORCache":
        instance = super().from_worker_state(state)
        instance.__class__ = cls
        return instance  # type: ignore[return-value]


def create_stateful_cache_for_workload(
    num_seeds: int,
    instrs_per_seed: int,
    false_positive_rate: float = 0.001,
    safety_factor: float = 1.5,
    name: Optional[str] = None,
) -> StatefulXORCache:
    cache = StatefulXORCache.create_for_workload(
        num_seeds=num_seeds,
        instrs_per_seed=instrs_per_seed,
        false_positive_rate=false_positive_rate,
        safety_factor=safety_factor,
        name=name,
    )
    cache.create()
    return cache
