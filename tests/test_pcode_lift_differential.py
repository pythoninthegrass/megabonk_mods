"""Differential check of the pcode emitter: lifted arm64 must match native arm64.

Freestanding C is compiled to an x86-64 ELF, lifted through Ghidra pcode and the emitter,
rebuilt for arm64, and run against the same C compiled natively for arm64 on pseudo-random
inputs. Skipped unless the LLVM toolchain, Ghidra and an arm64 macOS host are present.
"""

import json
import os
import pytest
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pcode_lift as pl

LLVM = Path("/opt/homebrew/opt/llvm/bin")
GHIDRA = next(iter(sorted(Path("/opt/homebrew/Cellar/ghidra").glob("*/libexec/support/analyzeHeadless"))), None)
SOURCE = Path(__file__).parent / "fixtures/lift/diff.c"
LIFT_DUMP = Path(__file__).resolve().parent.parent / "scripts/lift_probe"
JAVA = Path.home() / ".local/bin/mise"

pytestmark = pytest.mark.skipif(
    not (LLVM / "clang").exists() or GHIDRA is None or sys.platform != "darwin" or os.uname().machine != "arm64",
    reason="needs the LLVM toolchain, Ghidra and an arm64 macOS host",
)

# name -> (argument kinds, return kind)
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
}
RET_MASK = {"u64": "0xffffffffffffffffull", "u32": "0xffffffffull", "i32": "0xffffffffull", "u8": "0xffull"}
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
        for idx, kind in enumerate(args):
            if kind == "u":
                decl.append(f"uint64_t a{idx} = pick();")
                setup.append(f"*(uint64_t *)(reg + {REG[INT_ARGS[idx]]}) = a{idx};")
                call.append(f"(a{idx})")
            else:
                reg_name = ["xmm0", "xmm1"][idx]
                decl.append(f"double a{idx} = pickd();")
                setup.append(f"memcpy(reg + {REG[reg_name]}, &a{idx}, 8);")
                call.append(f"a{idx}")
        lines += decl + ["reset();"] + setup + [f"{sub}(reg);"]
        if ret == "d":
            lines.append(f"double got; memcpy(&got, reg + {REG['xmm0']}, 8); double want = {name}({', '.join(call)});")
            lines.append("if (memcmp(&got, &want, 8) != 0 && !(got != got && want != want))")
        else:
            lines.append(
                f"uint64_t got = *(uint64_t *)(reg + {REG['rax']}) & {RET_MASK[ret]}; uint64_t want = (uint64_t){name}({', '.join(call)}) & {RET_MASK[ret]};"
            )
            lines.append("if (got != want)")
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
