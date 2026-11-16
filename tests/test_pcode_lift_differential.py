"""Differential check of the pcode emitter: lifted arm64 must match native arm64.

Freestanding C is compiled to an x86-64 ELF, lifted through Ghidra pcode and the emitter,
rebuilt for arm64, and run against the same C compiled natively for arm64 on pseudo-random
inputs. Skipped unless the LLVM toolchain, Ghidra and an arm64 macOS host are present.
"""

import json
import lift_probe as lp
import os
import pcode_lift as pl
import pytest
import struct
import subprocess
import sys
from pathlib import Path

LLVM = Path("/opt/homebrew/opt/llvm/bin")
GHIDRA = next(iter(sorted(Path("/opt/homebrew/Cellar/ghidra").glob("*/libexec/support/analyzeHeadless"))), None)
SOURCE = Path(__file__).parent / "fixtures/lift/diff.c"
LIFT_DUMP = Path(__file__).resolve().parent.parent / "scripts/lift_probe"
JAVA = Path.home() / ".local/bin/mise"

pytestmark = pytest.mark.skipif(
    not (LLVM / "clang").exists() or GHIDRA is None or sys.platform != "darwin" or os.uname().machine != "arm64",
    reason="needs the LLVM toolchain, Ghidra and an arm64 macOS host",
)

# name -> (argument kinds, return kind). "s" is a scalar float, "d" a scalar double.
FUNCTIONS = {
    "f_sum": ("u", "u64"),
    "f_clamp": ("uuu", "i32"),
    "f_mix": ("uu", "u32"),
    "f_div": ("uu", "u64"),
    "f_u8": ("uu", "u8"),
    "f_sat": ("uu", "i32"),
    "f_collatz": ("u", "u64"),
    "f_switch": ("u", "i32"),
    "f_poly": ("dd", "d"),
    "f_f2i": ("d", "i32"),
    "f_d2i32": ("d", "i32"),
    "f_d2i64": ("d", "i64"),
    "f_f2i32": ("s", "i32"),
    "f_f2i64": ("s", "i64"),
    "f_divpd": ("vv", "v"),
    "f_divps": ("ff", "f"),
    "f_divps_mem": ("fp", "f"),
    "f_minps": ("ff", "f"),
    "f_maxps": ("ff", "f"),
    "f_movmskps": ("f", "u32"),
    "f_pshuflw": ("w", "w"),
}
# Returned lane by lane rather than computed, so a lifted version that picked the other
# source would differ in bits the tolerant comparison below forgives.
STRICT_LANES = {"f_minps", "f_maxps"}
RET_MASK = {
    "u64": "0xffffffffffffffffull",
    "i64": "0xffffffffffffffffull",
    "u32": "0xffffffffull",
    "i32": "0xffffffffull",
    "u8": "0xffull",
}
# name -> (C reference in diff.c, argument type, literals just inside and outside the
# destination's range). The reference is the oracle rather than a native cast because
# arm64 saturates where x86 returns the integer indefinite value.
CONVERSIONS = {
    "f_d2i32": (
        "r_d2i32",
        "double",
        ["2147483647.0", "2147483647.5", "2147483648.0", "-2147483648.0", "-2147483648.5", "-2147483649.0", "1e18", "-1e18"],
    ),
    "f_d2i64": (
        "r_d2i64",
        "double",
        [
            "9223372036854774784.0",
            "9223372036854775808.0",
            "-9223372036854775808.0",
            "-9223372036854776832.0",
            "4611686018427387904.0",
            "1e18",
            "-1e18",
        ],
    ),
    "f_f2i32": (
        "r_f2i32",
        "float",
        ["2147483392.0f", "2147483648.0f", "-2147483648.0f", "-2147483904.0f", "3e9f", "-3e9f"],
    ),
    "f_f2i64": (
        "r_f2i64",
        "float",
        ["9223372036854774784.0f", "9223372036854775808.0f", "-9223372036854775808.0f", "1e18f", "-1e18f", "1.7e30f"],
    ),
}

VEC_LANES = {"v": ("double", 2), "f": ("float", 4), "w": ("uint16_t", 8)}
REG = {"rax": 0x0, "rdx": 0x10, "rsp": 0x20, "rsi": 0x30, "rdi": 0x38, "xmm0": 0x1200, "xmm1": 0x1240}
INT_ARGS = ["rdi", "rsi", "rdx"]


def run(cmd, **kw):
    proc = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    assert proc.returncode == 0, f"{cmd[0]}: rc={proc.returncode} {proc.stdout[-400:]} {proc.stderr[-800:]}"
    return proc.stdout


def lift_x86_symbols(tmp_path):
    so = tmp_path / "diff.so"
    run(
        [
            LLVM / "clang",
            "--target=x86_64-linux-gnu",
            "-O1",
            "-fPIC",
            "-ffreestanding",
            "-nostdlib",
            "-shared",
            "-fuse-ld=lld",
            "-fno-stack-protector",
            "-fno-asynchronous-unwind-tables",
            "-o",
            so,
            SOURCE,
        ]
    )
    syms = {}
    for line in run([LLVM / "llvm-nm", "--print-size", "--defined-only", so]).splitlines():
        addr, size, kind, name = line.split()
        if name in FUNCTIONS:
            syms[name] = (int(addr, 16), int(size, 16))
    assert set(syms) == set(FUNCTIONS)
    for name, mnemonic in (("f_movmskps", "movmskps"), ("f_pshuflw", "pshuflw")):
        address, size = syms[name]
        assembly = run(
            [LLVM / "llvm-objdump", "-d", f"--start-address={address}", f"--stop-address={address + size}", so]
        )
        assert any(mnemonic in line.split() for line in assembly.splitlines())
    ranges = tmp_path / "ranges.txt"
    ranges.write_text("".join(f"{a:x} {s}\n" for a, s in syms.values()))
    env = {**os.environ, "JAVA_HOME": run([JAVA, "where", "java"]).strip(), "GHIDRA_HEADLESS_MAXMEM": "2G"}
    (tmp_path / "proj").mkdir()
    out = tmp_path / "pcode.jsonl"
    sections_json = tmp_path / "sections.json"
    run(
        [
            GHIDRA,
            tmp_path / "proj",
            "d",
            "-import",
            so,
            "-noanalysis",
            "-scriptPath",
            LIFT_DUMP,
            "-postScript",
            "LiftDump.java",
            ranges,
            out,
            sections_json,
        ],
        env=env,
    )
    sections = json.loads(sections_json.read_text())
    return syms, [json.loads(line) for line in out.read_text().splitlines()], sections, section_images(so, sections)


def section_images(so, sections):
    """Slices each loaded section's bytes out of the ELF through its PT_LOAD program headers."""
    data = so.read_bytes()
    phoff = struct.unpack_from("<Q", data, 0x20)[0]
    phentsize, phnum = struct.unpack_from("<HH", data, 0x36)
    loads = []
    for i in range(phnum):
        p_type, _flags, offset, vaddr, _paddr, filesz, _memsz, _align = struct.unpack_from(
            "<IIQQQQQQ", data, phoff + i * phentsize
        )
        if p_type == 1:
            loads.append((vaddr, offset, filesz))
    images = {}
    for sec in sections:
        for vaddr, offset, filesz in loads:
            if vaddr <= sec["va"] and sec["va"] + sec["size"] <= vaddr + filesz:
                start = offset + sec["va"] - vaddr
                images[sec["name"]] = data[start : start + sec["size"]]
    return images


def conversion_pickers():
    """One picker per conversion: the specials that make the x86 and arm64 rules disagree,
    the boundary literals, and scaled randoms on the rest."""
    out = []
    for name, (_, ty, bounds) in CONVERSIONS.items():
        if ty == "double":
            special = [
                "0.0",
                "-(double)0.0",
                "bitsd(0x7ff0000000000000ull)",
                "bitsd(0xfff0000000000000ull)",
                "bitsd(0x7ff8000000000000ull)",
                "bitsd(0x7ff0000000000001ull)",
            ]
            random = "(double)(int64_t)v / 1e12"
        else:
            special = [
                "0.0f",
                "-(float)0.0f",
                "bitsf(0x7f800000u)",
                "bitsf(0xff800000u)",
                "bitsf(0x7fc00000u)",
                "bitsf(0x7f800001u)",
            ]
            random = "(float)(int32_t)v / 1e6f"
        arms = " ".join(f"case {i}: return {v};" for i, v in enumerate(special + bounds))
        out.append(
            f"static {ty} pick_{name}(void) {{ uint64_t v = next();"
            f" switch (v % {len(special) + len(bounds) + 1}u) {{ {arms} default: return {random}; }} }}"
        )
    return out


def harness_source(syms):
    lines = ["#include <stdint.h>", "#include <stdio.h>", "#include <string.h>", "#include <math.h>"]
    for name in FUNCTIONS:
        lines.append(f"extern void sub_{syms[name][0]:x}(unsigned char *reg);")
    lines.append(open(SOURCE).read().replace("#include <stdint.h>", ""))
    lines += [
        "static unsigned char stack[1 << 16];",
        "static uint64_t lcg = 88172645463325252ull;",
        "static uint64_t next(void) { lcg = lcg * 6364136223846793005ull + 1442695040888963407ull; return lcg >> 7 ^ lcg << 3; }",
        "static uint64_t pick(void) { uint64_t v = next(); switch (v & 7) { case 0: return v & 0xff; case 1: return -(v & 0xff); case 2: return 0; case 3: return 0x7fffffff; default: return v; } }",
        "static double pickd(void) { return (double)(int64_t)next() / 1e12; }",
        "static double bitsd(uint64_t b) { double d; memcpy(&d, &b, 8); return d; }",
        "static float bitsf(uint32_t b) { float f; memcpy(&f, &b, 4); return f; }",
        "static double pickdv(void) { uint64_t v = next(); switch (v % 8u) {"
        " case 0: return 0.0; case 1: return -(double)0.0;"
        " case 2: return bitsd(0x7ff0000000000000ull); case 3: return bitsd(0xfff0000000000000ull);"
        " case 4: return bitsd(0x7ff8000000000000ull); case 5: return bitsd(0x7ff0000000000001ull);"
        " default: return (double)(int64_t)v / 1e12; } }",
        "static float pickfv(void) { uint32_t v = (uint32_t)(next() >> 16); switch (v % 8u) {"
        " case 0: return 0.0f; case 1: return -(float)0.0f;"
        " case 2: return bitsf(0x7f800000u); case 3: return bitsf(0xff800000u);"
        " case 4: return bitsf(0x7fc00000u); case 5: return bitsf(0x7f800001u);"
        " default: return (float)(int32_t)v / 1e6f; } }",
        "static float vsrc[4];",
        *conversion_pickers(),
        "static unsigned char reg[8192];",
        "static void reset(void) { memset(reg, 0, sizeof reg); *(uint64_t *)(reg + %d) = (uint64_t)(stack + sizeof stack - 64); }"
        % REG["rsp"],
        "int main(void) { int bad = 0; setvbuf(stdout, NULL, _IONBF, 0);",
    ]
    for name, (args, ret) in FUNCTIONS.items():
        sub = f"sub_{syms[name][0]:x}"
        lines.append(f'printf("run {name}\\n");')
        lines.append("for (int i = 0; i < 2000; i++) {")
        decl, call, setup = [], [], []
        int_arg, sse_arg = 0, 0
        for idx, kind in enumerate(args):
            if kind == "u":
                decl.append(f"uint64_t a{idx} = pick();")
                setup.append(f"*(uint64_t *)(reg + {REG[INT_ARGS[int_arg]]}) = a{idx};")
                int_arg += 1
                call.append(f"(a{idx})")
            elif kind == "p":
                decl.append("for (int l = 0; l < 4; l++) vsrc[l] = pickfv();")
                setup.append(f"*(uint64_t *)(reg + {REG[INT_ARGS[int_arg]]}) = (uint64_t)(uintptr_t)vsrc;")
                int_arg += 1
                call.append("vsrc")
            elif kind in VEC_LANES:
                ty, n = VEC_LANES[kind]
                pick = "pickdv" if kind == "v" else "pickfv"
                if name == "f_movmskps":
                    lanes = ", ".join(
                        f"bitsf(i < 48 ? ((uint32_t)((i >> {lane}) & 1) << 31) |"
                        " (i < 16 ? 0u : (i < 32 ? 0x7fc01234u : 0x7f800001u)) : (uint32_t)next())"
                        for lane in range(n)
                    )
                elif kind == "w":
                    lanes = ", ".join("(uint16_t)(next() | 1u)" for _ in range(n))
                else:
                    lanes = ", ".join(f"{pick}()" for _ in range(n))
                decl.append(f"{ty} t{idx}[{n}] = {{ {lanes} }};")
                decl.append(
                    f"__attribute__((vector_size(16))) {ty} a{idx} = {{ {', '.join(f't{idx}[{l}]' for l in range(n))} }};"
                )
                setup.append(f"memcpy(reg + {REG[['xmm0', 'xmm1'][sse_arg]]}, &a{idx}, 16);")
                sse_arg += 1
                call.append(f"a{idx}")
            else:
                ty, size = ("double", 8) if kind == "d" else ("float", 4)
                pick = f"pick_{name}" if name in CONVERSIONS else "pickd"
                decl.append(f"{ty} a{idx} = {pick}();")
                setup.append(f"memcpy(reg + {REG[['xmm0', 'xmm1'][sse_arg]]}, &a{idx}, {size});")
                sse_arg += 1
                call.append(f"a{idx}")
        lines += decl + ["reset();"] + setup + [f"{sub}(reg);"]
        if ret in VEC_LANES:
            ty, n = VEC_LANES[ret]
            lines.append(f"{ty} got[{n}]; memcpy(got, reg + {REG['xmm0']}, 16);")
            lines.append(
                f"{ty} native[{n}]; {ty} __attribute__((vector_size(16))) r = {name}({', '.join(call)}); memcpy(native, &r, 16);"
            )
            lines.append("int diff = 0;")
            either_nan = "" if name in STRICT_LANES or ret == "w" else " && !(got[l] != got[l] && native[l] != native[l])"
            lines.append(f"for (int l = 0; l < {n}; l++) if (memcmp(&got[l], &native[l], sizeof ({ty})){either_nan}) diff = 1;")
            cond = "if (diff)"
        elif ret == "d":
            lines.append(f"double got; memcpy(&got, reg + {REG['xmm0']}, 8); double want = {name}({', '.join(call)});")
            cond = "if (memcmp(&got, &want, 8) != 0 && !(got != got && want != want))"
        else:
            oracle = CONVERSIONS[name][0] if name in CONVERSIONS else name
            lines.append(
                f"uint64_t got = *(uint64_t *)(reg + {REG['rax']}) & {RET_MASK[ret]}; uint64_t want = (uint64_t){oracle}({', '.join(call)}) & {RET_MASK[ret]};"
            )
            cond = "if (got != want)"
        lines.append(cond)
        lines.append(f'{{ bad++; printf("{name} mismatch %d\\n", i); break; }}')
        lines.append("}")
    lines += ['printf("bad=%d\\n", bad); return bad != 0; }']
    return "\n".join(lines)


def test_lifted_arm64_matches_native_arm64(tmp_path):
    syms, bodies, sections, images = lift_x86_symbols(tmp_path)
    lifted = [pl.lift_body(b, sections) for b in bodies]
    for result, body in zip(lifted, bodies):
        assert result.holes == [], (hex(body["start"]), result.holes)
    ir = tmp_path / "lifted.ll"
    ir.write_text(pl.module_for(lifted, images))
    obj = tmp_path / "lifted.o"
    run([LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", obj, ir])
    harness = tmp_path / "harness.c"
    harness.write_text(harness_source(syms))
    exe = tmp_path / "harness"
    run([LLVM / "clang", "-O1", "-arch", "arm64", "-ffp-contract=off", harness, obj, "-o", exe, "-lm"])
    assert "bad=0" in run([exe], timeout=120)


def test_movmskps_reference_matches_x86_instruction(tmp_path):
    source = tmp_path / "movmskps-x86.c"
    source.write_text(
        "#include <stdio.h>\n#include <string.h>\n"
        + SOURCE.read_text()
        + """
int main(void) {
    uint32_t state = 0x12345678u;
    for (unsigned i = 0; i < 2000; i++) {
        uint32_t lanes[4], want = 0;
        for (unsigned j = 0; j < 4; j++) {
            state = state * 1664525u + 1013904223u;
            lanes[j] = i < 48 ? (((i >> j) & 1u) << 31) |
                (i < 16 ? 0u : (i < 32 ? 0x7fc01234u : 0x7f800001u)) : state;
            want |= (lanes[j] >> 31) << j;
        }
        __attribute__((vector_size(16))) float a;
        memcpy(&a, lanes, 16);
        if (f_movmskps(a) != want) return 1;
    }
    puts("ok 2000"); return 0;
}
"""
    )
    exe = tmp_path / "movmskps-x86"
    run([LLVM / "clang", "-O1", "-arch", "x86_64", source, "-o", exe])
    assert "ok 2000" in run(["arch", "-x86_64", exe])


def test_pshuflw_reference_matches_x86_instruction(tmp_path):
    source = tmp_path / "pshuflw-x86.c"
    source.write_text(
        "#include <stdio.h>\n#include <string.h>\n"
        + SOURCE.read_text()
        + """
int main(void) {
    uint32_t state = 0x12345678u;
    for (unsigned i = 0; i < 2000; i++) {
        uint16_t lanes[8], want[8], got[8];
        for (unsigned j = 0; j < 8; j++) {
            state = state * 1664525u + 1013904223u;
            lanes[j] = (uint16_t)(state | 1u);
            want[j] = lanes[j];
        }
        for (unsigned j = 0; j < 4; j++) want[j] = lanes[(0xe0 >> (2 * j)) & 3];
        __attribute__((vector_size(16))) uint16_t a;
        memcpy(&a, lanes, 16);
        a = f_pshuflw(a);
        memcpy(got, &a, 16);
        if (memcmp(got, want, 16)) return 1;
    }
    puts("ok 2000"); return 0;
}
"""
    )
    exe = tmp_path / "pshuflw-x86"
    run([LLVM / "clang", "-O1", "-arch", "x86_64", source, "-o", exe])
    assert "ok 2000" in run(["arch", "-x86_64", exe])


def test_best_opt_pipeline_preserves_lifted_arm64_semantics(tmp_path):
    """Run the winning pipeline through the unchanged native-arm64 oracle."""
    syms, bodies, sections, images = lift_x86_symbols(tmp_path)
    lifted = [pl.lift_body(b, sections) for b in bodies]
    for result, body in zip(lifted, bodies):
        assert result.holes == [], (hex(body["start"]), result.holes)
    ir = tmp_path / "lifted.ll"
    ir.write_text(pl.module_for(lifted, images))

    optimised = tmp_path / "lifted.opt.ll"
    assert lp.verify_body(ir.read_text(), 120) == (True, None)
    accepted, payload, error = lp.optimise_body(ir.read_text(), "default<O2>", 120)
    assert accepted and payload is not None, error
    optimised.write_bytes(payload)
    text = optimised.read_text()
    assert lp.verify_body(text, 120) == (True, None)
    assert text != ir.read_text(), "the pipeline must actually rewrite the IR"
    assert text.lstrip().startswith(("; ModuleID", "target triple", "define")), "opt must emit readable IR"

    obj = tmp_path / "lifted.opt.o"
    run([LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", obj, optimised])
    assert obj.stat().st_size > 0
    defined = {line.split()[-1] for line in run([LLVM / "llvm-nm", "--defined-only", obj]).splitlines()}
    assert {f"_sub_{syms[name][0]:x}" for name in FUNCTIONS} <= defined, "the pipeline must not drop a lifted function"

    plain = tmp_path / "lifted.plain.o"
    run([LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", plain, ir])
    assert obj.stat().st_size < plain.stat().st_size, "default<O2> should shrink the object"

    harness = tmp_path / "harness.c"
    harness.write_text(harness_source(syms))
    exe = tmp_path / "harness"
    run([LLVM / "clang", "-O1", "-arch", "arm64", "-ffp-contract=off", harness, obj, "-o", exe, "-lm"])
    assert "bad=0" in run([exe], timeout=120)
