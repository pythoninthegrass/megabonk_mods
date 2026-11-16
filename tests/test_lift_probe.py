"""Tests for the liftability spike driver.

The driver draws a size-stratified sample of function bodies from the shipped Linux
GameAssembly.so and scores each lift stage per body. The sampler, the scorer and the
accounting for bodies the pipeline could not score are pure logic, so they are testable
without a disassembler or a game process.
"""

import json
import os
import pytest
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

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


def row(start, size, **kw):
    base = {
        "start": start,
        "size": size,
        "holes": [],
        "unmapped_refs": 0,
        "indirect_calls": 0,
        "tail_calls": 0,
        "jump_tables": 0,
        "obj_bytes": 512,
        "error": None,
        "stages": {"decoded": True, "clean": True, "verify": True, "arm64": True},
    }
    base.update(kw)
    return base


def test_reconcile_keeps_sample_order_and_pairs_each_body_with_its_row():
    fdes = [lp.Fde(0x1000, 10), lp.Fde(0x2000, 100), lp.Fde(0x3000, 900)]
    rows = [row(0x3000, 900), row(0x1000, 10), row(0x2000, 100)]
    aligned, extras = lp.reconcile(fdes, rows)
    assert [r["start"] for r in aligned] == [0x1000, 0x2000, 0x3000]
    assert [r["size"] for r in aligned] == [10, 100, 900]
    assert extras == []


def test_reconcile_records_a_body_the_dump_never_emitted():
    fdes = [lp.Fde(0x1000, 10), lp.Fde(0x2000, 100), lp.Fde(0x3000, 900)]
    aligned, extras = lp.reconcile(fdes, [row(0x1000, 10), row(0x3000, 900)])
    dropped = aligned[1]
    assert dropped["start"] == 0x2000 and dropped["size"] == 100
    assert dropped["error"] == lp.MISSING_DUMP
    assert dropped["missing_dump"] is True
    assert dropped["stages"] == {"decoded": False, "clean": False, "verify": False, "arm64": False}
    assert dropped["holes"] == [] and dropped["obj_bytes"] == 0
    assert extras == []


def test_reconcile_hands_back_rows_that_match_no_sampled_body():
    fdes = [lp.Fde(0x1000, 10)]
    aligned, extras = lp.reconcile(fdes, [row(0x1000, 10), row(0x1000, 10), row(0x9000, 40)])
    assert len(aligned) == 1 and aligned[0]["start"] == 0x1000
    assert [(r["start"], r["size"]) for r in extras] == [(0x1000, 10), (0x9000, 40)]


def test_summarize_counts_an_unscored_body_in_its_class_and_the_totals():
    results = [row(0x1000, 10), lp.failed_row(0x2000, 900, "llc timed out after 120s", missing_dump=False)]
    summary = lp.summarize(results)
    assert summary["tiny"] == {"n": 1, "decoded": 1, "clean": 1, "verify": 1, "arm64": 1}
    assert summary["large"] == {"n": 1, "decoded": 0, "clean": 0, "verify": 0, "arm64": 0}
    assert summary["all"] == {"n": 2, "decoded": 1, "clean": 1, "verify": 1, "arm64": 1}


def test_tally_failures_groups_unscored_bodies_by_cause():
    results = [
        row(0x1000, 10),
        lp.failed_row(0x2000, 10, "llc timed out after 120s"),
        lp.failed_row(0x3000, 900, "llc timed out after 120s"),
        lp.failed_row(0x4000, 900, lp.MISSING_DUMP, missing_dump=True),
    ]
    assert lp.tally_failures(results) == {"llc timed out after 120s": 2, lp.MISSING_DUMP: 1}


def test_failure_rows_name_each_body_by_address_and_size():
    results = [row(0x1000, 10), lp.failed_row(0x4DD8A20, 312, "opt was killed by signal 6")]
    assert lp.failure_rows(results) == [
        {"start": 0x4DD8A20, "hex": "0x4dd8a20", "size": 312, "class": "small", "error": "opt was killed by signal 6"}
    ]


def healthy_lifted(*_args, **_kw):
    return SimpleNamespace(holes=[], unmapped_refs=0, indirect_calls=0, tail_calls=0)


def body_fn(start=0x4DD8A20, size=312):
    return {"start": start, "size": size, "undecoded": 0, "insns": [], "jt": []}


def test_score_body_records_a_lift_crash_against_the_body(monkeypatch):
    def raise_(fn, sections):
        raise ValueError("bad pcode")

    monkeypatch.setattr(lp.pcode_lift, "lift_body", raise_)
    scored = lp.score_body(body_fn(), [])
    assert scored["start"] == 0x4DD8A20 and scored["size"] == 312
    assert scored["error"] == "lift raised ValueError: bad pcode"
    assert scored["stages"] == {"decoded": False, "clean": False, "verify": False, "arm64": False}


def test_score_body_records_a_tool_timeout(monkeypatch):
    monkeypatch.setattr(lp.pcode_lift, "lift_body", healthy_lifted)
    monkeypatch.setattr(lp.pcode_lift, "module_for", lambda bodies: "define void @f() { ret void }")

    def run(cmd, **kw):
        if Path(cmd[0]).name == "opt":
            raise subprocess.TimeoutExpired(cmd, 1)
        return subprocess.CompletedProcess(cmd, 0, b"obj", b"")

    monkeypatch.setattr(lp, "run_tool", run)
    scored = lp.score_body(body_fn(), [], tool_timeout=7)
    assert scored["error"] == "opt timed out after 7s"
    assert scored["stages"] == {"decoded": True, "clean": True, "verify": False, "arm64": True}
    assert scored["obj_bytes"] == 3


def test_score_body_keeps_a_rejected_body_a_measurement_not_a_failure(monkeypatch):
    monkeypatch.setattr(lp.pcode_lift, "lift_body", healthy_lifted)
    monkeypatch.setattr(lp.pcode_lift, "module_for", lambda bodies: "define void @f() { ret void }")

    def run(cmd, **kw):
        code = 1 if Path(cmd[0]).name == "opt" else 0
        return subprocess.CompletedProcess(cmd, code, b"obj", b"")

    monkeypatch.setattr(lp, "run_tool", run)
    scored = lp.score_body(body_fn(), [])
    assert scored["error"] is None
    assert scored["stages"] == {"decoded": True, "clean": True, "verify": False, "arm64": True}


def test_score_body_records_a_tool_crash(monkeypatch):
    monkeypatch.setattr(lp.pcode_lift, "lift_body", healthy_lifted)
    monkeypatch.setattr(lp.pcode_lift, "module_for", lambda bodies: "define void @f() { ret void }")

    def run(cmd, **kw):
        code = 0 if Path(cmd[0]).name == "opt" else -6
        return subprocess.CompletedProcess(cmd, code, b"obj", b"")

    monkeypatch.setattr(lp, "run_tool", run)
    scored = lp.score_body(body_fn(), [])
    assert scored["error"] == "llc was killed by signal 6"
    assert scored["stages"] == {"decoded": True, "clean": True, "verify": True, "arm64": False}


def test_score_row_passes_an_already_failed_row_straight_through():
    dropped = lp.failed_row(0x1000, 10, lp.MISSING_DUMP, missing_dump=True)
    assert lp.score_row(dropped, [], 1) is dropped


def test_score_row_records_what_escapes_the_scorer(monkeypatch):
    def raise_(fn, sections, tool_timeout=1):
        raise KeyError("undecoded")

    monkeypatch.setattr(lp, "score_body", raise_)
    scored = lp.score_row({"start": 0x2000, "size": 40}, [], 1)
    assert scored["error"] == "scoring raised KeyError: 'undecoded'"
    assert scored["start"] == 0x2000 and scored["size"] == 40


READONLY_TABLE = "  [17] il2cpp            PROGBITS        0000000000000100 100 00001000 00  AX  0   0 16\n"
EH_THREE_CLASSES = """\
00000000 00000014 0000001c FDE cie=00000000 pc=00000100...0000010a
00000000 00000014 0000001c FDE cie=00000000 pc=00000200...00000264
00000000 00000014 0000001c FDE cie=00000000 pc=00000300...000006e8
"""


def drive_main(tmp_path, monkeypatch, dumped):
    so = tmp_path / "GameAssembly.so"
    so.write_bytes(b"\x7fELF")
    out = tmp_path / "out"

    def run(cmd, **kw):
        text = str(cmd[0])
        stdout = READONLY_TABLE if "llvm-readelf" in text else EH_THREE_CLASSES
        return subprocess.CompletedProcess(cmd, 0, stdout, b"")

    monkeypatch.setattr(lp, "run_tool", run)
    monkeypatch.setattr(lp, "dump_pcode", lambda so_, fdes, work, **kw: (dumped, []))
    monkeypatch.setattr(lp, "score_body", lambda r, sections, tool_timeout: row(r["start"], r["size"]))
    rc = lp.main([str(so), "--out", str(out), "--per-class", "1", "--seed", "5", "--r2-per-class", "0"])
    return rc, out, json.loads((out / "summary.json").read_text())


def test_main_scores_every_body_a_run_asks_for(tmp_path, monkeypatch):
    rc, out, summary = drive_main(tmp_path, monkeypatch, [row(0x100, 10), row(0x200, 100), row(0x300, 1000)])
    assert rc == 0
    assert summary["sample"] == {"per_class": 1, "seed": 5, "requested": 3, "n": 3}
    assert summary["stages"]["all"] == {"n": 3, "decoded": 3, "clean": 3, "verify": 3, "arm64": 3}
    assert summary["failures"] == {} and summary["failed_bodies"] == []
    assert len((out / "bodies.jsonl").read_text().splitlines()) == 3


def test_main_records_a_body_the_dump_dropped_and_reports_the_run_incomplete(tmp_path, monkeypatch, capsys):
    rc, out, summary = drive_main(tmp_path, monkeypatch, [row(0x100, 10), row(0x300, 1000)])
    assert rc == 1
    assert summary["sample"] == {"per_class": 1, "seed": 5, "requested": 3, "n": 3}
    assert summary["stages"]["small"] == {"n": 1, "decoded": 0, "clean": 0, "verify": 0, "arm64": 0}
    assert summary["failures"] == {lp.MISSING_DUMP: 1}
    assert summary["failed_bodies"] == [
        {"start": 0x200, "hex": "0x200", "size": 100, "class": "small", "error": lp.MISSING_DUMP}
    ]
    assert len((out / "bodies.jsonl").read_text().splitlines()) == 3
    assert "0x200" in capsys.readouterr().err


def test_main_reports_rows_that_match_no_sampled_body(tmp_path, monkeypatch, capsys):
    rc, _, summary = drive_main(tmp_path, monkeypatch, [row(0x100, 10), row(0x200, 100), row(0x300, 1000), row(0x900, 20)])
    assert rc == 0
    assert summary["unsampled_rows"] == ["0x900"]
    assert "0x900" in capsys.readouterr().err


def pcode_fn(start=0x2162990):
    """A two-instruction body in the shape the Ghidra dump emits: set a register, return."""
    return {
        "start": start,
        "size": 2,
        "insns": [
            {"a": start, "len": 1, "m": "mov", "ops": [{"op": "COPY", "out": "register,0,4", "in": ["const,0x1,8"]}]},
            {"a": start + 1, "len": 1, "m": "ret", "ops": [{"op": "RETURN", "out": None, "in": []}]},
        ],
        "undecoded": 0,
        "jt": [],
    }


SECTIONS = [{"address": 0, "size": 0x100000000, "offset": 0, "name": ".text"}]


def fake_ghidra(tmp_path, body):
    script = tmp_path / "ghidraRun"
    script.write_text(f"#!/bin/sh\n{body}")
    script.chmod(0o755)
    return script


def test_dump_pcode_keeps_partial_rows_when_ghidra_times_out(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    diag = tmp_path / "out"
    script = fake_ghidra(
        tmp_path,
        'printf \'{"start": 56088976, "size": 8, "basicBlocks": [], "undecoded": 0, "jt": []}\\n\' > "${11}"\n'
        'echo \'[{"address": 0, "size": 1, "offset": 0, "name": ".text"}]\' > "${12}"\n'
        'echo "analysis pass 3 of 40" >&2\n'
        "sleep 2\n",
    )
    monkeypatch.setattr(lp, "find_ghidra", lambda: str(script))
    killed = []
    monkeypatch.setattr(os, "kill", lambda pid, sig, *args: killed.append((pid, sig)))
    fdes = [lp.Fde(0x357D990, 8), lp.Fde(0x357D9A0, 20)]

    rows, sections = lp.dump_pcode(Path("GameAssembly.so"), fdes, work, timeout=1, diag=diag)

    assert [row["start"] for row in rows] == [0x357D990]
    assert sections[0]["name"] == ".text"
    assert killed, "the timed-out Ghidra process should have been signalled"
    log = (diag / "ghidra-stdout.txt").read_text()
    assert log.startswith("Ghidra timed out after 1s")
    assert "analysis pass 3 of 40" in log


def test_dump_pcode_keeps_rows_when_ghidra_exits_nonzero(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    diag = tmp_path / "out"
    script = fake_ghidra(
        tmp_path,
        'printf \'{"start": 56088976, "size": 8, "basicBlocks": [], "undecoded": 0, "jt": []}\\n\' > "${11}"\n'
        'echo \'[{"address": 0, "size": 1, "offset": 0, "name": ".text"}]\' > "${12}"\n'
        "exit 3\n",
    )
    monkeypatch.setattr(lp, "find_ghidra", lambda: str(script))

    rows, _ = lp.dump_pcode(Path("GameAssembly.so"), [lp.Fde(0x357D990, 8)], work, timeout=60, diag=diag)

    assert [row["start"] for row in rows] == [0x357D990]
    assert (diag / "ghidra-stdout.txt").read_text().startswith("Ghidra exited 3")


def test_dump_pcode_names_the_log_when_ghidra_produced_nothing(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    diag = tmp_path / "out"
    script = fake_ghidra(tmp_path, 'echo "OutOfMemoryError: Java heap space" >&2\nexit 1\n')
    monkeypatch.setattr(lp, "find_ghidra", lambda: str(script))

    with pytest.raises(SystemExit) as caught:
        lp.dump_pcode(Path("GameAssembly.so"), [lp.Fde(0x357D990, 8)], work, timeout=60, diag=diag)
    assert "Ghidra produced no pcode" in str(caught.value)
    assert "OutOfMemoryError" in str(caught.value)
    assert "OutOfMemoryError" in (diag / "ghidra-stdout.txt").read_text()


def test_dump_pcode_names_a_run_that_left_pcode_but_no_section_table(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    script = fake_ghidra(
        tmp_path,
        'printf \'{"start": 56088976, "size": 8, "basicBlocks": [], "undecoded": 0, "jt": []}\\n\' > "${11}"\n'
        "exit 0\n",
    )
    monkeypatch.setattr(lp, "find_ghidra", lambda: str(script))

    with pytest.raises(SystemExit) as caught:
        lp.dump_pcode(Path("GameAssembly.so"), [lp.Fde(0x357D990, 8)], work, timeout=60, diag=tmp_path / "out")
    assert "no section table" in str(caught.value)


def test_score_body_adds_the_extra_llvm_arguments(monkeypatch):
    seen = []

    def fake_run(cmd, **kw):
        seen.append([str(c) for c in cmd])
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    monkeypatch.setattr(lp, "run_tool", fake_run)
    monkeypatch.setattr(lp, "EXTRA_ARGS", ["--mcpu=neoverse-n1", "--unroll-count=1"])

    scored = lp.score_body(pcode_fn(), SECTIONS, 5)

    tools = [cmd for cmd in seen if cmd[0].endswith(("opt", "llc"))]
    assert len(tools) == 2
    for cmd in tools:
        assert "--mcpu=neoverse-n1" in cmd and "--unroll-count=1" in cmd
    assert scored["stages"]["arm64"] is True


def test_main_splits_extra_into_the_llvm_arguments(tmp_path, monkeypatch):
    so = tmp_path / "GameAssembly.so"
    so.write_bytes(b"\x7fELF")
    out = tmp_path / "out"
    captured = {}

    def run(cmd, **kw):
        text = str(cmd[0])
        stdout = READONLY_TABLE if "llvm-readelf" in text else EH_THREE_CLASSES
        return subprocess.CompletedProcess(cmd, 0, stdout, b"")

    def fake_dump(so_, fdes, work, **kw):
        captured["extra"] = list(lp.EXTRA_ARGS)
        return [row(0x100, 10), row(0x200, 100), row(0x300, 1000)], []

    monkeypatch.setattr(lp, "run_tool", run)
    monkeypatch.setattr(lp, "dump_pcode", fake_dump)
    monkeypatch.setattr(lp, "score_body", lambda r, sections, tool_timeout: row(r["start"], r["size"]))
    monkeypatch.setattr(lp, "EXTRA_ARGS", ["--stale-from-a-previous-run"])

    rc = lp.main(
        [
            str(so),
            "--out",
            str(out),
            "--per-class",
            "1",
            "--seed",
            "5",
            "--r2-per-class",
            "0",
            "--extra",
            "--mcpu=neoverse-n1 --unroll-count=1",
        ]
    )

    assert rc == 0
    assert captured["extra"] == ["--mcpu=neoverse-n1", "--unroll-count=1"]


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
