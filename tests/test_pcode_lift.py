"""Tests for the pcode-to-LLVM-IR emitter used by the liftability spike.

Ghidra's raw per-instruction pcode is translated to textual LLVM IR with the register
file as a byte array. The structural contract is testable on hand-written pcode; the
verifier and arm64 backend are exercised only when the LLVM toolchain is present.
"""

import pytest
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pcode_lift as pl

LLVM = Path("/opt/homebrew/opt/llvm/bin")
requires_llvm = pytest.mark.skipif(not (LLVM / "opt").exists(), reason="LLVM toolchain absent")


requires_rosetta = pytest.mark.skipif(
    not (LLVM / "clang").exists()
    or subprocess.run(["arch", "-x86_64", "/bin/echo"], capture_output=True).returncode != 0,
    reason="needs the LLVM toolchain and an x86-64 runtime to compare against",
)


def op(name, out, *ins, **extra):
    return {"op": name, "out": out, "in": list(ins), **extra}


def insn(addr, length, *ops):
    return {"a": addr, "len": length, "m": "x", "ops": list(ops)}


def body(*insns, start=0x1000, size=None):
    size = size if size is not None else sum(i["len"] for i in insns)
    return {"start": start, "size": size, "insns": list(insns)}


REG_EAX, REG_EDI = "register,0,4", "register,38,4"


def verify(ir):
    return subprocess.run(
        [LLVM / "opt", "-passes=verify", "-disable-output", "-"],
        input=ir,
        text=True,
        capture_output=True,
    )


def test_simple_copy_and_return_lifts_clean():
    fn = body(
        insn(0x1000, 2, op("COPY", REG_EAX, REG_EDI)),
        insn(0x1002, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn)
    assert "define void @sub_1000(ptr %reg)" in result.ir
    assert result.holes == []


@requires_llvm
def test_simple_body_verifies_and_compiles_for_arm64(tmp_path):
    fn = body(
        insn(0x1000, 2, op("COPY", REG_EAX, REG_EDI)),
        insn(0x1002, 1, op("RETURN", None, "register,288,8")),
    )
    ir = pl.module_for([pl.lift_body(fn)])
    assert verify(ir).returncode == 0
    obj = tmp_path / "o.o"
    proc = subprocess.run(
        [LLVM / "llc", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", obj, "-"],
        input=ir,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0 and obj.stat().st_size > 0


@requires_llvm
def test_conditional_branch_to_instruction_address_verifies():
    fn = body(
        insn(
            0x1000,
            2,
            op("INT_EQUAL", "unique,100,1", REG_EDI, "const,0,4"),
            op("CBRANCH", None, "ram,1006,8", "unique,100,1"),
        ),
        insn(0x1002, 4, op("INT_ADD", REG_EAX, REG_EDI, "const,1,4")),
        insn(0x1006, 1, op("RETURN", None, "register,288,8")),
    )
    ir = pl.module_for([pl.lift_body(fn)])
    assert verify(ir).returncode == 0, verify(ir).stderr


@requires_llvm
def test_load_store_and_call_verify():
    fn = body(
        insn(
            0x1000,
            3,
            op("LOAD", REG_EAX, "const,1,8", "register,38,8"),
            op("STORE", None, "const,1,8", "register,38,8", REG_EAX),
        ),
        insn(0x1003, 5, op("CALL", None, "ram,2000,8")),
        insn(0x1008, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn)
    assert "declare void @sub_2000(ptr)" in pl.module_for([result])
    assert verify(pl.module_for([result])).returncode == 0


def test_branchind_is_recorded_as_a_hole():
    fn = body(insn(0x1000, 2, op("BRANCHIND", None, "register,0,8")))
    assert pl.lift_body(fn).holes == ["BRANCHIND"]


def test_callother_is_recorded_as_a_hole_with_its_name():
    fn = body(
        insn(0x1000, 4, op("CALLOTHER", None, "const,5,4", REG_EDI, user="lzcnt")),
        insn(0x1004, 1, op("RETURN", None, "register,288,8")),
    )
    assert pl.lift_body(fn).holes == ["CALLOTHER:lzcnt"]


REG_XMM0, REG_XMM1, REG_XMM2 = "register,1200,16", "register,1240,16", "register,1280,16"
# The Ghidra userop ids as the varnode prints them for these instructions in the shipped binary.
DIVPS_ID, DIVPD_ID, MINPS_ID, MAXPS_ID = "97", "96", "9d", "9b"
XMM0_BYTES, XMM1_BYTES, XMM2_BYTES = 0x1200, 0x1240, 0x1280


def packed_call(user, op_id, dst, src, addr=0x1000):
    """The shape Ghidra gives the packed SSE maths ops: the destination twice, the source once, 16 bytes each."""
    return insn(addr, 3, op("CALLOTHER", dst, f"const,{op_id},4", dst, src, user=user))


def packed_body(user, op_id, dst=REG_XMM0, src=REG_XMM2):
    return body(
        packed_call(user, op_id, dst, src),
        insn(0x1003, 1, op("RETURN", None, "register,288,8")),
    )


def movmskps_body(dst=REG_EAX, src=REG_XMM1):
    return packed_body("movmskps", "a1", dst, src)


def pshuflw_body(selector=0xE0, src=REG_XMM0, start=0x1000):
    return body(
        insn(start, 5, op("CALLOTHER", REG_XMM0, "const,bb,4", REG_XMM0, src, f"const,{selector:x},8", user="pshuflw")),
        insn(start + 5, 1, op("RETURN", None, "register,288,8")),
        start=start,
    )


@pytest.mark.parametrize("src", [REG_XMM0, REG_XMM1])
@requires_llvm
def test_pshuflw_shipped_shape_verifies(src):
    result = pl.lift_body(pshuflw_body(src=src))
    assert result.holes == []
    checked = verify(pl.module_for([result]))
    assert checked.returncode == 0, checked.stderr
    assert result.ir.count("load i128") == 1
    assert result.ir.count("store i128") == 1


@pytest.mark.parametrize(
    "dst,inputs",
    [
        (None, ["const,bb,4", REG_XMM0, REG_XMM1, "const,e0,8"]),
        (REG_EAX, ["const,bb,4", REG_EAX, REG_XMM1, "const,e0,8"]),
        (REG_XMM0, ["const,bb,4", REG_XMM1, REG_XMM1, "const,e0,8"]),
        (REG_XMM0, ["const,bb,4", REG_XMM0, "register,1240,8", "const,e0,8"]),
        (REG_XMM0, ["const,bb,4", REG_XMM0, REG_XMM1]),
        (REG_XMM0, ["const,bb,4", REG_XMM0, REG_XMM1, REG_EAX]),
        (REG_XMM0, ["const,bb,4", REG_XMM0, REG_XMM1, "const,100,8"]),
        (REG_XMM0, ["const,bb,4", REG_XMM0, REG_XMM1, "const,e0,8", "const,0,8"]),
    ],
)
def test_pshuflw_unexpected_shape_stays_a_hole(dst, inputs):
    fn = body(insn(0x1000, 5, op("CALLOTHER", dst, *inputs, user="pshuflw")))
    assert pl.lift_body(fn).holes == ["CALLOTHER:pshuflw"]


@requires_llvm
@pytest.mark.parametrize("src", [REG_XMM0, REG_XMM1])
def test_pshuflw_all_selectors_match_word_reference(tmp_path, src):
    lifted = [pl.lift_body(pshuflw_body(selector, src, 0x1000 + selector * 16)) for selector in range(256)]
    assert all(result.holes == [] for result in lifted)
    ir = pl.module_for(lifted)
    checked = verify(ir)
    assert checked.returncode == 0, checked.stderr
    calls = ", ".join(f"sub_{result.start:x}" for result in lifted)
    declarations = "\n".join(f"extern void sub_{result.start:x}(unsigned char *);" for result in lifted)
    source = tmp_path / "pshuflw.c"
    source.write_text(
        "#include <stdint.h>\n#include <string.h>\n#include <stdio.h>\n"
        + declarations
        + f"\nstatic void (*calls[])(unsigned char *) = {{{calls}}};\n"
        "int main(void) { unsigned char reg[8192], before[8192];\n"
        "uint16_t words[8] = {0x1234, 0xabcd, 0x8001, 0x5678, 0xdead, 0xbeef, 0x4321, 0xfedc};\n"
        "for (unsigned imm = 0; imm < 256; imm++) {\n"
        "memset(reg, 0xa5, sizeof reg);\n"
        f"memcpy(reg + {pl.parse_varnode(src)[1]}, words, 16);\n"
        "memcpy(before, reg, sizeof reg); calls[imm](reg);\n"
        "uint16_t want[8]; memcpy(want, words, 16);\n"
        "for (unsigned lane = 0; lane < 4; lane++) want[lane] = words[(imm >> (2 * lane)) & 3];\n"
        "if (memcmp(reg + 0x1200, want, 16)) return 1;\n"
        "memcpy(before + 0x1200, want, 16);\n"
        "if (memcmp(reg, before, sizeof reg)) return 2;\n"
        '} puts("ok 256"); return 0; }\n'
    )
    obj = tmp_path / "pshuflw.o"
    proc = subprocess.run(
        [LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", obj, "-"],
        input=ir, text=True, capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert compile_and_run(tmp_path, source, "arm64", [obj]).strip() == "ok 256"


@pytest.mark.parametrize("dst", [REG_EAX, "register,8,4"])
@pytest.mark.parametrize("src", [REG_XMM0, REG_XMM1])
def test_movmskps_writes_a_32_bit_register(dst, src):
    result = pl.lift_body(movmskps_body(dst, src))
    assert result.holes == []
    stores = [line for line in result.ir.splitlines() if line.strip().startswith("store ")]
    assert len(stores) == 1 and stores[0].strip().startswith("store i32 ")
    pointer = stores[0].split("ptr")[1].split(",")[0].strip()
    assert f"ptr %reg, i64 {pl.parse_varnode(dst)[1]}" in producer(result.ir, pointer)
    assert "load i128" in result.ir
    assert "load i32" not in result.ir


@requires_llvm
def test_movmskps_verifies():
    result = pl.lift_body(movmskps_body())
    assert result.holes == []
    checked = verify(pl.module_for([result]))
    assert checked.returncode == 0, checked.stderr


@pytest.mark.parametrize(
    "dst,inputs",
    [
        ("register,0,8", ["const,a1,4", "register,0,8", REG_XMM0]),
        ("register,0,16", ["const,a1,4", "register,0,16", REG_XMM0]),
        ("unique,100,4", ["const,a1,4", "unique,100,4", REG_XMM0]),
        (REG_EAX, ["const,a1,4", REG_EAX, "register,1200,8"]),
        (REG_EAX, ["const,a1,4", REG_EAX, "register,1200,32"]),
        (REG_EAX, ["const,a1,4", REG_EAX, "unique,d600,16"]),
        (REG_EAX, ["const,a1,4", REG_EDI, REG_XMM0]),
        (REG_EAX, ["const,a1,4", REG_XMM0]),
        (None, ["const,a1,4", REG_EAX, REG_XMM0]),
    ],
)
def test_movmskps_unexpected_shape_stays_a_hole(dst, inputs):
    fn = body(insn(0x1000, 3, op("CALLOTHER", dst, *inputs, user="movmskps")))
    assert pl.lift_body(fn).holes == ["CALLOTHER:movmskps"]


def movmskps_cases():
    cases = [[0] * 4]
    for pattern in (0, 0x7FC01234, 0x7F800001, 0x3F800000, 0x7F800000, 1):
        cases += [[pattern | (((mask >> lane) & 1) << 31) for lane in range(4)] for mask in range(16)]
    return cases


@requires_llvm
def test_movmskps_matches_explicit_sign_bit_reference(tmp_path):
    result = pl.lift_body(movmskps_body())
    assert result.holes == []
    cases = movmskps_cases()
    rows = ",\n".join(
        "{%s, %d}"
        % (
            ", ".join(f"0x{word:08x}u" for word in words),
            sum(((word >> 31) & 1) << i for i, word in enumerate(words)),
        )
        for words in cases
    )
    source = tmp_path / "movmskps.c"
    source.write_text(
        "#include <stdint.h>\n#include <string.h>\n"
        "#include <stdio.h>\n"
        "extern void sub_1000(unsigned char *);\n"
        f"static const uint32_t cases[][5] = {{{rows}}};\n"
        "int main(void) { unsigned char reg[8192];\n"
        "for (unsigned i = 0; i < sizeof cases / sizeof *cases; i++) {\n"
        "memset(reg, 0xa5, sizeof reg); memcpy(reg + 0x1240, cases[i], 16);\n"
        "sub_1000(reg); uint32_t got; memcpy(&got, reg, 4);\n"
        "if (got != cases[i][4]) return 1;\n"
        "for (unsigned j = 4; j < sizeof reg; j++) {\n"
        "if (j >= 0x1240 && j < 0x1250) { if (reg[j] != ((const unsigned char *)cases[i])[j - 0x1240]) return 2; }\n"
        "else if (reg[j] != 0xa5) return 3;\n"
        '}} puts("ok"); return 0; }\n'
    )
    obj = tmp_path / "movmskps.o"
    proc = subprocess.run(
        [LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", obj, "-"],
        input=pl.module_for([result]),
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert compile_and_run(tmp_path, source, "arm64", [obj]).strip() == "ok"


def producer(ir, name):
    for line in ir.splitlines():
        if line.strip().startswith(f"{name} ="):
            return line.strip()
    raise AssertionError(f"no producer for {name}:\n{ir}")


def origin(ir, name, depth=8):
    """The getelementptr a value ultimately reads from, walking the SSA chain back past loads."""
    for _ in range(depth):
        line = producer(ir, name)
        operands = [t for t in line.split("=", 1)[1].replace(",", " ").split() if t.startswith("%t")]
        if not operands:
            return line
        name = operands[0]
    raise AssertionError(f"no origin for {name}:\n{ir}")


def test_divps_lifts_four_float_lanes_without_a_hole():
    result = pl.lift_body(packed_body("divps", DIVPS_ID))
    assert result.holes == []
    assert result.ir.count("= fdiv float") == 4
    assert "fdiv double" not in result.ir


def test_divpd_lifts_two_double_lanes_without_a_hole():
    result = pl.lift_body(packed_body("divpd", DIVPD_ID))
    assert result.holes == []
    assert result.ir.count("= fdiv double") == 2
    assert "fdiv float" not in result.ir


def test_packed_division_divides_the_destination_by_the_source():
    result = pl.lift_body(packed_body("divpd", DIVPD_ID))
    line = next(l for l in result.ir.splitlines() if "fdiv double" in l)
    dividend, divisor = (t.strip().rstrip(",") for t in line.split("fdiv double")[1].split(","))
    assert str(XMM0_BYTES) in origin(result.ir, dividend)
    assert str(XMM2_BYTES) in origin(result.ir, divisor)


def test_packed_division_result_lands_back_in_the_destination():
    result = pl.lift_body(packed_body("divps", DIVPS_ID))
    stores = [l for l in result.ir.splitlines() if l.strip().startswith("store i128")]
    assert len(stores) == 1
    pointer = stores[0].split("ptr")[1].split(",")[0].strip()
    assert f"i64 {XMM0_BYTES}" in producer(result.ir, pointer)


def test_packed_division_from_a_temporary_source_lifts_clean():
    result = pl.lift_body(packed_body("divpd", DIVPD_ID, src="unique,d600,16"))
    assert result.holes == []
    assert result.ir.count("= fdiv double") == 2


def unique_offsets(ir):
    """The %uniq byte offsets a body addresses, in the order it addresses them."""
    return [int(line.rsplit("i64 ", 1)[1]) for line in ir.splitlines() if "ptr %uniq" in line]


def test_unique_subpiece_addresses_its_parent_temp():
    result = pl.lift_body(
        body(
            insn(0x1000, 4, op("COPY", "unique,110b00,16", REG_XMM0)),
            insn(0x1004, 5, op("COPY", "register,1244,4", "unique,110b04,4")),
            insn(0x1009, 1, op("RETURN", None, "register,288,8")),
        )
    )
    assert result.holes == []
    assert unique_offsets(result.ir) == [0, 4]


def test_unique_pieces_of_one_temp_share_one_slot():
    ops = [op("COPY", "unique,110b00,16", REG_XMM0)]
    ops += [op("COPY", f"register,{0x1240 + 4 * lane:x},4", f"unique,{0x110B00 + 4 * lane:x},4") for lane in (1, 2, 3)]
    result = pl.lift_body(body(insn(0x1000, 5, *ops), insn(0x1005, 1, op("RETURN", None, "register,288,8"))))
    assert result.holes == []
    assert unique_offsets(result.ir) == [0, 4, 8, 12]


def test_distant_unique_temps_get_separate_slots():
    result = pl.lift_body(
        body(
            insn(0x1000, 4, op("COPY", "unique,d600,16", REG_XMM0)),
            insn(0x1004, 4, op("COPY", "unique,d800,16", REG_XMM1)),
            insn(0x1008, 1, op("RETURN", None, "register,288,8")),
        )
    )
    offsets = unique_offsets(result.ir)
    assert len(set(offsets)) == 2 and abs(offsets[1] - offsets[0]) >= 16


def test_packed_division_of_an_unexpected_width_stays_a_hole():
    assert pl.lift_body(packed_body("divps", DIVPS_ID, dst="register,1200,32", src="register,1280,32")).holes == ["CALLOTHER:divps"]
    assert pl.lift_body(packed_body("divps", DIVPS_ID, src="register,1280,8")).holes == ["CALLOTHER:divps"]


def test_packed_division_with_an_unmatched_destination_stays_a_hole():
    fn = body(
        insn(0x1000, 3, op("CALLOTHER", REG_XMM1, f"const,{DIVPS_ID},4", REG_XMM0, REG_XMM2, user="divps")),
        insn(0x1003, 1, op("RETURN", None, "register,288,8")),
    )
    assert pl.lift_body(fn).holes == ["CALLOTHER:divps"]


@requires_llvm
def test_packed_division_verifies():
    fn = body(
        packed_call("divps", DIVPS_ID, REG_XMM0, REG_XMM2),
        packed_call("divpd", DIVPD_ID, REG_XMM1, "unique,d600,16", addr=0x1003),
        insn(0x1006, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn)
    assert result.holes == []
    assert verify(pl.module_for([result])).returncode == 0


@requires_llvm
def test_packed_division_compiles_for_arm64(tmp_path):
    result = pl.lift_body(packed_body("divps", DIVPS_ID))
    assert result.holes == []
    ir = pl.module_for([result])
    obj = tmp_path / "o.o"
    proc = subprocess.run(
        [LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", obj, "-"],
        input=ir,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0 and obj.stat().st_size > 0
    assert proc.stderr == ""


def packed_minmax_reference(first, second, lanes, lane_bytes, lower):
    """The x86 rule, written out: a lane keeps the first source only while that comparison holds.

    NaN compares false against everything including itself, and zeros of either sign compare
    equal, so those lanes take the second source. Winners are copied bit for bit, so a NaN
    payload and the sign of a zero survive exactly as the instruction returns them.
    """
    fmt = {4: "f", 8: "d"}[lane_bytes]
    out = bytearray()
    for index in range(lanes):
        at = index * lane_bytes
        a, = struct.unpack_from(fmt, first, at)
        b, = struct.unpack_from(fmt, second, at)
        first_wins = (a < b) if lower else (a > b)
        out += first[at : at + lane_bytes] if first_wins else second[at : at + lane_bytes]
    return bytes(out)


PATTERNS = [0x00000000, 0x80000000, 0x3F800000, 0x40000000, 0xBF800000, 0x7F800000, 0x7FC00000, 0x7FC01234]


def lanes_of(words):
    return struct.pack("<4I", *words)


def packed_cases(lower):
    """Every ordered pair of patterns, rotated across the four lanes of 64 vector pairs."""
    cases = []
    for row in range(len(PATTERNS) ** 2):
        first = lanes_of([PATTERNS[(row + k) % len(PATTERNS)] for k in range(4)])
        second = lanes_of([PATTERNS[(2 * row + k) % len(PATTERNS)] for k in range(4)])
        cases.append((first, second, packed_minmax_reference(first, second, 4, 4, lower)))
    return cases


PACKED_DRIVER = r"""
#include <stdint.h>
#include <string.h>
#include <stdio.h>
{sse}
{extern}
static const uint64_t cases[] = {{{rows}}};
int main(void) {{
  unsigned char reg[8192];
  int bad = 0;
  unsigned n = (unsigned)(sizeof cases / sizeof *cases / 6);
  for (unsigned i = 0; i < n; i++) {{
    const uint64_t *c = cases + i * 6;
    uint64_t got[2];
    memset(reg, 0, sizeof reg);
    memcpy(reg + 0x{dst:x}, c, 16);
    memcpy(reg + 0x{src:x}, c + 2, 16);
    {call}
    {got}
    if (got[0] != c[4] || got[1] != c[5]) {{
      bad++;
      printf("case %u got %016llx%016llx want %016llx%016llx\n", i,
             (unsigned long long)got[0], (unsigned long long)got[1],
             (unsigned long long)c[4], (unsigned long long)c[5]);
    }}
  }}
  printf("bad=%d cases=%u\n", bad, n);
  return 0;
}}
"""


def packed_driver(cases, sse, extern, call, got):
    rows = ", ".join(f"0x{w:016x}" for case in cases for w in struct.unpack("<6Q", b"".join(case)))
    return PACKED_DRIVER.format(
        sse=sse, extern=extern, call=call, got=got, rows=rows, dst=XMM0_BYTES, src=XMM2_BYTES
    )


def run_packed_on(tmp_path, source, arch, extra=()):
    return [line for line in compile_and_run(tmp_path, source, arch, extra).splitlines() if "got" in line]


def run_packed_lifted(tmp_path, result, cases):
    """Runs each (first, second, want) pair through the lifted function via xmm0 and xmm2."""
    obj = tmp_path / "packed.o"
    proc = subprocess.run(
        [LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", obj, "-"],
        input=pl.module_for([result]),
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    source = tmp_path / "packed-arm64.c"
    source.write_text(
        packed_driver(
            cases,
            sse="",
            extern="extern void sub_1000(unsigned char *reg);",
            call="sub_1000(reg);",
            got=f"memcpy(got, reg + 0x{XMM0_BYTES:x}, 16);",
        )
    )
    return run_packed_on(tmp_path, source, "arm64", [obj])


def run_packed_on_x86(tmp_path, cases, intrinsic):
    """The reference is only an expectation until the instruction itself agrees with it."""
    source = tmp_path / "packed-x86_64.c"
    source.write_text(
        packed_driver(
            cases,
            sse="#include <xmmintrin.h>\n#include <emmintrin.h>",
            extern="",
            call=f"__m128 x, y; memcpy(&x, reg + 0x{XMM0_BYTES:x}, 16); memcpy(&y, reg + 0x{XMM2_BYTES:x}, 16);"
            f" __m128 r = {intrinsic}(x, y);",
            got="memcpy(got, &r, 16);",
        )
    )
    return run_packed_on(tmp_path, source, "x86_64")


def test_minps_lifts_four_float_lanes_without_a_hole():
    result = pl.lift_body(packed_body("minps", MINPS_ID))
    assert result.holes == []
    assert result.ir.count("= fcmp olt float") == 4
    assert result.ir.count("= select i1") == 4
    assert "fcmp ogt" not in result.ir
    assert "minnum" not in result.ir


def test_maxps_lifts_four_float_lanes_without_a_hole():
    result = pl.lift_body(packed_body("maxps", MAXPS_ID))
    assert result.holes == []
    assert result.ir.count("= fcmp ogt float") == 4
    assert result.ir.count("= select i1") == 4
    assert "fcmp olt" not in result.ir
    assert "maxnum" not in result.ir


def test_minps_reads_both_packed_sources():
    result = pl.lift_body(packed_body("minps", MINPS_ID))
    line = next(l for l in result.ir.splitlines() if "fcmp olt float" in l)
    first, second = (t.strip().rstrip(",") for t in line.split("fcmp olt float")[1].split(","))
    assert str(XMM0_BYTES) in origin(result.ir, first)
    assert str(XMM2_BYTES) in origin(result.ir, second)


def test_maxps_result_lands_back_in_the_destination():
    result = pl.lift_body(packed_body("maxps", MAXPS_ID))
    stores = [l for l in result.ir.splitlines() if l.strip().startswith("store i128")]
    assert len(stores) == 1
    pointer = stores[0].split("ptr")[1].split(",")[0].strip()
    assert f"i64 {XMM0_BYTES}" in producer(result.ir, pointer)


def test_minps_in_the_shape_the_binary_uses_lifts_clean():
    """Every shipped instance reads a destination against xmm0, as here."""
    assert pl.lift_body(packed_body("minps", MINPS_ID, dst=REG_XMM1, src=REG_XMM0)).holes == []
    assert pl.lift_body(packed_body("maxps", MAXPS_ID, dst=REG_XMM1, src=REG_XMM0)).holes == []


def test_packed_minmax_of_an_unexpected_width_stays_a_hole():
    assert (
        pl.lift_body(packed_body("minps", MINPS_ID, dst="register,1200,32", src="register,1280,32")).holes
        == ["CALLOTHER:minps"]
    )
    assert pl.lift_body(packed_body("maxps", MAXPS_ID, src="register,1280,8")).holes == ["CALLOTHER:maxps"]


def test_packed_minmax_with_another_destination_stays_a_hole():
    fn = body(
        insn(0x1000, 3, op("CALLOTHER", REG_XMM1, f"const,{MINPS_ID},4", REG_XMM0, REG_XMM2, user="minps")),
        insn(0x1003, 1, op("RETURN", None, "register,288,8")),
    )
    assert pl.lift_body(fn).holes == ["CALLOTHER:minps"]


@requires_llvm
@pytest.mark.parametrize("user,op_id", [("minps", MINPS_ID), ("maxps", MAXPS_ID)])
def test_packed_minmax_verifies(user, op_id):
    result = pl.lift_body(packed_body(user, op_id))
    assert result.holes == []
    assert verify(pl.module_for([result])).returncode == 0


@requires_llvm
@pytest.mark.parametrize("user,op_id,lower", [("minps", MINPS_ID, True), ("maxps", MAXPS_ID, False)])
def test_packed_minmax_keeps_the_first_source_only_while_it_compares(tmp_path, user, op_id, lower):
    mismatches = run_packed_lifted(tmp_path, pl.lift_body(packed_body(user, op_id)), packed_cases(lower))
    assert mismatches == []


SECOND_SOURCE = [
    (0x00000000, 0x80000000),
    (0x80000000, 0x00000000),
    (0x00000000, 0x00000000),
    (0x7FC00000, 0x3F800000),
    (0x3F800000, 0x7FC00000),
    (0x7FC00000, 0x7FC01234),
    (0x7FC01234, 0x7FC00000),
    (0x7F800000, 0x7FC00000),
    (0x7FC00000, 0xFF800000),
]


@requires_llvm
@pytest.mark.parametrize("user,op_id", [("minps", MINPS_ID), ("maxps", MAXPS_ID)])
def test_packed_minmax_returns_the_second_source_for_nan_and_signed_zero(tmp_path, user, op_id):
    """Neither comparison holds for two zeros or for a NaN on either side, so the second source wins.

    The wanted bits are written out rather than derived: the second vector, payload and sign included.
    """
    cases = [
        (lanes_of([first] * 4), lanes_of([second] * 4), lanes_of([second] * 4))
        for first, second in SECOND_SOURCE
    ]
    assert run_packed_lifted(tmp_path, pl.lift_body(packed_body(user, op_id)), cases) == []


@requires_rosetta
@pytest.mark.parametrize("user,intrinsic,lower", [("minps", "_mm_min_ps", True), ("maxps", "_mm_max_ps", False)])
def test_the_packed_reference_matches_the_real_instruction(tmp_path, user, intrinsic, lower):
    assert run_packed_on_x86(tmp_path, packed_cases(lower), intrinsic) == []


def test_unknown_opcode_is_a_hole_not_a_crash():
    fn = body(insn(0x1000, 1, op("NOSUCHOP", REG_EAX, REG_EDI)))
    assert pl.lift_body(fn).holes == ["NOSUCHOP"]


def test_branch_out_of_body_is_a_tail_call_not_a_hole():
    fn = body(insn(0x1000, 5, op("BRANCH", None, "ram,9000,8")))
    result = pl.lift_body(fn)
    assert result.holes == []
    assert "@sub_9000" in result.ir


@requires_llvm
def test_float_and_flag_ops_verify():
    fn = body(
        insn(
            0x1000,
            4,
            op("FLOAT_ADD", "register,1200,4", "register,1200,4", "register,1240,4"),
            op("INT_CARRY", "register,200,1", REG_EDI, REG_EAX),
            op("INT_SBORROW", "register,201,1", REG_EDI, REG_EAX),
            op("POPCOUNT", "register,202,1", "register,0,1"),
            op("INT_ZEXT", "register,8,8", REG_EAX),
            op("SUBPIECE", "register,10,1", "register,8,8", "const,0,4"),
        ),
        insn(0x1004, 1, op("RETURN", None, "register,288,8")),
    )
    assert verify(pl.module_for([pl.lift_body(fn)])).returncode == 0


@requires_llvm
def test_direct_ram_varnodes_read_and_write_memory():
    fn = body(
        insn(0x1000, 6, op("COPY", REG_EAX, "ram,5000,4")),
        insn(0x1006, 6, op("COPY", "ram,5004,4", REG_EAX)),
        insn(0x100C, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn)
    assert result.holes == []
    assert verify(pl.module_for([result])).returncode == 0


RODATA = {"name": "rodata", "va": 0x5000, "size": 0x100, "exec": False}
TEXT = {"name": "il2cpp", "va": 0x1000, "size": 0x1000, "exec": True}


def test_data_pointer_constant_becomes_section_symbol_offset():
    fn = body(
        insn(0x1000, 7, op("COPY", "register,0,8", "cptr,5010,8")),
        insn(0x1007, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn, [RODATA, TEXT])
    assert "@sec_rodata, i64 16" in result.ir
    assert result.data_sections == {"rodata"}
    assert result.unmapped_refs == 0
    assert "@sec_rodata = external global i8" in pl.module_for([result])


def test_code_pointer_constant_becomes_function_symbol():
    fn = body(
        insn(0x1000, 7, op("COPY", "register,0,8", "cptr,1800,8")),
        insn(0x1007, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn, [RODATA, TEXT])
    assert "ptrtoint (ptr @sub_1800 to i64)" in result.ir
    assert 0x1800 in result.externs


def test_ram_varnode_inside_a_section_uses_the_section_symbol():
    fn = body(
        insn(0x1000, 6, op("COPY", REG_EAX, "ram,5004,4")),
        insn(0x1006, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn, [RODATA, TEXT])
    assert "@sec_rodata, i64 4" in result.ir


def test_address_outside_every_section_is_counted_unmapped():
    fn = body(
        insn(0x1000, 7, op("COPY", "register,0,8", "cptr,9000,8")),
        insn(0x1007, 1, op("RETURN", None, "register,288,8")),
    )
    assert pl.lift_body(fn, [RODATA, TEXT]).unmapped_refs == 1


@requires_llvm
def test_jump_table_becomes_a_switch_over_the_rebased_target():
    table = {"at": 0x1004, "cases": [0x1006, 0x1008]}
    fn = body(
        insn(0x1000, 4, op("COPY", "register,0,8", "cptr,5000,8")),
        insn(0x1004, 2, op("BRANCHIND", None, "register,0,8")),
        insn(0x1006, 2, op("COPY", REG_EAX, "const,1,4"), op("RETURN", None, "register,288,8")),
        insn(0x1008, 2, op("COPY", REG_EAX, "const,2,4"), op("RETURN", None, "register,288,8")),
    )
    fn["jt"] = [table]
    result = pl.lift_body(fn, [RODATA, TEXT])
    assert result.holes == []
    assert "switch i64" in result.ir
    assert verify(pl.module_for([result])).returncode == 0


def test_jump_table_case_outside_the_body_is_a_hole():
    fn = body(
        insn(0x1000, 4, op("COPY", "register,0,8", "cptr,5000,8")),
        insn(0x1004, 2, op("BRANCHIND", None, "register,0,8")),
    )
    fn["jt"] = [{"at": 0x1004, "cases": [0x7000]}]
    assert pl.lift_body(fn, [RODATA, TEXT]).holes == ["JUMPTABLE_TARGET"]


def test_sparse_unique_offsets_are_compacted_into_a_small_frame():
    fn = body(
        insn(
            0x1000,
            4,
            op("INT_AND", "unique,58300,4", REG_EDI, "const,ff,4"),
            op("POPCOUNT", "unique,58400,1", "unique,58300,4"),
        ),
        insn(0x1004, 1, op("RETURN", None, "register,288,8")),
    )
    ir = pl.lift_body(fn).ir
    assert "alloca [64 x i8]" in ir
    assert "i64 361216" not in ir


@requires_llvm
def test_branchind_through_a_loaded_pointer_is_an_indirect_tail_call():
    fn = body(
        insn(
            0x1000,
            3,
            op("LOAD", "unique,100,8", "const,1,8", "register,0,8"),
            op("BRANCHIND", None, "unique,100,8"),
        ),
    )
    result = pl.lift_body(fn)
    assert result.holes == []
    assert result.indirect_calls == 1
    assert verify(pl.module_for([result])).returncode == 0


def test_branchind_on_a_computed_register_without_a_table_stays_a_hole():
    fn = body(
        insn(0x1000, 3, op("INT_ADD", "register,0,8", "register,0,8", "const,8,8")),
        insn(0x1003, 2, op("BRANCHIND", None, "register,0,8")),
    )
    assert pl.lift_body(fn).holes == ["BRANCHIND"]


@requires_llvm
def test_branchind_on_a_register_loaded_by_an_earlier_instruction_is_a_tail_call():
    fn = body(
        insn(0x1000, 4, op("LOAD", "register,8,8", "const,1,8", "register,38,8")),
        insn(0x1004, 3, op("COPY", "register,38,8", "register,0,8")),
        insn(0x1007, 2, op("BRANCHIND", None, "register,8,8")),
    )
    result = pl.lift_body(fn)
    assert result.holes == []
    assert result.tail_calls == 1
    assert verify(pl.module_for([result])).returncode == 0


def test_branchind_on_a_register_defined_by_arithmetic_stays_a_hole():
    fn = body(
        insn(0x1000, 4, op("LOAD", "register,8,8", "const,1,8", "register,38,8")),
        insn(0x1004, 3, op("INT_ADD", "register,8,8", "register,8,8", "register,10,8")),
        insn(0x1007, 2, op("BRANCHIND", None, "register,8,8")),
    )
    assert pl.lift_body(fn).holes == ["BRANCHIND"]


@requires_llvm
def test_branchind_follows_a_copy_from_a_loaded_temporary():
    fn = body(
        insn(
            0x1000,
            4,
            op("INT_ADD", "unique,8e00,8", "register,38,8", "const,18,8"),
            op("LOAD", "unique,23d00,8", "const,1b1,4", "unique,8e00,8"),
            op("COPY", "register,8,8", "unique,23d00,8"),
        ),
        insn(0x1004, 2, op("BRANCHIND", None, "register,8,8")),
    )
    result = pl.lift_body(fn)
    assert result.holes == []
    assert result.tail_calls == 1
    assert verify(pl.module_for([result])).returncode == 0


def trunc_body(src_size: int, dst_size: int) -> dict:
    """cvttss2si/cvttsd2si arrive as TRUNC from the xmm slot to a general-purpose slot."""
    return body(
        insn(0x1000, 6, op("TRUNC", f"register,0,{dst_size}", f"register,1200,{src_size}")),
        insn(0x1006, 1, op("RETURN", None, "register,288,8")),
    )


def fbits(value: float, size: int) -> int:
    return int.from_bytes(struct.pack(">f" if size == 4 else ">d", value), "big")


def cases(src_size: int, dst_size: int, rows: list[tuple]) -> list[tuple[int, int]]:
    """(value or raw bits, signed expectation) pairs as source and destination bit patterns."""
    mask = (1 << (dst_size * 8)) - 1
    return [(v if isinstance(v, int) else fbits(v, src_size), want & mask) for v, want in rows]


INDEF32, INDEF64 = -2147483648, -(2**63)
SNAN64, QUIET_NAN_NEG = 0x7FF0000000000001, 0xFFF8000000000000

# Every expectation below is truncation toward zero, not floor: -0.9999999 gives 0.
DOUBLE_TO_I32 = cases(8, 4, [
    (0.0, 0), (-0.0, 0), (1.5, 1), (-1.5, -1), (0.9999999, 0), (-0.9999999, 0),
    (2147483647.0, 2147483647), (2147483647.5, 2147483647),
    (-2147483648.0, INDEF32), (-2147483648.5, INDEF32), (-2147483649.0, INDEF32),
    (2147483648.0, INDEF32), (1e18, INDEF32),
    (float("inf"), INDEF32), (float("-inf"), INDEF32), (float("nan"), INDEF32),
    (0x7FF8000000000000, INDEF32), (QUIET_NAN_NEG, INDEF32), (SNAN64, INDEF32),
])
DOUBLE_TO_I64 = cases(8, 8, [
    (0.0, 0), (-0.0, 0), (0.5, 0), (-0.5, 0), (1.5, 1), (-1.5, -1), (1e18, 10**18),
    (2.0**62, 2**62), (9223372036854774784.0, 9223372036854774784),
    (-2.0**63, INDEF64), (-9223372036854776832.0, INDEF64),
    (2.0**63, INDEF64), (float("inf"), INDEF64), (float("-inf"), INDEF64),
    (float("nan"), INDEF64), (SNAN64, INDEF64),
])
FLOAT_TO_I32 = cases(4, 4, [
    (0.0, 0), (-0.0, 0), (0.5, 0), (-0.5, 0), (1.5, 1), (-1.5, -1), (100000.0, 100000),
    (2147483392.0, 2147483392), (-2147483648.0, INDEF32), (-2147483904.0, INDEF32),
    (2147483648.0, INDEF32), (3e9, INDEF32), (float("inf"), INDEF32), (float("-inf"), INDEF32),
    (float("nan"), INDEF32), (0x7F800001, INDEF32),
])
FLOAT_TO_I64 = cases(4, 8, [
    (0.0, 0), (-0.0, 0), (-0.5, 0), (1.5, 1), (-1.5, -1), (2.0**62, 2**62), (1e18, 999999984306749440),
    (-2.0**63, INDEF64), (2.0**63, INDEF64), (float("inf"), INDEF64),
    (float("-inf"), INDEF64), (float("nan"), INDEF64),
])
SHAPES = {(8, 4): DOUBLE_TO_I32, (8, 8): DOUBLE_TO_I64, (4, 4): FLOAT_TO_I32, (4, 8): FLOAT_TO_I64}
EVERY_SHAPE = pytest.mark.parametrize("src,dst", sorted(SHAPES))

# Rebuilds the source value from its bit pattern so the table can name a bit pattern exactly:
# a hex integer literal written into a double column gets rounded.
X86_LOAD = {
    8: "double v; memcpy(&v, &bits, 8);",
    4: "uint32_t b32 = (uint32_t)bits; float v; memcpy(&v, &b32, 4);",
}
X86_CONVERT = {
    (8, 4): "(uint64_t)(int32_t)_mm_cvttsd_si32(_mm_set_sd(v))",
    (8, 8): "(uint64_t)_mm_cvttsd_si64(_mm_set_sd(v))",
    (4, 4): "(uint64_t)(int32_t)_mm_cvttss_si32(_mm_set_ss(v))",
    (4, 8): "(uint64_t)_mm_cvttss_si64(_mm_set_ss(v))",
}

def compile_and_run(tmp_path, source, arch, extra=()):
    exe = tmp_path / f"run-{arch}"
    proc = subprocess.run(
        [LLVM / "clang", "-O1", "-arch", arch, *extra, "-o", exe, source], text=True, capture_output=True
    )
    assert proc.returncode == 0, proc.stderr
    argv = [str(exe)] if arch == "arm64" else ["arch", "-x86_64", str(exe)]
    return subprocess.run(argv, text=True, capture_output=True).stdout


CONVERSION_DRIVER = r"""
#include <stdint.h>
#include <stdio.h>
#include <string.h>
{sse}
{extern}
static unsigned char reg[8192];
typedef struct {{ uint64_t in; uint64_t want; }} row;
static row cases[] = {{ {rows} }};
int main(void) {{
  int bad = 0;
  for (unsigned i = 0; i < sizeof cases / sizeof *cases; i++) {{
    const row *c = &cases[i];
    uint64_t got, bits = c->in;
    {load}
    memset(reg, 0, sizeof reg);
    memcpy(reg + 0x1200, &bits, {src});
    {call}
    got = {got};
    if (got != (c->want & 0x{mask:x}ull)) {{
      bad++;
      printf("case %u got 0x%llx want 0x%llx\n", i, (unsigned long long)got,
             (unsigned long long)c->want);
    }}
  }}
  printf("bad=%d\n", bad);
  return 0;
}}
"""


def compare_conversion(tmp_path, result, src, dst, rows, arch, convert):
    """Feeds each input through the register file and reports the cases that disagree.

    The arm64 side calls the lifted function and reads the destination slot back out of the
    register file; the x86-64 side runs the instruction itself against the same table.
    """
    obj = None
    if arch == "arm64":
        obj = tmp_path / "lifted.o"
        proc = subprocess.run(
            [LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", obj, "-"],
            input=pl.module_for([result]),
            text=True,
            capture_output=True,
        )
        assert proc.returncode == 0, proc.stderr
    mask = (1 << (dst * 8)) - 1
    got = f"*(uint64_t *)(reg + 0) & 0x{mask:x}ull" if obj else f"({convert}) & 0x{mask:x}ull"
    source = tmp_path / f"{arch}.c"
    source.write_text(
        CONVERSION_DRIVER.format(
            sse="" if obj else "#include <xmmintrin.h>\n#include <emmintrin.h>",
            extern="extern void sub_1000(unsigned char *reg);" if obj else "",
            load="" if obj else X86_LOAD[src],
            rows=", ".join(f"{{ 0x{b:x}, 0x{w:x} }}" for b, w in rows),
            src=src,
            call="sub_1000(reg);" if obj else "",
            got=got,
            mask=mask,
        )
    )
    lines = compile_and_run(tmp_path, source, arch, [obj] if obj else []).splitlines()
    return [line for line in lines if "got" in line]


@EVERY_SHAPE
def test_trunc_lifts_with_no_hole_and_a_single_conversion(src, dst):
    result = pl.lift_body(trunc_body(src, dst))
    assert result.holes == []
    assert result.ir.count("fptosi") == 1


@requires_llvm
@EVERY_SHAPE
def test_trunc_verifies(src, dst):
    assert verify(pl.module_for([pl.lift_body(trunc_body(src, dst))])).returncode == 0


@requires_llvm
@EVERY_SHAPE
def test_trunc_gives_the_integer_indefinite_value_where_x86_does(tmp_path, src, dst):
    mismatches = compare_conversion(
        tmp_path, pl.lift_body(trunc_body(src, dst)), src, dst, SHAPES[(src, dst)], "arm64", None
    )
    assert mismatches == []


@requires_rosetta
@EVERY_SHAPE
def test_the_expectation_tables_match_the_real_x86_instruction(tmp_path, src, dst):
    """Native arm64 saturates where x86 returns the integer indefinite value, so the tables
    above need an oracle that is not arm64: this runs the instruction itself."""
    mismatches = compare_conversion(
        tmp_path, None, src, dst, SHAPES[(src, dst)], "x86_64", X86_CONVERT[(src, dst)]
    )
    assert mismatches == []
