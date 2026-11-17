"""Translate Ghidra raw per-instruction pcode to textual LLVM IR.

Each lifted body becomes `define void @sub_<addr>(ptr %reg)`: the register file is a byte
array passed in, the unique (temporary) space is a local byte array, memory is the host
address space. Anything the emitter cannot translate is recorded in `holes` instead of
being skipped silently, so a clean `holes` list means every pcode op in the body lifted.
"""

from __future__ import annotations

from dataclasses import dataclass, field

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
PACKED_DIVISION = {"divps": (4, 4), "divpd": (2, 8)}
PACKED_MINMAX = {"minps": (4, 4, "olt"), "maxps": (4, 4, "ogt")}
PACKED_WIDTH = 16
# Register-file words the guest unwinder and lifted code share: the landing pad to enter (0 when none is pending) and the frame that owns it.
EH_PENDING_PAD = 0x1F00
EH_PENDING_CFA = 0x1F08
# Ghidra's unique-space offsets are sparse; a temporary's slot is at least this wide, so it can hold a 256-bit value.
UNIQUE_STRIDE = 32


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
    """The net rsp change of one instruction: adds and subs of a constant, plus the 8 a CALL pushes.

    None means the frame cannot be balanced by counting, because rsp is written some other way
    (a POP, `leave`, a copy from a register or a temporary, an add or sub by a computed value).
    """
    delta = 0
    for op in insn["ops"]:
        if op.get("out") != RSP:
            if op["op"] == "CALL":
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


def is_packed_lane_op(out: str | None, ins: list[str]) -> bool:
    """The packed SSE ops arrive as destination = destination <op> source, every varnode 16 bytes wide."""
    return (
        out is not None
        and len(ins) >= 3
        and parse_varnode(out)[2] == PACKED_WIDTH
        and ins[1] == out
        and parse_varnode(ins[2])[2] == PACKED_WIDTH
    )


def is_movmskps_op(out: str | None, ins: list[str]) -> bool:
    """MOVMSKPS repeats a 32-bit register destination before its single XMM source."""
    return (
        out is not None
        and len(ins) == 3
        and parse_varnode(out)[0] == "register"
        and parse_varnode(out)[2] == 4
        and ins[1] == out
        and parse_varnode(ins[2])[0] == "register"
        and parse_varnode(ins[2])[2] == PACKED_WIDTH
    )


def is_pshuflw_op(out: str | None, ins: list[str]) -> bool:
    """PSHUFLW adds a constant immediate selector to the packed destination/source shape."""
    return (
        len(ins) == 4
        and is_packed_lane_op(out, ins)
        and parse_varnode(ins[3])[0] == "const"
        and 0 <= parse_varnode(ins[3])[1] <= 0xFF
    )


def itype(size: int) -> str:
    return f"i{size * 8}"


class BodyLifter:
    def __init__(
        self,
        fn: dict,
        sections: list[dict] | tuple = (),
        *,
        call_dispatch: bool = False,
        unwind: bool = False,
        pads: frozenset = frozenset(),
    ):
        self.fn = fn
        self.call_dispatch = call_dispatch
        self.unwind = unwind
        self.pads = frozenset(pads)
        self.call_checks = 0
        self.sections = list(sections)
        self.data_sections: set[str] = set()
        self.unmapped = 0
        self.unique_blocks: list[tuple[int, int, int]] = []
        self.unique_bytes = 0
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
        self.proof = site_proof(fn)
        self.frame = site_frame(fn)
        self.counter = 0
        self.addrs = {i["a"] for i in fn["insns"]}
        self.next_addr = {i["a"]: i["a"] + i["len"] for i in fn["insns"]}

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

    def terminate(self, target: str | None) -> None:
        self.emit(f"br label %{target}" if target else "unreachable")

    def lift_op(self, insn: dict, k: int, op: dict) -> bool:
        """Emits one op; returns True when the op ended the block."""
        name, out, ins = op["op"], op["out"], op.get("in") or []
        sz = lambda t: parse_varnode(t)[2]
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
            self.call_direct(ins[0])
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
            elif user == "movmskps" and is_movmskps_op(out, ins):
                self.packed_sign_mask(out, ins[2])
            elif user == "pshuflw" and is_pshuflw_op(out, ins):
                self.shuffle_low_words(out, ins[2], parse_varnode(ins[3])[1])
            else:
                self.holes.append(f"CALLOTHER:{user}")
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

    def shuffle_low_words(self, out: str, src: str, selector: int) -> None:
        source = self.read(src)
        indices = [(selector >> (2 * lane)) & 3 for lane in range(4)] + list(range(4, 8))
        pieces = [self.fit(self.lane(source, 128, index, 16), 16, 128) for index in indices]
        self.merge_lanes(out, pieces, 16, 128)

    def packed_sign_mask(self, out: str, src: str) -> None:
        value = self.read(src)
        pieces = []
        for index in range(4):
            lane = self.lane(value, 128, index, 32)
            sign = self.tmp()
            self.emit(f"{sign} = lshr i32 {lane}, 31")
            pieces.append(sign)
        self.merge_lanes(out, pieces, 1, 32)

    def float_op(self, name: str, out: str, ins: list[str]) -> None:
        osz, isz = parse_varnode(out)[2], parse_varnode(ins[0])[2]
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

    def call_direct(self, target: str) -> None:
        space, offset, _ = parse_varnode(target)
        if space != "ram":
            self.holes.append("CALL_TARGET")
            return
        self.externs.add(offset)
        self.emit(f"call void @sub_{offset:x}(ptr %reg)")
        self.pending_check()

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

    def branch(self, insn: dict, k: int, target: str) -> bool:
        space, offset, _ = parse_varnode(target)
        label = self.jump_target(target, insn, k)
        if label:
            self.emit(f"br label %{label}")
        elif space == "ram" and not (self.start <= offset < self.start + self.size):
            self.externs.add(offset)
            self.emit(f"call void @sub_{offset:x}(ptr %reg)")
            self.emit("ret void")
        else:
            self.holes.append("UNDECODED_TARGET")
            self.emit("unreachable")
        return True

    def cbranch(self, insn: dict, k: int, ins: list[str]) -> bool:
        taken = self.jump_target(ins[0], insn, k)
        if taken is None:
            space, offset, _ = parse_varnode(ins[0])
            if space == "ram" and not (self.start <= offset < self.start + self.size):
                stub = f"X{insn['a']:x}_{k}"
                self.externs.add(offset)
                self.pending_tail = getattr(self, "pending_tail", []) + [(stub, offset)]
                taken = stub
            else:
                self.holes.append("UNDECODED_TARGET")
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
        flat = []
        for earlier in self.fn["insns"]:
            if earlier is insn:
                flat += earlier["ops"][:k]
                break
            flat += earlier["ops"]
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

    def branch_indirect(self, insn: dict, k: int, target: str) -> None:
        """Lowers a BRANCHIND as a switch, or as an indirect call and a return for a loaded-pointer tail call.

        `jmp rax` with rsp at its entry value is `call rax` then `ret` only when the target is another
        function, so rsp balance licenses the rewrite just for a target read from memory.
        """
        cases = self.tables.get(insn["a"])
        sec = self.last_data
        if not cases:
            # A bare `jmp reg` lowers as a call and a return when the target is a loaded pointer (the
            # original rule), or when rsp is proven at its entry value and the target is read from memory.
            # The balance alone never licenses it: a frameless switch also has rsp at entry.
            load_traced = self.defined_by_load(insn, k, target)
            verdict = self.frame.get(insn["a"], {})
            balanced = verdict.get("reason") == "" and self.defined_by_load(insn, k, target, slots=True)
            if not (load_traced or balanced):
                self.unproven_branchind.append(
                    {
                        "a": insn["a"],
                        "reason": verdict.get("reason") or "no path in the dump reaches the site",
                        "rsp_delta": verdict.get("rsp_delta"),
                    }
                )
                self.holes.append("BRANCHIND")
                self.emit("unreachable")
                return
            self.tail_calls += 1
            if balanced:
                self.proven_tail_calls += 1
            else:
                self.unproven_branchind.append(
                    {
                        "a": insn["a"],
                        "reason": verdict.get("reason") or "no path in the dump reaches the site",
                        "rsp_delta": verdict.get("rsp_delta"),
                    }
                )
            self.call_indirect(target, check=False)
            self.emit("ret void")
            return
        if sec is None:
            self.holes.append("BRANCHIND")
            self.emit("unreachable")
            return
        value, bias, rebased = self.read(target), self.tmp(), self.tmp()
        self.emit(f"{bias} = sub i64 ptrtoint (ptr @sec_{sec['name']} to i64), {sec['va']}")
        self.emit(f"{rebased} = sub i64 {value}, {bias}")
        reachable = sorted({c for c in cases if c in self.addrs})
        if len(reachable) != len(set(cases)):
            self.holes.append("JUMPTABLE_TARGET")
        default = f"U{insn['a']:x}"
        self.pending_tail.append((default, None))
        arms = " ".join(f"i64 {c}, label %{self.label(c)}" for c in reachable)
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

    def run(self) -> Lifted:
        insns = self.fn["insns"]
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
            if not ops:
                self.lines.append(f"{self.label(insn['a'])}:")
                self.terminate(self.next_label({**insn, "ops": [None]}, 0))
                continue
            for k, op in enumerate(ops):
                self.lines.append(f"{self.label(insn['a'], k)}:")
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
        )


def lift_body(
    fn: dict,
    sections: list[dict] | tuple = (),
    *,
    call_dispatch: bool = False,
    unwind: bool = False,
    pads: frozenset = frozenset(),
) -> Lifted:
    return BodyLifter(fn, sections, call_dispatch=call_dispatch, unwind=unwind, pads=pads).run()


def section_global(name: str, image: bytes | None, patches: tuple = ()) -> str:
    if image is None:
        if patches:
            raise ValueError(f"section {name} has relocated words but no image")
        return f"@sec_{name} = external global i8"
    if not patches:
        data = "".join(f"\\{b:02X}" for b in image)
        return f'@sec_{name} = global [{len(image)} x i8] c"{data}", align 16'
    types, fields, cursor = [], [], 0

    def bytes_field(chunk: bytes) -> None:
        types.append(f"[{len(chunk)} x i8]")
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
        else:
            target, offset = patch.target
            types.append("ptr")
            fields.append(f"ptr getelementptr (i8, ptr @sec_{target}, i64 {offset})")
        cursor = patch.offset + 8
    if cursor < len(image):
        bytes_field(image[cursor:])
    return f"@sec_{name} = global <{{ {', '.join(types)} }}> <{{ {', '.join(fields)} }}>, align 16"


def module_for(bodies: list[Lifted], section_images: dict[str, bytes] | None = None, patches: list | tuple = ()) -> str:
    """`patches` are relocated words (lift_reloc.Patch); their sections, and any data section they point at, are defined."""
    defined = {b.start for b in bodies}
    externs = set().union(*(b.externs for b in bodies)) - defined if bodies else set()
    decls = set().union(*(b.decls for b in bodies)) if bodies else set()
    parts = sorted(decls)
    sections = set().union(*(b.data_sections for b in bodies)) if bodies else set()
    by_section: dict[str, list] = {}
    for patch in patches:
        by_section.setdefault(patch.section, []).append(patch)
        sections.add(patch.section)
        if patch.target:
            sections.add(patch.target[0])
    parts += [section_global(n, (section_images or {}).get(n), by_section.get(n, ())) for n in sorted(sections)]
    parts += [f"declare void @sub_{a:x}(ptr)" for a in sorted(externs)]
    parts += [b.ir for b in bodies]
    return "\n".join(parts) + "\n"
