"""The arm64 lowering of Ghidra's LOCK..UNLOCK atomic regions.

Ghidra brackets the read-modify-write of each `lock`-prefixed instruction with a `CALLOTHER`
userop named LOCK and UNLOCK. A region is lowered only when its ops describe one memory location
read and written once; anything else keeps the `CALLOTHER:LOCK` hole, because dropping the
markers would emit a non-atomic sequence. `tests/fixtures/lift/lock_regions.json` holds regions
copied out of the pcode dump and pinned against it; the shape builders below are canonicalized
from dumped regions so the width and operand variants can be exercised, and the executed checks
compare the lifted body against a Python model of the flags each instruction leaves behind.
"""

import ctypes
import json
import os
import pytest
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pcode_lift as pl

LLVM = Path("/opt/homebrew/opt/llvm/bin")
requires_llvm = pytest.mark.skipif(
    not (LLVM / "opt").exists() or sys.platform != "darwin" or os.uname().machine != "arm64",
    reason="needs the LLVM toolchain and an arm64 host",
)


class GuestAddress(int):
    """A guest address the host buffer stands in for; `call` biases it to the buffer's real address."""

    __add__ = lambda self, other: GuestAddress(int(self) + other)
    __sub__ = lambda self, other: GuestAddress(int(self) - other)


CF, PF, ZF, SF, OF = 0x200, 0x202, 0x206, 0x207, 0x20B
REG_SIZE = 8192
MEM = GuestAddress(0x1000)
DEFAULT = "const,1b1,4"


def op(name, out, *ins, **extra):
    return {"op": name, "out": out, "in": list(ins), **extra}


def insn(addr, length, *ops):
    return {"a": addr, "len": length, "m": "x", "ops": list(ops)}


def body(*insns, start=0x1000, size=None):
    size = size if size is not None else sum(i["len"] for i in insns)
    return {"start": start, "size": size, "insns": list(insns)}


def region(*ops):
    """One instruction: the LOCK marker, the region's ops, the UNLOCK marker, then a return."""
    return body(
        insn(
            0x1000,
            9,
            op("CALLOTHER", None, "const,11,4", user="LOCK"),
            *ops,
            op("CALLOTHER", None, "const,12,4", user="UNLOCK"),
        ),
        insn(0x1009, 1, op("RETURN", None, "register,288,8")),
    )


def lift(*ops, sections=()):
    return pl.lift_body(region(*ops), sections)


def load(varnode, addr):
    return op("LOAD", varnode, DEFAULT, addr)


def store(addr, value):
    return op("STORE", None, DEFAULT, addr, value)


def atomics(ir):
    return re.findall(r"= (atomicrmw \w+|cmpxchg)\b", ir)


def fences(ir):
    return ir.count('fence syncscope("sys") seq_cst')


def v(size):
    return {1: "1", 2: "2", 4: "4", 8: "8", 16: "16"}[size]


# --- region shape builders -----------------------------------------------------------------
#
# Canonicalized from dumped regions so operand and width variants can be exercised; the verbatim
# copies are in `tests/fixtures/lift/lock_regions.json`. Executed cases bias one register that the
# region's address chain reads onto a host buffer (see `call`).

ADDR, VAL = "unique,8e00,8", "unique,d300,4"

# `lock <op> [mem], <operand>`: the arithmetic op, the operand, the op that writes CF, the op that
# writes OF, and the displacement in the region's address chain. Modelled on 0x2089250 (`add`),
# 0x2111206 (subtract 1, which leaves carry alone) and 0x20f2c40 (or, which zeroes carry and
# overflow before the read), with the varnode names and displacement normalized.
LOCKED_ARITHMETIC = {
    "add": ("INT_ADD", "register,30,{t}", "INT_CARRY", "INT_SCARRY", 0x38),
    "add1": ("INT_ADD", "const,1,{t}", "INT_CARRY", "INT_SCARRY", 0x38),
    "sub1": ("INT_SUB", "const,1,{t}", None, "INT_SBORROW", -0x80),
    "or": ("INT_OR", "register,30,{t}", None, None, 0x38),
}


def arithmetic_memory(name="add", size=4, computed_address=True):
    """One locked read-modify-write, with the flags Ghidra recomputes from the value it stores.

    Every flag is derived from a fresh load of the location, so a body that kept those loads would
    read a word another thread could have changed between the read and the write.
    """
    t = v(size)
    arith, operand, carry, overflow, disp = LOCKED_ARITHMETIC[name]
    operand, value = operand.format(t=t), f"unique,d300,{t}"
    addr = ADDR if computed_address else "register,b8,8"
    ops = [op("INT_ADD", ADDR, "register,0,8", f"const,{disp % (1 << 64):x},8")] if computed_address else []
    if name == "or":
        ops += [op("COPY", "register,200,1", "const,0,1"), op("COPY", "register,20b,1", "const,0,1")]
    if carry:
        ops += [load(value, addr), op(carry, "register,200,1", value, operand)]
    if overflow:
        ops += [load(value, addr), op(overflow, "register,20b,1", value, operand)]
    ops += [
        load(value, addr),
        op(arith, value, value, operand),
        store(addr, value),
        load(value, addr),
        op("INT_SLESS", "register,207,1", value, f"const,0,{t}"),
        load(value, addr),
        op("INT_EQUAL", "register,206,1", value, f"const,0,{t}"),
        load(value, addr),
        op("INT_AND", f"unique,58300,{t}", value, f"const,ff,{t}"),
        op("POPCOUNT", "unique,58400,1", f"unique,58300,{t}"),
        op("INT_AND", "unique,58500,1", "unique,58400,1", "const,1,1"),
        op("INT_EQUAL", "register,202,1", "unique,58500,1", "const,0,1"),
    ]
    return ops


def xchg_memory(size=4):
    """`0x2092420`: `xchg eax, [rbx+8]` - the old value is kept, the register is stored, the old value is handed back."""
    t = v(size)
    value, kept = f"unique,d300,{t}", f"unique,1a0400,{t}"
    return [
        op("INT_ADD", ADDR, "register,b0,8", "const,8,8"),
        load(value, ADDR),
        op("COPY", kept, value),
        op("COPY", value, f"register,0,{t}"),
        store(ADDR, value),
        op("COPY", f"register,0,{t}", kept),
    ]


def xchg_static(size=4):
    """The exchange at 0x2057cd0 with the address folded to a constant `.data` word, so both accesses are `ram` COPYs."""
    t = v(size)
    kept, word = f"unique,1a0400,{t}", f"ram,536aa80,{t}"
    return [
        op("COPY", kept, word),
        op("COPY", word, f"register,0,{t}"),
        op("COPY", f"register,0,{t}", kept),
    ]


def xadd_memory(size=4):
    """`0x2056510`: `lock xadd [rax-8], ecx` - the sum is stored and the old value goes back to ECX."""
    t = v(size)
    value, sum_, operand = f"unique,d300,{t}", f"unique,19ff00,{t}", f"register,8,{t}"
    return [
        op("INT_ADD", ADDR, "register,0,8", "const,fffffffffffffff8,8"),
        load(value, ADDR),
        op("INT_CARRY", "register,200,1", value, operand),
        load(value, ADDR),
        op("INT_SCARRY", "register,20b,1", value, operand),
        load(value, ADDR),
        op("INT_ADD", sum_, value, operand),
        load(value, ADDR),
        op("COPY", f"register,8,{t}", value),
        op("INT_ZEXT", "register,8,8", f"register,8,{t}"),
        op("COPY", value, sum_),
        store(ADDR, value),
        op("INT_SLESS", "register,207,1", sum_, f"const,0,{t}"),
        op("INT_EQUAL", "register,206,1", sum_, f"const,0,{t}"),
        op("INT_AND", f"unique,58300,{t}", sum_, f"const,ff,{t}"),
        op("POPCOUNT", "unique,58400,1", f"unique,58300,{t}"),
        op("INT_AND", "unique,58500,1", "unique,58400,1", "const,1,1"),
        op("INT_EQUAL", "register,202,1", "unique,58500,1", "const,0,1"),
    ]


def cas_memory(size=4):
    """`0x2068010`: `lock cmpxchg [r18], ecx` - EAX is compared, the branch chooses exchange or reload."""
    t = v(size)
    value, kept, diff, addr = f"unique,d300,{t}", f"unique,19ab00,{t}", f"unique,19ad00,{t}", "register,18,8"
    zero = f"const,0,{t}"
    return [
        load(value, addr),
        op("COPY", kept, value),
        op("INT_LESS", "register,200,1", f"register,0,{t}", kept),
        op("INT_SBORROW", "register,20b,1", f"register,0,{t}", kept),
        op("INT_SUB", diff, f"register,0,{t}", kept),
        op("INT_SLESS", "register,207,1", diff, zero),
        op("INT_EQUAL", "register,206,1", diff, zero),
        op("INT_AND", f"unique,58300,{t}", diff, f"const,ff,{t}"),
        op("POPCOUNT", "unique,58400,1", f"unique,58300,{t}"),
        op("INT_AND", "unique,58500,1", "unique,58400,1", "const,1,1"),
        op("INT_EQUAL", "register,202,1", "unique,58500,1", "const,0,1"),
        op("CBRANCH", None, "const,4,4", "register,206,1"),
        op("COPY", f"register,0,{t}", kept),
        op("INT_ZEXT", "register,0,8", f"register,0,{t}"),
        op("BRANCH", None, "const,3,4"),
        op("COPY", value, f"register,8,{t}"),
        store(addr, value),
    ]


def cas16b_memory():
    """`lock cmpxchg16b` as dumped at 0x20c82c0: RDX:RAX compared against the 16-byte word, RBX:RCX exchanged in."""
    old, kept = "unique,d600,16", "unique,19be00,16"
    return [
        op("INT_ADD", ADDR, "register,b0,8", "const,40,8"),
        load(old, ADDR),
        op("COPY", kept, old),
        op("INT_ZEXT", "unique,19bf00,16", "register,10,8"),
        op("INT_LEFT", "unique,19c000,16", "unique,19bf00,16", "const,40,4"),
        op("INT_ZEXT", "unique,19c100,16", "register,0,8"),
        op("INT_OR", "unique,19c200,16", "unique,19c000,16", "unique,19c100,16"),
        op("INT_EQUAL", "register,206,1", "unique,19c200,16", kept),
        op("INT_EQUAL", "unique,19c400,1", "register,206,1", "const,1,1"),
        op("CBRANCH", None, "const,4,4", "unique,19c400,1"),
        op("SUBPIECE", "register,10,8", kept, "const,8,4"),
        op("SUBPIECE", "register,0,8", kept, "const,0,4"),
        op("BRANCH", None, "const,6,4"),
        op("INT_ZEXT", "unique,19c700,16", "register,8,8"),
        op("INT_LEFT", "unique,19c800,16", "unique,19c700,16", "const,40,4"),
        op("INT_ZEXT", "unique,19c900,16", "register,18,8"),
        op("INT_OR", old, "unique,19c800,16", "unique,19c900,16"),
        store(ADDR, old),
    ]


# --- verbatim regions from the dump --------------------------------------------------------
#
# `tests/fixtures/lift/lock_regions.json` holds LOCK..UNLOCK op lists copied out of the
# authoritative pcode dump: the shortest region for each locked mnemonic, plus the narrowest
# region at each access width. They are the dump's own ops, varnodes and displacements. These
# cases re-read the dump to prove the fixture is still what was dumped, and lift the body that
# contains each region so the emitted atomic is checked against the instruction Ghidra decoded.

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "lift" / "lock_regions.json"
DUMP = Path(".tools/lift-image-full")
LOCKED_FORM = {
    "add.lock": "atomicrmw add",
    "inc.lock": "atomicrmw add",
    "xadd.lock": "atomicrmw add",
    "or.lock": "atomicrmw or",
    "sub.lock": "atomicrmw sub",
    "dec.lock": "atomicrmw sub",
    "xchg": "atomicrmw xchg",
    "cmpxchg.lock": "cmpxchg",
    "cmpxchg16b.lock": "cmpxchg",
}
_fixture = json.loads(FIXTURE.read_text())
_rows: dict[int, tuple[dict, list]] = {}


def access_width(ops: list[dict]) -> int:
    """The width of the locked access: the address operand of a `ram` form, the stored value of a LOAD/STORE form."""
    for o in ops:
        for operand in [o.get("out")] + list(o.get("in") or []):
            if operand and operand.startswith("ram,"):
                return int(operand.rsplit(",", 1)[1])
    for o in ops:
        if o["op"] == "STORE":
            return int(o["in"][2].rsplit(",", 1)[1])
    raise AssertionError(f"no locked access found in {ops}")


def dump_body(address: int) -> tuple[dict, list]:
    """The dumped row and section table for one body, read once from the shards and cached."""
    if address not in _rows:
        if not DUMP.is_dir():
            pytest.skip(f"no pcode dump at {DUMP}")
        for path in sorted(DUMP.glob("pcode-*.jsonl")):
            if not re.fullmatch(r"pcode-\d+\.jsonl", path.name):
                continue
            lines = path.read_text().splitlines()
            sections = json.loads(lines[1])["sections"]
            for line in lines[2:]:
                row = json.loads(line)
                if row.get("start") == address:
                    _rows[address] = (row, sections)
            if address in _rows:
                break
    return _rows[address]


def dump_regions(address: int) -> list[list[dict]]:
    """Every LOCK..UNLOCK op list in the dumped body, in dump order."""
    row, _ = dump_body(address)
    regions = []
    for insn_row in row["insns"]:
        ops = insn_row["ops"]
        for i, marker in enumerate(ops):
            if marker["op"] != "CALLOTHER" or marker.get("user") != "LOCK":
                continue
            end = next(
                (j for j in range(i + 1, len(ops)) if ops[j]["op"] == "CALLOTHER" and ops[j].get("user") == "UNLOCK"),
                None,
            )
            regions.append(ops[i + 1 : end])
    return regions


def _id(entry: dict) -> str:
    return f'{entry["mnemonic"]}@{entry["address"]}'


def _form(entry: dict) -> str:
    """The emitted atomic for this region: LLVM puts the pointer first, then the value type."""
    return rf"{LOCKED_FORM[entry['mnemonic']]} ptr \S+, i{8 * access_width(entry['ops'])}\b"


@pytest.mark.parametrize("entry", _fixture["regions"], ids=_id)
def test_a_fixture_region_is_the_dumped_region(entry):
    dumped = dump_regions(int(entry["address"], 16))
    assert entry["ops"] in dumped, (
        f"{_id(entry)} is not one of the {len(dumped)} regions dumped there "
        f"(fixture {len(entry['ops'])} ops, dump {[len(r) for r in dumped]})"
    )


@pytest.mark.parametrize("entry", _fixture["regions"], ids=_id)
def test_a_fixture_body_lowers_its_region_as_one_atomic(entry):
    row, sections = dump_body(int(entry["address"], 16))
    lifted = pl.lift_body(row, sections)
    assert "CALLOTHER:LOCK" not in lifted.holes
    assert "CALLOTHER:UNLOCK" not in lifted.holes
    assert lifted.atomics >= 1
    assert re.search(_form(entry), lifted.ir), f"{_id(entry)} emitted no {_form(entry)}"


@pytest.mark.parametrize("entry", _fixture["regions"], ids=_id)
def test_a_fixture_atomic_is_fenced_on_both_sides(entry):
    row, sections = dump_body(int(entry["address"], 16))
    lines = pl.lift_body(row, sections).ir.splitlines()
    blocks, current = {}, None
    for text in lines:
        if re.fullmatch(r"[A-Za-z_%][\w.]*:", text.strip()):
            current = text.strip()[:-1]
            blocks[current] = []
        elif current is not None:
            blocks[current].append(text.strip())
    for name, body in blocks.items():
        hits = [i for i, text in enumerate(body) if re.search(_form(entry), text)]
        if not hits:
            continue
        i = hits[0]
        fences = [j for j, text in enumerate(body) if text == 'fence syncscope("sys") seq_cst']
        assert any(j < i for j in fences), f"{_id(entry)} atomic in {name} has no acquire fence"
        assert any(j > i for j in fences), f"{_id(entry)} atomic in {name} has no release fence"
        assert body[i].rstrip().endswith(", align 1"), f"{_id(entry)} atomic in {name} is not alignment-tolerant"
        return
    pytest.fail(f"{_id(entry)} emitted no {_form(entry)}")


# --- structural expectations ---------------------------------------------------------------


def test_lock_add_lowers_to_one_atomic_add_and_keeps_the_flags():
    result = lift(*arithmetic_memory("add"))
    assert result.holes == []
    assert atomics(result.ir) == ["atomicrmw add"]
    assert fences(result.ir) == 2
    assert result.ir.count("inttoptr") == 1, "the region's loads and store are replaced by the atomic"
    assert "llvm.uadd.with.overflow" in result.ir
    assert "llvm.sadd.with.overflow" in result.ir
    assert "llvm.ctpop" in result.ir
    assert re.search(r"atomicrmw add ptr %t\d+, i32 %t\d+ syncscope\(\"sys\"\) seq_cst", result.ir)


def test_the_lifter_reports_the_atomics_it_lowered():
    assert lift(*arithmetic_memory("add")).atomics == 1
    assert lift(*cas_memory()).atomics == 1
    assert lift(*cas16b_memory()).atomics == 1


def test_a_region_that_keeps_its_hole_reports_no_atomics():
    result = lift(*(xchg_memory() + [store("register,28,8", "register,0,4")]))
    assert "CALLOTHER:LOCK" in result.holes
    assert result.atomics == 0


def test_an_instruction_carrying_two_locked_regions_keeps_both_holes():
    """One region per instruction is the shape the rewrite understands; a second pair fails the whole instruction."""
    marker = lambda user: op("CALLOTHER", None, "const,11,4" if user == "LOCK" else "const,12,4", user=user)
    pair = xchg_memory()
    result = pl.lift_body(
        body(
            insn(0x1000, 9, marker("LOCK"), *pair, marker("UNLOCK"), marker("LOCK"), *pair, marker("UNLOCK")),
            insn(0x1009, 1, op("RETURN", None, "register,288,8")),
        )
    )
    assert result.atomics == 0
    assert "CALLOTHER:LOCK" in result.holes and "CALLOTHER:UNLOCK" in result.holes


def test_lock_add_with_the_address_in_a_register_is_one_atomic():
    assert atomics(lift(*arithmetic_memory("add", computed_address=False)).ir) == ["atomicrmw add"]


@pytest.mark.parametrize("name", ["add", "add1", "sub1", "or"])
@pytest.mark.parametrize("size", [1, 4, 8])
def test_every_locked_arithmetic_shape_lowers_to_one_atomic(name, size):
    result = lift(*arithmetic_memory(name, size))
    assert result.holes == []
    opname = "sub" if name == "sub1" else name.removesuffix("1")
    assert re.search(rf"atomicrmw {opname} ptr %t\d+, i{size * 8} \S+ syncscope\(\"sys\"\) seq_cst, align 1", result.ir), (
        result.ir
    )
    assert result.ir.count("inttoptr") == 1


def test_lock_or_lowers_to_one_atomic_or_with_the_zeroed_flags():
    result = lift(*arithmetic_memory("or", 8))
    assert result.holes == []
    assert re.search(r"atomicrmw or ptr %t\d+, i64 %t\d+ syncscope\(\"sys\"\) seq_cst", result.ir)


def test_lock_add_of_one_lowers_to_one_atomic_add_of_one():
    result = lift(*arithmetic_memory("add1", 4, computed_address=False))
    assert result.holes == []
    assert re.search(r"atomicrmw add ptr %t\d+, i32 1 syncscope\(\"sys\"\) seq_cst", result.ir)


@pytest.mark.parametrize("size", [1, 4, 8])
def test_lock_xchg_lowers_to_one_atomic_exchange(size):
    result = lift(*xchg_memory(size))
    assert result.holes == []
    assert atomics(result.ir) == ["atomicrmw xchg"]
    assert re.search(rf"atomicrmw xchg ptr %t\d+, i{size * 8} %t\d+ syncscope\(\"sys\"\) seq_cst", result.ir)


def test_lock_xchg_on_a_static_location_exchanges_the_section_word():
    sections = [{"name": "data", "va": 0x536A000, "size": 0x2000, "exec": False}]
    result = lift(*xchg_static(), sections=sections)
    assert result.holes == []
    assert atomics(result.ir) == ["atomicrmw xchg"]
    assert result.ir.count("@sec_data") == 1, "only the atomic may touch the section"


def test_a_static_location_outside_every_section_stays_a_hole():
    assert "CALLOTHER:LOCK" in lift(*xchg_static()).holes


def test_lock_cmpxchg_lowers_to_a_cmpxchg_guarded_by_the_compare():
    result = lift(*cas_memory())
    assert result.holes == []
    assert atomics(result.ir) == ["cmpxchg"]
    assert re.search(r"cmpxchg ptr %t\d+, i32 %t\d+, i32 %t\d+ syncscope\(\"sys\"\) seq_cst seq_cst", result.ir)
    assert fences(result.ir) == 2
    assert "br i1" in result.ir, "the compare still decides which path runs"


@pytest.mark.parametrize("size", [1, 8])
def test_every_locked_cmpxchg_width_lowers_to_a_cmpxchg(size):
    assert atomics(lift(*cas_memory(size)).ir) == ["cmpxchg"]


def test_lock_cmpxchg16b_lowers_to_a_128_bit_cmpxchg():
    result = lift(*cas16b_memory())
    assert result.holes == []
    assert atomics(result.ir) == ["cmpxchg"]
    assert re.search(r"cmpxchg ptr %t\d+, i128 %t\d+, i128 %t\d+ syncscope\(\"sys\"\) seq_cst seq_cst", result.ir)


def test_lock_xadd_lowers_to_one_atomic_add():
    result = lift(*xadd_memory())
    assert result.holes == []
    assert atomics(result.ir) == ["atomicrmw add"]


def test_a_region_with_an_op_the_rewriter_does_not_model_keeps_the_hole():
    """The region's ops must all be ones the rewrite reasons about, not merely absent from a deny-list."""
    ops = arithmetic_memory("add")
    ops.insert(1, op("INT_2MULTIPLE", "unique,7700,4", "const,2,4", "const,2,4"))
    assert "CALLOTHER:LOCK" in lift(*ops).holes


def test_a_region_with_a_branch_that_is_not_the_compare_pair_keeps_the_hole():
    assert "CALLOTHER:LOCK" in lift(*arithmetic_memory("add"), op("BRANCH", None, "const,1,4")).holes


# --- shapes that must stay holes -----------------------------------------------------------


def test_a_region_that_reads_a_second_location_stays_a_hole():
    assert "CALLOTHER:LOCK" in lift(*(xchg_memory() + [load("unique,ffff,4", "register,28,8")])).holes


def test_a_region_that_writes_a_second_location_stays_a_hole():
    assert "CALLOTHER:LOCK" in lift(*(xchg_memory() + [store("register,28,8", "register,0,4")])).holes


def test_a_region_that_calls_stays_a_hole():
    ops = xchg_memory()
    assert "CALLOTHER:LOCK" in lift(*(ops[:2] + [op("CALL", None, "const,2000,8")] + ops[2:])).holes


def test_a_region_with_a_nested_lock_marker_stays_a_hole():
    ops = xchg_memory()
    nested = op("CALLOTHER", None, "const,11,4", user="LOCK")
    assert "CALLOTHER:LOCK" in lift(*(ops[:2] + [nested] + ops[2:])).holes


def test_a_region_without_an_unlock_marker_stays_a_hole():
    result = pl.lift_body(
        body(
            insn(0x1000, 9, op("CALLOTHER", None, "const,11,4", user="LOCK"), *xchg_memory()),
            insn(0x1009, 1, op("RETURN", None, "register,288,8")),
        )
    )
    assert "CALLOTHER:LOCK" in result.holes


def test_an_unlock_without_a_lock_stays_a_hole():
    result = pl.lift_body(
        body(
            insn(0x1000, 9, op("CALLOTHER", None, "const,12,4", user="UNLOCK"), *xchg_memory()),
            insn(0x1009, 1, op("RETURN", None, "register,288,8")),
        )
    )
    assert "CALLOTHER:UNLOCK" in result.holes


def test_a_region_whose_stored_value_is_not_an_atomic_arithmetic_stays_a_hole():
    ops = [load(VAL, "register,38,8"), op("INT_DIV", VAL, VAL, "register,0,4"), store("register,38,8", VAL)]
    assert "CALLOTHER:LOCK" in lift(*ops).holes


def test_a_region_that_reads_the_location_after_a_conditional_store_stays_a_hole():
    assert "CALLOTHER:LOCK" in lift(*(cas_memory() + [load(VAL, "register,18,8")])).holes


def test_a_region_that_rewrites_the_operand_it_reads_stays_a_hole():
    ops = [
        load(VAL, "register,38,8"),
        op("COPY", "register,30,4", "const,7,4"),
        op("INT_ADD", VAL, VAL, "register,30,4"),
        store("register,38,8", VAL),
    ]
    assert "CALLOTHER:LOCK" in lift(*ops).holes


def test_a_region_that_computes_the_exchanged_value_after_the_load_exchanges_that_value():
    ops = [
        load(VAL, "register,38,8"),
        op("COPY", "unique,1a0400,4", "register,0,4"),
        op("COPY", "register,0,4", "const,7,4"),
        op("COPY", VAL, "register,0,4"),
        store("register,38,8", VAL),
        op("COPY", "register,0,4", "unique,1a0400,4"),
    ]
    result = lift(*ops)
    assert result.holes == []
    assert re.search(r"atomicrmw xchg ptr %t\d+, i32 7 syncscope\(\"sys\"\) seq_cst", result.ir), result.ir
    assert "store i32" in result.ir, "the region's writeback of the old value to EAX is kept"


def test_a_region_whose_compared_value_is_not_the_memory_value_stays_a_hole():
    ops = [op for op in cas_memory() if op["op"] != "COPY" or op["out"] != "unique,19ab00,4"]
    assert "CALLOTHER:LOCK" in lift(*ops).holes


# --- executed against the x86 flag model ---------------------------------------------------

# The generic primitives an arm64 Apple target gets from its own C runtime. `align 1` makes LLVM
# lower an atomic to a call to one of these instead of inlining the exclusives, so the executed
# cases have to resolve them; anything else they reference has no provider here.
PLATFORM_ATOMICS = {"___atomic_compare_exchange", "___atomic_exchange"}


def compile_body(tmp_path, ops, sections=(), images=None, tag="m"):
    lifted = lift(*ops, sections=sections)
    assert lifted.holes == []
    ir = tmp_path / f"{tag}.ll"
    ir.write_text(pl.module_for([lifted], images))
    obj = tmp_path / f"{tag}.o"
    subprocess.run(
        [LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", obj, ir],
        check=True,
        capture_output=True,
    )
    lib = tmp_path / f"{tag}.dylib"
    subprocess.run([LLVM / "clang", "-arch", "arm64", "-shared", obj, "-o", lib], check=True, capture_output=True)
    undefined = subprocess.run([LLVM / "llvm-nm", "-u", lib], capture_output=True, text=True).stdout.split()
    dangling = [s for s in undefined if ("atomic" in s or s.startswith("_aarch64_")) and s not in PLATFORM_ATOMICS]
    assert not dangling, f"nothing on this platform provides these atomics: {dangling}"
    entry = ctypes.cdll.LoadLibrary(str(lib)).sub_1000
    entry.argtypes, entry.restype = [ctypes.c_void_p], None
    return entry


def call(tmp_path, ops, reg, memory=b"", sections=(), images=None, shift=0):
    """Run the lifted body over a host buffer standing in for the guest address."""
    entry = compile_body(tmp_path, ops, sections, images)
    raw = (ctypes.c_char * 128)()
    base = ctypes.addressof(raw) + -ctypes.addressof(raw) % 16 + shift
    ctypes.memmove(base, memory.ljust(64, b"\0"), 64)
    file = (ctypes.c_char * REG_SIZE)()
    for text, value in reg.items():
        space, offset, width = pl.parse_varnode(text)
        assert space == "register"
        if isinstance(value, GuestAddress):
            value = base + (value - MEM)
        file[offset : offset + width] = int(value).to_bytes(width, "little")
    entry(ctypes.addressof(file))
    return file, bytes((ctypes.c_char * 64).from_address(base))


def reg(file, text):
    space, offset, size = pl.parse_varnode(text)
    return int.from_bytes(bytes(file[offset : offset + size]), "little")


def flags(file):
    file = bytes(file)
    return {name: file[offset] for name, offset in (("cf", CF), ("pf", PF), ("zf", ZF), ("sf", SF), ("of", OF))}


def expect(result, bits, cf=None, of=None):
    """The flags x86 leaves behind: PF is parity of the low byte, so even parity sets it."""
    result &= (1 << bits) - 1
    return {
        "cf": cf,
        "pf": int(bin(result & 0xFF).count("1") % 2 == 0),
        "zf": int(result == 0),
        "sf": (result >> (bits - 1)) & 1,
        "of": of,
    }


def add_flags(old, addend, bits):
    mask = (1 << bits) - 1
    result = (old + addend) & mask
    return result, expect(result, bits, cf=int(old + addend > mask), of=int(((old ^ result) & (addend ^ result)) >> (bits - 1)))


@requires_llvm
@pytest.mark.parametrize("size", [1, 4, 8])
def test_lifted_lock_add_matches_the_x86_result_and_flags(tmp_path, size):
    bits, addend = size * 8, 0x33
    old = 0xF0 if size == 1 else 0xFFFFFF01
    result, want = add_flags(old, addend, bits)
    file, memory = call(
        tmp_path,
        arithmetic_memory("add", size),
        {"register,0,8": MEM - 0x38, f"register,30,{v(size)}": addend},
        memory=old.to_bytes(size, "little"),
    )
    assert int.from_bytes(memory[:size], "little") == result
    assert flags(file) == want


@requires_llvm
@pytest.mark.parametrize("size,shift", [(4, 1), (4, 3), (8, 1), (8, 3)])
def test_lifted_lock_add_to_a_word_the_guest_left_unaligned_completes(tmp_path, size, shift):
    """Runs the emitted sequence over an address the guest did not align, the case `align 1` covers."""
    bits, addend = size * 8, 0x33
    old = 0xFFFFFF01
    result, want = add_flags(old, addend, bits)
    file, memory = call(
        tmp_path,
        arithmetic_memory("add", size),
        {"register,0,8": MEM - 0x38, f"register,30,{v(size)}": addend},
        memory=old.to_bytes(size, "little"),
        shift=shift,
    )
    assert int.from_bytes(memory[:size], "little") == result
    assert flags(file) == want


@requires_llvm
def test_the_atomics_the_lowering_calls_are_exported_by_the_platform_runtime():
    """`align 1` emits a call to a generic primitive, so the platform has to actually have it."""
    sdk = subprocess.run(["xcrun", "--show-sdk-path"], capture_output=True, text=True).stdout.strip()
    stub = Path(sdk) / "usr" / "lib" / "libSystem.tbd"
    if not stub.exists():
        pytest.skip(f"needs the macOS SDK export list, not {stub}")
    exports = stub.read_text()
    for symbol in sorted(PLATFORM_ATOMICS):
        # The suffixed forms are prefixes of the generic name, so a plain substring test would pass
        # on ___atomic_compare_exchange_1 alone.
        assert re.search(rf"{re.escape(symbol)}(?![A-Za-z0-9_])", exports), f"{symbol} is not exported by {stub}"


@requires_llvm
@pytest.mark.parametrize("size", [1, 4, 8])
def test_lifted_lock_or_matches_the_x86_result_and_zeroes_carry_and_overflow(tmp_path, size):
    bits = size * 8
    old, value = (0xF0, 0x0F) if size == 1 else (0xFFFFFFF0, 0x0000000F)
    file, memory = call(
        tmp_path,
        arithmetic_memory("or", size),
        {"register,0,8": MEM - 0x38, f"register,30,{v(size)}": value, "register,200,1": 1, "register,20b,1": 1},
        memory=old.to_bytes(size, "little"),
    )
    result = old | value
    assert int.from_bytes(memory[:size], "little") == result
    assert flags(file) == expect(result, bits, cf=0, of=0)


@requires_llvm
def test_lifted_lock_add_one_matches_the_x86_result_and_flags(tmp_path):
    file, memory = call(
        tmp_path,
        arithmetic_memory("add1", 4, computed_address=False),
        {"register,b8,8": MEM},
        memory=(0x7FFFFFFF).to_bytes(4, "little"),
    )
    assert int.from_bytes(memory[:4], "little") == 0x80000000
    assert flags(file) == {"cf": 0, "pf": 1, "zf": 0, "sf": 1, "of": 1}


@requires_llvm
def test_lifted_lock_subtract_one_leaves_carry_alone(tmp_path):
    file, memory = call(
        tmp_path,
        arithmetic_memory("sub1", 4, computed_address=False),
        {"register,b8,8": MEM, "register,200,1": 1},
        memory=0x80000000.to_bytes(4, "little"),
    )
    assert int.from_bytes(memory[:4], "little") == 0x7FFFFFFF
    assert flags(file) == {"cf": 1, "pf": 1, "zf": 0, "sf": 0, "of": 1}


@requires_llvm
def test_lifted_lock_xchg_exchanges_and_returns_the_old_value(tmp_path):
    file, memory = call(
        tmp_path,
        xchg_memory(),
        {"register,b0,8": MEM - 8, "register,0,4": 0xBEEF},
        memory=0xDEAD.to_bytes(4, "little"),
    )
    assert int.from_bytes(memory[:4], "little") == 0xBEEF
    assert reg(file, "register,0,4") == 0xDEAD


@requires_llvm
def test_lifted_lock_xadd_returns_the_old_value_and_stores_the_sum(tmp_path):
    file, memory = call(
        tmp_path,
        xadd_memory(),
        {"register,0,8": MEM + 8, "register,8,4": 7},
        memory=0x20.to_bytes(4, "little"),
    )
    assert int.from_bytes(memory[:4], "little") == 0x27
    assert reg(file, "register,8,4") == 0x20
    assert reg(file, "register,8,8") == 0x20
    assert flags(file) == expect(0x27, 32, cf=0, of=0)


@requires_llvm
@pytest.mark.parametrize("expected,matched", [(0x20, True), (0x21, False)])
def test_lifted_lock_cmpxchg_exchanges_only_on_a_match(tmp_path, expected, matched):
    old, desired = 0x20, 0x99
    file, memory = call(
        tmp_path,
        cas_memory(),
        {"register,18,8": MEM, "register,0,4": expected, "register,8,4": desired},
        memory=old.to_bytes(4, "little"),
    )
    assert int.from_bytes(memory[:4], "little") == (desired if matched else old)
    assert reg(file, "register,0,4") == old, "EAX takes the old value on both paths"
    diff = (expected - old) & 0xFFFFFFFF
    assert flags(file) == {
        "cf": int(expected < old),
        "pf": int(bin(diff & 0xFF).count("1") % 2 == 0),
        "zf": int(matched),
        "sf": diff >> 31,
        "of": 0,
    }


@requires_llvm
@pytest.mark.parametrize("matched", [True, False])
def test_lifted_lock_cmpxchg16b_exchanges_only_on_a_match(tmp_path, matched):
    high, low = 0x1122334455667788, 0x99AABBCCDDEEFF00
    stored = (0xAA << 64) | 0xBB
    file, memory = call(
        tmp_path,
        cas16b_memory(),
        {
            "register,b0,8": MEM - 0x40,
            "register,10,8": high if matched else high ^ 1,
            "register,0,8": low,
            "register,8,8": 0xAA,
            "register,18,8": 0xBB,
        },
        memory=((high << 64) | low).to_bytes(16, "little"),
    )
    assert int.from_bytes(memory[:16], "little") == (stored if matched else (high << 64) | low)
    assert flags(file)["zf"] == int(matched)
    if not matched:
        assert reg(file, "register,10,8") == high
        assert reg(file, "register,0,8") == low
