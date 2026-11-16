"""Tests for the BRANCHIND census that records a reason per unproven indirect jump."""

import branchind_report as br  # type: ignore[import-not-found]  # resolved at runtime via pytest pythonpath
import json


def row(start, proven=0, unproven=()):
    return {"start": start, "proven_tail_calls": proven, "unproven_branchind": [dict(s) for s in unproven]}


def test_census_counts_proven_and_unproven_sites():
    rows = [
        row(0x1000, proven=2),
        row(0x2000, proven=1, unproven=[{"a": 0x2010, "reason": "rsp not at entry value", "rsp_delta": -8}]),
    ]
    report = br.census(rows)
    assert report["bodies"] == 2
    assert report["proven_tail_calls"] == 3
    assert report["unproven_sites"] == 1


def test_census_groups_unproven_sites_by_body_in_order():
    rows = [
        row(0x2000, unproven=[{"a": 0x2020, "reason": "no path in the dump reaches the site", "rsp_delta": None}]),
        row(
            0x1000,
            unproven=[
                {"a": 0x1010, "reason": "rsp not at entry value", "rsp_delta": -8},
                {"a": 0x1030, "reason": "rsp not at entry value", "rsp_delta": -16},
            ],
        ),
    ]
    report = br.census(rows)
    bodies = [b["body"] for b in report["unproven_by_body"]]
    assert bodies == ["0x2000", "0x1000"]  # body order follows the rows, not sorted address
    first = report["unproven_by_body"][1]
    assert [s["at"] for s in first["sites"]] == ["0x1010", "0x1030"]
    assert all(s["reason"] == "rsp not at entry value" for s in first["sites"])


def test_census_tallies_reasons_and_untracked_rsp():
    rows = [
        row(0x1000, unproven=[{"a": 0x1010, "reason": br.UNTRACKED, "rsp_delta": None}]),
        row(0x2000, unproven=[{"a": 0x2010, "reason": br.UNTRACKED, "rsp_delta": None}]),
        row(0x3000, unproven=[{"a": 0x3010, "reason": "rsp not at entry value", "rsp_delta": -8}]),
    ]
    report = br.census(rows)
    assert report["unproven_reasons"][br.UNTRACKED] == 2
    assert report["unproven_reasons"]["rsp not at entry value"] == 1
    assert report["untracked_rsp_sites"] == 2  # sites whose rsp could not be followed at all


def test_census_of_a_body_with_no_indirect_jump_is_clean():
    report = br.census([row(0x1000, proven=1)])
    assert report["unproven_sites"] == 0
    assert report["unproven_by_body"] == []
    assert report["unproven_reasons"] == {}


def test_main_exits_zero_when_a_site_is_proven(tmp_path):
    out = tmp_path / "probe"
    out.mkdir()
    (out / "bodies.jsonl").write_text(
        json.dumps({"start": 0x1000, "proven_tail_calls": 1, "unproven_branchind": []}) + "\n"
    )
    assert br.main([str(out), "--write"]) == 0
    assert (out / "branchind.json").exists()


def test_main_exits_one_when_no_site_is_proven(tmp_path):
    out = tmp_path / "probe"
    out.mkdir()
    (out / "bodies.jsonl").write_text(
        json.dumps(
            {
                "start": 0x1000,
                "proven_tail_calls": 0,
                "unproven_branchind": [{"a": 0x1010, "reason": "rsp not at entry value", "rsp_delta": -8}],
            }
        )
        + "\n"
    )
    assert br.main([str(out)]) == 1  # the acceptance-criterion #1 stop rule: zero proven is a bail


def test_read_rows_skips_blank_and_error_lines(tmp_path):
    path = tmp_path / "bodies.jsonl"
    path.write_text(
        "\n"
        + json.dumps({"start": 0x1000, "proven_tail_calls": 1, "unproven_branchind": []})
        + "\n"
        + "{not json}\n"
        + json.dumps({"start": 0x2000, "error": "dump failed"})
        + "\n"
    )
    rows = br.read_rows(path)
    assert [r["start"] for r in rows] == [0x1000]
