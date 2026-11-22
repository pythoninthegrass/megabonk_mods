"""Translate Ghidra raw per-instruction pcode to textual LLVM IR.

Each lifted body becomes `define void @sub_<addr>(ptr %reg)`: the register file is a byte
array passed in, the unique (temporary) space is a local byte array, memory is the host
address space. Anything the emitter cannot translate is recorded in `holes` instead of
being skipped silently, so a clean `holes` list means every pcode op in the body lifted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from lift_tables import direct_branch_targets

INT_BINARY = {
    "INT_ADD": "add",
    "INT_SUB": "sub",
    "INT_MULT": "mul",
    "INT_AND": "and",
    "INT_OR": "or",
    "INT_XOR": "xor",
    "INT_DIV": "udiv",
    "INT_REM": "urem",
    "INT_SDIV": "sdiv",
    "INT_SREM": "srem",
    "BOOL_AND": "and",
    "BOOL_OR": "or",
    "BOOL_XOR": "xor",
}
INT_COMPARE = {
    "INT_EQUAL": "eq",
    "INT_NOTEQUAL": "ne",
    "INT_SLESS": "slt",
    "INT_SLESSEQUAL": "sle",
    "INT_LESS": "ult",
    "INT_LESSEQUAL": "ule",
}
FLOAT_BINARY = {"FLOAT_ADD": "fadd", "FLOAT_SUB": "fsub", "FLOAT_MULT": "fmul", "FLOAT_DIV": "fdiv"}
FLOAT_COMPARE = {
    "FLOAT_EQUAL": "oeq",
    "FLOAT_NOTEQUAL": "une",
    "FLOAT_LESS": "olt",
    "FLOAT_LESSEQUAL": "ole",
}
FLOAT_UNARY_INTRINSIC = {
    "FLOAT_ABS": "fabs",
    "FLOAT_SQRT": "sqrt",
    "FLOAT_CEIL": "ceil",
    "FLOAT_FLOOR": "floor",
}
OVERFLOW_INTRINSIC = {"INT_CARRY": "uadd", "INT_SCARRY": "sadd", "INT_SBORROW": "ssub"}
# Ghidra's register-space offset for rsp in the x86-64 language definition.
RSP = "register,20,8"
FLOAT_TYPES = {4: "float", 8: "double"}
# The 80-bit x87 encoding: sign at 79, exponent at 64..78, explicit integer bit at 63, fraction below it.
X87 = 10
X87_SIGN_BIT = 79
X87_INT_BIT = 1 << 63
X87_QUIET_BIT = 1 << 62
X87_FRACTION_BITS = (1 << 63) - 1
X87_MAGNITUDE_BITS = (1 << 79) - 1
X87_EXPONENT_MAX = (1 << 15) - 1
X87_BIAS = 16383
X87_PREDICATES = {"FLOAT_NAN": 1, "FLOAT_EQUAL": 2, "FLOAT_LESS": 2}
SINGLE_MANTISSA_MASK = (1 << 23) - 1
SINGLE_FRACTION_SHIFT = 63 - 23
PACKED_DIVISION = {"divps": (4, 4), "divpd": (2, 8)}
PACKED_MINMAX = {"minps": (4, 4, "olt"), "maxps": (4, 4, "ogt"), "maxpd": (2, 8, "ogt")}
PACKED_WIDTH = 16
# Register-file words the guest unwinder and lifted code share: the landing pad to enter (0 when none is pending) and the frame that owns it.
# Ghidra's load address for the ELF; the dump subtracts it from every constant it marks cptr.
IMAGE_BASE = 0x100000
EH_PENDING_PAD = 0x1F00
EH_PENDING_CFA = 0x1F08
# Ghidra's unique-space offsets are sparse; a temporary's slot is at least this wide, so it can hold a 256-bit value.
UNIQUE_STRIDE = 32
# Host-only byte blocks in %uniq, for the CALLOTHER helpers that hand back a pointer instead of a value.
HELPER_RESULT_BASE = 0x900000
CPUID_RESULT_BYTES = 16
RDRAND_RESULT_BYTES = 8


@dataclass
class Lifted:
    start: int
    ir: str
    holes: list[str] = field(default_factory=list)
    externs: set[int] = field(default_factory=set)
    decls: set[str] = field(default_factory=set)
    indirect_calls: int = 0
    data_sections: set[str] = field(default_factory=set)
    unmapped_refs: int = 0
    tail_calls: int = 0
    proven_tail_calls: int = 0
    unproven_branchind: list[dict] = field(default_factory=list)
    tables_audited: int = 0
    evidence_switches: int = 0
    atomics: int = 0


def parse_varnode(text: str) -> tuple[str, int, int]:
    space, offset, size = text.split(",")
    return space, int(offset, 16), int(size)


def const_of(text: str | None) -> int | None:
    """The value of a const varnode, or None when the operand is not a constant."""
    try:
        space, offset, _ = parse_varnode(text or "")
    except (AttributeError, ValueError):
        return None
    return offset if space == "const" else None


def branch_target(op: dict, order: list[int]) -> int | None:
    """Where a BRANCH or CBRANCH goes: an address in the dump, or None when it leaves it.

    A const operand is the signed op-index offset from within the same instruction, which is
    where the target is an op the emitter has already labelled.
    """
    space, offset, size = parse_varnode(op["in"][0])
    if space != "const":
        return offset if offset in addresses(order) else None
    modulus = 1 << (size * 8)
    index = offset - modulus if offset >= (modulus >> 1) else offset
    return order[index] if 0 <= index < len(order) else None


def addresses(order: list[int]) -> frozenset[int]:
    """The dump's instruction addresses, for the repeated membership test the walk does."""
    return frozenset(order)


def escapes_the_dump(insn: dict, order: list[int], follows: int | None) -> bool:
    """Whether control can leave the dump from this instruction by a path whose frame is unknown.

    A branch to an address the dump never emitted, and a straight-line or conditional fallthrough
    past the last instruction, both hand control somewhere the balance pass cannot read. A
    terminating `BRANCH` to an unemitted address is not such a path: the emitter lowers it to a call
    and a return, which hands control back balanced, so only a non-terminating branch to an
    unemitted address (or a fallthrough off the end) makes everything downstream untrackable.
    """
    terminates = any(op["op"] in ("BRANCH", "RETURN", "BRANCHIND") for op in insn["ops"])
    if any(branch_target(op, order) is None for op in insn["ops"] if op["op"] == "CBRANCH"):
        return True
    return not terminates and follows is None


def successors(insn: dict, order: list[int], follows: int | None) -> list[int]:
    """The addresses control can reach inside the dump from one instruction.

    A BRANCH, RETURN or BRANCHIND is a terminator and contributes only the address its target names
    (a BRANCHIND names none: where it goes is not in the body). A CBRANCH that is not a terminator
    also falls through to the next instruction, as does any straight-line instruction.
    """
    out: list[int] = []
    terminator = False
    for op in insn["ops"]:
        if op["op"] not in ("BRANCH", "CBRANCH"):
            continue
        target = branch_target(op, order)
        if target is not None:
            out.append(target)
        if op["op"] == "BRANCH":
            terminator = True
    if any(op["op"] in ("RETURN", "BRANCHIND") for op in insn["ops"]):
        terminator = True
    if not terminator and follows is not None:
        out.append(follows)
    return out


def rsp_effect(insn: dict) -> int | None:
    """The net rsp change of one instruction: adds and subs of a constant, plus the 8 a CALL or CALLIND pushes.

    None means the frame cannot be balanced by counting, because rsp is written some other way
    (a POP, `leave`, a copy from a register or a temporary, an add or sub by a computed value).
    """
    delta = 0
    for op in insn["ops"]:
        if op.get("out") != RSP:
            if op["op"] in ("CALL", "CALLIND"):
                delta += 8
            continue
        operands = op.get("in") or []
        amount = const_of(operands[1]) if len(operands) > 1 else None
        if op["op"] in ("INT_SUB", "INT_ADD") and len(operands) > 1 and operands[0] == RSP and amount is not None:
            delta += -amount if op["op"] == "INT_SUB" else amount
        else:
            return None
    return delta


MISSING = object()
PROVEN = {"reason": "", "rsp_delta": 0}


def join(state: dict[int, int | None], target: int, value: int | None, todo: list[int]) -> bool:
    """Merges one path's rsp balance into `state[target]`; returns True when the merge changed it."""
    seen = state.get(target, MISSING)
    if seen is MISSING:
        state[target] = value
        todo.append(target)
        return True
    if seen != value:
        state[target] = None
        todo.append(target)
        return True
    return False


def rsp_verdict(balance: object) -> dict:
    """Why a site is or is not liftable as an indirect call followed by a return."""
    if balance is MISSING:
        return {"reason": "no path in the dump reaches the site", "rsp_delta": None}
    if balance is None:
        return {"reason": "rsp untrackable on a path into the site", "rsp_delta": None}
    return PROVEN if not balance else {"reason": "rsp not at entry value", "rsp_delta": balance}


def site_frame(fn: dict) -> dict[int, dict]:
    """Per BRANCHIND address, whether a frame-safe tail call can be read off the body, conservatively.

    `unknown_balanced` says the pass cannot prove the site off-entry: no path in the dump reaches it,
    or every path into it leaves rsp trackable and free of an intervening call. That is the shape the
    old straight-line load rule lifted, and the refinement keeps lifting it. A CALL or an untrackable
    rsp write on a path to the site is not unknown: it is a frame the pass can see and cannot balance.
    """
    order = sorted(insn["a"] for insn in fn["insns"])
    if not order:
        return {}
    by_addr = {insn["a"]: insn for insn in fn["insns"]}
    follows = {addr: nxt for addr, nxt in zip(order, order[1:])}
    state: dict[int, int | None] = {order[0]: 0}
    called: dict[int, bool] = {order[0]: False}
    todo = [order[0]]
    while todo:
        addr = todo.pop()
        insn = by_addr[addr]
        effect, balance = rsp_effect(insn), state[addr]
        reached = None if effect is None or balance is None else balance + effect
        call_on_path = called.get(addr, False) or any(op["op"] == "CALL" for op in insn["ops"])
        if escapes_the_dump(insn, order, follows.get(addr)):
            reached = None
        for target in successors(insn, order, follows.get(addr)):
            if join(state, target, reached, todo):
                called[target] = call_on_path
    verdicts = {}
    for insn in fn["insns"]:
        if not any(op["op"] == "BRANCHIND" for op in insn["ops"]):
            continue
        balance = state.get(insn["a"], MISSING)
        verdicts[insn["a"]] = {
            "reason": rsp_verdict(balance)["reason"],
            "rsp_delta": rsp_verdict(balance)["rsp_delta"],
            "unknown_balanced": balance is MISSING or (balance is not None and not called.get(insn["a"], False)),
        }
    return verdicts


def site_proof(fn: dict) -> dict[int, dict]:
    """Per BRANCHIND address, whether rsp is proven equal to its entry value on every path into it.

    The lattice is balanced, off by a constant, or untrackable (None). A branch whose target is not
    in the dump makes everything downstream of it untrackable: the emitter turns that branch into a
    call and a return, so it balances only because of the shape the emitter gives it, which is not
    something read off the body.
    """
    order = sorted(insn["a"] for insn in fn["insns"])
    if not order:
        return {}
    by_addr = {insn["a"]: insn for insn in fn["insns"]}
    follows = {addr: nxt for addr, nxt in zip(order, order[1:])}
    state: dict[int, int | None] = {order[0]: 0}
    todo = [order[0]]
    while todo:
        addr = todo.pop()
        insn = by_addr[addr]
        effect, balance = rsp_effect(insn), state[addr]
        reached = None if effect is None or balance is None else balance + effect
        if escapes_the_dump(insn, order, follows.get(addr)):
            reached = None
        for target in successors(insn, order, follows.get(addr)):
            join(state, target, reached, todo)
    return {
        insn["a"]: rsp_verdict(state.get(insn["a"], MISSING))
        for insn in fn["insns"]
        if any(op["op"] == "BRANCHIND" for op in insn["ops"])
    }


RAX = "register,0,8"


def overlaps(varnode: str | None, other: str) -> bool:
    """Whether two register or memory varnodes share a byte."""
    if not varnode:
        return False
    space, offset, size = parse_varnode(varnode)
    other_space, other_offset, other_size = parse_varnode(other)
    return space == other_space and offset < other_offset + other_size and other_offset < offset + size


def rax_after(origin: tuple, ops: list[dict]) -> tuple:
    """What rax holds after these ops: a fixed word's value, a call's result (stored or not), or other.

    A CALL leaves the callee's result in rax. Storing rax whole into a fixed word while it holds a
    call result records where that result now lives, so a later read of the word returns the same value.
    """
    kind, slot = origin
    for op in ops:
        out, inputs = op.get("out"), op.get("in") or []
        if op["op"] in ("CALL", "CALLIND"):
            kind, slot = "called", None
        elif overlaps(out, RAX):
            fixed_word = op["op"] == "COPY" and out == RAX and inputs[0].startswith("ram,") and parse_varnode(inputs[0])[2] == 8
            kind, slot = ("word", inputs[0]) if fixed_word else ("other", None)
        elif kind == "called" and op["op"] == "COPY" and out and out.startswith("ram,") and inputs[0] == RAX:
            kind, slot = "stored", out
    return kind, slot


def lazily_resolved_target(fn: dict, site: int, k: int) -> bool:
    """True when rax at a BRANCHIND is always one cached function pointer, read or freshly resolved.

    Every path into the site has to end rax's history in one of two ways: a read of one fixed word, or a
    call's result stored into that same word. That is the lazy icall stub: `rax = [slot]; if null
    { rax = resolve(); [slot] = rax }; jmp rax`. The target is then whatever the slot holds, which is
    what a jump through the slot is, and at a proven frame it lowers as a call and a return. The body
    must also read the word into rax somewhere, since that read is what shows the word caches a
    pointer; any other write to rax on any path, a second word, or a call result that was not stored
    keeps the hole.
    """
    insns = sorted(fn["insns"], key=lambda insn: insn["a"])
    order = [insn["a"] for insn in insns]
    by_addr = {insn["a"]: insn for insn in insns}
    follows = dict(zip(order, order[1:]))
    if site not in by_addr:
        return False
    state: dict[int, set[tuple]] = {order[0]: {("other", None)}}
    todo = [order[0]]
    while todo:
        addr = todo.pop()
        insn = by_addr[addr]
        after = {rax_after(origin, insn["ops"]) for origin in state[addr]}
        for target in successors(insn, order, follows.get(addr)):
            seen = state.setdefault(target, set())
            if not after <= seen:
                seen |= after
                todo.append(target)
    if site not in state:
        return False
    kinds = {rax_after(origin, by_addr[site]["ops"][:k]) for origin in state[site]}
    slots = {slot for _, slot in kinds}
    if len(slots) != 1 or None in slots or any(kind not in ("word", "stored") for kind, _ in kinds):
        return False
    slot = next(iter(slots))
    return any(op["op"] == "COPY" and op.get("out") == RAX and op["in"][0] == slot for insn in insns for op in insn["ops"])


def is_packed_lane_op(out: str | None, ins: list[str]) -> bool:
    """The packed SSE ops arrive as destination = destination <op> source, every varnode 16 bytes wide."""
    return (
        out is not None
        and len(ins) >= 3
        and parse_varnode(out)[2] == PACKED_WIDTH
        and ins[1] == out
        and parse_varnode(ins[2])[2] == PACKED_WIDTH
    )


def is_movmsk_op(out: str | None, ins: list[str]) -> bool:
    """MOVMSKPS and MOVMSKPD repeat a 32-bit register destination before their single XMM source."""
    return (
        out is not None
        and len(ins) == 3
        and parse_varnode(out)[0] == "register"
        and parse_varnode(out)[2] == 4
        and ins[1] == out
        and parse_varnode(ins[2])[0] == "register"
        and parse_varnode(ins[2])[2] == PACKED_WIDTH
    )


def is_pshufw_op(out: str | None, ins: list[str]) -> bool:
    """PSHUFLW and PSHUFHW add a constant immediate selector to the packed destination/source shape."""
    return (
        len(ins) == 4
        and is_packed_lane_op(out, ins)
        and parse_varnode(ins[3])[0] == "const"
        and 0 <= parse_varnode(ins[3])[1] <= 0xFF
    )


def is_helper_call(ins: list[str]) -> bool:
    """Ghidra's model intrinsics carry their own opcode constant as the only operand."""
    return len(ins) == 1 and parse_varnode(ins[0])[0] == "const"


def is_undefined_opcode(out: str | None, ins: list[str], following: dict | None) -> bool:
    """An undefined opcode is modelled as a helper whose result the very next op jumps through."""
    return (
        out is not None
        and is_helper_call(ins)
        and following is not None
        and following["op"] == "BRANCHIND"
        and (following.get("in") or [None])[0] == out
    )


def is_cpuid_op(out: str | None, ins: list[str]) -> bool:
    """CPUID reads the leaf from EAX and hands back a pointer to the four result dwords."""
    return (
        out is not None
        and parse_varnode(out)[2] == 8
        and len(ins) == 2
        and parse_varnode(ins[0])[0] == "const"
        and parse_varnode(ins[1])[0] in ("register", "unique")
    )


def is_rdrand_op(out: str | None, ins: list[str]) -> bool:
    """RDRAND writes the 32-bit destination EAX receives, from a single opcode constant."""
    return out is not None and parse_varnode(out)[2] == 4 and is_helper_call(ins)


def itype(size: int) -> str:
    return f"i{size * 8}"


DATA_SPACE = 0x1B1
ATOMIC_WIDTHS = (1, 2, 4, 8, 16)
ATOMIC_ARITHMETIC = {"INT_ADD": "add", "INT_SUB": "sub", "INT_AND": "and", "INT_OR": "or", "INT_XOR": "xor"}
ATOMIC_TEST_OPS = frozenset(INT_COMPARE) | {"INT_SUB", "INT_CARRY", "INT_SCARRY", "INT_SBORROW"}
ATOMIC_OPS = (
    frozenset(
        {
            "COPY",
            "PIECE",
            "SUBPIECE",
            "LOAD",
            "STORE",
            "CBRANCH",
            "BRANCH",
            "POPCOUNT",
            "INT_ZEXT",
            "INT_SEXT",
            "INT_LEFT",
            "INT_RIGHT",
            "INT_SRIGHT",
            "INT_CARRY",
            "INT_SCARRY",
            "INT_SBORROW",
        }
    )
    | frozenset(INT_BINARY)
    | frozenset(INT_COMPARE)
)
ATOMIC_HOISTABLE = (
    frozenset({"COPY", "PIECE", "SUBPIECE", "INT_ZEXT", "INT_SEXT", "INT_LEFT", "INT_RIGHT", "INT_SRIGHT"})
    | frozenset(INT_BINARY)
    | frozenset(INT_COMPARE)
)
ATOMIC_RESULT_BASE = 0x7F000000
NOP = {"op": "NOP", "out": None, "in": []}


def width_of(text: str | None) -> int:
    return parse_varnode(text or "const,0,1")[2]


def region_accesses(body: list[dict]) -> list[dict]:
    """Every read or write of a memory location in a LOCK region, keyed by the varnode naming it."""
    found: list[dict] = []
    for i, op in enumerate(body):
        name, out, ins = op["op"], op.get("out"), op.get("in") or []
        if name == "LOAD":
            if len(ins) < 2 or const_of(ins[0]) != DATA_SPACE:
                return []
            found.append({"i": i, "key": ins[1], "size": width_of(out), "dest": out})
        elif name == "STORE":
            if len(ins) < 3 or const_of(ins[0]) != DATA_SPACE:
                return []
            found.append({"i": i, "key": ins[1], "size": width_of(ins[2]), "write": True, "src": ins[2]})
        elif name == "COPY" and len(ins) == 1 and _space(out or "") == "ram":
            found.append({"i": i, "key": out, "size": width_of(out), "write": True, "src": ins[0]})
        elif name == "COPY" and len(ins) == 1 and _space(ins[0]) == "ram":
            found.append({"i": i, "key": ins[0], "size": width_of(ins[0]), "dest": out})
        else:
            for j, text in enumerate(ins):
                if _space(text) == "ram":
                    found.append({"i": i, "key": text, "size": width_of(text), "operand": j})
    return found


def _space(text: str) -> str:
    return text.split(",", 1)[0]


def def_of(body: list[dict], text: str, before: int, after: int = 0) -> int | None:
    for i in range(min(before, len(body)) - 1, max(after, 0) - 1, -1):
        if body[i].get("out") == text:
            return i
    return None


def def_window(body: list[dict], text: str, windows: list[tuple[int, int]]) -> int | None:
    """The op that writes a value, searched through the given index ranges, later ones first."""
    for after, before in windows:
        i = def_of(body, text, before, after)
        if i is not None:
            return i
    return None


def value_origin(
    body: list[dict], text: str, before: int, windows: list[tuple[int, int]] | None = None
) -> tuple[str | None, int | None]:
    """Where a value comes from: the varnode at the head of its COPY chain, and the op that made it."""
    for _ in range(16):
        i = def_window(body, text, windows) if windows else def_of(body, text, before)
        if i is None:
            return text, None
        op = body[i]
        if op["op"] == "COPY" and len(op.get("in") or []) == 1:
            text = op["in"][0]
            continue
        return text, i
    return None, None


def derived_from(body: list[dict], seeds: list[str], upto: int) -> set[str]:
    """Varnodes in the region's first ops whose value comes, through any op, from one of the seeds."""
    closure = set(seeds)
    for op in body[:upto]:
        out, ins = op.get("out"), op.get("in") or []
        if out is None or op["op"] in ("LOAD", "STORE"):
            continue
        if any(t in closure for t in ins):
            closure.add(out)
    return closure


def compared_against(body: list[dict], condition: str, closure: set[str], windows: list[tuple[int, int]]) -> str | None:
    """The operand a branch compares against the old value, following the condition's def chain."""
    text = condition
    for _ in range(16):
        i = def_window(body, text, windows)
        if i is None:
            return None
        op, ins = body[i], body[i].get("in") or []
        if op["op"] in ATOMIC_TEST_OPS and len(ins) == 2:
            sides = [t for t in ins if t in closure]
            rest = [t for t in ins if t not in closure]
            if len(sides) == 1 and len(rest) == 1 and _space(rest[0]) != "const":
                return rest[0]
        if not ins:
            return None
        text = ins[0]
    return None


def def_chain(body: list[dict], texts: list[str], windows: list[tuple[int, int]]) -> list[int]:
    """Every op that produces any of the values, transitively, through the windows that reach the use."""
    queue, seen, indices = list(texts), set(texts), set()
    while queue:
        i = def_window(body, queue.pop(), windows)
        if i is None or i in indices:
            continue
        indices.add(i)
        for operand in body[i].get("in") or []:
            if operand not in seen:
                seen.add(operand)
                queue.append(operand)
    return sorted(indices)


def hoistable(body: list[dict], indices: list[int], at: int, dropped: set[int], restored: str | None) -> bool:
    """Whether these ops may run at `at`: pure, and ordered the same against everything they jump over."""
    moved = set(indices)
    for i in indices:
        op, out = body[i], body[i].get("out")
        if op["op"] not in ATOMIC_HOISTABLE or out is None or _space(out) != "unique":
            return False
        if restored is not None and restored in (op.get("in") or []):
            return False
        skipped = [j for j in range(at, i) if j not in moved and j not in dropped]
        if any(body[j].get("out") == out for j in skipped):
            return False
        if out != restored and any(out in (body[j].get("in") or []) for j in skipped):
            return False
        for text in op.get("in") or []:
            d = def_of(body, text, i)
            if d is not None and d >= at and d not in moved and d not in dropped:
                return False
    return True


def atomic_region(body: list[dict], sections: list[dict] | tuple, fresh) -> dict | None:
    """How to lower the ops between a LOCK and an UNLOCK marker, or None to keep the hole.

    The region lowers only when every access names one location through one varnode, exactly one
    access writes it, and the value stored is an x86 locked arithmetic op or a plain exchange. The
    plan replaces the access slots; everything else Ghidra emitted, the flags included, lifts
    unchanged, so the register file at the region's exit is what the dump says it should be.
    """
    if not body or any(op["op"] not in ATOMIC_OPS for op in body):
        return None
    accesses = region_accesses(body)
    if not accesses or len({a["key"] for a in accesses}) != 1:
        return None
    reads = [a for a in accesses if not a.get("write")]
    writes = [a for a in accesses if a.get("write")]
    width = reads[0]["size"] if reads else 0
    if len(writes) != 1 or not reads or width not in ATOMIC_WIDTHS:
        return None
    if any(a["size"] != width for a in accesses) or accesses[0] is not reads[0]:
        return None
    branching = [i for i, op in enumerate(body) if op["op"] in ("CBRANCH", "BRANCH")]
    cas = any(body[i]["op"] == "CBRANCH" for i in branching)
    if branching and not cas:
        return None
    if cas and (len(branching) != 2 or branching[0] != min(branching) or body[branching[1]]["op"] != "BRANCH"):
        return None

    key, store = accesses[0]["key"], writes[0]
    space, offset, _ = parse_varnode(key)
    if space == "ram":
        if not any(sec["va"] <= offset < sec["va"] + sec["size"] for sec in sections):
            return None
        addr = f"cptr,{offset:x},8"
    else:
        defs = [i for i, op in enumerate(body) if op.get("out") == key]
        if len(defs) > 1 or (defs and defs[0] >= accesses[0]["i"]):
            return None
        addr = key

    result = fresh(width)
    at = accesses[0]["i"]
    if cas:
        cb = branching[0]
        if store["i"] < cb or any(a["i"] > store["i"] for a in reads):
            return None
        closure = derived_from(body[:cb], [reads[0].get("dest") or key], cb)
        # Only the prefix before the compare and the arm holding the store reach the store: reads
        # in the other arm would be read as definitions and feed the atomic a value it discarded.
        taken, prefix = [(branching[1] + 1, store["i"] + 1)], [(0, cb)]
        expected = compared_against(body, body[cb]["in"][1], closure, prefix)
        if expected is None or expected in closure:
            return None
        desired, _ = value_origin(body, store["src"], store["i"] + 1, taken + prefix)
        if desired is None:
            return None
        chain_bounds = [(expected, prefix), (desired, taken + prefix)]
        atomic = {"op": "ATOMIC", "out": result, "in": [addr, expected, desired], "user": "cmpxchg"}
    else:
        origin, origin_i = value_origin(body, store["src"], store["i"])
        if origin is None:
            return None
        closure = derived_from(body, [reads[0].get("dest") or key], origin_i if origin_i is not None else len(body))
        if origin_i is None:
            opname, operand = "xchg", origin
        elif body[origin_i]["op"] in ATOMIC_ARITHMETIC and len(body[origin_i].get("in") or []) == 2:
            sides = [t for t in body[origin_i]["in"] if t in closure]
            rest = [t for t in body[origin_i]["in"] if t not in closure]
            if len(sides) != 1 or len(rest) != 1:
                return None
            opname, operand = ATOMIC_ARITHMETIC[body[origin_i]["op"]], rest[0]
        else:
            return None
        chain_bounds = [(operand, [(0, (origin_i if origin_i is not None else store["i"]) + 1)])]
        atomic = {"op": "ATOMIC", "out": result, "in": [addr, operand], "user": opname}

    hoist = sorted({i for text, windows in chain_bounds for i in def_chain(body, [text], windows) if i > at})
    if hoist and not hoistable(body, hoist, at, {at, store["i"]}, reads[0].get("dest")):
        return None

    edits = {i: NOP for i in hoist}
    for a in accesses:
        if a.get("write"):
            edits[a["i"]] = NOP
        elif a["i"] != at:
            edits[a["i"]] = redirect(body, a, result if a["i"] < store["i"] else store["src"])
    then = redirect(body, accesses[0], result)
    return {"at": at, "atomic": {**atomic, "width": width, "then": then}, "edits": edits, "hoist": hoist}


def redirect(body: list[dict], access: dict, text: str) -> dict:
    """The op that stands in for a location read: the value the region should have seen instead."""
    if "operand" in access:
        ins = list(body[access["i"]]["in"])
        ins[access["operand"]] = text
        return {**body[access["i"]], "in": ins}
    dest = access.get("dest")
    if dest is None or dest == text:
        return NOP
    return {"op": "COPY", "out": dest, "in": [text]}


class BodyLifter:
    def __init__(
        self,
        fn: dict,
        sections: list[dict] | tuple = (),
        *,
        call_dispatch: bool = False,
        unwind: bool = False,
        pads: frozenset = frozenset(),
        evidence=None,
        trap_holes: bool = False,
        entries: frozenset | None = None,
    ):
        self.fn = fn
        self.call_dispatch = call_dispatch
        self.trap_holes = trap_holes
        self.entries = entries
        self.hole_stubs: dict[str, int] = {}
        self.unwind = unwind
        self.pads = frozenset(pads)
        self.call_checks = 0
        self.sections = list(sections)
        self.data_sections: set[str] = set()
        self.unmapped = 0
        self.unique_blocks: list[tuple[int, int, int]] = []
        self.unique_bytes = 0
        self.helper_count = 0
        self.trapped = False
        self.rdrand_call: tuple[int, str, str] | None = None
        self.last_data: dict | None = None
        self.tables = {t["at"]: t["cases"] for t in fn.get("jt", [])}
        self.start, self.size = fn["start"], fn["size"]
        self.lines: list[str] = []
        self.holes: list[str] = []
        self.externs: set[int] = set()
        self.decls: set[str] = set()
        self.indirect_calls = 0
        self.tail_calls = 0
        self.proven_tail_calls = 0
        self.unproven_branchind: list[dict] = []
        self.evidence = evidence
        self.tables_audited = 0
        self.evidence_switches = 0
        self.direct: set[int] | None = None
        self.proof = site_proof(fn)
        self.frame = site_frame(fn)
        self.counter = 0
        self.atomic_count = 0
        self.atomics = 0
        self.varnodes = {
            text
            for insn in fn["insns"]
            for op in insn["ops"]
            for text in ([op["out"]] if op.get("out") else []) + list(op.get("in") or [])
        }
        self.addrs = {i["a"] for i in fn["insns"]}
        self.next_addr = {i["a"]: i["a"] + i["len"] for i in fn["insns"]}
        self.branch_targets = self.collect_targets(fn["insns"])

    def tmp(self) -> str:
        self.counter += 1
        return f"%t{self.counter}"

    def emit(self, line: str) -> None:
        self.lines.append(f"  {line}")

    def section_of(self, offset: int) -> dict | None:
        for sec in self.sections:
            if sec["va"] <= offset < sec["va"] + sec["size"]:
                return sec
        return None

    def data_pointer(self, offset: int) -> str:
        sec = self.section_of(offset)
        if sec is None:
            self.unmapped += 1
            return f"inttoptr (i64 {offset} to ptr)"
        self.data_sections.add(sec["name"])
        self.last_data = sec
        return f"getelementptr (i8, ptr @sec_{sec['name']}, i64 {offset - sec['va']})"

    def address_value(self, offset: int) -> str:
        sec = self.section_of(offset)
        if sec is not None and sec["exec"]:
            self.externs.add(offset)
            return f"ptrtoint (ptr @sub_{offset:x} to i64)"
        if sec is None:
            self.unmapped += 1
            return str(offset)
        return f"ptrtoint (ptr {self.data_pointer(offset)} to i64)"

    def unique_block(self, offset: int, size: int) -> int:
        """Maps a temporary onto a slot in %uniq, so a sub-varnode lands inside the temp that holds it."""
        for base, extent, slot in self.unique_blocks:
            if base <= offset and offset + size <= base + extent:
                return slot + (offset - base)
        extent = max(size, UNIQUE_STRIDE)
        slot = self.unique_bytes
        self.unique_blocks.append((offset, extent, slot))
        self.unique_bytes += extent
        return slot

    def slot(self, space: str, offset: int, size: int) -> str:
        if space == "ram":
            return self.data_pointer(offset)
        if space == "unique":
            offset = self.unique_block(offset, size)
        base = "%reg" if space == "register" else "%uniq"
        p = self.tmp()
        self.emit(f"{p} = getelementptr i8, ptr {base}, i64 {offset}")
        return p

    def read(self, text: str) -> str:
        space, offset, size = parse_varnode(text)
        if space == "const":
            return str(offset & ((1 << (size * 8)) - 1))
        if space == "cptr":
            return self.address_value(offset)
        if space not in ("register", "unique", "ram"):
            raise ValueError(f"read from {space} space")
        v = self.tmp()
        self.emit(f"{v} = load {itype(size)}, ptr {self.slot(space, offset, size)}, align 1")
        return v

    def write(self, text: str, value: str) -> None:
        space, offset, size = parse_varnode(text)
        if space not in ("register", "unique", "ram"):
            raise ValueError(f"write to {space} space")
        self.emit(f"store {itype(size)} {value}, ptr {self.slot(space, offset, size)}, align 1")

    def widen_i1(self, flag: str, size: int) -> str:
        v = self.tmp()
        self.emit(f"{v} = zext i1 {flag} to {itype(size)}")
        return v

    def as_float(self, value: str, size: int) -> str:
        v = self.tmp()
        self.emit(f"{v} = bitcast {itype(size)} {value} to {FLOAT_TYPES[size]}")
        return v

    def from_float(self, value: str, size: int) -> str:
        v = self.tmp()
        self.emit(f"{v} = bitcast {FLOAT_TYPES[size]} {value} to {itype(size)}")
        return v

    def label(self, addr: int, k: int = 0) -> str:
        return f"L{addr:x}_{k}"

    def next_label(self, insn: dict, k: int) -> str | None:
        if k + 1 < len(insn["ops"]):
            return self.label(insn["a"], k + 1)
        nxt = self.next_addr[insn["a"]]
        if nxt in self.addrs:
            return self.label(nxt)
        if nxt < self.start + self.size:
            self.holes.append("GAP")
        return None

    def target_addr(self, text: str, insn: dict, k: int) -> int | None:
        """The address a branch operand names, or None when it is not an address in this body."""
        space, offset, size = parse_varnode(text)
        if space == "const":
            signed = offset - (1 << (size * 8)) if offset >> (size * 8 - 1) else offset
            return insn["a"] if k + signed < len(insn["ops"]) else self.next_addr[insn["a"]]
        return offset if offset in self.addrs else None

    def collect_targets(self, insns: list[dict]) -> set[int]:
        """Every address a branch can land on, so code the guest cannot reach can be proved dead."""
        targets = set()
        for insn in insns:
            for k, op in enumerate(insn["ops"]):
                if op["op"] not in ("BRANCH", "CBRANCH") or not op.get("in"):
                    continue
                addr = self.target_addr(op["in"][0], insn, k)
                if addr is not None:
                    targets.add(addr)
        return targets

    def jump_target(self, text: str, insn: dict, k: int) -> str | None:
        space, offset, size = parse_varnode(text)
        if space == "const":
            signed = offset - (1 << (size * 8)) if offset >> (size * 8 - 1) else offset
            idx = k + signed
            if idx >= len(insn["ops"]):
                return self.next_label(insn, len(insn["ops"]) - 1)
            return self.label(insn["a"], idx)
        if offset in self.addrs:
            return self.label(offset)
        return None

    def mid_body_target(self, offset: int) -> bool:
        """Whether a direct transfer lands inside another body: known entries, and not a body start or a PLT stub."""
        if self.entries is None or offset in self.entries:
            return False
        sec = self.section_of(offset)
        return not (sec is not None and sec["name"].lstrip("._").startswith("plt"))

    def emit_hole(self, site: int) -> None:
        """Ends the block at an unresolved jump: a logging noreturn call when trap_holes is set, else unreachable."""
        if self.trap_holes:
            self.decls.add("declare void @lift_hole(i64, i64) noreturn")
            self.emit(f"call void @lift_hole(i64 {self.start}, i64 {site})")
        self.emit("unreachable")

    def terminate(self, target: str | None) -> None:
        self.emit(f"br label %{target}" if target else "unreachable")

    def lift_op(self, insn: dict, k: int, op: dict) -> bool:
        """Emits one op; returns True when the op ended the block."""
        name, out, ins = op["op"], op["out"], op.get("in") or []
        sz = lambda t: parse_varnode(t)[2]
        if name == "INT_ADD" and sorted(parse_varnode(t)[0] for t in ins) == ["cptr", "register"]:
            # The dump rebased a displacement constant that fell inside the image; add the base back.
            ins = [f"const,{parse_varnode(t)[1] + IMAGE_BASE:x},{sz(t)}" if t.startswith("cptr,") else t for t in ins]
        folded_address = name == "INT_ADD" and sorted(parse_varnode(t)[0] for t in ins) == ["const", "cptr"]
        if name not in ("COPY", "ATOMIC") and not folded_address and any(t.startswith("cptr,") for t in ins):
            # Verified cptr operands: a COPY or constant offset of an address, a register plus displacement, and a rewritten atomic's address.
            self.holes.append("CPTR_OPERAND")
            self.emit_hole(insn["a"])
            return True
        if name == "COPY":
            self.write(out, self.read(ins[0]))
        elif name in INT_BINARY:
            a, b = self.read(ins[0]), self.read(ins[1])
            v = self.tmp()
            self.emit(f"{v} = {INT_BINARY[name]} {itype(sz(out))} {a}, {b}")
            self.write(out, v)
        elif name in ("INT_LEFT", "INT_RIGHT", "INT_SRIGHT"):
            self.shift(name, out, ins)
        elif name in INT_COMPARE:
            a, b = self.read(ins[0]), self.read(ins[1])
            c = self.tmp()
            self.emit(f"{c} = icmp {INT_COMPARE[name]} {itype(sz(ins[0]))} {a}, {b}")
            self.write(out, self.widen_i1(c, sz(out)))
        elif name in ("INT_ZEXT", "INT_SEXT"):
            src_bits = sz(ins[0]) * 8
            self.write(out, self.fit(self.read(ins[0]), src_bits, sz(out) * 8, name == "INT_SEXT"))
        elif name in ("INT_2COMP", "INT_NEGATE"):
            a, v = self.read(ins[0]), self.tmp()
            if name == "INT_2COMP":
                self.emit(f"{v} = sub {itype(sz(out))} 0, {a}")
            else:
                self.emit(f"{v} = xor {itype(sz(out))} {a}, -1")
            self.write(out, v)
        elif name in OVERFLOW_INTRINSIC:
            self.overflow(name, out, ins)
        elif name == "BOOL_NEGATE":
            v = self.tmp()
            self.emit(f"{v} = xor i8 {self.read(ins[0])}, 1")
            self.write(out, v)
        elif name == "POPCOUNT":
            n = sz(ins[0]) * 8
            self.decls.add(f"declare i{n} @llvm.ctpop.i{n}(i{n})")
            v = self.tmp()
            self.emit(f"{v} = call i{n} @llvm.ctpop.i{n}(i{n} {self.read(ins[0])})")
            self.write(out, self.fit(v, n, sz(out) * 8))
        elif name == "SUBPIECE":
            src, off = self.read(ins[0]), parse_varnode(ins[1])[1]
            v = src
            if off:
                v = self.tmp()
                self.emit(f"{v} = lshr {itype(sz(ins[0]))} {src}, {off * 8}")
            self.write(out, self.fit(v, sz(ins[0]) * 8, sz(out) * 8))
        elif name == "PIECE":
            hi, lo = self.read(ins[0]), self.read(ins[1])
            n = sz(out) * 8
            h = self.fit(hi, sz(ins[0]) * 8, n)
            l = self.fit(lo, sz(ins[1]) * 8, n)
            s, v = self.tmp(), self.tmp()
            self.emit(f"{s} = shl i{n} {h}, {sz(ins[1]) * 8}")
            self.emit(f"{v} = or i{n} {s}, {l}")
            self.write(out, v)
        elif name == "LOAD":
            p = self.pointer(ins[1])
            v = self.tmp()
            self.emit(f"{v} = load {itype(sz(out))}, ptr {p}, align 1")
            self.write(out, v)
        elif name == "STORE":
            p = self.pointer(ins[1])
            self.emit(f"store {itype(sz(ins[2]))} {self.read(ins[2])}, ptr {p}, align 1")
        elif (
            name in FLOAT_BINARY
            or name in FLOAT_COMPARE
            or name in FLOAT_UNARY_INTRINSIC
            or name
            in (
                "FLOAT_NEG",
                "FLOAT_NAN",
                "INT2FLOAT",
                "FLOAT2FLOAT",
                "TRUNC",
            )
        ):
            self.float_op(name, out, ins)
        elif name == "BRANCH":
            return self.branch(insn, k, ins[0])
        elif name == "CBRANCH":
            return self.cbranch(insn, k, ins)
        elif name == "CALL":
            return self.call_direct(ins[0], insn)
        elif name == "CALLIND":
            self.call_indirect(ins[0])
        elif name == "RETURN":
            self.emit("ret void")
            return True
        elif name == "BRANCHIND":
            self.branch_indirect(insn, k, ins[0])
            return True
        elif name == "CALLOTHER":
            user = op.get("user", "?")
            if user in PACKED_DIVISION and is_packed_lane_op(out, ins):
                self.packed_division(out, ins[2], *PACKED_DIVISION[user])
            elif user in PACKED_MINMAX and is_packed_lane_op(out, ins):
                self.packed_minmax(out, ins[2], *PACKED_MINMAX[user])
            elif user == "movmskps" and is_movmsk_op(out, ins):
                self.packed_sign_mask(out, ins[2], 4, 4)
            elif user == "movmskpd" and is_movmsk_op(out, ins):
                self.packed_sign_mask(out, ins[2], 2, 8)
            elif user == "pshuflw" and is_pshufw_op(out, ins):
                self.shuffle_words(out, ins[2], parse_varnode(ins[3])[1], high=False)
            elif user == "pshufhw" and is_pshufw_op(out, ins):
                self.shuffle_words(out, ins[2], parse_varnode(ins[3])[1], high=True)
            elif user == "packssdw" and is_packed_lane_op(out, ins):
                self.packed_pack_signed(out, ins[2])
            elif user in ("monitorx", "mwaitx") and out is None and is_helper_call(ins):
                self.advisory_wait(out, ins)
            elif user.startswith("cpuid") and is_cpuid_op(out, ins):
                self.cpuid_helper(out, ins[1])
            elif user == "rdrand" and is_rdrand_op(out, ins):
                self.rdrand(insn, out)
            elif user == "rdrandIsValid" and out is not None and parse_varnode(out)[2] == 1 and is_helper_call(ins):
                self.rdrand_flag(insn, out)
            elif user == "invalidInstructionException":
                return self.undefined_opcode(insn, k, out, ins)
            else:
                self.holes.append(f"CALLOTHER:{user}")
        elif name == "NOP":
            pass
        elif name == "ATOMIC":
            self.atomic(insn, k, out, ins, op)
            if op.get("then") is not None:
                self.lift_op(insn, k, op["then"])
        else:
            self.holes.append(name)
        return False

    def fit(self, value: str, src_bits: int, dst_bits: int, signed: bool = False) -> str:
        if src_bits == dst_bits:
            return value
        v = self.tmp()
        kind = "trunc" if dst_bits < src_bits else ("sext" if signed else "zext")
        self.emit(f"{v} = {kind} i{src_bits} {value} to i{dst_bits}")
        return v

    def pointer(self, addr_varnode: str) -> str:
        a = self.read(addr_varnode)
        bits = parse_varnode(addr_varnode)[2] * 8
        a = self.fit(a, bits, 64)
        p = self.tmp()
        self.emit(f"{p} = inttoptr i64 {a} to ptr")
        return p

    def shift(self, name: str, out: str, ins: list[str]) -> None:
        n = parse_varnode(out)[2] * 8
        a = self.read(ins[0])
        amt = self.fit(self.read(ins[1]), parse_varnode(ins[1])[2] * 8, n)
        ok, shifted, v = self.tmp(), self.tmp(), self.tmp()
        self.emit(f"{ok} = icmp ult i{n} {amt}, {n}")
        if name == "INT_SRIGHT":
            clamp = self.tmp()
            self.emit(f"{clamp} = select i1 {ok}, i{n} {amt}, i{n} {n - 1}")
            self.emit(f"{v} = ashr i{n} {a}, {clamp}")
        else:
            op = "shl" if name == "INT_LEFT" else "lshr"
            self.emit(f"{shifted} = {op} i{n} {a}, {amt}")
            self.emit(f"{v} = select i1 {ok}, i{n} {shifted}, i{n} 0")
        self.write(out, v)

    def overflow(self, name: str, out: str, ins: list[str]) -> None:
        n = parse_varnode(ins[0])[2] * 8
        kind = OVERFLOW_INTRINSIC[name]
        self.decls.add(f"declare {{i{n}, i1}} @llvm.{kind}.with.overflow.i{n}(i{n}, i{n})")
        pair, flag = self.tmp(), self.tmp()
        self.emit(
            f"{pair} = call {{i{n}, i1}} @llvm.{kind}.with.overflow.i{n}(i{n} {self.read(ins[0])}, i{n} {self.read(ins[1])})"
        )
        self.emit(f"{flag} = extractvalue {{i{n}, i1}} {pair}, 1")
        self.write(out, self.widen_i1(flag, parse_varnode(out)[2]))

    def lane(self, value: str, total_bits: int, index: int, bits: int) -> str:
        shifted = value
        if index:
            shifted = self.tmp()
            self.emit(f"{shifted} = lshr i{total_bits} {value}, {index * bits}")
        return self.fit(shifted, total_bits, bits)

    def packed_division(self, out: str, src: str, lanes: int, lane_bytes: int) -> None:
        """DIVPS and DIVPD: each lane of the destination is replaced by that lane divided by the source lane."""
        ft, bits, total = FLOAT_TYPES[lane_bytes], lane_bytes * 8, PACKED_WIDTH * 8
        dividend, divisor = self.read(out), self.read(src)
        pieces = []
        for index in range(lanes):
            a = self.as_float(self.lane(dividend, total, index, bits), lane_bytes)
            b = self.as_float(self.lane(divisor, total, index, bits), lane_bytes)
            quotient = self.tmp()
            self.emit(f"{quotient} = fdiv {ft} {a}, {b}")
            pieces.append(self.fit(self.from_float(quotient, lane_bytes), bits, total))
        self.merge_lanes(out, pieces, bits, total)

    def packed_minmax(self, out: str, src: str, lanes: int, lane_bytes: int, predicate: str) -> None:
        """MINPS and MAXPS: a lane keeps the first source only while it strictly compares with the second."""
        ft, bits, total = FLOAT_TYPES[lane_bytes], lane_bytes * 8, PACKED_WIDTH * 8
        first, second = self.read(out), self.read(src)
        pieces = []
        for index in range(lanes):
            a, b = self.lane(first, total, index, bits), self.lane(second, total, index, bits)
            fa, fb = self.as_float(a, lane_bytes), self.as_float(b, lane_bytes)
            holds = self.tmp()
            self.emit(f"{holds} = fcmp {predicate} {ft} {fa}, {fb}")
            chosen = self.tmp()
            self.emit(f"{chosen} = select i1 {holds}, i{bits} {a}, i{bits} {b}")
            pieces.append(self.fit(chosen, bits, total))
        self.merge_lanes(out, pieces, bits, total)

    def merge_lanes(self, out: str, pieces: list[str], bits: int, total: int) -> None:
        """Assembles per-lane results, each already widened to the packed width, into one value."""
        result = "0"
        for index, piece in enumerate(pieces):
            if index:
                shifted = self.tmp()
                self.emit(f"{shifted} = shl i{total} {piece}, {index * bits}")
                piece = shifted
            merged = self.tmp()
            self.emit(f"{merged} = or i{total} {result}, {piece}")
            result = merged
        self.write(out, result)

    def shuffle_words(self, out: str, src: str, selector: int, high: bool) -> None:
        """PSHUFLW and PSHUFHW permute one half of the words by the immediate and leave the other half."""
        source = self.read(src)
        picked = [(selector >> (2 * lane)) & 3 for lane in range(4)]
        indices = (list(range(4)) + [4 + word for word in picked]) if high else (picked + list(range(4, 8)))
        pieces = [self.fit(self.lane(source, 128, index, 16), 16, 128) for index in indices]
        self.merge_lanes(out, pieces, 16, 128)

    def packed_sign_mask(self, out: str, src: str, lanes: int, lane_bytes: int) -> None:
        """MOVMSKPS and MOVMSKPD: one bit of the destination per lane, taken from that lane's sign bit."""
        value = self.read(src)
        bits, total = lane_bytes * 8, PACKED_WIDTH * 8
        pieces = []
        for index in range(lanes):
            sign = self.tmp()
            self.emit(f"{sign} = lshr i{bits} {self.lane(value, total, index, bits)}, {bits - 1}")
            pieces.append(self.fit(sign, bits, 32))
        self.merge_lanes(out, pieces, 1, 32)

    def packed_pack_signed(self, out: str, src: str) -> None:
        """PACKSSDW: the destination's dwords saturate into the low words, the source's into the high ones."""
        first, second = self.read(out), self.read(src)
        pieces = []
        for index in range(8):
            dword = self.lane(first if index < 4 else second, PACKED_WIDTH * 8, index % 4, 32)
            pieces.append(self.fit(self.fit(self.saturate_word(dword), 32, 16), 16, 128))
        self.merge_lanes(out, pieces, 16, 128)

    def saturate_word(self, value: str) -> str:
        """Clamp a signed dword to the signed word range, which is the saturation PACKSSDW applies."""
        below = self.tmp()
        self.emit(f"{below} = icmp slt i32 {value}, -32768")
        clamped = self.tmp()
        self.emit(f"{clamped} = select i1 {below}, i32 -32768, i32 {value}")
        above = self.tmp()
        self.emit(f"{above} = icmp sgt i32 {clamped}, 32767")
        result = self.tmp()
        self.emit(f"{result} = select i1 {above}, i32 32767, i32 {clamped}")
        return result

    def float_op(self, name: str, out: str, ins: list[str]) -> None:
        osz, isz = parse_varnode(out)[2], parse_varnode(ins[0])[2]
        if X87 in (osz, isz):
            self.x87_op(name, out, ins, osz, isz)
            return
        for size in (osz, isz):
            if size not in FLOAT_TYPES and name not in ("INT2FLOAT", "TRUNC", "FLOAT_NAN") + tuple(FLOAT_COMPARE):
                raise ValueError(f"float width {size}")
        if name in FLOAT_BINARY:
            a = self.as_float(self.read(ins[0]), isz)
            b = self.as_float(self.read(ins[1]), isz)
            v = self.tmp()
            self.emit(f"{v} = {FLOAT_BINARY[name]} {FLOAT_TYPES[isz]} {a}, {b}")
            self.write(out, self.from_float(v, osz))
        elif name in FLOAT_COMPARE:
            a = self.as_float(self.read(ins[0]), isz)
            b = self.as_float(self.read(ins[1]), isz)
            c = self.tmp()
            self.emit(f"{c} = fcmp {FLOAT_COMPARE[name]} {FLOAT_TYPES[isz]} {a}, {b}")
            self.write(out, self.widen_i1(c, osz))
        elif name == "FLOAT_NAN":
            a = self.as_float(self.read(ins[0]), isz)
            c = self.tmp()
            self.emit(f"{c} = fcmp uno {FLOAT_TYPES[isz]} {a}, {a}")
            self.write(out, self.widen_i1(c, osz))
        elif name == "FLOAT_NEG":
            a = self.as_float(self.read(ins[0]), isz)
            v = self.tmp()
            self.emit(f"{v} = fneg {FLOAT_TYPES[isz]} {a}")
            self.write(out, self.from_float(v, osz))
        elif name in FLOAT_UNARY_INTRINSIC:
            ft = FLOAT_TYPES[isz]
            fn = FLOAT_UNARY_INTRINSIC[name]
            self.decls.add(f"declare {ft} @llvm.{fn}.{ft}({ft})")
            a = self.as_float(self.read(ins[0]), isz)
            v = self.tmp()
            self.emit(f"{v} = call {ft} @llvm.{fn}.{ft}({ft} {a})")
            self.write(out, self.from_float(v, osz))
        elif name == "INT2FLOAT":
            v = self.tmp()
            self.emit(f"{v} = sitofp {itype(isz)} {self.read(ins[0])} to {FLOAT_TYPES[osz]}")
            self.write(out, self.from_float(v, osz))
        elif name == "FLOAT2FLOAT":
            a = self.as_float(self.read(ins[0]), isz)
            if osz == isz:
                self.write(out, self.from_float(a, osz))
            else:
                v = self.tmp()
                kind = "fpext" if osz > isz else "fptrunc"
                self.emit(f"{v} = {kind} {FLOAT_TYPES[isz]} {a} to {FLOAT_TYPES[osz]}")
                self.write(out, self.from_float(v, osz))
        elif name == "TRUNC":
            # x86 cvttss2si/cvttsd2si hand back the integer indefinite value exactly where
            # fptosi is poison, so keep the operand in range and replace the result.
            fty, limit = FLOAT_TYPES[isz], 1 << (osz * 8 - 1)
            a = self.as_float(self.read(ins[0]), isz)
            nan, high, low = self.tmp(), self.tmp(), self.tmp()
            self.emit(f"{nan} = fcmp uno {fty} {a}, {a}")
            self.emit(f"{high} = fcmp oge {fty} {a}, {limit}.0")
            self.emit(f"{low} = fcmp olt {fty} {a}, -{limit}.0")
            over, bad = self.tmp(), self.tmp()
            self.emit(f"{over} = or i1 {high}, {low}")
            self.emit(f"{bad} = or i1 {over}, {nan}")
            safe = self.tmp()
            self.emit(f"{safe} = select i1 {bad}, {fty} 0.0, {fty} {a}")
            v = self.tmp()
            self.emit(f"{v} = fptosi {fty} {safe} to {itype(osz)}")
            result = self.tmp()
            self.emit(f"{result} = select i1 {bad}, {itype(osz)} {-limit}, {itype(osz)} {v}")
            self.write(out, result)

    def x87_op(self, name: str, out: str, ins: list[str], osz: int, isz: int) -> None:
        """The 80-bit shapes the pinned image contains; every other width-10 op stays a hole."""
        shape = (name, osz, isz, len(ins))
        if shape == ("FLOAT2FLOAT", X87, 4, 1):
            self.write(out, self.fit(self.x87_from_single(self.read(ins[0])), 128, 80))
        elif shape == ("INT2FLOAT", X87, 4, 1):
            self.write(out, self.fit(self.x87_from_int(self.read(ins[0])), 128, 80))
        elif name in X87_PREDICATES and (osz, isz) == (1, X87) and len(ins) == X87_PREDICATES[name]:
            values = [self.fit(self.read(text), 80, 128) for text in ins]
            if name == "FLOAT_NAN":
                flag = self.x87_unordered(self.x87_parts(values[0]))
            elif name == "FLOAT_EQUAL":
                flag = self.x87_equal(*values)
            else:
                flag = self.x87_less(*values)
            self.write(out, self.widen_i1(flag, osz))
        else:
            raise ValueError(f"float width {X87}")

    def calc(self, ty: str, opcode: str, left: str, right: str) -> str:
        v = self.tmp()
        self.emit(f"{v} = {opcode} {ty} {left}, {right}")
        return v

    def test(self, ty: str, left: str, predicate: str, right: str) -> str:
        v = self.tmp()
        self.emit(f"{v} = icmp {predicate} {ty} {left}, {right}")
        return v

    def pick(self, flag: str, ty: str, if_true: str, if_false: str) -> str:
        v = self.tmp()
        self.emit(f"{v} = select i1 {flag}, {ty} {if_true}, {ty} {if_false}")
        return v

    def field(self, value: str, shift: int, mask: int) -> str:
        """One field of an i128-held 80-bit encoding."""
        return self.calc("i128", "and", self.calc("i128", "lshr", value, str(shift)), str(mask))

    def leading_zeros(self, value: str) -> str:
        v = self.tmp()
        self.decls.add("declare i64 @llvm.ctlz.i64(i64, i1)")
        self.emit(f"{v} = call i64 @llvm.ctlz.i64(i64 {value}, i1 false)")
        return v

    def x87_from_single(self, bits: str) -> str:
        """FLDS: the single's payload sits at the top of the 63-bit fraction, subnormals renormalize."""
        sign = self.calc("i32", "lshr", bits, "31")
        exponent = self.field_of_single(bits, 23, 0xFF)
        payload = self.calc("i32", "and", bits, str(SINGLE_MANTISSA_MASK))
        empty = self.test("i32", payload, "eq", "0")
        unbiased = self.test("i32", exponent, "eq", "0")
        saturated = self.test("i32", exponent, "eq", str(0xFF))
        lead = self.leading_zeros(self.fit(payload, 32, 64))
        top = self.calc("i64", "sub", "63", lead)
        scaled = self.calc("i128", "shl", self.fit(payload, 32, 128), str(SINGLE_FRACTION_SHIFT))
        normal_mantissa = self.calc("i128", "or", str(X87_INT_BIT), scaled)
        quiet_mantissa = self.calc("i128", "or", normal_mantissa, str(X87_QUIET_BIT))
        denormal_mantissa = self.calc("i128", "shl", self.fit(payload, 32, 128), self.fit(lead, 64, 128))
        normal_exponent = self.calc("i128", "add", self.fit(exponent, 32, 128), str(X87_BIAS - 127))
        denormal_exponent = self.calc("i128", "add", self.fit(top, 64, 128), str(X87_BIAS - 149))
        is_nan = self.calc("i1", "and", saturated, self.negate(empty))
        is_denormal = self.calc("i1", "and", unbiased, self.negate(empty))
        is_normal = self.calc("i1", "and", self.negate(unbiased), self.negate(saturated))
        mantissa = self.pick(
            is_nan,
            "i128",
            quiet_mantissa,
            self.pick(
                saturated,
                "i128",
                str(X87_INT_BIT),
                self.pick(
                    is_normal,
                    "i128",
                    normal_mantissa,
                    self.pick(is_denormal, "i128", denormal_mantissa, "0"),
                ),
            ),
        )
        exponent_field = self.pick(
            saturated,
            "i128",
            str(X87_EXPONENT_MAX),
            self.pick(
                is_normal,
                "i128",
                normal_exponent,
                self.pick(is_denormal, "i128", denormal_exponent, "0"),
            ),
        )
        sign_field = self.calc("i128", "shl", self.fit(sign, 32, 128), str(X87_SIGN_BIT))
        return self.calc(
            "i128", "or", self.calc("i128", "or", sign_field, self.calc("i128", "shl", exponent_field, "64")), mantissa
        )

    def field_of_single(self, bits: str, shift: int, mask: int) -> str:
        return self.calc("i32", "and", self.calc("i32", "lshr", bits, str(shift)), str(mask))

    def x87_from_int(self, value: str) -> str:
        """FILD: a 32-bit integer is exact at this width, so the mantissa is its magnitude with the top bit at 63."""
        negative = self.test("i32", value, "slt", "0")
        wide = self.fit(value, 32, 64, signed=True)
        magnitude = self.pick(negative, "i64", self.calc("i64", "sub", "0", wide), wide)
        lead = self.leading_zeros(magnitude)
        top = self.calc("i64", "sub", "63", lead)
        zero = self.test("i64", magnitude, "eq", "0")
        mantissa = self.pick(
            zero,
            "i128",
            "0",
            self.calc("i128", "shl", self.fit(magnitude, 64, 128), self.fit(lead, 64, 128)),
        )
        exponent = self.pick(zero, "i128", "0", self.calc("i128", "add", self.fit(top, 64, 128), str(X87_BIAS)))
        sign_field = self.calc("i128", "shl", self.pick(negative, "i128", "1", "0"), str(X87_SIGN_BIT))
        return self.calc("i128", "or", self.calc("i128", "or", sign_field, self.calc("i128", "shl", exponent, "64")), mantissa)

    def x87_parts(self, value: str) -> dict:
        """Sign, exponent, explicit integer bit, fraction and the magnitude without its sign."""
        return {
            "sign": self.calc("i128", "lshr", value, str(X87_SIGN_BIT)),
            "exponent": self.field(value, 64, X87_EXPONENT_MAX),
            "integer": self.field(value, 63, 1),
            "fraction": self.calc("i128", "and", value, str(X87_FRACTION_BITS)),
            "magnitude": self.calc("i128", "and", value, str(X87_MAGNITUDE_BITS)),
        }

    def negate(self, flag: str) -> str:
        return self.calc("i1", "xor", flag, "true")

    def x87_unordered(self, parts: dict) -> str:
        """The encodings x87 refuses to order: a set exponent without its integer bit, or an all-ones exponent with a payload."""
        all_ones = self.test("i128", parts["exponent"], "eq", str(X87_EXPONENT_MAX))
        set_exponent = self.test("i128", parts["exponent"], "ne", "0")
        no_integer = self.test("i128", parts["integer"], "eq", "0")
        payload = self.test("i128", parts["fraction"], "ne", "0")
        unsupported = self.calc("i1", "and", set_exponent, no_integer)
        special = self.calc("i1", "and", all_ones, self.calc("i1", "or", payload, no_integer))
        return self.calc("i1", "or", unsupported, special)

    def x87_ordered(self, left: dict, right: dict) -> str:
        return self.calc("i1", "and", self.negate(self.x87_unordered(left)), self.negate(self.x87_unordered(right)))

    def x87_equal(self, left: str, right: str) -> str:
        a, b = self.x87_parts(left), self.x87_parts(right)
        same_magnitude = self.test("i128", a["magnitude"], "eq", b["magnitude"])
        both_zero = self.test("i128", a["magnitude"], "eq", "0")
        same_sign = self.test("i128", a["sign"], "eq", b["sign"])
        ordered = self.x87_ordered(a, b)
        return self.calc(
            "i1", "and", ordered, self.calc("i1", "and", same_magnitude, self.calc("i1", "or", both_zero, same_sign))
        )

    def x87_less(self, left: str, right: str) -> str:
        """Ordered less-than over sign-magnitude fields, with -0 and +0 equal."""
        a, b = self.x87_parts(left), self.x87_parts(right)
        negative = self.test("i128", a["sign"], "ne", "0")
        lower = self.pick(negative, "i128", b["magnitude"], a["magnitude"])
        higher = self.pick(negative, "i128", a["magnitude"], b["magnitude"])
        apart = self.test("i128", a["sign"], "ne", b["sign"])
        apart_by_sign = self.pick(apart, "i1", negative, self.test("i128", lower, "ult", higher))
        equal_magnitude = self.test("i128", a["magnitude"], "eq", b["magnitude"])
        nonzero = self.test("i128", a["magnitude"], "ne", "0")
        other_positive = self.test("i128", b["sign"], "eq", "0")
        minus_first = self.calc("i1", "and", negative, self.calc("i1", "and", other_positive, nonzero))
        return self.calc("i1", "and", self.x87_ordered(a, b), self.pick(equal_magnitude, "i1", minus_first, apart_by_sign))

    def call_direct(self, target: str, insn: dict) -> bool:
        """Emits a direct call; returns True when the call was a hole that ended the block."""
        space, offset, _ = parse_varnode(target)
        if space != "ram":
            self.holes.append("CALL_TARGET")
            return False
        if self.mid_body_target(offset):
            self.holes.append("MID_BODY_TARGET")
            self.emit_hole(insn["a"])
            return True
        self.externs.add(offset)
        self.emit(f"call void @sub_{offset:x}(ptr %reg)")
        self.pending_check()
        return False

    def pending_check(self) -> None:
        """After a call, leaves the body for the unwind landing block when an exception is pending."""
        if not self.unwind:
            return
        self.call_checks += 1
        word, flag = self.tmp(), self.tmp()
        slot = self.tmp()
        self.emit(f"{slot} = getelementptr i8, ptr %reg, i64 {EH_PENDING_PAD}")
        self.emit(f"{word} = load i64, ptr {slot}, align 8")
        self.emit(f"{flag} = icmp ne i64 {word}, 0")
        resume = f"C{self.call_checks}"
        self.emit(f"br i1 {flag}, label %EH_LAND, label %{resume}")
        self.lines.append(f"{resume}:")

    def call_indirect(self, target: str, *, check: bool = True) -> None:
        self.indirect_calls += 1
        if self.call_dispatch:
            value = self.read(target)
            value = self.fit(value, parse_varnode(target)[2] * 8, 64)
            self.decls.add("declare void @lift_dispatch(i64, ptr)")
            self.emit(f"call void @lift_dispatch(i64 {value}, ptr %reg)")
        else:
            self.emit(f"call void {self.pointer(target)}(ptr %reg)")
        if check:
            self.pending_check()

    def advisory_wait(self, out: str | None, ins: list[str]) -> None:
        """MONITORX and MWAITX are address-monitor hints, and neither result is read; dropping one is what
        a host without them does, so a spin loop still spins."""

    def helper_pointer(self, size: int) -> str:
        """A byte block in %uniq for a helper's result, clear of every varnode the body names."""
        self.helper_count += 1
        offset = HELPER_RESULT_BASE + self.helper_count * UNIQUE_STRIDE
        while any(t.startswith(f"unique,{offset:x},") for t in self.varnodes):
            offset += UNIQUE_STRIDE
        return self.slot("unique", offset, size)

    def cpuid_helper(self, out: str, leaf: str) -> None:
        """CPUID's model returns a pointer to four dwords; the runtime fills them in as the leaf dictates."""
        self.decls.add("declare void @lift_cpuid(i64, ptr)")
        buf = self.helper_pointer(CPUID_RESULT_BYTES)
        value = self.fit(self.read(leaf), parse_varnode(leaf)[2] * 8, 64)
        self.emit(f"call void @lift_cpuid(i64 {value}, ptr {buf})")
        addr = self.tmp()
        self.emit(f"{addr} = ptrtoint ptr {buf} to i64")
        self.write(out, addr)

    def rdrand_pair(self, insn: dict) -> tuple[str, str]:
        """RDRAND and its validity flag are two model ops over one host call, so the second reuses the first."""
        if self.rdrand_call and self.rdrand_call[0] == insn["a"]:
            return self.rdrand_call[1], self.rdrand_call[2]
        self.decls.add("declare zeroext i1 @lift_rdrand(ptr)")
        buf = self.helper_pointer(RDRAND_RESULT_BYTES)
        ok = self.tmp()
        self.emit(f"{ok} = call zeroext i1 @lift_rdrand(ptr {buf})")
        value = self.tmp()
        self.emit(f"{value} = load i64, ptr {buf}, align 1")
        self.rdrand_call = (insn["a"], value, ok)
        return value, ok

    def rdrand(self, insn: dict, out: str) -> None:
        value, _ = self.rdrand_pair(insn)
        self.write(out, self.fit(value, RDRAND_RESULT_BYTES * 8, parse_varnode(out)[2] * 8))

    def rdrand_flag(self, insn: dict, out: str) -> None:
        _, ok = self.rdrand_pair(insn)
        self.write(out, self.widen_i1(ok, parse_varnode(out)[2]))

    def undefined_opcode(self, insn: dict, k: int, out: str | None, ins: list[str]) -> bool:
        """An undefined opcode traps, so the block ends there and the model's fabricated jump dies with it.

        The guest never continues past the instruction, so the code after it is dead only if nothing else
        can branch into it; the jump target the model invented is its own artifact, not a control transfer.
        """
        ops = insn["ops"]
        dead_from = self.next_addr[insn["a"]]
        live = any(addr >= dead_from for addr in self.branch_targets | self.pads)
        if live or not is_undefined_opcode(out, ins, ops[k + 1] if k + 1 < len(ops) else None):
            self.holes.append("CALLOTHER:invalidInstructionException")
            return False
        self.decls.add("declare void @llvm.trap()")
        self.emit("call void @llvm.trap()")
        self.terminate(None)
        self.trapped = True
        return True

    def branch(self, insn: dict, k: int, target: str) -> bool:
        space, offset, _ = parse_varnode(target)
        label = self.jump_target(target, insn, k)
        if label:
            self.emit(f"br label %{label}")
        elif space == "ram" and not (self.start <= offset < self.start + self.size):
            if self.mid_body_target(offset):
                self.holes.append("MID_BODY_TARGET")
                self.emit_hole(insn["a"])
                return True
            self.externs.add(offset)
            self.emit(f"call void @sub_{offset:x}(ptr %reg)")
            self.emit("ret void")
        else:
            self.holes.append("UNDECODED_TARGET")
            self.emit_hole(insn["a"])
        return True

    def cbranch(self, insn: dict, k: int, ins: list[str]) -> bool:
        taken = self.jump_target(ins[0], insn, k)
        if taken is None:
            space, offset, _ = parse_varnode(ins[0])
            if space == "ram" and not (self.start <= offset < self.start + self.size):
                stub = f"X{insn['a']:x}_{k}"
                if self.mid_body_target(offset):
                    self.holes.append("MID_BODY_TARGET")
                    self.hole_stubs[stub] = insn["a"]
                    self.pending_tail = getattr(self, "pending_tail", []) + [(stub, None)]
                else:
                    self.externs.add(offset)
                    self.pending_tail = getattr(self, "pending_tail", []) + [(stub, offset)]
                taken = stub
            else:
                self.holes.append("UNDECODED_TARGET")
                self.hole_stubs[f"X{insn['a']:x}_{k}"] = insn["a"]
                self.pending_tail = getattr(self, "pending_tail", []) + [(f"X{insn['a']:x}_{k}", None)]
                taken = f"X{insn['a']:x}_{k}"
        fall = self.next_label(insn, k)
        cond, c = self.read(ins[1]), self.tmp()
        self.emit(f"{c} = icmp ne i8 {cond}, 0")
        if fall is None:
            stub = f"F{insn['a']:x}_{k}"
            self.pending_tail = getattr(self, "pending_tail", []) + [(stub, None)]
            fall = stub
        self.emit(f"br i1 {c}, label %{taken}, label %{fall}")
        return True

    def defined_by_load(self, insn: dict, k: int, target: str, slots: bool = False) -> bool:
        """True when `target` traces back through COPYs to a LOAD, in instruction order.

        With `slots`, a COPY from a fixed memory slot (a ram-space varnode) also counts as a load.
        """
        flat = self.ops_before(insn, k)
        for op in reversed(flat):
            if op["out"] != target:
                continue
            if op["op"] == "LOAD":
                return True
            if op["op"] != "COPY":
                return False
            if slots and op["in"][0].startswith("ram,"):
                return True
            target = op["in"][0]
        return False

    def audited_cases(self, site: int, cases: list[int]) -> list[int] | None:
        """Replaces a case list that runs past the body with the image's own table bytes, when they explain it.

        Accepted only when every byte-decoded case lies in the body and every case Ghidra added beyond
        the bytes is either a target the body already reaches by a direct branch or code outside the
        body, which cannot be an edge of it. A case on the body's own code that no branch reaches is
        the sign of a wrong entry count, so it keeps the hole.
        """
        if self.evidence is None:
            return None
        raw = self.evidence.raw_cases(sorted(self.addrs), site)
        if not raw or any(c not in self.addrs for c in raw):
            return None
        if self.direct is None:
            self.direct = direct_branch_targets(self.fn)
        outside = self.start + self.size
        if any(c not in self.direct and self.start <= c < outside for c in set(cases) - set(raw)):
            return None
        self.tables_audited += 1
        return raw

    def handed_over_target(self, insn: dict, k: int, target: str) -> bool:
        """True when one COPY from an architectural register, ahead of the site, hands `target` its value.

        One write in the whole body, none after the site: the value is that copy or the caller's own,
        and neither is computed, so no dominance check is needed. A `unique` source is refused: that is
        how the body delivers a value it built itself, which is the computed target this rule rejects.
        """
        before: list[dict] = []
        after: list[dict] = []
        past = False
        for here in self.fn["insns"]:
            if here is insn:
                before += here["ops"][:k]
                after += here["ops"][k:]
                past = True
                continue
            (after if past else before).extend(here["ops"])
        writes = [op for op in before if op.get("out") == target]
        if len(writes) != 1 or any(op.get("out") == target for op in after):
            return False
        op = writes[0]
        inputs = op.get("in") or []
        if op["op"] != "COPY" or len(inputs) != 1:
            return False
        return parse_varnode(inputs[0])[0] == "register"

    def table_in_the_image(self, site: int) -> bool:
        """True when the image's own bytes decode a complete in-body table for a site the dump has none for."""
        if self.evidence is None:
            return False
        try:
            raw = self.evidence.raw_cases(sorted(self.addrs), site)
        except Exception:
            return False
        return bool(raw) and all(c in self.addrs for c in raw)

    def ops_before(self, insn: dict, k: int) -> list[dict]:
        """Every op the body executes ahead of operand k of this instruction, in dump order."""
        flat: list[dict] = []
        for earlier in self.fn["insns"]:
            if earlier is insn:
                return flat + earlier["ops"][:k]
            flat += earlier["ops"]
        return flat

    def index_of(self, ops: list[dict], op: dict) -> int:
        """Where an op sits in the flattened list, found by identity so equal ops cannot collide."""
        for i in range(len(ops) - 1, -1, -1):
            if ops[i] is op:
                return i
        return len(ops)

    def last_write(self, ops: list[dict], varnode: str, limit: int | None = None) -> dict | None:
        """The op that most recently wrote `varnode`, looking no further than `limit` in the list."""
        for op in reversed(ops[: len(ops) if limit is None else limit]):
            if op.get("out") == varnode:
                return op
        return None

    def table_pointer_chain(self, ops: list[dict], target: str, table_base: int) -> bool:
        """Whether the target is built the way the dump builds a base-relative jump-table target.

        entry = LOAD(base + index * entry_size) and target = sext(entry) + base, the base an address
        constant (cptr) equal to the decoded table's own base. A ram source is a load of the value stored
        there, not an address. That construction is what makes the runtime value a dumped address plus
        that section's bias, which is the only value the switch's rebasing can resolve; a target
        assembled any other way keeps its hole rather than lowering a switch that could never match.
        """
        joined = self.last_write(ops, target)
        if not joined or joined["op"] != "INT_ADD" or len(joined.get("in") or []) != 2 or target not in joined["in"]:
            return False
        base = next((v for v in joined["in"] if v != target), None)
        sext = self.last_write(ops, target, self.index_of(ops, joined))
        if not sext or sext["op"] != "INT_SEXT" or len(sext.get("in") or []) != 1:
            return False
        entry = sext["in"][0]
        load = self.last_write(ops, entry)
        if not load or load["op"] != "LOAD" or len(load.get("in") or []) != 2 or parse_varnode(entry)[2] != 4:
            return False
        slot = self.last_write(ops, load["in"][1])
        if not slot or slot["op"] != "INT_ADD" or len(slot.get("in") or []) != 2 or base not in slot["in"]:
            return False
        scaled = next((v for v in slot["in"] if v != base), None)
        mult = self.last_write(ops, scaled)
        if not mult or mult["op"] != "INT_MULT" or len(mult.get("in") or []) != 2:
            return False
        if next((const_of(v) for v in mult["in"] if v.startswith("const,")), None) != 4:
            return False
        copied = self.last_write(ops, base)
        if not copied or copied["op"] != "COPY" or len(copied.get("in") or []) != 1:
            return False
        source = copied["in"][0]
        return source.startswith("cptr,") and int(source.split(",")[1], 16) == table_base

    def evidence_switch(self, insn: dict, k: int, target: str) -> tuple[list[int], dict] | None:
        """Cases and bias section for a site Ghidra left without a table, when the image's bytes prove one.

        Only base-relative (4-byte) tables are accepted: their entries are offsets from the table itself,
        so the bytes in the image say exactly where the dispatch can land. Absolute entries name a
        runtime address the lifter cannot resolve, so those sites keep their hole.
        """
        if self.evidence is None:
            return None
        try:
            table = self.evidence.raw_table(sorted(self.addrs), insn["a"])
        except Exception:
            return None
        if not table or table.get("scale") != 4 or table.get("count") is None or table.get("base") is None:
            return None
        cases = table.get("cases") or []
        if not cases or any(c not in self.addrs for c in cases):
            return None
        sec = self.section_of(table["base"])
        if sec is None or not self.guard_dominates(table.get("window"), insn["a"]):
            return None
        if not self.table_pointer_chain(self.ops_before(insn, k), target, table["base"]):
            return None
        return sorted(set(cases)), sec

    def guard_dominates(self, window: int | None, site: int) -> bool:
        """Whether nothing enters the span from `window` to the jump except by running it from its first instruction.

        An edge landing after the bound compare skips the guard the case list rests on, and one landing
        after the base load skips the definition the chain reads. With no such edge the span is
        straight-line, so the dump-order last write of each chain value is the one that reaches the jump.
        """
        if window is None:
            return False
        if self.direct is None:
            self.direct = direct_branch_targets(self.fn)
        entries = self.direct.union(*self.tables.values())
        return not any(window < target <= site for target in entries)

    def refusal_reason(self, verdict: dict, table_bytes: bool) -> str:
        """Why a BRANCHIND stayed a hole, in the terms of the gate that actually refused it.

        The frame pass speaks only when it has a complaint; an empty reason means it proved the site,
        so what follows has to name the target-shape gate instead of borrowing the frame pass's wording.
        """
        if verdict.get("reason"):
            return verdict["reason"]
        return "jump table not in the dump" if table_bytes else "frame proven, handover shape refused"

    def branch_indirect(self, insn: dict, k: int, target: str) -> None:
        """Lowers a BRANCHIND as a switch, or as an indirect call and a return for a tail call.

        `jmp rax` with rsp at its entry value is `call rax` then `ret` when the target is another
        function: a pointer read from memory, or a register the caller handed over.
        """
        cases = self.tables.get(insn["a"])
        sec = self.last_data
        if not cases:
            # A bare `jmp reg` lowers as a call and a return when the target is a loaded pointer (the
            # original rule), when rsp is proven at its entry value and the target is read from
            # memory, or when rsp is proven and the target is a register handed over by one COPY.
            # Balance alone never licenses it: a frameless switch also has rsp at entry.
            load_traced = self.defined_by_load(insn, k, target)
            verdict = self.frame.get(insn["a"], {})
            fixed_word = target.startswith("ram,")
            balanced = verdict.get("reason") == "" and (fixed_word or self.defined_by_load(insn, k, target, slots=True))
            proven = self.proof.get(insn["a"], {}).get("reason") == ""
            sibling = proven and (
                self.handed_over_target(insn, k, target) or (target == RAX and lazily_resolved_target(self.fn, insn["a"], k))
            )
            if not (load_traced or balanced or sibling):
                switched = self.evidence_switch(insn, k, target)
                if switched is not None:
                    self.evidence_switches += 1
                    self.emit_switch(insn, target, *switched)
                    return
                table_bytes = self.table_in_the_image(insn["a"])
                self.unproven_branchind.append(
                    {
                        "a": insn["a"],
                        "reason": self.refusal_reason(verdict, table_bytes),
                        "rsp_delta": verdict.get("rsp_delta"),
                        "table_bytes": table_bytes,
                    }
                )
                self.holes.append("BRANCHIND")
                self.emit_hole(insn["a"])
                return
            self.tail_calls += 1
            if balanced or sibling:
                self.proven_tail_calls += 1
            else:
                table_bytes = self.table_in_the_image(insn["a"])
                self.unproven_branchind.append(
                    {
                        "a": insn["a"],
                        "reason": self.refusal_reason(verdict, table_bytes),
                        "rsp_delta": verdict.get("rsp_delta"),
                        "table_bytes": table_bytes,
                    }
                )
            self.call_indirect(target, check=False)
            self.emit("ret void")
            return
        if sec is None:
            self.holes.append("BRANCHIND")
            self.emit_hole(insn["a"])
            return
        reachable = sorted({c for c in cases if c in self.addrs})
        if len(reachable) != len(set(cases)):
            audited = self.audited_cases(insn["a"], cases)
            if audited is None:
                self.holes.append("JUMPTABLE_TARGET")
            else:
                reachable = sorted(set(audited))
        self.emit_switch(insn, target, reachable, sec)

    def emit_switch(self, insn: dict, target: str, cases: list[int], sec: dict) -> None:
        """Compares the dispatch value section-relative: a computed target carries the load bias its
        section's symbol carries, so subtracting that section's own bias recovers the dumped address."""
        self.data_sections.add(sec["name"])
        value, bias, rebased = self.read(target), self.tmp(), self.tmp()
        self.emit(f"{bias} = sub i64 ptrtoint (ptr @sec_{sec['name']} to i64), {sec['va']}")
        self.emit(f"{rebased} = sub i64 {value}, {bias}")
        default = f"U{insn['a']:x}"
        self.pending_tail.append((default, None))
        arms = " ".join(f"i64 {c}, label %{self.label(c)}" for c in cases)
        self.emit(f"switch i64 {rebased}, label %{default} [{arms}]")

    def landing_blocks(self) -> None:
        """Appends the block every post-call check branches to: land on a pad this frame owns, else return."""
        if not (self.unwind and self.call_checks):
            return

        def reg_word(name: str, offset: int) -> list[str]:
            return [
                f"  %{name}_slot = getelementptr i8, ptr %reg, i64 {offset}",
                f"  %{name} = load i64, ptr %{name}_slot, align 8",
            ]

        lines = ["EH_LAND:"]
        if self.pads:
            lines += reg_word("eh_owner", EH_PENDING_CFA)
            lines += ["  %eh_mine = icmp eq i64 %eh_owner, %eh_cfa", "  br i1 %eh_mine, label %EH_DISPATCH, label %EH_RET"]
            lines += ["EH_DISPATCH:"] + reg_word("eh_pad", EH_PENDING_PAD)
            arms = " ".join(f"i64 {pad}, label %{self.label(pad)}" for pad in sorted(self.pads))
            lines += [
                "  store i64 0, ptr %eh_pad_slot, align 8",
                f"  switch i64 %eh_pad, label %EH_BAD [{arms}]",
                "EH_BAD:",
                "  call void @abort()",
                "  unreachable",
            ]
            self.decls.add("declare void @abort()")
        else:
            lines += ["  br label %EH_RET"]
        lines += ["EH_RET:", "  ret void"]
        self.lines += lines

    def atomic_varnode(self, size: int) -> str:
        """A unique-space slot for an atomic's result, clear of every varnode the body already names."""
        self.atomic_count += 1
        offset = ATOMIC_RESULT_BASE + self.atomic_count * UNIQUE_STRIDE
        while any(t.startswith(f"unique,{offset:x},") for t in self.varnodes):
            offset += UNIQUE_STRIDE
        return f"unique,{offset:x},{size}"

    def lower_locks(self, insns: list[dict]) -> list[dict]:
        """Replaces each LOCK..UNLOCK region the analyzer accepts with one atomic op.

        The rewrite keeps the op count, so the op-index offsets Ghidra's branches carry still land
        where they did: displaced ops become NOP.
        """
        lowered = []
        for insn in insns:
            ops = insn["ops"]
            marks = [i for i, op in enumerate(ops) if op["op"] == "CALLOTHER" and op.get("user") in ("LOCK", "UNLOCK")]
            if len(marks) != 2 or [ops[i].get("user") for i in marks] != ["LOCK", "UNLOCK"]:
                lowered.append(insn)
                continue
            body = ops[marks[0] + 1 : marks[1]]
            plan = atomic_region(body, self.sections, self.atomic_varnode)
            if plan is None:
                lowered.append(insn)
                continue
            base = marks[0] + 1
            self.atomics += 1
            new = [NOP if i in marks else op for i, op in enumerate(ops)]
            for i, replacement in plan["edits"].items():
                new[base + i] = replacement
            new[base + plan["at"]] = {**plan["atomic"], "hoist": [body[i] for i in plan["hoist"]]}
            lowered.append({**insn, "ops": new})
        return lowered

    def atomic(self, insn: dict, k: int, out: str, ins: list[str], op: dict) -> None:
        """One x86 locked operation: a sys-scope seq_cst atomic, fenced on both sides."""
        for hoisted in op.get("hoist") or ():
            self.lift_op(insn, k, hoisted)
        ty = itype(op["width"])
        p = self.pointer(ins[0])
        self.emit('fence syncscope("sys") seq_cst')
        if op["user"] == "cmpxchg":
            pair, old = self.tmp(), self.tmp()
            self.emit(
                f'{pair} = cmpxchg ptr {p}, {ty} {self.read(ins[1])}, {ty} {self.read(ins[2])}'
                ' syncscope("sys") seq_cst seq_cst, align 1'
            )
            self.emit(f"{old} = extractvalue {{ {ty}, i1 }} {pair}, 0")
            self.write(out, old)
        else:
            v = self.tmp()
            self.emit(f'{v} = atomicrmw {op["user"]} ptr {p}, {ty} {self.read(ins[1])} syncscope("sys") seq_cst, align 1')
            self.write(out, v)
        self.emit('fence syncscope("sys") seq_cst')

    def run(self) -> Lifted:
        insns = self.lower_locks(self.fn["insns"])
        if self.pads and not self.unwind:
            self.holes.append("EH_PAD_WITHOUT_UNWIND")
        elif any(pad not in self.addrs for pad in self.pads):
            self.holes.append("EH_PAD_NOT_INSN")
            self.pads = frozenset(pad for pad in self.pads if pad in self.addrs)
        self.pending_tail: list[tuple[str, int | None]] = []
        if not insns:
            self.lines.append("entry:\n  unreachable")
        else:
            self.lines.append(f"entry:\n  br label %{self.label(insns[0]['a'])}")
        for insn in insns:
            ops = insn["ops"]
            if insn["a"] in self.branch_targets | self.pads:
                self.trapped = False
            if not ops:
                self.lines.append(f"{self.label(insn['a'])}:")
                self.terminate(self.next_label({**insn, "ops": [None]}, 0))
                continue
            for k, op in enumerate(ops):
                self.lines.append(f"{self.label(insn['a'], k)}:")
                if self.trapped:
                    self.emit("unreachable")
                    continue
                try:
                    ended = self.lift_op(insn, k, op)
                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    self.holes.append(f"{op['op']}:{exc}")
                    ended = False
                if not ended:
                    self.terminate(self.next_label(insn, k))
        for stub, target in self.pending_tail:
            self.lines.append(f"{stub}:")
            if target is None:
                if stub in self.hole_stubs:
                    self.emit_hole(self.hole_stubs[stub])
                else:
                    self.emit("unreachable")
            else:
                self.emit(f"call void @sub_{target:x}(ptr %reg)")
                self.emit("ret void")
        self.landing_blocks()
        header = f"define void @sub_{self.start:x}(ptr %reg) {{"
        body = "\n".join(self.lines)
        uniq = f"  %uniq = alloca [{max(self.unique_bytes, UNIQUE_STRIDE)} x i8], align 16"
        if self.unwind and self.call_checks:
            uniq += "\n  %eh_rsp_slot = getelementptr i8, ptr %reg, i64 32"
            uniq += "\n  %eh_rsp = load i64, ptr %eh_rsp_slot, align 8"
            uniq += "\n  %eh_cfa = add i64 %eh_rsp, 8"
        ir = f"{header}\n{body}\n}}\n".replace("entry:\n", f"entry:\n{uniq}\n", 1)
        return Lifted(
            self.start,
            ir,
            self.holes,
            self.externs,
            self.decls,
            self.indirect_calls,
            self.data_sections,
            self.unmapped,
            self.tail_calls,
            self.proven_tail_calls,
            self.unproven_branchind,
            self.tables_audited,
            self.evidence_switches,
            self.atomics,
        )


def lift_body(
    fn: dict,
    sections: list[dict] | tuple = (),
    *,
    call_dispatch: bool = False,
    unwind: bool = False,
    pads: frozenset = frozenset(),
    evidence=None,
    trap_holes: bool = False,
    entries: frozenset | None = None,
) -> Lifted:
    return BodyLifter(
        fn,
        sections,
        call_dispatch=call_dispatch,
        unwind=unwind,
        pads=pads,
        evidence=evidence,
        trap_holes=trap_holes,
        entries=entries,
    ).run()


def section_global(name: str, image: bytes | None, patches: tuple = (), constant: bool = False) -> str:
    kind = "constant" if constant else "global"
    if image is None:
        if patches:
            raise ValueError(f"section {name} has relocated words but no image")
        return f"@sec_{name} = external global i8"
    if not patches:
        if not any(image):
            return f"@sec_{name} = {kind} [{len(image)} x i8] zeroinitializer, align 16"
        data = "".join(f"\\{b:02X}" for b in image)
        return f'@sec_{name} = {kind} [{len(image)} x i8] c"{data}", align 16'
    types, fields, cursor = [], [], 0

    def bytes_field(chunk: bytes) -> None:
        types.append(f"[{len(chunk)} x i8]")
        if not any(chunk):
            fields.append(f"[{len(chunk)} x i8] zeroinitializer")
            return
        fields.append(f'[{len(chunk)} x i8] c"' + "".join(f"\\{b:02X}" for b in chunk) + '"')

    for patch in sorted(patches, key=lambda p: p.offset):
        if patch.offset < cursor:
            raise ValueError(f"relocated words overlap at {name}+{patch.offset:#x}")
        if patch.offset + 8 > len(image):
            raise ValueError(f"relocated word at {name}+{patch.offset:#x} lies past the end of the section")
        if patch.offset > cursor:
            bytes_field(image[cursor : patch.offset])
        if patch.code is not None:
            types.append("i64")
            fields.append(f"i64 {patch.code}")
        elif patch.function is not None:
            types.append("ptr")
            fields.append(f"ptr @sub_{patch.function:x}")
        elif patch.literal is not None:
            types.append("i64")
            fields.append(f"i64 {patch.literal}")
        elif patch.host is not None:
            types.append("ptr")
            fields.append(f"ptr @{patch.host}")
        else:
            target, offset = patch.target
            types.append("ptr")
            fields.append(f"ptr getelementptr (i8, ptr @sec_{target}, i64 {offset})")
        cursor = patch.offset + 8
    if cursor < len(image):
        bytes_field(image[cursor:])
    return f"@sec_{name} = {kind} <{{ {', '.join(types)} }}> <{{ {', '.join(fields)} }}>, align 16"


def module_for(
    bodies: list[Lifted],
    section_images: dict[str, bytes] | None = None,
    patches: list | tuple = (),
    sections: list | tuple = (),
    readonly: frozenset | set = frozenset(),
) -> str:
    """`patches` are relocated words (lift_reloc.Patch); their sections, and any data section they point at, are defined.

    `sections` names further sections to define, for a module that holds the data the bodies' modules leave external,
    and `readonly` the sections to define as constants.
    """
    defined = {b.start for b in bodies}
    externs = set().union(*(b.externs for b in bodies)) - defined if bodies else set()
    externs |= {p.function for p in patches if p.function is not None} - defined
    decls = set().union(*(b.decls for b in bodies)) if bodies else set()
    parts = sorted(decls)
    sections = set(sections) | (set().union(*(b.data_sections for b in bodies)) if bodies else set())
    by_section: dict[str, list] = {}
    for patch in patches:
        by_section.setdefault(patch.section, []).append(patch)
        sections.add(patch.section)
        if patch.target:
            sections.add(patch.target[0])
    parts += [section_global(n, (section_images or {}).get(n), by_section.get(n, ()), n in readonly) for n in sorted(sections)]
    parts += [f"@{h} = external global i8" for h in sorted({p.host for p in patches if p.host})]
    parts += [f"declare void @sub_{a:x}(ptr)" for a in sorted(externs)]
    parts += [b.ir for b in bodies]
    return "\n".join(parts) + "\n"
