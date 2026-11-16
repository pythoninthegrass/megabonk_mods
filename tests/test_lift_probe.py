"""Tests for the liftability spike driver.

The driver draws a size-stratified sample of function bodies from the shipped Linux
GameAssembly.so and scores each lift stage per body. The sampler, the scorer and the
accounting for bodies the pipeline could not score are pure logic, so they are testable
without a disassembler or a game process.
"""

import json
import lift_probe as lp
import os
import pytest
import subprocess
from pathlib import Path
from types import SimpleNamespace

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
        "stages": {
            "decoded": True,
            "clean": True,
            "verify": True,
            "pipeline": False,
            "arm64": True,
            "arm64_pipeline": False,
        },
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
    assert dropped["stages"] == {
        "decoded": False,
        "clean": False,
        "verify": False,
        "pipeline": False,
        "arm64": False,
        "arm64_pipeline": False,
    }
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
    assert summary["tiny"] == {"n": 1, "decoded": 1, "clean": 1, "verify": 1, "pipeline": 0, "arm64": 1, "arm64_pipeline": 0}
    assert summary["large"] == {"n": 1, "decoded": 0, "clean": 0, "verify": 0, "pipeline": 0, "arm64": 0, "arm64_pipeline": 0}
    assert summary["all"] == {"n": 2, "decoded": 1, "clean": 1, "verify": 1, "pipeline": 0, "arm64": 1, "arm64_pipeline": 0}


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
    assert scored["stages"] == {
        "decoded": False,
        "clean": False,
        "verify": False,
        "pipeline": False,
        "arm64": False,
        "arm64_pipeline": False,
    }


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
    assert scored["stages"] == {
        "decoded": True,
        "clean": True,
        "verify": False,
        "pipeline": False,
        "arm64": True,
        "arm64_pipeline": False,
    }
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
    assert scored["stages"] == {
        "decoded": True,
        "clean": True,
        "verify": False,
        "pipeline": False,
        "arm64": True,
        "arm64_pipeline": False,
    }


def test_score_body_records_a_tool_crash(monkeypatch):
    monkeypatch.setattr(lp.pcode_lift, "lift_body", healthy_lifted)
    monkeypatch.setattr(lp.pcode_lift, "module_for", lambda bodies: "define void @f() { ret void }")

    def run(cmd, **kw):
        code = 0 if Path(cmd[0]).name == "opt" else -6
        return subprocess.CompletedProcess(cmd, code, b"obj", b"")

    monkeypatch.setattr(lp, "run_tool", run)
    scored = lp.score_body(body_fn(), [])
    assert scored["error"] == "llc was killed by signal 6"
    assert scored["stages"] == {
        "decoded": True,
        "clean": True,
        "verify": True,
        "pipeline": False,
        "arm64": False,
        "arm64_pipeline": False,
    }


def test_score_row_passes_an_already_failed_row_straight_through():
    dropped = lp.failed_row(0x1000, 10, lp.MISSING_DUMP, missing_dump=True)
    assert lp.score_row(dropped, [], 1) is dropped


def test_score_row_records_what_escapes_the_scorer(monkeypatch):
    def raise_(fn, sections, tool_timeout=1, pipeline=""):
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
    monkeypatch.setattr(lp, "score_body", lambda r, sections, tool_timeout, pipeline="": row(r["start"], r["size"]))
    rc = lp.main([str(so), "--out", str(out), "--per-class", "1", "--seed", "5", "--r2-per-class", "0"])
    return rc, out, json.loads((out / "summary.json").read_text())


def test_main_scores_every_body_a_run_asks_for(tmp_path, monkeypatch):
    rc, out, summary = drive_main(tmp_path, monkeypatch, [row(0x100, 10), row(0x200, 100), row(0x300, 1000)])
    assert rc == 0
    assert summary["sample"] == {"per_class": 1, "seed": 5, "requested": 3, "n": 3}
    assert summary["stages"]["all"] == {
        "n": 3,
        "decoded": 3,
        "clean": 3,
        "verify": 3,
        "pipeline": 0,
        "arm64": 3,
        "arm64_pipeline": 0,
    }
    assert summary["failures"] == {} and summary["failed_bodies"] == []
    assert len((out / "bodies.jsonl").read_text().splitlines()) == 3


def test_main_records_a_body_the_dump_dropped_and_reports_the_run_incomplete(tmp_path, monkeypatch, capsys):
    rc, out, summary = drive_main(tmp_path, monkeypatch, [row(0x100, 10), row(0x300, 1000)])
    assert rc == 1
    assert summary["sample"] == {"per_class": 1, "seed": 5, "requested": 3, "n": 3}
    assert summary["stages"]["small"] == {
        "n": 1,
        "decoded": 0,
        "clean": 0,
        "verify": 0,
        "pipeline": 0,
        "arm64": 0,
        "arm64_pipeline": 0,
    }
    assert summary["failures"] == {lp.MISSING_DUMP: 1}
    assert summary["failed_bodies"] == [{"start": 0x200, "hex": "0x200", "size": 100, "class": "small", "error": lp.MISSING_DUMP}]
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
        'printf \'{"start": 56088976, "size": 8, "basicBlocks": [], "undecoded": 0, "jt": []}\\n\' > "${11}"\nexit 0\n',
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


PIPELINE_IR = "define void @f(ptr %p) {\n  ret void\n}\n"
OPTIMISED_IR = "define void @f(ptr nofree %p) {\n  ret void\n}\n"


def llvm_fakes(monkeypatch, pipeline_output=None):
    """Capture LLVM commands and their input IR while faking output."""
    seen: list[list[str]] = []
    fed: list[str] = []

    def fake_run(cmd, **kw):
        cmd = [str(c) for c in cmd]
        name = Path(cmd[0]).name
        if name in ("opt", "llc"):
            seen.append(cmd)
            fed.append((kw.get("input") or b"").decode())
            stdout = b"obj"
            if name == "opt" and any(c.startswith("-passes=") and c != "-passes=verify" for c in cmd):
                stdout = (pipeline_output or PIPELINE_IR).encode()
            return subprocess.CompletedProcess(cmd, 0, stdout, b"")
        text = " ".join(cmd)
        stdout = READONLY_TABLE if "llvm-readelf" in text else EH_THREE_CLASSES
        return subprocess.CompletedProcess(cmd, 0, stdout, b"")

    monkeypatch.setattr(lp, "run_tool", fake_run)
    monkeypatch.setattr(lp.pcode_lift, "lift_body", healthy_lifted)
    monkeypatch.setattr(lp.pcode_lift, "module_for", lambda bodies: PIPELINE_IR)
    return seen, fed


def pipeline_tools(tmp_path, monkeypatch, argv_extra, pipeline_output=None):
    """Runs the driver over a single body with the tools faked, returning the opt and llc calls made."""
    so = tmp_path / "GameAssembly.so"
    so.write_bytes(b"\x7fELF")
    seen, _ = llvm_fakes(monkeypatch, pipeline_output)
    argv = [str(so), "--out", str(tmp_path / "out"), "--per-class", "1", "--seed", "5", "--r2-per-class", "0", "--jobs", "1"]
    body = {"start": 0x100, "size": 10, "undecoded": 0, "insns": [], "jt": []}
    monkeypatch.setattr(lp, "stratified_sample", lambda fdes, per_class, seed, *w: [lp.Fde(0x100, 10)])
    monkeypatch.setattr(
        lp, "dump_pcode", lambda so_, fdes, work, **kw: ([dict(body, start=fdes[0].start, size=fdes[0].size)], [])
    )
    monkeypatch.setattr(lp, "PCODE_CACHE", None)
    monkeypatch.setattr(lp, "EXTRA_ARGS", [])
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        lp.main(argv + argv_extra)
    return seen


def drive_pipeline_main(tmp_path, monkeypatch, argv_extra):
    so = tmp_path / "GameAssembly.so"
    so.write_bytes(b"\x7fELF")
    out = tmp_path / "out"

    def run(cmd, **kw):
        text = str(cmd[0])
        stdout = READONLY_TABLE if "llvm-readelf" in text else EH_THREE_CLASSES
        return subprocess.CompletedProcess(cmd, 0, stdout, b"")

    captured = {}

    def fake_dump(so_, fdes, work, **kw):
        captured["cache"] = getattr(lp, "PCODE_CACHE", None)
        return [row(0x100, 10), row(0x200, 100), row(0x300, 1000)], []

    def fake_dump_pcode_cached(so_, fdes, work, cache, **kw):
        captured["chunk"] = kw.get("chunk", "absent")
        captured["cache"] = getattr(lp, "PCODE_CACHE", None)
        return fake_dump(so_, fdes, work)

    monkeypatch.setattr(lp, "run_tool", run)
    monkeypatch.setattr(lp, "dump_pcode", fake_dump)
    monkeypatch.setattr(lp, "dump_pcode_cached", fake_dump_pcode_cached)
    monkeypatch.setattr(lp, "score_body", lambda r, sections, tool_timeout, pipeline="": row(r["start"], r["size"]))
    monkeypatch.setattr(lp, "EXTRA_ARGS", [])
    monkeypatch.setattr(lp, "PCODE_CACHE", None)
    argv = [str(so), "--out", str(out), "--per-class", "1", "--seed", "5", "--r2-per-class", "0", "--jobs", "1"]
    rc = lp.main(argv + argv_extra)
    return rc, captured, json.loads((out / "summary.json").read_text())


def _scored_tools(cmds: list[list[str]]) -> list[list[str]]:
    """The per-body scoring calls, dropping the run's ELF-reading tool calls."""
    return [cmd for cmd in cmds if "-mtriple=arm64-apple-macosx" in cmd or Path(cmd[0]).name == "opt"]


def test_pipeline_option_defaults_to_the_verify_only_behaviour(tmp_path, monkeypatch):
    scored = _scored_tools(pipeline_tools(tmp_path, monkeypatch, []))
    assert len(scored) == 2, scored
    assert [Path(cmd[0]).name for cmd in scored] == ["opt", "llc"]
    assert "-passes=verify" in scored[0] and "-disable-output" in scored[0]
    assert "-passes=default<O2>" not in scored[0]
    assert "-O2" in scored[1]


def test_pipeline_option_selects_the_opt_pipeline_before_llc(tmp_path, monkeypatch):
    scored = _scored_tools(pipeline_tools(tmp_path, monkeypatch, ["--pipeline", "default<O2>"]))
    assert len(scored) == 4, scored
    assert [Path(cmd[0]).name for cmd in scored] == ["opt", "opt", "opt", "llc"], scored
    optimise = scored[1]
    assert optimise[0].endswith("opt")
    assert "-passes=default<O2>" in optimise
    assert "-filetype=obj" not in optimise
    assert "-passes=verify" in scored[0] and "-passes=verify" in scored[2] and "-O2" in scored[3]


def test_verifier_still_runs_after_an_opt_pipeline(tmp_path, monkeypatch):
    seen, fed = llvm_fakes(monkeypatch, pipeline_output=OPTIMISED_IR)
    scored = lp.score_body(pcode_fn(), SECTIONS, 5, pipeline="default<O2>")
    opt_passes = [c for cmd in seen if Path(cmd[0]).name == "opt" for c in cmd if c.startswith("-passes=")]
    assert opt_passes == ["-passes=verify", "-passes=default<O2>", "-passes=verify"]
    assert fed[1] == PIPELINE_IR, "the pipeline is fed the emitter's IR"
    assert fed[2] == OPTIMISED_IR, "the verifier after the pipeline is fed the rewritten IR"
    assert fed[3] == OPTIMISED_IR, "llc is fed the rewritten IR"
    assert scored["stages"]["verify"] is True and scored["stages"]["arm64"] is True


def test_a_pipeline_that_breaks_a_body_is_recorded_with_its_address(tmp_path, monkeypatch):
    """The pipeline rewrites the IR and the verifier after it rejects the rewritten body."""
    seen = []

    def fake_run(cmd, **kw):
        cmd = [str(c) for c in cmd]
        seen.append(cmd)
        ir = (kw.get("input") or b"").decode()
        pipeline = "-passes=default<O2>" in cmd
        if pipeline:
            return subprocess.CompletedProcess(cmd, 0, OPTIMISED_IR.encode(), b"")
        rewritten = ir == OPTIMISED_IR
        code = 1 if rewritten and ("-passes=verify" in cmd or "-mtriple=arm64-apple-macosx" in cmd) else 0
        return subprocess.CompletedProcess(cmd, code, b"obj", b"")

    monkeypatch.setattr(lp, "run_tool", fake_run)
    monkeypatch.setattr(lp.pcode_lift, "lift_body", healthy_lifted)
    monkeypatch.setattr(lp.pcode_lift, "module_for", lambda bodies: PIPELINE_IR)
    scored = lp.score_body(pcode_fn(0x4DD8A20), SECTIONS, 5, pipeline="default<O2>")
    assert [Path(cmd[0]).name for cmd in seen] == ["opt", "opt", "opt"], seen
    assert scored["start"] == 0x4DD8A20
    assert scored["stages"] == {
        "decoded": True,
        "clean": True,
        "verify": False,
        "pipeline": True,
        "arm64": False,
        "arm64_pipeline": False,
    }
    assert scored["error"] is not None and scored["obj_bytes"] == 0
    assert sum("-mtriple=arm64-apple-macosx" in cmd for cmd in seen) == 0, "no llc run on IR that failed verify"
    assert sum("-passes=default<O2>" in cmd for cmd in seen) == 1


def test_summary_names_the_pipeline_that_measured_the_sample(tmp_path, monkeypatch):
    _, _, summary = drive_pipeline_main(tmp_path, monkeypatch, [])
    assert summary["pipeline"] == "none"
    _, _, summary = drive_pipeline_main(tmp_path, monkeypatch, ["--pipeline", "default<O2>"])
    assert summary["pipeline"] == "default<O2>"


def test_summary_times_the_scoring_stage(tmp_path, monkeypatch):
    _, _, summary = drive_pipeline_main(tmp_path, monkeypatch, [])
    assert summary["scoring_seconds"] >= 0
    assert isinstance(summary["scoring_seconds"], float)


def test_summary_records_raw_size_denominators_and_stage_timings(tmp_path, monkeypatch):
    _, _, summary = drive_pipeline_main(tmp_path, monkeypatch, [])
    assert summary["object_bytes"] == 3 * 512
    assert summary["x86_bytes"] == 1110
    assert summary["compiled_x86_bytes"] == 1110
    assert summary["pcode_seconds"] >= 0
    assert summary["wall_seconds"] >= summary["scoring_seconds"]


def test_pcode_cache_option_names_the_cache_file(tmp_path, monkeypatch):
    _, captured, _ = drive_pipeline_main(tmp_path, monkeypatch, [])
    assert captured["cache"].path is None
    path = tmp_path / "pcode.jsonl"
    _, captured, _ = drive_pipeline_main(tmp_path, monkeypatch, ["--pcode-cache", str(path)])
    assert captured["cache"].path == path


def _keyed(tmp_path, digest, records, fdes=None):
    """Write a cache file the way the tool writes one: a header, a section table, then bodies."""
    fdes = fdes or [lp.Fde(r["start"], r["size"]) for r in records if "start" in r]
    key = lp.cache_key(digest, fdes)
    lines = [json.dumps(lp.cache_header(key, digest, lp.dump_script_fingerprint(), lp.ghidra_version()))]
    lines.append(json.dumps(lp.section_record(digest, [{"name": ".text"}], key)))
    lines += [json.dumps({"cache": key, **r}) for r in records]
    path = tmp_path / "cache.jsonl"
    path.write_text("".join(line + "\n" for line in lines))
    return path, key


def _load(tmp_path, path, digest, key):
    return lp.PcodeCache.load(path, digest, key, lp.dump_script_fingerprint(), lp.ghidra_version())


def test_pcode_cache_reuses_only_records_matching_the_run(tmp_path):
    so = tmp_path / "GameAssembly.so"
    so.write_bytes(b"\x7fELF")
    digest = lp.sha256(so)
    fdes = [lp.Fde(0x100, 10), lp.Fde(0x200, 100)]
    key = lp.cache_key(digest, fdes)
    (tmp_path / "cache.jsonl").write_text(
        "\n".join(
            json.dumps(rec)
            for rec in (
                lp.cache_header(key, digest, lp.dump_script_fingerprint(), lp.ghidra_version()),
                lp.section_record(digest, [{"name": ".text"}], key),
                {"cache": key, "sha256": digest, "start": 0x100, "size": 10, "undecoded": 0, "insns": [], "jt": []},
                {"cache": key, "sha256": "deadbeef", "start": 0x200, "size": 100, "undecoded": 0, "insns": [], "jt": []},
            )
        )
        + "\n"
    )
    cache = lp.PcodeCache.load(tmp_path / "cache.jsonl", digest, key, lp.dump_script_fingerprint(), lp.ghidra_version())
    rows = cache.lookup(fdes)
    assert cache.matched == []
    assert rows == []
    assert cache.missing == [0x100, 0x200]


def test_dump_pcode_cached_without_a_cache_asks_ghidra_for_everything(tmp_path, monkeypatch):
    so = tmp_path / "GameAssembly.so"
    so.write_bytes(b"\x7fELF")
    fdes = [lp.Fde(0x100, 10), lp.Fde(0x200, 100)]
    asked = []

    def record_dump(so_, asked_fdes, work, **kw):
        asked.extend(fde.start for fde in asked_fdes)
        return [{"start": fde.start, "size": fde.size} for fde in asked_fdes], [{"name": ".text"}]

    monkeypatch.setattr(lp, "dump_pcode", record_dump)
    bodies, sections = lp.dump_pcode_cached(so, fdes, tmp_path, None)
    assert asked == [0x100, 0x200], "no cache means no body is skipped"
    assert [b["start"] for b in bodies] == [0x100, 0x200]
    assert sections == [{"name": ".text"}]


def test_pcode_cache_merges_reused_and_dumped_records(tmp_path, monkeypatch):
    so = tmp_path / "GameAssembly.so"
    so.write_bytes(b"\x7fELF")
    digest = lp.sha256(so)
    cache_path = tmp_path / "cache.jsonl"
    fdes = [lp.Fde(0x100, 10), lp.Fde(0x200, 100)]
    key = lp.cache_key(digest, fdes)
    cache_path.write_text(
        json.dumps(lp.cache_header(key, digest, lp.dump_script_fingerprint(), lp.ghidra_version()))
        + "\n"
        + json.dumps(lp.section_record(digest, [{"name": ".text"}], key))
        + "\n"
        + json.dumps({"cache": key, "sha256": digest, "start": 0x100, "size": 10, "insns": []})
        + "\n"
    )
    cache = lp.PcodeCache.load(cache_path, digest, key, lp.dump_script_fingerprint(), lp.ghidra_version())
    dumped = [{"start": 0x100, "size": 10, "junk": True, "insns": []}, {"start": 0x200, "size": 100, "insns": []}]
    monkeypatch.setattr(lp, "dump_pcode", lambda so_, fdes_, work, **kw: (dumped, [{"name": ".text"}]))
    bodies, sections = lp.dump_pcode_cached(so, fdes, tmp_path, cache)
    assert [b["start"] for b in bodies] == [0x100, 0x200]
    assert bodies[0]["junk"], "a partial sample is replaced in full"
    assert cache.missing == [0x100, 0x200]
    assert sections == [{"name": ".text"}]


def test_pcode_cache_file_gains_the_records_the_run_needed(tmp_path, monkeypatch):
    so = tmp_path / "GameAssembly.so"
    so.write_bytes(b"\x7fELF")
    monkeypatch.setattr(
        lp,
        "dump_pcode",
        lambda so_, fdes, work, **kw: ([{"start": f.start, "size": f.size, "insns": []} for f in fdes], [{"name": ".text"}]),
    )
    fdes = [lp.Fde(0x100, 2), lp.Fde(0x200, 2)]
    key = lp.cache_key(lp.sha256(so), fdes)
    cache = lp.PcodeCache.load(tmp_path / "cache.jsonl", lp.sha256(so), key, lp.dump_script_fingerprint(), lp.ghidra_version())
    bodies, _ = lp.dump_pcode_cached(so, fdes, tmp_path, cache)
    assert [b["start"] for b in bodies] == [0x100, 0x200]
    cache.save()
    rows = [json.loads(line) for line in (tmp_path / "cache.jsonl").read_text().splitlines() if "start" in line]
    assert [r["start"] for r in rows] == [0x100, 0x200]
    assert [r["size"] for r in rows] == [2, 2]
    assert all(r["sha256"] == lp.sha256(so) for r in rows)
    again = lp.PcodeCache.load(tmp_path / "cache.jsonl", lp.sha256(so), key, lp.dump_script_fingerprint(), lp.ghidra_version())
    assert [b["start"] for b in again.lookup(fdes)] == [0x100, 0x200]
    assert again.missing == []


def test_dump_pcode_cached_uses_one_work_dir_for_the_exact_sample(tmp_path, monkeypatch):
    so = tmp_path / "GameAssembly.so"
    so.write_bytes(b"\x7fELF")
    seen_work = []

    def counting_dump(so_, fdes, work, **kw):
        assert Path(work).is_dir(), "dump_pcode needs the work directory to already exist"
        seen_work.append(Path(work))
        return [{"start": f.start, "size": f.size, "insns": []} for f in fdes], [{"name": ".text"}]

    monkeypatch.setattr(lp, "dump_pcode", counting_dump)
    fdes = [lp.Fde(0x100 * i, 10) for i in range(1, 6)]
    cache = lp.PcodeCache.load(tmp_path / "cache.jsonl", lp.sha256(so))
    cache.key = lp.cache_key(lp.sha256(so), fdes)
    bodies, _ = lp.dump_pcode_cached(so, fdes, tmp_path, cache)
    assert [b["start"] for b in bodies] == [f.start for f in fdes]
    assert seen_work == [tmp_path]


def test_dump_pcode_cached_dumps_the_whole_sample_in_one_ghidra_run(tmp_path, monkeypatch):
    """A chunk size of zero asks Ghidra for every missing body at once, matching an uncached run."""
    so = tmp_path / "GameAssembly.so"
    so.write_bytes(b"\x7fELF")
    asked = []

    def counting_dump(so_, fdes, work, **kw):
        asked.append(len(fdes))
        return [{"start": f.start, "size": f.size, "insns": []} for f in fdes], [{"name": ".text"}]

    monkeypatch.setattr(lp, "dump_pcode", counting_dump)
    cache = lp.PcodeCache.load(tmp_path / "cache.jsonl", lp.sha256(so))
    fdes = [lp.Fde(0x100 * i, 10) for i in range(1, 6)]
    bodies, _ = lp.dump_pcode_cached(so, fdes, tmp_path, cache)
    assert asked == [5], "one Ghidra run for the whole sample"
    assert [b["start"] for b in bodies] == [f.start for f in fdes]


def test_dump_pcode_cached_needs_no_ghidra_run_when_the_cache_is_warm(tmp_path, monkeypatch):
    """A fully warm cache must skip Ghidra entirely rather than build a zero-length range."""
    so = tmp_path / "GameAssembly.so"
    so.write_bytes(b"\x7fELF")
    digest = lp.sha256(so)
    fdes = [lp.Fde(0x100 * i, 10) for i in range(1, 4)]
    key = lp.cache_key(digest, fdes)
    warm = tmp_path / "warm.jsonl"
    warm.write_text(
        json.dumps(lp.cache_header(key, digest, lp.dump_script_fingerprint(), lp.ghidra_version()))
        + "\n"
        + json.dumps(lp.section_record(digest, [{"name": ".text"}], key))
        + "\n"
        + "".join(
            json.dumps({"cache": key, "sha256": digest, "start": f.start, "size": f.size, "insns": []}) + "\n" for f in fdes
        )
    )
    calls = []
    monkeypatch.setattr(lp, "dump_pcode", lambda *a, **k: calls.append(a) or ([], []))
    cache = lp.PcodeCache.load(warm, digest, key, lp.dump_script_fingerprint(), lp.ghidra_version())
    bodies, _ = lp.dump_pcode_cached(so, fdes, tmp_path, cache)
    assert [b["start"] for b in bodies] == [f.start for f in fdes]
    assert calls == [], "warm cache should not reach for Ghidra"


def test_dump_pcode_cached_keeps_every_body_it_just_dumped(tmp_path):
    """A keyless cold cache must still return all freshly dumped rows."""
    so = tmp_path / "GameAssembly.so"
    so.write_bytes(b"\x7fELF")
    fdes = [lp.Fde(0x100 * i, 10) for i in range(1, 4)]

    def fake(so_, part, work, **kw):
        return [{"start": f.start, "size": f.size, "insns": []} for f in part], [{"name": ".text"}]

    cache = lp.PcodeCache.load(tmp_path / "c.jsonl", lp.sha256(so))
    assert cache.key is None, "a cache used only for reading has no sample key"
    rows, sections = lp.dump_pcode_cached(so, fdes, tmp_path, cache, dump=fake)
    assert [r["start"] for r in rows] == [f.start for f in fdes]
    assert sections == [{"name": ".text"}]


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
