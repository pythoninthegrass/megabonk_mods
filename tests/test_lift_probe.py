"""Tests for the liftability spike driver.

The driver draws a size-stratified sample of function bodies from the shipped Linux
GameAssembly.so and scores each lift stage per body. The sampler and the scorer are pure
logic, so they are testable without a disassembler or a game process.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import lift_probe as lp

EH_FRAME_TEXT = """\
.eh_frame contents:

00000000 00000014 00000000 CIE
  Format:                DWARF32

00000018 00000014 0000001c FDE cie=00000000 pc=02162990...02162997
  DW_CFA_nop:

00000030 0000002c 00000034 FDE cie=00000000 pc=021629a0...02162a14
  DW_CFA_advance_loc: 1

00000060 00000024 00000064 FDE cie=00000000 pc=02162a20...02162a4b
"""


def test_parse_fdes_reads_start_and_size():
    fdes = lp.parse_fdes(EH_FRAME_TEXT)
    assert fdes == [
        lp.Fde(0x2162990, 7),
        lp.Fde(0x21629A0, 0x74),
        lp.Fde(0x2162A20, 0x2B),
    ]


def test_parse_fdes_ignores_cie_and_other_lines():
    assert lp.parse_fdes("00000000 00000014 00000000 CIE\nrandom\n") == []


def test_size_class_boundaries():
    assert lp.size_class(1) == "tiny"
    assert lp.size_class(63) == "tiny"
    assert lp.size_class(64) == "small"
    assert lp.size_class(512) == "small"
    assert lp.size_class(513) == "large"


def make_fdes(count, size):
    return [lp.Fde(0x1000 + i * 0x1000, size) for i in range(count)]


def test_sample_takes_requested_count_per_class():
    fdes = make_fdes(50, 10) + make_fdes(50, 100) + make_fdes(50, 1000)
    picked = lp.stratified_sample(fdes, per_class=5, seed=1)
    counts = {}
    for fde in picked:
        counts[lp.size_class(fde.size)] = counts.get(lp.size_class(fde.size), 0) + 1
    assert counts == {"tiny": 5, "small": 5, "large": 5}


def test_sample_is_deterministic_for_a_seed():
    fdes = make_fdes(200, 10) + make_fdes(200, 600)
    assert lp.stratified_sample(fdes, 8, seed=7) == lp.stratified_sample(fdes, 8, seed=7)
    assert lp.stratified_sample(fdes, 8, seed=7) != lp.stratified_sample(fdes, 8, seed=8)


def test_sample_takes_everything_when_a_class_is_short():
    fdes = make_fdes(3, 10)
    assert len(lp.stratified_sample(fdes, per_class=10, seed=1)) == 3


def test_sample_respects_address_window():
    fdes = [lp.Fde(0x100, 10), lp.Fde(0x5000, 10), lp.Fde(0x9000, 10)]
    picked = lp.stratified_sample(fdes, 10, seed=1, lo=0x4000, hi=0x6000)
    assert picked == [lp.Fde(0x5000, 10)]


def test_summarize_counts_passes_per_stage_and_class():
    results = [
        {"size": 10, "stages": {"disasm": True, "cfg": True, "ir": False}},
        {"size": 20, "stages": {"disasm": True, "cfg": False, "ir": False}},
        {"size": 900, "stages": {"disasm": True, "cfg": False, "ir": False}},
    ]
    summary = lp.summarize(results)
    assert summary["tiny"] == {"n": 2, "disasm": 2, "cfg": 1, "ir": 0}
    assert summary["large"] == {"n": 1, "disasm": 1, "cfg": 0, "ir": 0}
    assert summary["all"] == {"n": 3, "disasm": 3, "cfg": 1, "ir": 0}


def test_tally_holes_counts_each_kind_once_per_body():
    results = [
        {"holes": ["BRANCHIND", "BRANCHIND"]},
        {"holes": ["BRANCHIND", "CALLOTHER:divps"]},
        {"holes": []},
    ]
    assert lp.tally_holes(results) == {"BRANCHIND": 2, "CALLOTHER:divps": 1}


def test_parse_exec_sections_reads_llvm_readelf_table():
    text = (
        "  [16] .text             PROGBITS        0000000001d35040 1d35040 42d941 00  AX  0   0 16\n"
        "  [17] il2cpp            PROGBITS        0000000002162990 2162990 2cc3ab0 00  AX  0   0 16\n"
        "  [11] .rodata           PROGBITS        0000000000b30a80 b30a80 4898f8 00   A  0   0 32\n"
    )
    assert lp.parse_exec_sections(text) == {
        ".text": (0x1D35040, 0x1D35040 + 0x42D941),
        "il2cpp": (0x2162990, 0x2162990 + 0x2CC3AB0),
    }
