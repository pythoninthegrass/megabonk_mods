"""Tests for the complete-image coverage accounting of the lift."""

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
