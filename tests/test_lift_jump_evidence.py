"""Tests for bounded, resumable jump-table evidence recovery."""

import json
import lift_jump_evidence as evidence
from lift_probe import Fde


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
