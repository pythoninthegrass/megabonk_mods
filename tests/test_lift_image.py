"""Tests for the complete-image coverage accounting of the lift."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import lift_image as li
from lift_probe import Fde


def test_single_byte_nops_and_int3_are_padding():
    assert li.classify_gap(b"\x90\x90\xcc\xcc") == "padding"


def test_multi_byte_nop_forms_are_padding():
    forms = [
        b"\x66\x90",
        b"\x0f\x1f\x00",
        b"\x0f\x1f\x40\x00",
        b"\x0f\x1f\x44\x00\x00",
        b"\x66\x0f\x1f\x44\x00\x00",
        b"\x0f\x1f\x80\x00\x00\x00\x00",
        b"\x0f\x1f\x84\x00\x00\x00\x00\x00",
        b"\x66\x0f\x1f\x84\x00\x00\x00\x00\x00",
        b"\x66\x2e\x0f\x1f\x84\x00\x00\x00\x00\x00",
        b"\x66\x66\x2e\x0f\x1f\x84\x00\x00\x00\x00\x00",
    ]
    for form in forms:
        assert li.classify_gap(form) == "padding", form.hex()


def test_a_nop_run_followed_by_an_instruction_is_other():
    assert li.classify_gap(b"\x90\x55") == "other"
    assert li.classify_gap(b"\x66\x2e\x0f\x1f\x84\x00\x00\x00\x00\x00\x55") == "other"


def test_truncated_nop_is_other():
    assert li.classify_gap(b"\x0f\x1f\x84\x00") == "other"


def test_zero_fill_is_reported_apart_from_padding():
    assert li.classify_gap(b"\x00" * 16) == "zero_fill"
    assert li.classify_gap(b"\x00\x00\x90") == "other"


def test_empty_gap_is_padding():
    assert li.classify_gap(b"") == "padding"


def test_gaps_between_bodies_and_at_section_ends():
    fdes = [Fde(0x110, 0x20), Fde(0x140, 0x10)]
    assert li.gaps(fdes, 0x100, 0x200) == [(0x100, 0x10), (0x130, 0x10), (0x150, 0xB0)]


def test_overlapping_bodies_leave_no_negative_gap():
    fdes = [Fde(0x100, 0x30), Fde(0x110, 0x10), Fde(0x130, 0x10)]
    assert li.gaps(fdes, 0x100, 0x140) == []


def test_body_straddling_a_section_end_is_clamped():
    assert li.gaps([Fde(0x100, 0x200)], 0x100, 0x180) == []


def test_section_account_names_every_byte():
    code = bytearray(0x100)
    code[0x00:0x10] = b"\x90" * 0x10
    code[0x10:0x20] = b"\x55" * 0x10
    acct = li.account_section("t", 0, 0x100, bytes(code), [Fde(0x10, 0x10)], stubs=False)
    assert acct["bodies"] == 1
    assert acct["body_bytes"] == 0x10
    assert acct["gap_bytes"] == {"padding": 0x10, "zero_fill": 0xE0, "other": 0}
    assert acct["unaccounted"] == []


def test_unaccounted_code_is_listed_with_its_address():
    code = bytearray(0x40)
    code[0x20:0x22] = b"\x55\xc3"
    acct = li.account_section("t", 0x1000, 0x1040, bytes(code), [Fde(0x1000, 0x10)], stubs=False)
    assert acct["unaccounted"] == [{"start": 0x1010, "size": 0x30}]


def test_stub_sections_are_named_not_unaccounted():
    acct = li.account_section(".plt", 0x1000, 0x1040, bytes(range(0x40)), [], stubs=True)
    assert acct["stub_bytes"] == 0x40
    assert acct["unaccounted"] == []


def test_verdict_blocks_on_unaccounted_code():
    clean = {"unaccounted": [], "stub_bytes": 0}
    dirty = {"unaccounted": [{"start": 1, "size": 2}], "stub_bytes": 0}
    assert li.coverage_complete({"a": clean})
    assert not li.coverage_complete({"a": clean, "b": dirty})


UNFRAMED = [
    {"name": "a", "start": 0x1000, "size": 0x10},
    {"name": "b", "start": 0x1010, "size": 0x8},
]


def test_unframed_entries_must_cover_every_unaccounted_range():
    data = bytes(range(0x30))
    un = [{"start": 0x1000, "size": 0x18}]
    assert li.resolve_unframed(un, UNFRAMED, 0x1000, data) == [Fde(0x1000, 0x10), Fde(0x1010, 0x8)]


def test_unframed_tail_after_the_last_entry_must_be_padding():
    data = bytes(0x10) + b"\x55" * 8 + b"\x90\xcc"
    un = [{"start": 0x1000, "size": 0x1A}]
    assert li.resolve_unframed(un, UNFRAMED, 0x1000, data) == [Fde(0x1000, 0x10), Fde(0x1010, 0x8)]
    bad = data[:0x18] + b"\x55\x55"
    try:
        li.resolve_unframed(un, UNFRAMED, 0x1000, bad)
    except ValueError as exc:
        assert "0x1018" in str(exc)
    else:
        raise AssertionError("uncovered code must raise")


def test_an_unaccounted_range_with_no_entry_raises():
    try:
        li.resolve_unframed([{"start": 0x5000, "size": 4}], UNFRAMED, 0x1000, bytes(0x100))
    except ValueError as exc:
        assert "0x5000" in str(exc)
    else:
        raise AssertionError("an unrecorded range must raise")


def test_shards_are_deterministic_and_complete():
    bodies = [Fde(i * 0x10, 0x10) for i in range(10)]
    parts = li.shards(bodies, 4)
    assert [len(p) for p in parts] == [4, 4, 2]
    assert [b for p in parts for b in p] == bodies


def test_body_shards_exclude_empty_frames_without_moving_other_shards():
    bodies = [Fde(1, 0), Fde(1, 2), Fde(3, 1)]
    assert li.body_shards(bodies, 2) == [[Fde(1, 2)], [Fde(3, 1)]]


def test_shard_identity_changes_with_any_input():
    base = li.shard_identity("sha", "fp", "ghidra", [Fde(0, 4)], "")
    assert base == li.shard_identity("sha", "fp", "ghidra", [Fde(0, 4)], "")
    for other in (
        li.shard_identity("sha2", "fp", "ghidra", [Fde(0, 4)], ""),
        li.shard_identity("sha", "fp2", "ghidra", [Fde(0, 4)], ""),
        li.shard_identity("sha", "fp", "ghidra2", [Fde(0, 4)], ""),
        li.shard_identity("sha", "fp", "ghidra", [Fde(0, 5)], ""),
        li.shard_identity("sha", "fp", "ghidra", [Fde(0, 4)], "default<O2>"),
    ):
        assert other != base


def test_a_shard_file_is_reused_only_under_its_own_identity(tmp_path):
    path = tmp_path / "shard-0.jsonl"
    li.write_shard(path, "id1", [{"start": 1, "size": 2}])
    assert li.read_shard(path, "id1") == [{"start": 1, "size": 2}]
    assert li.read_shard(path, "id2") is None
    assert li.read_shard(tmp_path / "missing.jsonl", "id1") is None


def test_a_truncated_shard_file_is_not_reused(tmp_path):
    path = tmp_path / "shard-0.jsonl"
    li.write_shard(path, "id1", [{"start": 1, "size": 2}, {"start": 3, "size": 4}])
    path.write_text(path.read_text().rsplit("\n", 2)[0] + "\n")
    assert li.read_shard(path, "id1") is None


def test_blocker_selection_requires_a_complete_matching_verdict():
    parts = [[Fde(1, 2)], [Fde(3, 4), Fde(5, 6)]]
    report = {"binary_sha256": "sha", "bodies": 3, "scored": 3,
              "verdict": {"coverage_complete": True, "blocking": [5]}}
    assert li.select_blockers(report, "sha", parts) == [(1, parts[1], [Fde(5, 6)])]
    for bad in (
        {**report, "binary_sha256": "other"},
        {**report, "scored": 2},
        {**report, "verdict": {"coverage_complete": False, "blocking": [5]}},
        {**report, "verdict": {"coverage_complete": True, "blocking": [7]}},
        {**report, "verdict": {"coverage_complete": True, "blocking": [5, 5]}},
    ):
        with pytest.raises(ValueError):
            li.select_blockers(bad, "sha", parts)


def test_blocker_shard_reuses_scores_only_for_the_same_scorer(tmp_path, monkeypatch):
    import lift_probe as lp

    baseline, out = tmp_path / "baseline", tmp_path / "out"
    baseline.mkdir()
    out.mkdir()
    part = [Fde(1, 2), Fde(3, 4)]
    rows = [{"start": b.start, "size": b.size} for b in part]
    path = baseline / "pcode-0004.jsonl"
    identity = li.shard_identity("sha", "dump", "ghidra", part, "")
    li.write_shard(path, identity, [{"kind": "sections", "sections": []}, *rows])
    original = path.read_bytes()
    calls = []

    def score(row, sections, timeout, pipeline):
        calls.append(row["start"])
        return row

    monkeypatch.setattr(lp, "score_row", score)
    ctx = dict(sha="sha", fingerprint="dump", ghidra="ghidra", pipeline="", tool_timeout=10, score_jobs=1, out=out)
    for scorer in ("first", "first", "changed"):
        assert li.score_blocker_shard(4, part, part[1:], baseline, ctx, scorer) == rows[1:]
    assert calls == [3, 3]
    assert path.read_bytes() == original
    with pytest.raises(ValueError, match="pcode shard 4"):
        li.score_blocker_shard(4, part, part[1:], baseline, {**ctx, "fingerprint": "changed"}, "first")


@pytest.mark.parametrize("second", [{"start": 1, "size": 2}, {"start": 3, "size": 5}, None])
@pytest.mark.parametrize("pcode", [False, True])
def test_a_shard_with_the_wrong_body_inventory_is_not_reused(tmp_path, second, pcode):
    path = tmp_path / "shard.jsonl"
    rows = [{"start": 1, "size": 2}, second]
    if pcode:
        rows.insert(0, {"kind": "sections", "sections": []})
    li.write_shard(path, "id", rows)
    assert li.read_shard(path, "id", [Fde(1, 2), Fde(3, 4)], pcode=pcode) is None
    rows[-1] = {"start": 3, "size": 4}
    li.write_shard(path, "id", rows)
    assert li.read_shard(path, "id", [Fde(1, 2), Fde(3, 4)], pcode=pcode) == rows


def test_verdict_is_runnable_only_when_every_body_is_clean():
    ok = {"start": 1, "size": 1, "error": None, "stages": {"decoded": True, "clean": True, "verify": True, "arm64": True}}
    hole = {**ok, "start": 2, "stages": {**ok["stages"], "clean": False}}
    assert li.build_verdict([ok], coverage=True)["runnable"]
    assert not li.build_verdict([ok, hole], coverage=True)["runnable"]
    assert not li.build_verdict([ok], coverage=False)["runnable"]
    assert li.build_verdict([ok, hole], coverage=True)["blocking"] == [2]


def test_empty_verdict_is_not_runnable():
    assert not li.build_verdict([], coverage=True)["runnable"]


def test_build_inventory_accounts_for_stubs_and_resolved_unframed_bodies():
    sections, bodies = li.build_inventory(
        {".text": (0, 4), ".plt": (4, 8)},
        b"\x55\x90\x55\x90" + b"\x55" * 4,
        [Fde(0, 2)],
        [{"name": "helper", "start": 2, "size": 1}],
    )
    assert bodies == [Fde(2, 1)]
    assert sections[".text"]["bodies"] == 2
    assert sections[".text"]["unaccounted"] == []
    assert sections[".plt"]["excluded"] == [{"start": 4, "size": 4, "reason": "lazy-binding import stubs"}]


@pytest.mark.parametrize("frame", [Fde(4, 1), Fde(3, 2)])
def test_build_inventory_rejects_frames_outside_body_sections(frame):
    with pytest.raises(ValueError, match="executable body section"):
        li.build_inventory({".text": (0, 4), ".plt": (4, 8)}, b"\x90" * 8, [frame], [])


class DumpFailed(Exception):
    pass


def _fake_dump(bad):
    calls = []

    def dump(part, timeout):
        calls.append((len(part), timeout))
        if any(b.start in bad for b in part):
            raise DumpFailed("timeout")
        return [{"start": b.start, "size": b.size} for b in part], [{"name": "s"}]

    return dump, calls


def test_bisect_returns_all_rows_when_the_whole_part_dumps():
    part = [Fde(i, 1) for i in range(8)]
    dump, calls = _fake_dump(set())
    rows, sections, failed = li.dump_bisecting(part, dump, DumpFailed, timeout=100)
    assert len(rows) == 8 and sections == [{"name": "s"}] and failed == {}
    assert calls == [(8, 100)]


def test_bisect_isolates_a_single_failing_body():
    part = [Fde(i, 1) for i in range(8)]
    dump, _ = _fake_dump({5})
    rows, _, failed = li.dump_bisecting(part, dump, DumpFailed, timeout=100)
    assert sorted(r["start"] for r in rows) == [0, 1, 2, 3, 4, 6, 7]
    assert list(failed) == [5] and "timeout" in failed[5]


def test_bisect_retries_with_a_timeout_scaled_to_the_part():
    part = [Fde(i, 1) for i in range(4)]
    dump, calls = _fake_dump({0})
    li.dump_bisecting(part, dump, DumpFailed, timeout=3600, retry_base=300, retry_per_body=2)
    assert calls[0] == (4, 3600) and calls[1] == (2, 304)


def test_bisect_retries_only_ranges_missing_from_a_partial_dump():
    part = [Fde(i, 1) for i in range(6)]
    calls = []

    def dump(bodies, timeout):
        calls.append([body.start for body in bodies])
        rows = [{"start": b.start, "size": b.size} for b in bodies if b.start != 3]
        return rows, [{"name": "s"}]

    rows, sections, failed = li.dump_bisecting(part, dump, DumpFailed, timeout=100)
    assert calls == [[0, 1, 2, 3, 4, 5], [3]]
    assert [r["start"] for r in rows] == [0, 1, 2, 4, 5]
    assert sections == [{"name": "s"}]
    assert list(failed) == [3]


def test_missing_dump_cache_can_be_retried_without_discarding_good_rows(tmp_path, monkeypatch):
    import lift_probe as lp

    part = [Fde(1, 1), Fde(2, 1)]
    sections = [{"name": "s"}]
    body = {"start": 1, "size": 1}
    failed = lp.failed_row(2, 1, "old partial dump", missing_dump=True)
    ctx = dict(out=tmp_path, sha="a", fingerprint="b", ghidra="c", pipeline="", ghidra_timeout=10,
               score_jobs=1, tool_timeout=10, so=tmp_path / "image.so", retry_missing_dump=True)
    identity = li.shard_identity("a", "b", "c", part, "")
    li.write_shard(tmp_path / "scored-0000.jsonl", identity, [body, failed])
    li.write_shard(tmp_path / "pcode-0000.jsonl", identity,
                   [{"kind": "sections", "sections": sections}, body, failed])

    def dump(so, bodies, work, **kwargs):
        assert bodies == [part[1]]
        return [{"start": 2, "size": 1}], sections

    def score(row, sections, timeout, pipeline):
        assert row["start"] == 2
        return row

    monkeypatch.setattr(lp, "dump_pcode", dump)
    monkeypatch.setattr(lp, "score_row", score)
    assert li.build_shard(0, part, ctx) == [body, {"start": 2, "size": 1}]
