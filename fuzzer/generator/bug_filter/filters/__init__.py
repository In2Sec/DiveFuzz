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

from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# Type: Each pattern (pattern_tuple, bug_name)
# pattern_tuple is a parameter pattern like ('1','*') (only allows '*' or numeric strings)
BugPattern = Tuple[Tuple[str, ...], str]
Registry = Dict[str, List[BugPattern]]  # instr -> patterns

def _is_number(tok: str) -> bool:
    # Allow decimal "1", "31", optionally support hexadecimal "0x1F"
    if not tok:
        return False
    base = 16 if tok.strip().startswith('0x') else 10
    try:
        int(tok.strip(), base)
        return True
    except ValueError:
        return False


def add_bug(registry: Registry, instr: str, bug_name: str, *arg_pattern: str) -> None:
    """
    Register a known bug to the registry.
    - instr: instruction name, such as 'mv', 'add'
    - bug_name: bug identifier to return
    - arg_pattern: sequence of parameter patterns, only allows '*' or numeric strings (decimal/optional hexadecimal)
      Example: add_bug(reg, 'mv', 'mv_src_is_1', '1', '*')
    """
    if not instr:
        raise ValueError("instr cannot be empty")
    if not bug_name:
        raise ValueError("bug_name cannot be empty")
    # if not arg_pattern:
    #     raise ValueError("must provide at least one parameter pattern")

    norm = []
    for p in arg_pattern:
        if p == '*':
            norm.append('*')
        elif _is_number(p):
            norm.append(p.lower())
        else:
            raise ValueError(f"parameter pattern only supports '*' or numbers: received {p!r}")
    registry[instr].append((tuple(norm), bug_name))


def _match_args(args: List[int], pattern: Tuple[str, ...]) -> bool:
    """
    Parameter matching: only supports '*' or numbers (decimal/hexadecimal strings).
    Matching strategy: requires args to cover at least the length of pattern, and at corresponding positions:
      '*'  -> any
      number -> must be exactly equal (string equality; hex统一小写以匹配)
    """
    if len(args) < len(pattern):
        return False
    for i, pat in enumerate(pattern):
        if pat == '*':
            continue
        # Use int(pat, 0) to auto-detect base (supports 0x prefix for hex)
        if args[i] != int(pat, 0):
            return False
    return True


def match_bug(registry: Registry, instr_op: str, register_values: List[int]) -> Optional[str]:
    """
    Match an instruction line in the given registry:
      - If hits a (instr, parameter pattern), return its bug_name
      - Otherwise return None
    """
    patterns = registry.get(instr_op)
    if not patterns:
        return None
    for pattern, bug_name in patterns:
        if _match_args(register_values, pattern):
            return bug_name
    return None


# ---------- Build and expose known_bugs for each architecture ----------
def _build_registry() -> Registry:
    """Create an empty instruction -> bug pattern table."""
    return defaultdict(list)

def _build_xs_bugs() -> Registry:
    reg = _build_registry()
    from . import filters_xs
    filters_xs.register(reg)
    return reg

def _build_nts_bugs() -> Registry:
    reg = _build_registry()
    from . import filters_nts
    filters_nts.register(reg)
    return reg

def get_known_bugs(architecture: str) -> Registry:
    """
    Return known bug patterns for the corresponding architecture based on the input architecture name
    architecture: str, supports 'xs', 'nts', 'rkt', 'kmh'
    """
    if architecture == 'xs':
        return _build_xs_bugs()
    elif architecture == 'nts':
        return _build_nts_bugs()
    else:
        raise ValueError(f"Unknown architecture: {architecture}")
