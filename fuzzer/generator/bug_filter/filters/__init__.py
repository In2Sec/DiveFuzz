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
from typing import Dict, List, Tuple, Optional, Set

# Type: Each pattern (pattern_tuple, bug_name)
# pattern_tuple is a parameter pattern like ('1','*') (only allows '*' or numeric strings)
BugPattern = Tuple[Tuple[str, ...], str]
Registry = Dict[str, List[BugPattern]]  # instr -> patterns

# CSR blacklist: Set of CSR names to filter out
CSRBlacklist = Set[str]

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


def add_csr_blacklist(blacklist: CSRBlacklist, *csr_names: str) -> None:
    """
    Add CSR names to the blacklist.

    Args:
        blacklist: CSR blacklist set to modify
        csr_names: CSR names to add (e.g., 'hpmcounter3', 'hpmcounter15')

    Example:
        add_csr_blacklist(blacklist, 'hpmcounter3', 'hpmcounter15')
    """
    for csr in csr_names:
        blacklist.add(csr.lower())


def add_bug(registry: Registry, instr: str, bug_name: str, *arg_pattern: str) -> None:
    """
    Register a known bug to the registry.

    Args:
        instr: Instruction name, supports trailing '*' for prefix matching
               - 'sc.w' matches only 'sc.w'
               - 'sc.w*' matches 'sc.w', 'sc.w.aq', 'sc.w.rl', 'sc.w.aqrl', etc.
               - 'lr*' matches all lr variants (lr.w, lr.d, lr.w.aq, etc.)
        bug_name: Bug identifier string to return when matched
        arg_pattern: Optional source register value patterns.
                     - If not provided: matches ALL instructions with this opcode (recommended!)
                     - '*': matches any value at this position
                     - number: matches exact value (decimal or hex with 0x prefix)

    Examples:
        # Filter ALL sc instructions (recommended - no arg_pattern needed)
        add_bug(reg, 'sc*', 'lr_sc_false_positive')

        # Filter ALL lr instructions
        add_bug(reg, 'lr*', 'lr_sc_false_positive')

        # Filter div instructions only when rs2=0 (division by zero)
        add_bug(reg, 'div', 'div_by_zero', '*', '0')

        # Filter specific register value combination
        add_bug(reg, 'mv', 'mv_src_is_1', '1')
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
    Match source register values against a pattern.

    Matching rules:
      - Empty pattern (): matches ANY args (unconditional match)
      - '*': matches any value at this position
      - number: must equal exactly (decimal or 0x hex)

    Args:
        args: List of source register values from the instruction
        pattern: Tuple of pattern strings ('*' or numeric)

    Returns:
        True if pattern matches, False otherwise

    Examples:
        _match_args([10, 20], ())           -> True  (empty = match all)
        _match_args([10, 20], ('*', '*'))   -> True
        _match_args([10, 0], ('*', '0'))    -> True  (rs2 == 0)
        _match_args([10, 5], ('*', '0'))    -> False (rs2 != 0)
        _match_args([10], ('*', '*'))       -> False (not enough args)
    """
    # Empty pattern matches everything (unconditional filter)
    if not pattern:
        return True

    # Pattern requires at least len(pattern) source values
    if len(args) < len(pattern):
        return False

    for i, pat in enumerate(pattern):
        if pat == '*':
            continue
        # Use int(pat, 0) to auto-detect base (supports 0x prefix for hex)
        if args[i] != int(pat, 0):
            return False
    return True


def _match_instr(instr_op: str, pattern_instr: str) -> bool:
    """
    Match instruction name with support for trailing wildcard.
    - 'sc.w' matches only 'sc.w'
    - 'sc.w*' matches 'sc.w', 'sc.w.aq', 'sc.w.rl', 'sc.w.aqrl', etc.
    """
    if pattern_instr.endswith('*'):
        # Wildcard matching: check if instr_op starts with the prefix
        prefix = pattern_instr[:-1]  # Remove trailing '*'
        return instr_op.startswith(prefix)
    else:
        # Exact matching
        return instr_op == pattern_instr


def match_bug(registry: Registry, instr_op: str, register_values: List[int]) -> Optional[str]:
    """
    Match an instruction line in the given registry:
      - First tries exact match on instruction name
      - Then tries wildcard match (patterns ending with '*')
      - If hits a (instr, parameter pattern), return its bug_name
      - Otherwise return None
    """
    # First, try exact match
    patterns = registry.get(instr_op)
    if patterns:
        for pattern, bug_name in patterns:
            if _match_args(register_values, pattern):
                return bug_name

    # Then, try wildcard match (iterate through all patterns)
    for pattern_instr, pattern_list in registry.items():
        if pattern_instr.endswith('*'):
            if _match_instr(instr_op, pattern_instr):
                for pattern, bug_name in pattern_list:
                    if _match_args(register_values, pattern):
                        return bug_name

    return None


# ---------- Build and expose known_bugs for each architecture ----------
def _build_registry() -> Registry:
    """Create an empty instruction -> bug pattern table."""
    return defaultdict(list)


def _build_csr_blacklist() -> CSRBlacklist:
    """Create an empty CSR blacklist set."""
    return set()


def _build_xs_bugs() -> Tuple[Registry, CSRBlacklist]:
    reg = _build_registry()
    csr_bl = _build_csr_blacklist()
    from . import filters_xs
    filters_xs.register(reg)
    if hasattr(filters_xs, 'register_csr_blacklist'):
        filters_xs.register_csr_blacklist(csr_bl)
    return reg, csr_bl


def _build_nts_bugs() -> Tuple[Registry, CSRBlacklist]:
    reg = _build_registry()
    csr_bl = _build_csr_blacklist()
    from . import filters_nts
    filters_nts.register(reg)
    if hasattr(filters_nts, 'register_csr_blacklist'):
        filters_nts.register_csr_blacklist(csr_bl)
    return reg, csr_bl


def _build_cva6_bugs() -> Tuple[Registry, CSRBlacklist]:
    """Build CVA6-specific bug patterns and CSR blacklist."""
    reg = _build_registry()
    csr_bl = _build_csr_blacklist()
    from . import filters_cva6
    filters_cva6.register(reg)
    if hasattr(filters_cva6, 'register_csr_blacklist'):
        filters_cva6.register_csr_blacklist(csr_bl)
    return reg, csr_bl


def _build_boom_bugs() -> Tuple[Registry, CSRBlacklist]:
    """Build BOOM-specific bug patterns and CSR blacklist."""
    reg = _build_registry()
    csr_bl = _build_csr_blacklist()
    from . import filters_boom
    filters_boom.register(reg)
    if hasattr(filters_boom, 'register_csr_blacklist'):
        filters_boom.register_csr_blacklist(csr_bl)
    return reg, csr_bl


def get_known_bugs(architecture: str) -> Tuple[Registry, CSRBlacklist]:
    """
    Return known bug patterns and CSR blacklist for the corresponding architecture.

    Args:
        architecture: str, supports 'xs', 'nts', 'rkt', 'kmh', 'cva6', 'boom'

    Returns:
        Tuple of (Registry, CSRBlacklist):
        - Registry: instruction -> bug pattern table
        - CSRBlacklist: set of CSR names to filter out
    """
    if architecture == 'xs':
        return _build_xs_bugs()
    elif architecture == 'nts':
        return _build_nts_bugs()
    elif architecture == 'cva6':
        return _build_cva6_bugs()
    elif architecture == 'boom':
        return _build_boom_bugs()
    else:
        raise ValueError(f"Unknown architecture: {architecture}")
