"""Tests for the native arm64 execution gate: Linux control parsing, comparison and the report.

The driver lifts one shipped body to arm64, runs it natively, and compares its result with the
value the frozen shipped Linux runtime returned for the same method. These tests cover the pure
parts: parsing both sides, the checks that decide the verdict, and the report layout.
"""

import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import native_exec_probe as nep

SHA = "a" * 64


def control_evidence(**overrides):
    evidence = {
        "leg": "leg2",
        "arch": "x86_64",
        "platform": "linux",
        "image": "Assembly-CSharp.dll",
        "method_name": "GetWeaponMaxLevel",
        "method_rva": "0x225b7d0",
        "returned": "40",
        "state0": "0x1",
        "state1": "0x7f39f8b5b5e8,0x1e3716a0,0x1",
        "state2": "0x7f39f8b5b5e8,0x1e3716a0,0x7f39f299af60,0x0",
    }
    evidence.update(overrides)
    return evidence


def control_text(status="pass", **overrides):
    payload = {"status": status, "reason": "", "evidence": control_evidence(**overrides)}
    return "[host] noise\n#JSON# " + json.dumps(payload) + "\n"


def harness_payload(**overrides):
    payload = {
        "arch": "arm64",
        "proc_translated": 0,
        "rva": "0x225b7d0",
        "result": 40,
        "stubs_reached": [],
        "state": {"guard_set": True, "class_initialised": True, "instance_null": True},
    }
    payload.update(overrides)
    return payload


def harness_text(**overrides):
    return "#JSON# " + json.dumps(harness_payload(**overrides)) + "\n"


def make_report(control=None, run=None, **kwargs):
    control = control or nep.parse_control(control_text())
    run = run or nep.parse_harness(harness_text())
    return nep.build_report(control, run, binary_sha256=SHA, **kwargs)


def failed_checks(report):
    return {check["name"] for check in report["checks"] if not check["passed"]}


def test_parse_control_reads_identity_result_and_state():
    control = nep.parse_control(control_text())
    assert control.image == "Assembly-CSharp.dll"
    assert control.method == "GetWeaponMaxLevel"
    assert control.rva == 0x225B7D0
    assert control.returned == 40
    assert control.state == {"guard_set": True, "class_initialised": True, "instance_null": True}


def test_parse_control_reports_unset_guard_and_present_instance():
    control = nep.parse_control(control_text(state0="0x0", state1="0x1,0x2,0x0", state2="0x1,0x2,0x7f00,0x55"))
    assert control.state == {"guard_set": False, "class_initialised": False, "instance_null": False}


@pytest.mark.parametrize(
    "text, message",
    [
        ("no json here\n", "no host report"),
        (control_text(status="fail"), "did not pass"),
        (control_text(platform="macos"), "not the shipped Linux"),
        (control_text(method_rva="zzz"), "method_rva"),
        (control_text(returned="forty"), "returned"),
    ],
)
def test_parse_control_rejects_unusable_reports(text, message):
    with pytest.raises(nep.ProbeError, match=message):
        nep.parse_control(text)


def test_parse_control_rejects_a_report_without_state_chains():
    text = control_text()
    payload = json.loads(text.split("#JSON# ", 1)[1])
    del payload["evidence"]["state0"]
    with pytest.raises(nep.ProbeError, match="state"):
        nep.parse_control("#JSON# " + json.dumps(payload))


def test_parse_harness_reads_the_run():
    run = nep.parse_harness(harness_text())
    assert (run.arch, run.proc_translated, run.rva, run.result) == ("arm64", 0, 0x225B7D0, 40)
    assert run.stubs_reached == []


def test_parse_harness_rejects_missing_report():
    with pytest.raises(nep.ProbeError, match="no harness report"):
        nep.parse_harness("crashed\n")


def test_matching_run_passes_every_check():
    report = make_report()
    assert report["verdict"] == "pass"
    assert failed_checks(report) == set()


def test_wrong_candidate_result_fails():
    report = make_report(run=nep.parse_harness(harness_text(result=41)))
    assert report["verdict"] == "fail"
    assert failed_checks(report) == {"result_matches"}


def test_override_marks_the_report_tampered_and_fails():
    run = nep.apply_result_override(nep.parse_harness(harness_text()), 7)
    report = make_report(run=run)
    assert run.result == 7
    assert report["verdict"] == "fail"
    assert report["candidate"]["result_overridden"] is True
    assert "result_matches" in failed_checks(report)


def test_rva_mismatch_fails():
    report = make_report(run=nep.parse_harness(harness_text(rva="0x225b7e0")))
    assert failed_checks(report) == {"body_identity"}


@pytest.mark.parametrize(
    "overrides",
    [
        {"proc_translated": 1},
        {"proc_translated": -1},
        {"arch": "x86_64"},
    ],
)
def test_translated_or_non_arm64_run_fails(overrides):
    report = make_report(run=nep.parse_harness(harness_text(**overrides)))
    assert failed_checks(report) == {"native_arm64"}


def test_reached_stub_fails_because_unmodelled_runtime_code_ran():
    report = make_report(run=nep.parse_harness(harness_text(stubs_reached=["sub_20563d0"])))
    assert failed_checks(report) == {"no_unmodelled_calls"}


def test_modelled_state_must_match_the_state_the_linux_control_observed():
    state = {"guard_set": True, "class_initialised": True, "instance_null": False}
    report = make_report(run=nep.parse_harness(harness_text(state=state)))
    assert failed_checks(report) == {"state_matches"}


def test_malformed_binary_digest_fails_identity():
    report = nep.build_report(nep.parse_control(control_text()), nep.parse_harness(harness_text()), binary_sha256="not-a-digest")
    assert failed_checks(report) == {"binary_identity"}


def test_report_separates_shipped_game_evidence_from_harness_and_probe_player():
    report = make_report()
    shipped = report["evidence"]["shipped_game"]
    assert shipped["source"] == "frozen shipped Linux GameAssembly.so run through the il2cpp C API"
    assert shipped["binary_sha256"] == SHA
    assert (shipped["image"], shipped["method"], shipped["rva"], shipped["result"]) == (
        "Assembly-CSharp.dll",
        "GetWeaponMaxLevel",
        "0x225b7d0",
        40,
    )
    harness = report["evidence"]["lifted_arm64_harness"]
    assert harness["arch"] == "arm64" and harness["proc_translated"] == 0 and harness["result"] == 40
    assert report["evidence"]["probe_player"] is None


def test_report_names_the_method_and_body_it_ran():
    report = make_report()
    assert report["candidate"]["method"] == "InventoryUtility.GetWeaponMaxLevel"
    assert report["candidate"]["rva"] == "0x225b7d0"
    assert report["candidate"]["result_overridden"] is False


def fde(start, size=16):
    return nep.lift_probe.Fde(start, size)


def test_select_bodies_follows_callees_in_the_game_code_window_up_to_the_depth():
    fdes = [fde(0x100), fde(0x200), fde(0x300), fde(0x9000)]
    calls = {0x100: {0x200, 0x9000}, 0x200: {0x300}}
    chosen = nep.select_bodies(fdes, 0x100, 1, (0x100, 0x400), lambda address: calls.get(address, set()))
    assert [f.start for f in chosen] == [0x100, 0x200]
    deeper = nep.select_bodies(fdes, 0x100, 2, (0x100, 0x400), lambda address: calls.get(address, set()))
    assert [f.start for f in deeper] == [0x100, 0x200, 0x300]


def test_body_bounds_rejects_an_address_that_starts_no_body():
    with pytest.raises(nep.ProbeError, match="no .eh_frame body"):
        nep.body_bounds([fde(0x100)], 0x104)


def test_stub_source_defines_one_stub_per_unlifted_callee():
    source = nep.stub_source([0x2056710, 0x20563D0])
    assert source.count("stub_hit(") == 3
    assert 'sub_20563d0(unsigned char *reg) { (void)reg; stub_hit("sub_20563d0"); }' in source
