"""A typed catch is runnable only for the LSDAs a type plan proved; everything else stays rejected."""

import lift_reloc as rl
import lift_unwind as lu
import struct
from test_lift_eh import hand_lsda, sleb
from test_lift_unwind_tables import PERSONALITY, PROLOGUE, frames_for

TYPED = hand_lsda(1, bytes([1, 0]), struct.pack("<i", 0x100))
SPEC = hand_lsda(1, sleb(-1) + bytes([0]), struct.pack("<i", 0x100))
BASE = 0x40


def build(table, lsda, typed_ok):
    frames = frames_for((0x1000, PROLOGUE, lsda))
    return lu.build_entries(frames, {0x1000}, PERSONALITY, lsda_tables=[(table, BASE)], typed_ok=typed_ok)


def test_a_typed_catch_outside_the_proven_set_is_still_rejected():
    assert build(TYPED, BASE, frozenset()).problems == ["EH_TYPED_CATCH:1000"]


def test_a_typed_catch_in_the_proven_set_is_accepted():
    table = build(TYPED, BASE, frozenset({BASE}))
    assert table.problems == [] and [e.pc_begin for e in table.entries] == [0x1000]


def test_proving_a_typed_catch_does_not_excuse_an_exception_specification():
    assert build(SPEC, BASE, frozenset({BASE})).problems == ["EH_EXC_SPEC:1000"]


def test_the_filter_report_splits_typed_bodies_into_runnable_and_rejected_by_reason():
    data = TYPED + TYPED + TYPED
    each = len(TYPED)
    frames = frames_for((0x1000, PROLOGUE, BASE), (0x2000, PROLOGUE, BASE + each), (0x3000, PROLOGUE, BASE + 2 * each))
    plan = rl.TypePlan(
        proven={BASE}, rejected={BASE + each: "EH_TYPED_CATCH", BASE + 2 * each: "EH_TYPEINFO_RELOC:RELOC_TYPE:GLOB_DAT"}
    )
    report = lu.filter_report(frames, data, BASE, 0x1000, 0x5000, plan)
    assert report["typed_catch"] == 3
    assert report["typed_runnable"] == 1
    assert report["typed_rejected"] == {"EH_TYPED_CATCH": 1, "EH_TYPEINFO_RELOC:RELOC_TYPE:GLOB_DAT": 1}
