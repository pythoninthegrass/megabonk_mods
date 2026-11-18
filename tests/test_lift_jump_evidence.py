"""Tests for bounded, resumable jump-table evidence recovery."""

import json
import lift_jump_evidence as evidence
from lift_probe import Fde


def test_out_of_body_switch_evidence_is_preserved_but_unresolved():
    body = Fde(0x1000, 8)
    tables = [{"at": 0x1002, "cases": [0x1004, 0x1008]}, {"at": 0x1010, "cases": [0x1001]}]
    row = {"start": body.start, "size": body.size, "status": "complete", "jt": tables}
    assert evidence.check_table_bounds(body, row) == {
        **row, "status": "unresolved_bounds",
        "out_of_body": [{"at": 0x1002, "cases": [0x1008]}, {"at": 0x1010, "cases": []}],
    }
    clean = {**row, "jt": [{"at": 0x1002, "cases": [0x1007]}]}
    assert evidence.check_table_bounds(body, clean) == clean


def test_a_batch_timeout_names_the_active_body_and_preserves_finished_rows(tmp_path):
    bodies = [Fde(0x1000, 8), Fde(0x2000, 12), Fde(0x3000, 16)]
    calls = []

    def dump(part, work):
        calls.append(part)
        row = {"start": part[0].start, "size": part[0].size, "status": "complete", "jt": []}
        (work / f"{part[0].start:x}.json").write_text(json.dumps(row))
        if len(part) > 1:
            (work / "active").write_text(f"{part[1].start:x}")
            return False
        return True

    rows = evidence.recover(bodies, tmp_path, "identity", dump, batch_size=8)
    assert [r["status"] for r in rows] == ["complete", "batch_timeout", "complete"]
    assert calls == [bodies, bodies[2:]]
    assert evidence.recover(bodies, tmp_path, "identity", dump, batch_size=8) == rows
    assert calls == [bodies, bodies[2:]]
    assert evidence.recover(bodies, tmp_path, "new-deadline", dump, batch_size=8) == rows
    assert calls == [bodies, bodies[2:], bodies, bodies[2:]]
