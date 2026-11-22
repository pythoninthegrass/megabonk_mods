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
    not (LLVM / "clang").exists() or subprocess.run(["arch", "-x86_64", "/bin/echo"], capture_output=True).returncode != 0,
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


def test_branchind_hole_calls_the_logging_trap_when_asked():
    fn = body(insn(0x1000, 2, op("BRANCHIND", None, "register,0,8")))
    result = pl.lift_body(fn, trap_holes=True)
    assert result.holes == ["BRANCHIND"]
    assert "call void @lift_hole(i64 4096, i64 4096)" in result.ir
    assert "declare void @lift_hole(i64, i64) noreturn" in pl.module_for([result])


def test_holes_stay_a_bare_unreachable_by_default():
    fn = body(insn(0x1000, 2, op("BRANCHIND", None, "register,0,8")))
    assert "lift_hole" not in pl.lift_body(fn).ir


def test_undecoded_branch_target_calls_the_logging_trap_when_asked():
    fn = body(insn(0x1000, 5, op("BRANCH", None, "ram,1003,8")), insn(0x1005, 1, op("RETURN", None, "register,288,8")))
    result = pl.lift_body(fn, trap_holes=True)
    assert result.holes == ["UNDECODED_TARGET"]
    assert "call void @lift_hole(i64 4096, i64 4096)" in result.ir


def test_undecoded_conditional_target_calls_the_logging_trap_when_asked():
    fn = body(
        insn(0x1000, 5, op("CBRANCH", None, "ram,1003,8", "unique,100,1")),
        insn(0x1005, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn, trap_holes=True)
    assert result.holes == ["UNDECODED_TARGET"]
    assert "call void @lift_hole(i64 4096, i64 4096)" in result.ir


@requires_llvm
def test_trap_hole_module_verifies():
    fn = body(insn(0x1000, 2, op("BRANCHIND", None, "register,0,8")))
    assert verify(pl.module_for([pl.lift_body(fn, trap_holes=True)])).returncode == 0


ENTRIES = frozenset({0x1000, 0x2000})
PLT = [{"name": "_plt", "va": 0x3000, "size": 0x100, "exec": True}]


def transfer(kind, target):
    ret = insn(0x1005, 1, op("RETURN", None, "register,288,8"))
    if kind == "CBRANCH":
        return body(insn(0x1000, 5, op("CBRANCH", None, f"ram,{target:x},8", "unique,100,1")), ret)
    return body(insn(0x1000, 5, op(kind, None, f"ram,{target:x},8")), ret)


@pytest.mark.parametrize("kind", ["CALL", "BRANCH", "CBRANCH"])
def test_a_transfer_into_the_middle_of_another_body_is_a_hole_when_entries_are_known(kind):
    result = pl.lift_body(transfer(kind, 0x2003), entries=ENTRIES, trap_holes=True)
    assert result.holes == ["MID_BODY_TARGET"]
    assert "@sub_2003" not in result.ir and result.externs == set()
    assert "call void @lift_hole(i64 4096, i64 4096)" in result.ir


@pytest.mark.parametrize("kind", ["CALL", "BRANCH", "CBRANCH"])
def test_a_transfer_to_another_body_start_stays_a_call(kind):
    result = pl.lift_body(transfer(kind, 0x2000), entries=ENTRIES)
    assert result.holes == [] and "@sub_2000" in result.ir


@pytest.mark.parametrize("kind", ["CALL", "BRANCH", "CBRANCH"])
def test_a_transfer_to_a_plt_stub_is_not_a_mid_body_target(kind):
    result = pl.lift_body(transfer(kind, 0x3010), PLT, entries=ENTRIES)
    assert result.holes == [] and "@sub_3010" in result.ir


@pytest.mark.parametrize("kind", ["CALL", "BRANCH", "CBRANCH"])
def test_without_entries_a_transfer_is_never_second_guessed(kind):
    assert pl.lift_body(transfer(kind, 0x2003)).holes == []


@requires_llvm
@pytest.mark.parametrize("kind", ["CALL", "BRANCH", "CBRANCH"])
def test_a_mid_body_hole_module_verifies(kind):
    fn = transfer(kind, 0x2003)
    assert verify(pl.module_for([pl.lift_body(fn, entries=ENTRIES, trap_holes=True)])).returncode == 0


DISPLACEMENT_SECTIONS = [
    {"name": "text", "va": 0x1000, "size": 0x2000, "exec": True},
    {"name": "data", "va": 0x4000, "size": 0x100, "exec": False},
]


def cptr_add(*operands):
    return body(
        insn(0x1000, 7, op("INT_ADD", "register,0,8", *operands)),
        insn(0x1007, 1, op("RETURN", None, "register,288,8")),
    )


@pytest.mark.parametrize("operands", [("register,30,8", "cptr,2000,8"), ("cptr,2000,8", "register,30,8")])
@pytest.mark.parametrize("target", [0x2000, 0x4010])
def test_a_register_plus_a_cptr_is_a_displacement_hole_not_a_pointer(operands, target):
    fn = cptr_add(*[o.replace("2000", f"{target:x}") for o in operands])
    result = pl.lift_body(fn, DISPLACEMENT_SECTIONS, trap_holes=True)
    assert result.holes == ["CPTR_DISPLACEMENT"]
    assert f"@sub_{target:x}" not in result.ir and "@sec_" not in result.ir
    assert "call void @lift_hole(i64 4096, i64 4096)" in result.ir


def test_a_cptr_copy_is_still_an_address():
    fn = body(
        insn(0x1000, 7, op("COPY", "register,0,8", "cptr,2000,8")),
        insn(0x1007, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn, DISPLACEMENT_SECTIONS)
    assert result.holes == [] and "@sub_2000" in result.ir


def test_a_cptr_plus_a_constant_is_still_an_address():
    fn = cptr_add("cptr,2000,8", "const,8,8")
    assert pl.lift_body(fn, DISPLACEMENT_SECTIONS).holes == []


@requires_llvm
def test_a_displacement_hole_module_verifies():
    fn = cptr_add("register,30,8", "cptr,2000,8")
    assert verify(pl.module_for([pl.lift_body(fn, DISPLACEMENT_SECTIONS, trap_holes=True)])).returncode == 0


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
        input=ir,
        text=True,
        capture_output=True,
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


MAXPD_ID, MOVMSKPD_ID, PACKSSDW_ID, PSHUFHW_ID = "9a", "a0", "a3", "ba"


def maxpd_body(dst=REG_XMM0, src=REG_XMM2):
    return packed_body("maxpd", MAXPD_ID, dst, src)


def packssdw_body(dst=REG_XMM0, src=REG_XMM2):
    return packed_body("packssdw", PACKSSDW_ID, dst, src)


def movmskpd_body(dst=REG_EAX, src=REG_XMM1):
    return packed_body("movmskpd", MOVMSKPD_ID, dst, src)


def pshufhw_body(selector=0x1B, src=REG_XMM0, start=0x1000):
    return body(
        insn(
            start, 5, op("CALLOTHER", REG_XMM0, f"const,{PSHUFHW_ID},4", REG_XMM0, src, f"const,{selector:x},8", user="pshufhw")
        ),
        insn(start + 5, 1, op("RETURN", None, "register,288,8")),
        start=start,
    )


PACKED_PAIR_DRIVER = r"""
#include <stdint.h>
#include <stdio.h>
#include <string.h>
{include}
{extern}
static unsigned char reg[8192];
typedef struct {{ uint32_t a[4]; uint32_t b[4]; }} pair;
static pair cases[] = {{ {rows} }};
int main(void) {{
  for (unsigned i = 0; i < sizeof cases / sizeof *cases; i++) {{
    memset(reg, 0xa5, sizeof reg);
    memcpy(reg + {dst_off}, cases[i].a, 16);
    memcpy(reg + {src_off}, cases[i].b, 16);
    {operation}
    uint32_t out[4];
    memcpy(out, reg + {dst_off}, 16);
    unsigned rest = 0;
    for (unsigned j = 0; j < sizeof reg; j++) {{
      if (j >= {dst_off} && j < {dst_off} + 16u) continue;
      if (j >= {src_off} && j < {src_off} + 16u) continue;
      rest = rest * 33u + reg[j];
    }}
    printf("%u %08x %08x %08x %08x %08x\n", i, out[0], out[1], out[2], out[3], rest);
  }}
  return 0;
}}
"""


def words(lane_values):
    return "{" + ", ".join(f"0x{v:08x}u" for v in lane_values) + "}"


def compare_packed(tmp_path, result, cases, x86_op, dst_off=0x1200, src_off=0x1280):
    """Runs each operand pair through the lifted body and through the real instruction on x86-64.

    The checksum of the untouched register file rides along, so a lifted body that writes somewhere
    it should not shows up as a disagreement rather than as a passing value.
    """
    obj = tmp_path / "lifted.o"
    proc = subprocess.run(
        [LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", obj, "-"],
        input=pl.module_for([result]),
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    rows = ",\n".join(f"{{{words(a)}, {words(b)}}}" for a, b in cases)
    outputs = []
    for arch, operation, include, extern, extra in (
        ("arm64", "sub_1000(reg);", "", "extern void sub_1000(unsigned char *);", [obj]),
        ("x86_64", x86_op, "#include <emmintrin.h>", "", []),
    ):
        source = tmp_path / f"packed-{arch}.c"
        source.write_text(
            PACKED_PAIR_DRIVER.format(
                include=include, extern=extern, rows=rows, operation=operation, dst_off=dst_off, src_off=src_off
            )
        )
        outputs.append(compile_and_run(tmp_path, source, arch, extra).splitlines())
    return outputs[0], outputs[1]


def doubles(*pair):
    """The four 32-bit words of two packed doubles, by bit pattern, low lane first."""
    raw = struct.pack("<2d", *pair)
    return [int.from_bytes(raw[4 * i : 4 * i + 4], "little") for i in range(4)]


MAXPD_CASES = [
    (doubles(1.0, 3.0), doubles(2.0, 4.0)),
    (doubles(2.0, 4.0), doubles(1.0, 3.0)),
    (doubles(0.0, -0.0), doubles(-0.0, 0.0)),
    (doubles(float("nan"), 1.0), doubles(2.0, 3.0)),
    (doubles(2.0, 3.0), doubles(float("nan"), 1.0)),
    (doubles(float("nan"), 1.0), doubles(float("nan"), -1.0)),
    (doubles(float("inf"), float("-inf")), doubles(float("-inf"), float("inf"))),
    (doubles(1.7976931348623157e308, 5e-324), doubles(1.7976931348623155e308, 1e-323)),
    (doubles(-4.5, -4.5), doubles(-4.5, -4.6)),
    (doubles(0.0, 0.0), doubles(0.0, 0.0)),
]


@requires_llvm
@requires_rosetta
def test_maxpd_matches_the_real_instruction(tmp_path):
    result = pl.lift_body(maxpd_body())
    assert result.holes == []
    assert verify(pl.module_for([result])).returncode == 0
    lifted, native = compare_packed(
        tmp_path,
        result,
        MAXPD_CASES,
        "__m128d a, b, r; memcpy(&a, reg + 0x1200, 16); memcpy(&b, reg + 0x1280, 16); "
        "r = _mm_max_pd(a, b); memcpy(reg + 0x1200, &r, 16);",
    )
    assert len(lifted) == len(MAXPD_CASES) > 0
    assert lifted == native


@requires_llvm
@requires_rosetta
def test_packssdw_matches_the_real_instruction(tmp_path):
    result = pl.lift_body(packssdw_body())
    assert result.holes == []
    assert verify(pl.module_for([result])).returncode == 0
    edges = [0x7FFFFFFF, 0x80000000, 32767, 32768, 0x7FFF8000, 0xFFFF8000, 0xFFFF7FFF, 1, 0xFFFFFFFF, 0x12345678, 0]
    cases = [
        ([edges[(i + j) % len(edges)] for j in range(4)], [edges[(i * 3 + j) % len(edges)] for j in range(4)])
        for i in range(len(edges))
    ]
    cases.append(([0x7FFFFFFF] * 4, [0x80000000] * 4))
    cases.append(([0x80000000] * 4, [0x7FFFFFFF] * 4))
    lifted, native = compare_packed(
        tmp_path,
        result,
        cases,
        "__m128i a, b, r; memcpy(&a, reg + 0x1200, 16); memcpy(&b, reg + 0x1280, 16); "
        "r = _mm_packs_epi32(a, b); memcpy(reg + 0x1200, &r, 16);",
    )
    assert len(lifted) == len(cases) > 0
    assert lifted == native


@requires_llvm
@pytest.mark.parametrize("src", [REG_XMM0, REG_XMM1])
def test_pshufhw_all_selectors_match_word_reference(tmp_path, src):
    lifted = [pl.lift_body(pshufhw_body(selector, src, 0x1000 + selector * 16)) for selector in range(256)]
    assert all(result.holes == [] for result in lifted)
    ir = pl.module_for(lifted)
    checked = verify(ir)
    assert checked.returncode == 0, checked.stderr
    calls = ", ".join(f"sub_{result.start:x}" for result in lifted)
    declarations = "\n".join(f"extern void sub_{result.start:x}(unsigned char *);" for result in lifted)
    source = tmp_path / "pshufhw.c"
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
        "for (unsigned lane = 0; lane < 4; lane++) want[4 + lane] = words[4 + ((imm >> (2 * lane)) & 3)];\n"
        "if (memcmp(reg + 0x1200, want, 16)) return 1;\n"
        "memcpy(before + 0x1200, want, 16);\n"
        "if (memcmp(reg, before, sizeof reg)) return 2;\n"
        '} puts("ok 256"); return 0; }\n'
    )
    obj = tmp_path / "pshufhw.o"
    proc = subprocess.run(
        [LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", obj, "-"],
        input=ir,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert compile_and_run(tmp_path, source, "arm64", [obj]).strip() == "ok 256"


def movmskpd_cases():
    lanes = [0x0000000000000000, 0x8000000000000000, 0x3FF0000000000000, 0x7FF8000000000000, 0xFFFFFFFFFFFFFFFF]
    return [
        (low | (0x8000000000000000 if mask & 1 else 0), high | (0x8000000000000000 if mask & 2 else 0))
        for low in lanes
        for high in lanes
        for mask in range(4)
    ]


@requires_llvm
def test_movmskpd_matches_explicit_sign_bit_reference(tmp_path):
    result = pl.lift_body(movmskpd_body())
    assert result.holes == []
    rows = ",\n".join(
        "{0x%016xULL, 0x%016xULL, %d}" % (low, high, (low >> 63) | ((high >> 63) << 1)) for low, high in movmskpd_cases()
    )
    source = tmp_path / "movmskpd.c"
    source.write_text(
        "#include <stdint.h>\n#include <string.h>\n#include <stdio.h>\n"
        "extern void sub_1000(unsigned char *);\n"
        f"static const uint64_t cases[][3] = {{{rows}}};\n"
        "int main(void) { unsigned char reg[8192];\n"
        "for (unsigned i = 0; i < sizeof cases / sizeof *cases; i++) {\n"
        "memset(reg, 0xa5, sizeof reg);\n"
        "memcpy(reg + 0x1240, cases[i], 16); sub_1000(reg);\n"
        "uint32_t got; memcpy(&got, reg, 4);\n"
        "if (got != (uint32_t)cases[i][2]) return 1;\n"
        "for (unsigned j = 4; j < sizeof reg; j++) {\n"
        "if (j >= 0x1240 && j < 0x1250) { if (reg[j] != ((const unsigned char *)cases[i])[j - 0x1240]) return 2; }\n"
        "else if (reg[j] != 0xa5) return 3;\n"
        '}} puts("ok"); return 0; }\n'
    )
    obj = tmp_path / "movmskpd.o"
    proc = subprocess.run(
        [LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", obj, "-"],
        input=pl.module_for([result]),
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert compile_and_run(tmp_path, source, "arm64", [obj]).strip() == "ok"


@pytest.mark.parametrize(
    "dst, src",
    [("register,1200,8", REG_XMM2), (REG_XMM0, "register,1280,8"), ("register,1200,8", "register,1280,8")],
)
def test_packed_sse_ops_of_an_unexpected_width_stay_holes(dst, src):
    for user, op_id in (("maxpd", MAXPD_ID), ("packssdw", PACKSSDW_ID)):
        fn = body(packed_call(user, op_id, dst, src), insn(0x1003, 1, op("RETURN", None, "register,288,8")))
        assert pl.lift_body(fn).holes == [f"CALLOTHER:{user}"]


def test_pshufhw_with_a_non_constant_selector_stays_a_hole():
    fn = body(
        insn(
            0x1000, 5, op("CALLOTHER", REG_XMM0, f"const,{PSHUFHW_ID},4", REG_XMM0, REG_XMM1, "register,12c0,8", user="pshufhw")
        ),
        insn(0x1005, 1, op("RETURN", None, "register,288,8")),
    )
    assert pl.lift_body(fn).holes == ["CALLOTHER:pshufhw"]


def test_movmskpd_reading_an_unexpected_width_stays_a_hole():
    fn = packed_body("movmskpd", MOVMSKPD_ID, REG_EAX, "register,1240,8")
    assert pl.lift_body(fn).holes == ["CALLOTHER:movmskpd"]


CPUID_ID, RDRAND_ID, RDRAND_VALID_ID, MONITORX_ID, MWAITX_ID, INVALID_ID = "2d", "67c", "67d", "f", "d", "57"


def invalid_insn(addr=0x208BB6D):
    """The dump's model of an undefined instruction: a helper result that the very next op jumps through."""
    return insn(
        addr,
        2,
        op("CALLOTHER", "unique,d5d00,8", f"const,{INVALID_ID},4", user="invalidInstructionException"),
        op("BRANCHIND", None, "unique,d5d00,8"),
    )


def invalid_body(start=0x208BB6D, tail=True):
    insns = [insn(start - 5, 5, op("COPY", "register,0,8", "const,7,8")), invalid_insn(start)]
    if tail:
        insns += [
            insn(start + 2, 4, op("COPY", "register,8,8", "const,1,8")),
            insn(start + 6, 1, op("RETURN", None, "register,288,8")),
        ]
    return body(*insns, start=start - 5)


def test_invalid_instruction_lowers_to_a_trap():
    result = pl.lift_body(invalid_body())
    assert result.holes == []
    assert result.unproven_branchind == []
    assert "call void @llvm.trap()" in result.ir
    assert verify(pl.module_for([result])).returncode == 0


def test_invalid_instruction_trap_ends_the_block():
    """Nothing the guest would never execute survives: the dead tail and its jump are gone."""
    ir = pl.lift_body(invalid_body()).ir
    assert "store i64 1," not in ir


def test_a_live_branch_target_after_the_trap_keeps_it_a_hole():
    fn = body(
        insn(
            0x208BB60,
            5,
            op("INT_EQUAL", "unique,10,1", "register,0,8", "const,3,8"),
            op("CBRANCH", None, "ram,208bb71,8", "unique,10,1"),
            op("BRANCH", None, "ram,208bb73,8"),
        ),
        invalid_insn(0x208BB6D),
        insn(0x208BB6F, 2, op("COPY", "register,8,8", "const,1,8")),
        insn(0x208BB71, 2, op("RETURN", None, "register,288,8")),
        start=0x208BB60,
    )
    # Refusing the trap leaves the model's jump unlowered too: both blockers stay, neither is silently absorbed.
    assert pl.lift_body(fn).holes == ["CALLOTHER:invalidInstructionException", "BRANCHIND"]


def test_a_trap_whose_result_the_jump_does_not_read_stays_a_hole():
    """The jump the trap absorbs has to be the one that jumps through the helper's own result."""
    fn = body(
        insn(
            0x208BB6D,
            1,
            op("COPY", "register,38,8", "unique,9f8,8"),
            op("CALLOTHER", "unique,9f0,8", f"const,{INVALID_ID},4", user="invalidInstructionException"),
            op("BRANCHIND", None, "unique,9f8,8"),
        ),
        start=0x208BB6D,
    )
    assert pl.lift_body(fn).holes == ["CALLOTHER:invalidInstructionException", "BRANCHIND"]


def test_an_invalid_instruction_result_used_as_data_stays_a_hole():
    fn = body(
        insn(
            0x208BB6D,
            2,
            op("CALLOTHER", "unique,d5d00,8", f"const,{INVALID_ID},4", user="invalidInstructionException"),
            op("INT_ADD", "register,0,8", "unique,d5d00,8", "const,1,8"),
        ),
        insn(0x208BB6F, 1, op("RETURN", None, "register,288,8")),
    )
    assert pl.lift_body(fn).holes == ["CALLOTHER:invalidInstructionException"]


def monitorx_insn(addr=0x2092944):
    return insn(addr, 4, op("CALLOTHER", None, f"const,{MONITORX_ID},4", user="monitorx"))


def hint_body(hints=True):
    ops = []
    if hints:
        ops += [
            op("CALLOTHER", None, f"const,{MONITORX_ID},4", user="monitorx"),
            op("CALLOTHER", None, f"const,{MWAITX_ID},4", user="mwaitx"),
        ]
    ops.append(op("COPY", "register,0,8", "register,38,8"))
    return body(
        insn(0x2092940, 4, *ops),
        insn(0x2092944, 4, op("COPY", "register,8,8", "const,2,8")),
        insn(0x2092948, 1, op("RETURN", None, "register,288,8")),
        start=0x2092940,
    )


def test_monitorx_and_mwaitx_are_dropped():
    result = pl.lift_body(hint_body())
    assert result.holes == []
    assert "monitorx" not in result.ir and "mwaitx" not in result.ir
    assert "store i64" in result.ir


def operations(ir):
    """The emitted instructions, ignoring the per-op labels and fallthroughs every body carries."""
    lines = []
    for line in ir.splitlines():
        line = line.strip()
        if not line or line.endswith(":") or line.startswith("br label"):
            continue
        lines.append(line)
    return lines


def test_the_dropped_hints_emit_not_even_an_instruction():
    """Dropping means the same code a host without those instructions runs, not a call to something else."""
    assert operations(pl.lift_body(hint_body()).ir) == operations(pl.lift_body(hint_body(hints=False)).ir)


def test_a_monitorx_that_returns_something_stays_a_hole():
    fn = body(
        insn(0x2092944, 4, op("CALLOTHER", "register,0,8", f"const,{MONITORX_ID},4", user="monitorx")),
        insn(0x2092948, 1, op("RETURN", None, "register,288,8")),
    )
    assert pl.lift_body(fn).holes == ["CALLOTHER:monitorx"]


CPUID_BUFFER = "unique,7c900,8"


def cpuid_body(user="cpuid", leaf="register,0,4"):
    """The switch arm and the four dwords the model reads back out of the helper's result block."""
    return body(
        insn(
            0x2153D33,
            4,
            op("INT_EQUAL", "unique,7ca00,1", leaf, "const,0,4"),
            op("CBRANCH", None, "const,21,4", "unique,7ca00,1"),
            op("CALLOTHER", CPUID_BUFFER, f"const,{CPUID_ID},4", leaf, user=user),
            op("BRANCH", None, "const,21,4"),
            op("LOAD", "unique,7eb00,4", "const,1b1,8", CPUID_BUFFER),
            op("INT_ZEXT", "register,0,8", "unique,7eb00,4"),
            op("INT_ADD", "unique,7ed00,8", CPUID_BUFFER, "const,4,8"),
            op("LOAD", "unique,7ee00,4", "const,1b1,8", "unique,7ed00,8"),
            op("INT_ZEXT", "register,18,8", "unique,7ee00,4"),
            op("INT_ADD", "unique,7f000,8", CPUID_BUFFER, "const,8,8"),
            op("LOAD", "unique,7f100,4", "const,1b1,8", "unique,7f000,8"),
            op("INT_ZEXT", "register,10,8", "unique,7f100,4"),
            op("INT_ADD", "unique,7f300,8", CPUID_BUFFER, "const,c,8"),
            op("LOAD", "unique,7f400,4", "const,1b1,8", "unique,7f300,8"),
            op("INT_ZEXT", "register,8,8", "unique,7f400,4"),
        ),
        insn(0x2153D37, 1, op("RETURN", None, "register,288,8")),
        start=0x2153D33,
    )


def cpuid_argument_line(ir):
    """The last definition the helper's leaf argument is built from, so the test can see which register fed it."""
    lines = ir.splitlines()
    call = next(line for line in lines if "call void @lift_cpuid" in line)
    temp = call.split("i64 ", 1)[1].split(",")[0]
    line = next(row for row in lines if row.strip().startswith(f"{temp} ="))
    while True:
        right_hand_side = line.partition("=")[2]
        operands = [token for token in right_hand_side.replace(",", " ").split() if token.startswith("%")]
        defined = [o for o in operands if any(row.strip().startswith(f"{o} =") for row in lines)]
        if not defined:
            return line
        line = next(row for row in lines if row.strip().startswith(f"{defined[-1]} ="))


def test_cpuid_calls_the_host_helper_and_reads_the_result_block():
    result = pl.lift_body(cpuid_body())
    assert result.holes == []
    assert "declare void @lift_cpuid(i64, ptr)" in result.decls
    assert "call void @lift_cpuid(i64" in result.ir
    assert cpuid_argument_line(result.ir).endswith("i64 0")
    buffer = next(line for line in result.ir.splitlines() if "call void @lift_cpuid" in line).rsplit("ptr ", 1)[1].rstrip(")")
    address = next(row for row in result.ir.splitlines() if f"= ptrtoint ptr {buffer} to i64" in row).split(" =")[0].strip()
    assert any(f"store i64 {address}," in row for row in result.ir.splitlines())
    assert verify(pl.module_for([result])).returncode == 0


def test_cpuid_passes_the_selected_leaf_to_the_helper():
    first, second = (pl.lift_body(cpuid_body(leaf=leaf)).ir for leaf in ("register,0,4", "register,8,4"))
    assert cpuid_argument_line(first).endswith("i64 0")
    assert cpuid_argument_line(second).endswith("i64 8")


def uniq_slots(ir):
    """Maps each pointer temp to the %uniq slot it addresses."""
    slots = {}
    for line in ir.splitlines():
        line = line.strip()
        if line.startswith("%") and "getelementptr i8, ptr %uniq" in line:
            name, _, right = line.partition(" =")
            slots[name.strip()] = int(right.rsplit("i64 ", 1)[1])
    return slots


def test_the_helper_result_block_avoids_the_body_own_temporaries():
    """The block is handed to the runtime as a pointer, so nothing in the body may write through it."""
    fn = body(
        insn(
            0x2153D33,
            5,
            op("CALLOTHER", "unique,900020,8", f"const,{CPUID_ID},4", "register,0,4", user="cpuid"),
            op("COPY", "unique,900020,8", "register,0,8"),
        ),
        start=0x2153D33,
    )
    result = pl.lift_body(fn)
    slots = uniq_slots(result.ir)
    buffer = next(line for line in result.ir.splitlines() if "call void @lift_cpuid" in line)
    buffer = buffer.rsplit("ptr ", 1)[1].rstrip(")")
    written = [line.rsplit("ptr ", 1)[1].rstrip(", align 1") for line in result.ir.splitlines() if " store " in line]
    assert slots[buffer] not in [slots[temp] for temp in written]


def test_cpuid_of_an_unexpected_shape_stays_a_hole():
    for out, extra in (("unique,7c900,4", []), (CPUID_BUFFER, ["const,1,4"])):
        fn = body(
            insn(0x2153D33, 4, op("CALLOTHER", out, f"const,{CPUID_ID},4", "register,0,4", *extra, user="cpuid")),
            insn(0x2153D37, 1, op("RETURN", None, "register,288,8")),
        )
        assert pl.lift_body(fn).holes == ["CALLOTHER:cpuid"]


def rdrand_body(start=0x2153CE9):
    return body(
        insn(
            start,
            6,
            op("CALLOTHER", "register,0,4", f"const,{RDRAND_ID},4", user="rdrand"),
            op("CALLOTHER", "register,200,1", f"const,{RDRAND_VALID_ID},4", user="rdrandIsValid"),
            op("COPY", "register,20b,1", "const,0,1"),
            op("INT_ZEXT", "register,30,8", "register,30,4"),
        ),
        insn(start + 6, 1, op("RETURN", None, "register,288,8")),
        start=start,
    )


def test_rdrand_calls_the_host_helper_once_and_sets_the_flag():
    result = pl.lift_body(rdrand_body())
    assert result.holes == []
    assert result.ir.count("call zeroext i1 @lift_rdrand(ptr") == 1
    assert "declare zeroext i1 @lift_rdrand(ptr)" in result.decls
    assert verify(pl.module_for([result])).returncode == 0


def test_rdrand_alone_and_the_valid_flag_alone_both_lower():
    for op_index, name in ((0, "rdrand"), (1, "rdrandIsValid")):
        insn_row = rdrand_body()["insns"][0]
        ops = [insn_row["ops"][op_index], insn_row["ops"][-1]]
        fn = body(insn(0x2153CE9, 6, *ops), insn(0x2153CEF, 1, op("RETURN", None, "register,288,8")))
        result = pl.lift_body(fn)
        assert result.holes == [], name
        assert result.ir.count("call zeroext i1 @lift_rdrand(ptr") == 1


def test_rdrand_of_an_unexpected_result_width_stays_a_hole():
    fn = body(
        insn(0x2153CE9, 6, op("CALLOTHER", "register,0,8", f"const,{RDRAND_ID},4", user="rdrand")),
        insn(0x2153CEF, 1, op("RETURN", None, "register,288,8")),
    )
    assert pl.lift_body(fn).holes == ["CALLOTHER:rdrand"]


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
    assert pl.lift_body(packed_body("divps", DIVPS_ID, dst="register,1200,32", src="register,1280,32")).holes == [
        "CALLOTHER:divps"
    ]
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
        (a,) = struct.unpack_from(fmt, first, at)
        (b,) = struct.unpack_from(fmt, second, at)
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
    return PACKED_DRIVER.format(sse=sse, extern=extern, call=call, got=got, rows=rows, dst=XMM0_BYTES, src=XMM2_BYTES)


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
    assert pl.lift_body(packed_body("minps", MINPS_ID, dst="register,1200,32", src="register,1280,32")).holes == [
        "CALLOTHER:minps"
    ]
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
    cases = [(lanes_of([first] * 4), lanes_of([second] * 4), lanes_of([second] * 4)) for first, second in SECOND_SOURCE]
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


BSS = {"name": "_bss", "va": 0x53_00000, "size": 0x20_0000, "exec": False}
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


class StubEvidence:
    def __init__(self, raw):
        self.raw = raw
        self.calls = []

    def raw_cases(self, boundaries, site):
        self.calls.append((tuple(boundaries), site))
        return self.raw


def switch_body(*extra_ops):
    fn = body(
        insn(0x1000, 4, op("COPY", "register,0,8", "cptr,5000,8")),
        insn(0x1004, 2, op("BRANCHIND", None, "register,0,8")),
        insn(0x1006, 2, op("COPY", REG_EAX, "const,1,4"), op("RETURN", None, "register,288,8")),
        insn(0x1008, 2, op("COPY", REG_EAX, "const,2,4"), op("RETURN", None, "register,288,8")),
        insn(0x100A, 5, *extra_ops) if extra_ops else insn(0x100A, 1, op("RETURN", None, "register,288,8")),
    )
    fn["jt"] = [{"at": 0x1004, "cases": [0x1006, 0x1008, 0x7000]}]
    return fn


def test_table_bytes_replace_a_case_list_ghidra_padded_with_a_direct_edge():
    fn = switch_body(op("BRANCH", None, "ram,7000,8"))
    evidence = StubEvidence([0x1006, 0x1008])
    result = pl.lift_body(fn, [RODATA, TEXT], evidence=evidence)
    assert result.holes == []
    assert result.tables_audited == 1
    assert evidence.calls == [((0x1000, 0x1004, 0x1006, 0x1008, 0x100A), 0x1004)]
    assert "switch i64" in result.ir
    arms = result.ir.split("switch i64")[1].split("[")[1].split("]")[0]
    assert arms.count("i64 ") == 2
    assert "28672" not in arms


def test_table_bytes_are_refused_when_the_dropped_case_lands_on_the_bodys_own_code():
    fn = switch_body()
    fn["jt"] = [{"at": 0x1004, "cases": [0x1006, 0x1008, 0x1005]}]
    result = pl.lift_body(fn, [RODATA, TEXT], evidence=StubEvidence([0x1006, 0x1008]))
    assert result.holes == ["JUMPTABLE_TARGET"]
    assert result.tables_audited == 0


def test_table_bytes_replace_a_case_list_ghidra_padded_with_code_from_another_frame():
    fn = switch_body()
    fn["jt"] = [{"at": 0x1004, "cases": [0x1006, 0x1008, 0x7000, 0x9000]}]
    result = pl.lift_body(fn, [RODATA, TEXT], evidence=StubEvidence([0x1006, 0x1008]))
    assert result.holes == []
    assert result.tables_audited == 1


def test_table_bytes_are_refused_when_they_run_past_the_body_too():
    fn = switch_body(op("BRANCH", None, "ram,7000,8"))
    result = pl.lift_body(fn, [RODATA, TEXT], evidence=StubEvidence([0x1006, 0x7000]))
    assert result.holes == ["JUMPTABLE_TARGET"]
    assert result.tables_audited == 0


def test_table_bytes_are_refused_when_an_entry_is_not_an_instruction_start():
    fn = switch_body()
    fn["jt"] = [{"at": 0x1004, "cases": [0x1006, 0x1008, 0x7000]}]
    result = pl.lift_body(fn, [RODATA, TEXT], evidence=StubEvidence([0x1006, 0x1009]))
    assert result.holes == ["JUMPTABLE_TARGET"]
    assert result.tables_audited == 0


def test_table_bytes_are_not_consulted_when_the_case_list_is_already_clean():
    fn = body(
        insn(0x1000, 4, op("COPY", "register,0,8", "cptr,5000,8")),
        insn(0x1004, 2, op("BRANCHIND", None, "register,0,8")),
        insn(0x1006, 2, op("COPY", REG_EAX, "const,1,4"), op("RETURN", None, "register,288,8")),
    )
    fn["jt"] = [{"at": 0x1004, "cases": [0x1006]}]
    evidence = StubEvidence([0x1006])
    assert pl.lift_body(fn, [RODATA, TEXT], evidence=evidence).holes == []
    assert evidence.calls == []


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


def test_branchind_on_a_computed_register_with_an_unbalanced_frame_stays_a_hole():
    # The same computed target, but a push with no matching pop leaves rsp off its entry value, so the
    # proof fails and the site stays a recorded hole: the emitter never guesses a tail call.
    fn = body(
        insn(0x1000, 3, op("INT_SUB", REG_RSP, REG_RSP, "const,8,8")),
        insn(0x1003, 3, op("INT_ADD", "register,0,8", "register,0,8", "const,8,8")),
        insn(0x1006, 2, op("BRANCHIND", None, "register,0,8")),
    )
    assert pl.lift_body(fn).holes == ["BRANCHIND"]


@requires_llvm
def test_branchind_on_a_fixed_memory_word_at_a_proven_frame_is_an_indirect_tail_call():
    # `jmp *[rip+slot]` has no index register, so it cannot be a jump table; relocations are not consulted.
    fn = body(insn(0x1000, 6, op("BRANCHIND", None, "ram,5353720,8")))
    result = pl.lift_body(fn)
    assert result.holes == []
    assert result.tail_calls == 1
    assert result.proven_tail_calls == 1
    assert result.indirect_calls == 1
    assert result.unproven_branchind == []
    assert verify(pl.module_for([result])).returncode == 0


def test_branchind_on_a_fixed_memory_word_with_an_unbalanced_frame_stays_a_hole():
    fn = body(
        insn(0x1000, 3, op("INT_SUB", REG_RSP, REG_RSP, "const,8,8")),
        insn(0x1003, 6, op("BRANCHIND", None, "ram,5353720,8")),
    )
    result = pl.lift_body(fn)
    assert result.holes == ["BRANCHIND"]
    assert result.tail_calls == 0
    assert result.unproven_branchind[0]["reason"] == "rsp not at entry value"


def test_refused_branchind_with_a_proven_frame_names_the_handover_shape():
    # rsp is proven at its entry value here, so the frame pass has nothing to complain about: the site
    # is refused because its target is computed. The record has to say that, not a frame failure.
    fn = body(
        insn(0x1000, 3, op("INT_ADD", "register,0,8", "register,0,8", "const,8,8")),
        insn(0x1003, 2, op("BRANCHIND", None, "register,0,8")),
    )
    result = pl.lift_body(fn)
    assert result.holes == ["BRANCHIND"]
    assert result.unproven_branchind[0]["reason"] == "frame proven, handover shape refused"
    assert result.unproven_branchind[0]["rsp_delta"] == 0


def test_refused_branchind_names_a_missing_table_when_the_image_bytes_decode_one():
    # The same shape, but the image's own bytes say the target is a jump-table dispatch: the cause of
    # the hole is the table Ghidra never recovered, and that is what the record has to say.
    fn = body(
        insn(0x1000, 3, op("INT_ADD", "register,0,8", "register,0,8", "const,8,8")),
        insn(0x1003, 2, op("BRANCHIND", None, "register,0,8")),
        insn(0x1005, 2, op("COPY", REG_EAX, "const,1,4"), op("RETURN", None, "register,288,8")),
        insn(0x1007, 2, op("COPY", REG_EAX, "const,2,4"), op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn, [RODATA, TEXT], evidence=StubEvidence([0x1005, 0x1007]))
    assert result.holes == ["BRANCHIND"]
    assert result.unproven_branchind[0]["reason"] == "jump table not in the dump"


def test_refused_branchind_reports_a_table_only_when_the_bytes_decode_a_complete_one():
    # A table with a case outside the body explains nothing, so the refusal is still the handover shape.
    fn = body(
        insn(0x1000, 3, op("INT_ADD", "register,0,8", "register,0,8", "const,8,8")),
        insn(0x1003, 2, op("BRANCHIND", None, "register,0,8")),
        insn(0x1005, 2, op("COPY", REG_EAX, "const,1,4"), op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn, [RODATA, TEXT], evidence=StubEvidence([0x1005, 0x9000]))
    assert result.unproven_branchind[0]["reason"] == "frame proven, handover shape refused"


def test_refused_branchind_keeps_the_frame_verdict_when_a_path_really_is_missing():
    # A BRANCHIND no instruction in the body can reach: the frame pass is the one with the complaint,
    # and its own wording has to survive into the record.
    fn = body(
        insn(0x1000, 3, op("BRANCH", None, "ram,1003,8")),
        insn(0x1003, 1, op("RETURN", None, "register,288,8")),
        insn(0x1004, 2, op("BRANCHIND", None, "register,0,8")),
    )
    result = pl.lift_body(fn)
    assert result.holes == ["BRANCHIND"]
    assert result.unproven_branchind[0]["reason"] == "no path in the dump reaches the site"


def test_refused_branchind_reports_a_frame_verdict_and_the_table_bytes_together():
    # The shape the Unity.Mathematics dispatches have: rsp is off its entry value, so the frame pass has
    # the complaint, and the image's bytes still say the target is a jump-table dispatch. Both belong
    # in the record: the reason is what the frame pass saw, table_bytes is what the image says.
    fn = body(
        insn(0x1000, 3, op("INT_SUB", REG_RSP, REG_RSP, "const,8,8")),
        insn(0x1003, 3, op("INT_ADD", "register,0,8", "register,0,8", "const,8,8")),
        insn(0x1006, 2, op("BRANCHIND", None, "register,0,8")),
        insn(0x1008, 2, op("COPY", REG_EAX, "const,1,4"), op("RETURN", None, "register,288,8")),
        insn(0x100A, 2, op("COPY", REG_EAX, "const,2,4"), op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn, [RODATA, TEXT], evidence=StubEvidence([0x1008, 0x100A]))
    assert result.unproven_branchind[0]["reason"] == "rsp not at entry value"
    assert result.unproven_branchind[0]["table_bytes"] is True


def test_refused_branchind_records_no_table_bytes_without_evidence_or_a_partial_decode():
    fn = body(
        insn(0x1000, 3, op("INT_SUB", REG_RSP, REG_RSP, "const,8,8")),
        insn(0x1003, 3, op("INT_ADD", "register,0,8", "register,0,8", "const,8,8")),
        insn(0x1006, 2, op("BRANCHIND", None, "register,0,8")),
        insn(0x1008, 2, op("COPY", REG_EAX, "const,1,4"), op("RETURN", None, "register,288,8")),
    )
    assert pl.lift_body(fn, [RODATA, TEXT]).unproven_branchind[0]["table_bytes"] is False
    partial = pl.lift_body(fn, [RODATA, TEXT], evidence=StubEvidence([0x1008, 0x9000]))
    assert partial.unproven_branchind[0]["table_bytes"] is False
    assert partial.unproven_branchind[0]["reason"] == "rsp not at entry value"


class StubTable:
    """TableEvidence stand-in answering both the case-list and the pattern-and-cases question."""

    def __init__(self, table):
        self.table = table
        self.calls = []

    def raw_table(self, boundaries, site):
        self.calls.append((tuple(boundaries), site))
        return self.table

    def raw_cases(self, boundaries, site):
        table = self.raw_table(boundaries, site)
        return None if table is None else table["cases"]


def dispatch_insn(base="cptr,5010,8", entry="unique,23c00,4", loader=None, scale="const,4,8"):
    """The op sequence the dump carries for a base-relative jump-table dispatch.

    Copied from 0x3ac553c: the table base copied from a cptr constant, the index scaled by the entry
    size, the entry loaded and sign-extended, then added to the base to land on the target.
    """
    return [
        op("COPY", "register,10,8", base),
        op("INT_MULT", "unique,9200,8", "register,0,8", scale),
        op("INT_ADD", "unique,9400,8", "register,10,8", "unique,9200,8"),
        loader or op("LOAD", entry, "const,4,4", "unique,9400,8"),
        op("INT_SEXT", "register,0,8", entry),
        op("INT_ADD", "register,0,8", "register,0,8", "register,10,8"),
    ]


def dispatch_body(extra=(), jt=(), **kw):
    fn = body(
        insn(0x1000, 4, op("COPY", "register,38,4", "const,0,4")),
        insn(0x1004, 16, *dispatch_insn(**kw)),
        insn(0x1014, 2, op("BRANCHIND", None, "register,0,8")),
        insn(0x1016, 2, op("COPY", REG_EAX, "const,1,4"), op("RETURN", None, "register,288,8")),
        insn(0x1018, 2, op("COPY", REG_EAX, "const,2,4"), op("RETURN", None, "register,288,8")),
        *extra,
    )
    return {**fn, "jt": list(jt)}


TABLE = {"base": 0x5010, "scale": 4, "count": 2, "cases": [0x1016, 0x1018], "window": 0x1000}


def test_the_images_table_bytes_drive_a_switch_ghidra_left_without_one():
    result = pl.lift_body(dispatch_body(), [RODATA, TEXT], evidence=StubTable(TABLE))
    assert result.holes == []
    assert result.evidence_switches == 1
    assert "switch i64" in result.ir
    assert "ptr @sec_rodata" in result.ir
    arms = result.ir.split("switch i64")[1].split("[")[1].split("]")[0]
    assert arms.count("i64 ") == 2
    assert "4118" in arms and "4120" in arms


@requires_llvm
def test_a_switch_from_byte_evidence_verifies():
    result = pl.lift_body(dispatch_body(), [RODATA, TEXT], evidence=StubTable(TABLE))
    assert result.holes == []
    assert "switch i64" in result.ir
    assert verify(pl.module_for([result])).returncode == 0


def test_an_evidence_switch_is_refused_for_absolute_entries():
    # Scale 8 entries hold absolute addresses, which the switch's rebasing cannot resolve back to a
    # dumped address, so the site keeps its hole rather than lowering a switch that never matches.
    result = pl.lift_body(dispatch_body(), [RODATA, TEXT], evidence=StubTable({**TABLE, "scale": 8}))
    assert result.holes == ["BRANCHIND"]
    assert result.evidence_switches == 0


def test_an_evidence_switch_is_refused_when_a_case_lands_outside_the_body():
    result = pl.lift_body(dispatch_body(), [RODATA, TEXT], evidence=StubTable({**TABLE, "cases": [0x1016, 0x7000]}))
    assert result.holes == ["BRANCHIND"]
    assert result.evidence_switches == 0


def test_an_evidence_switch_is_refused_when_the_base_is_not_the_tables_section():
    # A target built from a pointer that did not come from the table's own section cannot be rebased
    # against it, whatever the table bytes say.
    elsewhere = pl.lift_body(dispatch_body(base="cptr,9000,8"), [RODATA, TEXT], evidence=StubTable(TABLE))
    assert elsewhere.holes == ["BRANCHIND"]
    assert elsewhere.evidence_switches == 0
    computed = pl.lift_body(dispatch_body(base="unique,9100,8"), [RODATA, TEXT], evidence=StubTable(TABLE))
    assert computed.holes == ["BRANCHIND"]
    assert computed.evidence_switches == 0


def test_an_evidence_switch_is_refused_when_the_base_is_not_the_tables_own_address():
    # Another address in the same section is not the decoded table: the dispatch would read a different table.
    result = pl.lift_body(dispatch_body(base="cptr,5014,8"), [RODATA, TEXT], evidence=StubTable(TABLE))
    assert result.holes == ["BRANCHIND"]
    assert result.evidence_switches == 0


def test_an_evidence_switch_is_refused_when_the_base_is_read_from_memory():
    # A ram COPY loads the value stored at that address, so it names a pointer, not the table.
    result = pl.lift_body(dispatch_body(base="ram,5010,8"), [RODATA, TEXT], evidence=StubTable(TABLE))
    assert result.holes == ["BRANCHIND"]
    assert result.evidence_switches == 0


def side_entry(target, at=0x101A):
    return insn(at, 2, op("CBRANCH", None, f"ram,{target:x},8", "unique,25400,1"))


def test_an_evidence_switch_is_refused_when_a_branch_enters_after_the_guard():
    # An edge into the span between the guard and the dispatch skips the bound the case list rests on.
    result = pl.lift_body(dispatch_body(extra=[side_entry(0x1004)]), [RODATA, TEXT], evidence=StubTable(TABLE))
    assert result.holes == ["BRANCHIND"]
    assert result.evidence_switches == 0
    at_dispatch = pl.lift_body(dispatch_body(extra=[side_entry(0x1014)]), [RODATA, TEXT], evidence=StubTable(TABLE))
    assert at_dispatch.holes == ["BRANCHIND"]
    assert at_dispatch.evidence_switches == 0


def test_an_evidence_switch_is_refused_when_a_jump_table_case_enters_after_the_guard():
    result = pl.lift_body(dispatch_body(jt=[{"at": 0x9000, "cases": [0x1004]}]), [RODATA, TEXT], evidence=StubTable(TABLE))
    assert result.holes == ["BRANCHIND"]
    assert result.evidence_switches == 0


def test_an_evidence_switch_accepts_a_branch_that_enters_at_the_start_of_the_guarded_span():
    result = pl.lift_body(dispatch_body(extra=[side_entry(0x1000)]), [RODATA, TEXT], evidence=StubTable(TABLE))
    assert result.holes == []
    assert result.evidence_switches == 1


def test_an_evidence_switch_is_refused_without_a_guarded_span():
    result = pl.lift_body(dispatch_body(), [RODATA, TEXT], evidence=StubTable({**TABLE, "window": None}))
    assert result.holes == ["BRANCHIND"]
    assert result.evidence_switches == 0


def test_an_evidence_switch_is_refused_unless_the_entry_is_a_table_load():
    copied = dispatch_insn(loader=op("COPY", "unique,23c00,4", "unique,9400,8"))
    fn = body(insn(0x1000, 20, *copied), insn(0x1014, 2, op("BRANCHIND", None, "register,0,8")))
    result = pl.lift_body(fn, [RODATA, TEXT], evidence=StubTable({**TABLE, "cases": [0x1014]}))
    assert result.holes == ["BRANCHIND"]
    assert result.evidence_switches == 0


def test_an_evidence_switch_is_refused_when_the_index_is_not_scaled_by_the_entry_size():
    fn = body(
        insn(
            0x1000,
            20,
            *dispatch_insn(scale="const,8,8"),
        ),
        insn(0x1014, 2, op("BRANCHIND", None, "register,0,8")),
        insn(0x1016, 2, op("COPY", REG_EAX, "const,1,4"), op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn, [RODATA, TEXT], evidence=StubTable({**TABLE, "cases": [0x1016]}))
    assert result.holes == ["BRANCHIND"]
    assert result.evidence_switches == 0


def test_byte_evidence_never_replaces_a_proven_sibling_tail_call():
    # The evidence switch is only reached by a site the tail-call gates refuse: a site that already
    # lowers as a proven tail call keeps that lowering whatever the table bytes say about it.
    fn = body(
        insn(0x1000, 3, op("COPY", "register,0,8", "register,30,8")),
        insn(0x1003, 2, op("BRANCHIND", None, "register,0,8")),
    )
    result = pl.lift_body(fn, [RODATA, TEXT], evidence=StubTable(TABLE))
    assert result.holes == []
    assert result.tail_calls == 1
    assert result.evidence_switches == 0
    assert "switch i64" not in result.ir


def test_a_hole_without_evidence_records_no_switch():
    result = pl.lift_body(dispatch_body(), [RODATA, TEXT])
    assert result.holes == ["BRANCHIND"]
    assert result.evidence_switches == 0


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


@requires_llvm
def test_branchind_on_a_handed_over_register_at_a_proven_frame_is_a_tail_call():
    """`mov rbx, rdi ... mov rdi, rdx; jmp rbx`: a tail call through a pointer the caller supplied.

    This is the shape the image's blocked sites ship. The target register is written exactly once,
    before the jump, by a plain COPY from another register, and rsp is proven at its entry value:
    the callee returns to our caller, which is what `call reg; ret` does.
    """
    fn = body(
        insn(0x1000, 3, op("COPY", "register,80,8", "register,38,8")),
        insn(0x1003, 3, op("COPY", "register,38,8", "register,10,8")),
        insn(0x1006, 2, op("BRANCHIND", None, "register,80,8")),
    )
    result = pl.lift_body(fn)
    assert result.holes == []
    assert result.tail_calls == 1
    assert result.proven_tail_calls == 1
    assert verify(pl.module_for([result])).returncode == 0


def test_branchind_on_a_handed_over_register_without_a_proven_frame_stays_a_hole():
    """The shape alone licenses nothing: a push with no matching pop still refuses the rewrite."""
    fn = body(
        insn(0x1000, 3, op("COPY", "register,80,8", "register,38,8")),
        insn(0x1003, 3, op("INT_SUB", REG_RSP, REG_RSP, "const,8,8")),
        insn(0x1006, 3, op("COPY", "register,38,8", "register,10,8")),
        insn(0x1009, 2, op("BRANCHIND", None, "register,80,8")),
    )
    assert pl.lift_body(fn).holes == ["BRANCHIND"]


def test_branchind_on_a_target_written_twice_before_the_jump_stays_a_hole():
    fn = body(
        insn(0x1000, 3, op("COPY", "register,80,8", "register,38,8")),
        insn(0x1003, 3, op("COPY", "register,80,8", "register,10,8")),
        insn(0x1006, 2, op("BRANCHIND", None, "register,80,8")),
    )
    assert pl.lift_body(fn).holes == ["BRANCHIND"]


def test_branchind_on_a_target_written_after_the_jump_stays_a_hole():
    """A register the body keeps writing is reused storage, not a value handed over for this jump."""
    fn = body(
        insn(0x1000, 3, op("COPY", "register,80,8", "register,38,8")),
        insn(0x1003, 2, op("BRANCHIND", None, "register,80,8")),
        insn(0x1005, 3, op("COPY", "register,80,8", "register,10,8")),
    )
    assert pl.lift_body(fn).holes == ["BRANCHIND"]


def test_branchind_on_a_target_copied_from_a_constant_stays_a_hole():
    fn = body(
        insn(0x1000, 3, op("COPY", "register,80,8", "const,4000,8")),
        insn(0x1003, 2, op("BRANCHIND", None, "register,80,8")),
    )
    assert pl.lift_body(fn).holes == ["BRANCHIND"]


def test_branchind_on_a_target_copied_from_a_computed_temporary_stays_a_hole():
    """The one write is a COPY, but from a temporary the body built: that is a computed target."""
    fn = body(
        insn(
            0x1000,
            4,
            op("INT_ADD", "unique,8e00,8", "register,38,8", "register,10,8"),
            op("COPY", "register,80,8", "unique,8e00,8"),
        ),
        insn(0x1004, 2, op("BRANCHIND", None, "register,80,8")),
    )
    result = pl.lift_body(fn)
    assert result.holes == ["BRANCHIND"]
    assert result.tail_calls == 0


def test_branchind_on_a_target_sign_extended_before_the_jump_stays_a_hole():
    """A one-operand arithmetic op, so the arity of the operands is not what refuses it."""
    fn = body(
        insn(0x1000, 3, op("INT_SEXT", "register,80,8", "register,80,4")),
        insn(0x1003, 2, op("BRANCHIND", None, "register,80,8")),
    )
    assert pl.lift_body(fn).holes == ["BRANCHIND"]


def test_branchind_on_a_target_defined_by_an_intrinsic_stays_a_hole():
    """The image has this shape: a CALLOTHER result jumped through, one operand, never a handover."""
    fn = body(
        insn(0x1000, 4, op("CALLOTHER", "register,80,8", "const,57,4", user="rdrand")),
        insn(0x1004, 2, op("BRANCHIND", None, "register,80,8")),
    )
    result = pl.lift_body(fn)
    assert result.tail_calls == 0
    assert "BRANCHIND" in result.holes


def test_branchind_on_a_target_copied_after_an_untrackable_write_stays_a_hole():
    fn = body(
        insn(0x1000, 3, op("COPY", "register,80,8", "register,38,8")),
        insn(0x1003, 3, op("COPY", REG_RSP, "register,48,8")),
        insn(0x1006, 2, op("BRANCHIND", None, "register,80,8")),
    )
    assert pl.lift_body(fn).holes == ["BRANCHIND"]


REG_RSP = "register,20,8"


SLOT = 0x53_67070


def thunk_body(*, unbalanced=None, entry=0x1000, table=False, guard_target=None):
    """The il2cpp lazily-resolved thunk: a slot load, a null-guard to a cold resolver, teardown, `jmp rax`.

    The cold block resolves the slot by calling the resolver and returning, so the site is reached
    only by the fallthrough. `unbalanced` puts an extra rsp write on that fallthrough (a trackable
    `INT_SUB`/`INT_ADD`, or a `COPY` of rsp from a register), the only way to knock the site off the
    entry value. `table` swaps the jump target for a slot reloaded through a computed pointer, the
    shape a recovered jump table arrives in.
    """
    slot = f"ram,{SLOT:x},8"
    target = "register,80,8" if table else "register,0,8"
    taken = f"ram,{entry + 0x20:x},8" if guard_target is None else guard_target
    insns = [
        insn(
            entry,
            1,
            op("COPY", "unique,4f900,8", "register,18,8"),
            op("INT_SUB", REG_RSP, REG_RSP, "const,8,8"),
            op("STORE", None, "const,1b1,8", REG_RSP, "unique,4f900,8"),
        ),
        insn(
            entry + 1,
            2,
            op("COPY", "register,0,8", slot),
            op("INT_EQUAL", "register,206,1", "register,0,8", "const,0,8"),
        ),
        insn(entry + 3, 2, op("CBRANCH", None, taken, "register,206,1")),
        insn(entry + 5, 1, op("INT_ADD", REG_RSP, REG_RSP, "const,8,8"), op("COPY", "register,18,8", "unique,4f900,8")),
    ]
    if unbalanced is not None:
        insns.append(insn(entry + 6, 1, unbalanced))
    site_at = entry + 6 + (1 if unbalanced is not None else 0)
    if table:
        insns.append(
            insn(
                site_at,
                3,
                op("INT_ADD", "unique,8e00,8", "register,38,8", "const,40,8"),
                op("LOAD", "unique,23d00,8", "const,1b1,8", "unique,8e00,8"),
                op("COPY", "register,80,8", "unique,23d00,8"),
            )
        )
        site_at += 3
    insns.append(insn(site_at, 2, op("BRANCHIND", None, target)))
    cold = entry + 0x20
    insns += [
        insn(cold, 1, op("CALL", None, "ram,2056380,8")),
        insn(cold + 1, 1, op("RETURN", None, "register,288,8")),
    ]
    return body(*insns, start=entry)


def test_branchind_at_balanced_rsp_from_a_slot_load_lifts_as_a_tail_call():
    result = pl.lift_body(thunk_body(), [BSS, RODATA, TEXT])
    assert pl.site_proof(thunk_body()) == {0x1006: {"reason": "", "rsp_delta": 0}}
    assert result.holes == []
    assert result.tail_calls == 1
    assert result.proven_tail_calls == 1
    assert result.unproven_branchind == []


@requires_llvm
def test_proven_tail_call_emits_an_indirect_call_and_a_return():
    result = pl.lift_body(thunk_body(), [BSS, RODATA, TEXT])
    assert "call void %t" in result.ir
    assert "inttoptr" in result.ir
    assert "ret void" in result.ir
    assert "switch i64" not in result.ir
    assert verify(pl.module_for([result])).returncode == 0


def test_branchind_after_an_unbalanced_trackable_write_stays_a_hole():
    """An extra `sub rsp` on the only path into the site leaves it off the entry value."""
    sub_op = op("INT_SUB", REG_RSP, REG_RSP, "const,10,8")
    result = pl.lift_body(thunk_body(unbalanced=sub_op), [BSS, RODATA, TEXT])
    assert result.holes == ["BRANCHIND"]
    assert result.tail_calls == 0
    assert result.proven_tail_calls == 0
    assert pl.site_proof(thunk_body(unbalanced=sub_op))[0x1007] == {
        "reason": "rsp not at entry value",
        "rsp_delta": -16,
    }


def test_branchind_after_a_frame_pointer_restore_stays_a_hole():
    """`leave` restores rsp from rbp, a COPY the balance pass cannot reduce to a delta."""
    leave = op("COPY", REG_RSP, "register,10,8")
    result = pl.lift_body(thunk_body(unbalanced=leave), [BSS, RODATA, TEXT])
    assert result.holes == ["BRANCHIND"]
    assert result.proven_tail_calls == 0
    assert pl.site_proof(thunk_body(unbalanced=leave))[0x1007] == {
        "reason": "rsp untrackable on a path into the site",
        "rsp_delta": None,
    }


def test_branchind_reaching_a_target_outside_the_dump_is_untracked_not_proven():
    """A body whose only path into the site runs off its end leaves the balance untrackable."""
    fn = thunk_body()
    fn["insns"] = [i for i in fn["insns"] if i["a"] < 0x1020]  # drop the cold block: the site is now the last byte
    del fn["size"]
    fn = body(*fn["insns"], start=fn["start"])
    del fn["insns"][-1]  # drop the site itself; a fallthrough off the end with nothing to balance
    assert pl.site_proof(fn) == {}


def test_branchind_past_an_unemitted_branch_target_is_untracked_not_proven():
    """A CBRANCH whose target the dump never emitted makes every site downstream untrackable."""
    fn = thunk_body(guard_target="ram,0x900000,8")  # guard jumps to an address with no instruction there
    assert pl.site_proof(fn)[0x1006] == {
        "reason": "rsp untrackable on a path into the site",
        "rsp_delta": None,
    }
    result = pl.lift_body(fn, [BSS, RODATA, TEXT])
    assert result.holes == ["BRANCHIND"]
    assert result.proven_tail_calls == 0


def test_terminating_branch_to_an_unemitted_target_stays_a_balanced_tail_call():
    """A `jmp` out of the dump is a tail call the emitter lowers to call+ret, which returns balanced."""
    # A BRANCHIND site reached without crossing an escaping CBRANCH still proves, even though the
    # body also terminates on a BRANCH to an address the dump never emitted.
    fn = body(
        insn(0x1000, 3, op("INT_SUB", REG_RSP, REG_RSP, "const,20,8"), op("COPY", "register,0,8", f"ram,{SLOT:x},8")),
        insn(0x1003, 3, op("INT_ADD", REG_RSP, REG_RSP, "const,20,8")),
        insn(0x1006, 2, op("BRANCHIND", None, "register,0,8")),
        insn(0x1008, 5, op("BRANCH", None, "ram,0x900000,8")),
    )
    assert pl.site_proof(fn)[0x1006] == {"reason": "", "rsp_delta": 0}
    assert pl.lift_body(fn).proven_tail_calls == 1


def test_branchind_left_hung_by_an_untrackable_body_is_not_proven():
    """A straight-line instruction whose fallthrough runs off the body end makes the site untrackable."""
    # A push, then an unconditional BRANCHIND reached by fallthrough with nothing after it: the
    # straight-line push leaves the body with rsp off entry and no return to balance it.
    fn = body(
        insn(
            0x1000,
            1,
            op("COPY", "unique,4f900,8", "register,18,8"),
            op("INT_SUB", REG_RSP, REG_RSP, "const,8,8"),
            op("STORE", None, "const,1b1,8", REG_RSP, "unique,4f900,8"),
        ),
        insn(0x1001, 1, op("COPY", "register,0,8", "const,0,8")),
        insn(0x1002, 2, op("BRANCHIND", None, "register,0,8")),
    )
    assert pl.site_proof(fn)[0x1002] == {
        "reason": "rsp not at entry value",
        "rsp_delta": -8,
    }


def test_branchind_on_a_load_traced_target_at_unbalanced_rsp_still_lifts():
    """A mid-function `jmp reg` whose target traces to a LOAD lifts on the straight-line rule.

    The frame at the site is off entry (a push with no matching pop), so the balance proof does not
    prove it, but the load rule the emitter always trusted still lifts it: the proof is a refinement
    that may only add sites, never un-lift what `defined_by_load` already did.
    """
    fn = body(
        insn(0x1000, 3, op("INT_SUB", REG_RSP, REG_RSP, "const,8,8")),
        insn(
            0x1003,
            4,
            op("INT_ADD", "unique,8e00,8", "register,38,8", "const,40,8"),
            op("LOAD", "unique,23d00,8", "const,1b1,8", "unique,8e00,8"),
            op("COPY", "register,0,8", "unique,23d00,8"),
        ),
        insn(0x1007, 2, op("BRANCHIND", None, "register,0,8")),
        insn(0x1009, 1, op("INT_SUB", REG_RSP, REG_RSP, "const,8,8"), op("CALL", None, "ram,2056380,8")),
        insn(0x100A, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn)
    assert result.holes == []
    assert result.tail_calls == 1
    assert result.proven_tail_calls == 0  # lifted by the load rule, not by the balance proof
    assert pl.site_proof(fn)[0x1007] == {"reason": "rsp not at entry value", "rsp_delta": -8}


def test_body_with_no_indirect_jump_records_no_proof():
    fn = body(
        insn(0x1000, 3, op("INT_SUB", REG_RSP, REG_RSP, "const,20,8")),
        insn(0x1003, 1, op("RETURN", None, "register,288,8")),
    )
    result = pl.lift_body(fn)
    assert result.holes == []
    assert result.proven_tail_calls == 0
    assert result.unproven_branchind == []


def test_site_at_an_undecoded_address_is_a_hole_and_an_unproven_record():
    fn = thunk_body()
    fn["insns"] = [i for i in fn["insns"] if i["a"] != 0x1006]
    result = pl.lift_body(fn, [BSS, RODATA, TEXT])
    assert "GAP" in result.holes
    assert pl.site_proof(fn) == {}


@pytest.mark.parametrize("malformed", ["ops", "out", "varnode"])
def test_malformed_pcode_is_a_recorded_hole_not_a_crash(malformed):
    """An op the emitter cannot read is recorded, and the body never lifts as a tail call."""
    fn = thunk_body()
    teardown = next(i for i in fn["insns"] if i["a"] == 0x1005)
    rsp_op = next(o for o in teardown["ops"] if o.get("out") == REG_RSP)
    if malformed == "ops":
        rsp_op["in"] = []
    elif malformed == "out":
        rsp_op["in"][1] = "register,20"
    else:
        rsp_op["op"] = "NOSUCHOP"
    result = pl.lift_body(fn, [BSS, RODATA, TEXT])
    assert result.holes
    assert result.tail_calls == 0 and result.proven_tail_calls == 0


def test_branchind_with_a_recovered_table_stays_a_switch_and_needs_no_proof():
    """The switch route is unchanged: a table at the site wins over the balance proof."""
    fn = thunk_body(table=True)
    fn["jt"] = [{"at": 0x1009, "cases": [0x1000, 0x1020]}]
    result = pl.lift_body(fn, [BSS, RODATA, TEXT])
    assert result.holes == []
    assert "switch i64" in result.ir
    assert result.proven_tail_calls == 0
    assert result.unproven_branchind == []


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
DOUBLE_TO_I32 = cases(
    8,
    4,
    [
        (0.0, 0),
        (-0.0, 0),
        (1.5, 1),
        (-1.5, -1),
        (0.9999999, 0),
        (-0.9999999, 0),
        (2147483647.0, 2147483647),
        (2147483647.5, 2147483647),
        (-2147483648.0, INDEF32),
        (-2147483648.5, INDEF32),
        (-2147483649.0, INDEF32),
        (2147483648.0, INDEF32),
        (1e18, INDEF32),
        (float("inf"), INDEF32),
        (float("-inf"), INDEF32),
        (float("nan"), INDEF32),
        (0x7FF8000000000000, INDEF32),
        (QUIET_NAN_NEG, INDEF32),
        (SNAN64, INDEF32),
    ],
)
DOUBLE_TO_I64 = cases(
    8,
    8,
    [
        (0.0, 0),
        (-0.0, 0),
        (0.5, 0),
        (-0.5, 0),
        (1.5, 1),
        (-1.5, -1),
        (1e18, 10**18),
        (2.0**62, 2**62),
        (9223372036854774784.0, 9223372036854774784),
        (-(2.0**63), INDEF64),
        (-9223372036854776832.0, INDEF64),
        (2.0**63, INDEF64),
        (float("inf"), INDEF64),
        (float("-inf"), INDEF64),
        (float("nan"), INDEF64),
        (SNAN64, INDEF64),
    ],
)
FLOAT_TO_I32 = cases(
    4,
    4,
    [
        (0.0, 0),
        (-0.0, 0),
        (0.5, 0),
        (-0.5, 0),
        (1.5, 1),
        (-1.5, -1),
        (100000.0, 100000),
        (2147483392.0, 2147483392),
        (-2147483648.0, INDEF32),
        (-2147483904.0, INDEF32),
        (2147483648.0, INDEF32),
        (3e9, INDEF32),
        (float("inf"), INDEF32),
        (float("-inf"), INDEF32),
        (float("nan"), INDEF32),
        (0x7F800001, INDEF32),
    ],
)
FLOAT_TO_I64 = cases(
    4,
    8,
    [
        (0.0, 0),
        (-0.0, 0),
        (-0.5, 0),
        (1.5, 1),
        (-1.5, -1),
        (2.0**62, 2**62),
        (1e18, 999999984306749440),
        (-(2.0**63), INDEF64),
        (2.0**63, INDEF64),
        (float("inf"), INDEF64),
        (float("-inf"), INDEF64),
        (float("nan"), INDEF64),
    ],
)
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
    proc = subprocess.run([LLVM / "clang", "-O1", "-arch", arch, *extra, "-o", exe, source], text=True, capture_output=True)
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
    mismatches = compare_conversion(tmp_path, pl.lift_body(trunc_body(src, dst)), src, dst, SHAPES[(src, dst)], "arm64", None)
    assert mismatches == []


@requires_rosetta
@EVERY_SHAPE
def test_the_expectation_tables_match_the_real_x86_instruction(tmp_path, src, dst):
    """Native arm64 saturates where x86 returns the integer indefinite value, so the tables
    above need an oracle that is not arm64: this runs the instruction itself."""
    mismatches = compare_conversion(tmp_path, None, src, dst, SHAPES[(src, dst)], "x86_64", X86_CONVERT[(src, dst)])
    assert mismatches == []
