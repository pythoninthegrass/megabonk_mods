"""Regression tests for exact object sizes, whole-sample caching and LLVM failures."""

from __future__ import annotations

import json
import lift_probe as lp
import subprocess
from pathlib import Path

DIGEST = "ab" * 32


def proc(stdout=b"", code=0):
    return subprocess.CompletedProcess(["tool"], code, stdout, b"")


def test_llc_size_counts_object_bytes_not_decoded_characters():
    """Count the original binary stream, not a decoded approximation."""
    blob = b"\x7fMELF\x00" + bytes([0xC3, 0x28, 0xFF, 0xFE]) + bytes(200)
    assert blob.decode(errors="replace").encode() != blob, "blob must not survive a text round-trip"
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return proc(stdout=blob)

    original = lp.run_tool
    lp.run_tool = fake_run
    try:
        accepted, size, error = lp.llc_arm64("define void @f(){ret void}", 5)
    finally:
        lp.run_tool = original
    assert accepted and error is None
    assert size == len(blob), f"arm64 object must be counted in bytes, got {size} != {len(blob)}"


def test_opt_pipeline_size_counts_text_bytes_of_the_emitted_ir():
    blob = b"; ModuleID = 'm'\n"
    original = lp.run_tool
    lp.run_tool = lambda cmd, **kw: proc(stdout=blob)
    try:
        accepted, size, error = lp.score_tool("opt", ["opt", "-passes=verify"], "ir", 5)
    finally:
        lp.run_tool = original
    assert accepted and size == len(blob) and error is None


def test_run_tool_body_returns_bytes_so_callers_can_size_them():
    original = lp.run_tool
    blob = bytes([0xC3, 0x28, 0xFF, 0xFE, 0x00]) + bytes(11)
    lp.run_tool = lambda cmd, **kw: proc(stdout=blob)
    try:
        accepted, payload, error = lp.run_tool_body("llc", ["llc"], "ir", 5)
    finally:
        lp.run_tool = original
    assert accepted and error is None
    assert isinstance(payload, bytes), f"binary stdout must stay bytes, got {type(payload).__name__}"
    assert payload == blob, "the payload must be the tool's exact bytes, not a decoded approximation"


def warm_cache(tmp_path, fdes, sections, key=None, fingerprint=None, ghidra=None):
    """Write a cache file the way the tool writes one: header, section table, then keyed bodies."""
    digest = "cd" * 32
    key = key or lp.cache_key(digest, fdes)
    fingerprint = fingerprint or lp.dump_script_fingerprint()
    ghidra = ghidra or lp.ghidra_version()
    path = tmp_path / "cache.jsonl"
    lines = [json.dumps(lp.cache_header(key, digest, fingerprint, ghidra))]
    lines.append(json.dumps(lp.section_record(digest, sections, key)))
    lines += [json.dumps({"cache": key, "sha256": digest, "start": f.start, "size": f.size, "insns": []}) for f in fdes]
    path.write_text("".join(line + "\n" for line in lines))
    return digest, path, key


def load_keyed(path, digest, key, fingerprint=None, ghidra=None):
    return lp.PcodeCache.load(path, digest, key, fingerprint or lp.dump_script_fingerprint(), ghidra or lp.ghidra_version())


def test_warm_cache_returns_the_persisted_section_table(tmp_path):
    """A fully warm cache must not silently score bodies against no sections."""
    fdes = [lp.Fde(0x1000, 40), lp.Fde(0x2000, 80)]
    sections = [{"name": "il2cpp", "va": 0x1000, "size": 0x9000}]
    digest, path, key = warm_cache(tmp_path, fdes, sections)

    def never_dump(*a, **k):
        raise AssertionError("a warm cache must not call for Ghidra")

    cache = load_keyed(path, digest, key)
    rows, out_sections = lp.dump_pcode_cached(Path("so"), fdes, tmp_path, cache, dump=never_dump)
    assert [r["start"] for r in rows] == [0x1000, 0x2000]
    assert out_sections == sections, f"warm cache lost the section table: {out_sections!r}"


def test_warm_cache_without_a_section_record_is_not_a_hit(tmp_path):
    """A cache missing its section table is stale, not complete: it must trigger a dump."""
    fdes = [lp.Fde(0x1000, 40)]
    digest = "ef" * 32
    path = tmp_path / "cache.jsonl"
    path.write_text(json.dumps({"sha256": digest, "start": 0x1000, "size": 40, "insns": []}) + "\n")
    asked = []

    def fake_dump(so_, part, work, **kw):
        asked.append([f.start for f in part])
        return [{"start": f.start, "size": f.size, "insns": []} for f in part], [{"name": "il2cpp", "va": 0x1000, "size": 0x9000}]

    cache = lp.PcodeCache.load(path, digest)
    rows, sections = lp.dump_pcode_cached(Path("so"), fdes, tmp_path, cache, dump=fake_dump)
    assert asked, "a cache with no section table must not masquerade as a complete hit"
    assert sections, "sections must be present for scoring"


def test_cold_and_warm_scoring_agree_on_real_sections(tmp_path):
    """Cold and warm paths must produce the same scored row when sections are nonempty."""
    fdes = [lp.Fde(0x1000, 64)]
    sections = [{"name": "il2cpp", "va": 0x1000, "size": 0x9000}, {"name": "_rodata", "va": 0x20000, "size": 0x400}]
    record = {
        "start": 0x1000,
        "size": 64,
        "undecoded": 0,
        "jt": [],
        "insns": [
            {"a": 0x1000, "len": 1, "m": "mov", "ops": [{"op": "COPY", "out": "register,0,8", "in": ["ram,20000,8"]}]},
            {"a": 0x1001, "len": 1, "m": "ret", "ops": [{"op": "RETURN", "out": None, "in": []}]},
        ],
    }
    digest = "aa" * 32
    cold_row = lp.score_body(dict(record), sections, tool_timeout=5)

    path = tmp_path / "cache.jsonl"
    key = lp.cache_key(digest, fdes)
    path.write_text(
        json.dumps(lp.cache_header(key, digest, lp.dump_script_fingerprint(), lp.ghidra_version()))
        + "\n"
        + json.dumps({"cache": key, "sha256": digest, **record})
        + "\n"
        + json.dumps(lp.section_record(digest, sections, key))
        + "\n"
    )
    cache = lp.PcodeCache.load(path, digest, key, lp.dump_script_fingerprint(), lp.ghidra_version())
    rows, warm_sections = lp.dump_pcode_cached(Path("so"), fdes, tmp_path, cache, dump=lambda *a, **k: ([], []))
    assert warm_sections == sections
    warm_row = lp.score_body(dict(rows[0]), warm_sections, tool_timeout=5)
    assert warm_row == cold_row
    cold_ir = lp.pcode_lift.module_for([lp.pcode_lift.lift_body(record, sections)])
    warm_ir = lp.pcode_lift.module_for([lp.pcode_lift.lift_body(rows[0], warm_sections)])
    assert "@sec__rodata" in cold_ir
    assert warm_ir == cold_ir


def test_cache_key_binds_digest_addresses_and_sizes():
    a = lp.cache_key("ab" * 32, [lp.Fde(0x10, 8), lp.Fde(0x20, 16)])
    b = lp.cache_key("ab" * 32, [lp.Fde(0x10, 8), lp.Fde(0x20, 16)])
    assert a == b, "the same sample must key identically"
    assert a != lp.cache_key("ab" * 32, [lp.Fde(0x10, 8), lp.Fde(0x20, 17)]), "a changed size must change the key"
    assert a != lp.cache_key("ab" * 32, [lp.Fde(0x20, 16), lp.Fde(0x10, 8)]), "order is part of the key"
    assert a != lp.cache_key("ab" * 31 + "00", [lp.Fde(0x10, 8), lp.Fde(0x20, 16)]), "digest is part of the key"


def test_records_from_a_different_sample_are_not_reused(tmp_path):
    """Bodies dumped for another sample must never answer this one, even at matching addresses."""
    fdes = [lp.Fde(0x1000, 40), lp.Fde(0x2000, 80)]
    other = [lp.Fde(0x1000, 40)]
    digest = "be" * 32
    key = lp.cache_key(digest, fdes)
    stale_key = lp.cache_key(digest, other)
    path = tmp_path / "cache.jsonl"
    path.write_text(
        json.dumps({"cache": stale_key, "sha256": digest, "start": 0x1000, "size": 40, "insns": []})
        + "\n"
        + json.dumps({"cache": stale_key, "sha256": digest, "kind": "sections", "sections": []})
        + "\n"
    )
    asked = []

    def fake_dump(so_, part, work, **kw):
        asked.append(sorted(f.start for f in part))
        return [{"start": f.start, "size": f.size, "insns": []} for f in part], []

    cache = lp.PcodeCache.load(path, digest, want_key=key)
    lp.dump_pcode_cached(Path("so"), fdes, tmp_path, cache, dump=fake_dump)
    assert asked and 0x1000 in asked[0], "a record from another sample must not be a hit"


def test_partial_cache_is_not_reported_as_a_complete_hit(tmp_path):
    fdes = [lp.Fde(0x1000, 40), lp.Fde(0x2000, 80), lp.Fde(0x3000, 12)]
    digest = "11" * 32
    key = lp.cache_key(digest, fdes)
    path = tmp_path / "cache.jsonl"
    path.write_text(
        json.dumps(lp.cache_header(key, digest, lp.dump_script_fingerprint(), lp.ghidra_version()))
        + "\n"
        + json.dumps({"cache": key, "sha256": digest, "start": 0x1000, "size": 40, "insns": []})
        + "\n"
        + json.dumps(lp.section_record(digest, [{"name": ".text"}], key))
        + "\n"
    )
    asked = []

    def fake_dump(so_, part, work, **kw):
        asked.append(sorted(f.start for f in part))
        return [{"start": f.start, "size": f.size, "insns": []} for f in part], []

    cache = lp.PcodeCache.load(path, digest, want_key=key)
    rows, _ = lp.dump_pcode_cached(Path("so"), fdes, tmp_path, cache, dump=fake_dump)
    assert cache.missing == [0x1000, 0x2000, 0x3000]
    assert sorted(r["start"] for r in rows) == [0x1000, 0x2000, 0x3000]


def test_malformed_records_are_rejected_not_silently_kept(tmp_path):
    digest = "22" * 32
    fdes = [lp.Fde(0x1000, 40)]
    key = lp.cache_key(digest, fdes)
    path = tmp_path / "cache.jsonl"
    path.write_text(
        "not json\n"
        + json.dumps({"cache": key, "sha256": digest, "start": "0x1000", "size": 40})
        + "\n"
        + json.dumps({"cache": key, "sha256": digest, "start": 0x1000, "size": "40"})
        + "\n"
        + json.dumps({"cache": key, "sha256": digest, "start": 0x1000, "size": 40, "insns": "nope"})
        + "\n"
    )
    asked = []

    def fake_dump(so_, part, work, **kw):
        asked.append([f.start for f in part])
        return [{"start": f.start, "size": f.size, "insns": []} for f in part], []

    cache = lp.PcodeCache.load(path, digest, want_key=key)
    lp.dump_pcode_cached(Path("so"), fdes, tmp_path, cache, dump=fake_dump)
    assert asked == [[0x1000]], "schema-invalid records must count as missing"


def test_cache_records_the_dump_script_fingerprint_and_ghidra_version():
    header = lp.cache_header("k", "ab" * 32, "fp123", "11.3.1")
    assert header["kind"] == "header"
    assert header["script_fingerprint"] == "fp123" and header["ghidra"] == "11.3.1"
    assert lp.cache_header("k", "ab" * 32, "other", "11.3.1")["script_fingerprint"] == "other"


def test_stale_fingerprint_or_version_is_not_a_hit(tmp_path):
    digest = "33" * 32
    fdes = [lp.Fde(0x1000, 40)]
    key = lp.cache_key(digest, fdes)
    path = tmp_path / "cache.jsonl"
    path.write_text(
        json.dumps(lp.cache_header(key, digest, "old-fp", "11.1.0"))
        + "\n"
        + json.dumps({"cache": key, "sha256": digest, "start": 0x1000, "size": 40, "insns": []})
        + "\n"
        + json.dumps({"cache": key, "sha256": digest, "kind": "sections", "sections": []})
        + "\n"
    )
    asked = []

    def fake_dump(so_, part, work, **kw):
        asked.append([f.start for f in part])
        return [{"start": f.start, "size": f.size, "insns": []} for f in part], []

    cache = lp.PcodeCache.load(path, digest, want_key=key, want_fingerprint="new-fp", want_ghidra="11.3.1")
    lp.dump_pcode_cached(Path("so"), fdes, tmp_path, cache, dump=fake_dump)
    assert asked == [[0x1000]], "a cache from another Ghidra build must be recomputed"


def test_dump_defaults_to_one_ghidra_pass_for_the_whole_sample(tmp_path):
    so = tmp_path / "GameAssembly.so"
    so.write_bytes(b"\x7fELF")
    asked = []
    original = lp.dump_pcode
    lp.dump_pcode = lambda so_, fdes, work, **kw: (
        asked.append(len(fdes)) or [{k: getattr(f, k) for k in ("start", "size")} for f in fdes],
        [],
    )
    try:
        digest = lp.sha256(so)
        cache = lp.PcodeCache.load(tmp_path / "c.jsonl", digest)
        fdes = [lp.Fde(0x100 * i, 8) for i in range(1, 501)]
        bodies, _ = lp.dump_pcode_cached(so, fdes, tmp_path, cache, dump=lp.dump_pcode)
    finally:
        lp.dump_pcode = original
    assert asked == [500], f"default must be a single Ghidra pass, got {asked}"


def rejected_pipeline_run(cmd, **kw):
    text = " ".join(str(c) for c in cmd)
    if "-passes=verify" in text:
        return proc(stdout=b"")
    if "opt" in Path(str(cmd[0])).name and "-passes=boom<O2>" in text:
        return proc(stdout=b"", code=1)
    if "llc" in Path(str(cmd[0])).name:
        return proc(stdout=b"\x7fMO" + bytes(200))
    return proc(stdout=b"")


def test_rejected_pipeline_is_recorded_at_the_body_address():
    original = lp.run_tool
    lp.run_tool = rejected_pipeline_run
    try:
        row = lp.score_body(
            {"start": 0x4000, "size": 64, "insns": [], "undecoded": 0, "sw": True, "uw": [], "dc": False, "jt": []},
            [{"name": "il2cpp", "va": 0x1000, "size": 0x9000}],
            tool_timeout=5,
            pipeline="boom<O2>",
        )
    finally:
        lp.run_tool = original
    assert row["start"] == 0x4000
    assert row["stages"]["arm64"] is False, "a pipeline that was rejected must not report arm64 success"
    assert row["stages"]["arm64_pipeline"] is False
    assert row["pipeline"] == "boom<O2>"
    assert row["error"] and "boom<O2>" in row["error"]


def test_rejected_pipeline_does_not_report_fallback_object_bytes():
    original = lp.run_tool
    lp.run_tool = rejected_pipeline_run
    try:
        row = lp.score_body(
            {"start": 0x4000, "size": 64, "insns": [], "undecoded": 0, "sw": True, "uw": [], "dc": False, "jt": []},
            [{"name": "il2cpp", "va": 0x1000, "size": 0x9000}],
            tool_timeout=5,
            pipeline="boom<O2>",
        )
    finally:
        lp.run_tool = original
    assert row["obj_bytes"] in (0, None), f"fallback bytes must not be billed to a rejected pipeline: {row['obj_bytes']}"


def test_successful_pipeline_verifies_the_post_pass_ir_before_compiling():
    calls = []

    def spy(cmd, **kw):
        text = " ".join(str(c) for c in cmd)
        calls.append(text)
        if "-passes=verify" in text:
            return proc(stdout=b"", code=1)
        if "llc" in Path(str(cmd[0])).name:
            return proc(stdout=b"\x7fMO" + bytes(100))
        return proc(stdout=b"; module\n")

    original = lp.run_tool
    lp.run_tool = spy
    try:
        row = lp.score_body(
            {"start": 0x5000, "size": 64, "insns": [], "undecoded": 0, "sw": True, "uw": [], "dc": False, "jt": []},
            [{"name": "il2cpp", "va": 0x1000, "size": 0x9000}],
            tool_timeout=5,
            pipeline="default<O2>",
        )
    finally:
        lp.run_tool = original
    verify_calls = [c for c in calls if "-passes=verify" in c]
    assert verify_calls, "post-pass IR must be verified"
    assert row["stages"]["arm64"] is False, "post-pass IR that fails verify must not be compiled for size"


def test_totals_keep_every_requested_body_when_a_pipeline_is_rejected():
    rows = [
        {"start": 0x1, "size": 8, "error": "x"},
        {"start": 0x2, "size": 8},
    ]
    scored = [lp.score_row(r, [], 5, "boom<O2>") for r in rows]
    assert len(scored) == 2
    assert {r["start"] for r in scored} == {0x1, 0x2}


def test_partial_sample_is_redumped_in_full(tmp_path):
    fdes = [lp.Fde(0x1000, 40), lp.Fde(0x2000, 80)]
    digest, path, key = warm_cache(tmp_path, fdes, [{"name": ".text"}])
    lines = path.read_text().splitlines()
    path.write_text("\n".join(lines[:-1]) + "\n")
    cache = load_keyed(path, digest, key)
    asked = []

    def dump(so, sample, work, **kw):
        asked.append(sample)
        return [{"start": f.start, "size": f.size, "insns": []} for f in sample], [{"name": ".text"}]

    lp.dump_pcode_cached(Path("so"), fdes, tmp_path, cache, dump=dump)
    assert asked == [fdes]
    assert cache.matched == []


def test_cache_rejects_wrong_record_size_and_empty_sections(tmp_path):
    fdes = [lp.Fde(0x1000, 40)]
    for sections, size in [([], 40), ([{"name": ".text"}], 41)]:
        digest, path, key = warm_cache(tmp_path, fdes, sections)
        path.write_text(path.read_text().replace('"size": 40', f'"size": {size}'))
        cache = load_keyed(path, digest, key)
        assert cache.lookup(fdes) == []
        assert cache.missing == [0x1000]


def test_opt_rejection_keeps_stderr(monkeypatch):
    monkeypatch.setattr(lp, "run_tool", lambda *a, **kw: subprocess.CompletedProcess([], 1, b"", b"broken pass detail\n"))
    accepted, payload, error = lp.run_tool_body("opt", ["opt"], "ir", 5)
    assert not accepted and payload is None
    assert error == "opt rejected IR: broken pass detail"
