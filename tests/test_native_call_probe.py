"""The shipped-call oracle must bind input values and overloads to a binary."""

import copy
import json
import native_call_probe as probe
import pytest
from test_lift_abi import requires_arm64


def control(case):
    return "#JSON# " + json.dumps(
        {
            "status": "pass",
            "evidence": {
                "platform": "linux",
                "arch": "x86_64",
                "loader_images": 0,
                "image": case.image,
                "method_name": case.method,
                "method_rva": "0x1234",
                "invoke_class": case.class_name,
                "param_count": len(case.values),
                "return_type": case.return_type,
                "returned": "1",
                **{f"arg{i}_kind": f"{case.arg_kind}={v}" for i, v in enumerate(case.values)},
                **{f"param{i}_type": case.return_type for i in range(len(case.values))},
            },
        }
    )


def bundle():
    return {"schema": 1, "binary_sha256": "a" * 64, "controls": {case.name: control(case) for case in probe.CASES}}


def test_valid_control_bundle_keeps_all_cases():
    parsed = probe.parse_controls(bundle(), "a" * 64)
    assert set(parsed) == {case.name for case in probe.CASES}
    assert all(row["rva"] == 0x1234 for row in parsed.values())


@pytest.mark.parametrize("mutation", ["digest", "missing", "failed", "input", "type", "image", "rva", "nan"])
def test_control_rejects_wrong_identity_inputs_or_signature(mutation):
    data = copy.deepcopy(bundle())
    case = probe.CASES[0]
    payload = json.loads(data["controls"][case.name][7:])
    if mutation == "digest":
        data["binary_sha256"] = "b" * 64
    elif mutation == "missing":
        del data["controls"][case.name]
    elif mutation == "failed":
        payload["status"] = "fail"
    elif mutation == "input":
        payload["evidence"]["arg0_kind"] = "i=999"
    elif mutation == "type":
        payload["evidence"]["param0_type"] = "double"
    elif mutation == "image":
        payload["evidence"]["image"] = "fake.dll"
    elif mutation == "rva":
        payload["evidence"]["method_rva"] = "0x0"
    elif mutation == "nan":
        payload["evidence"]["returned"] = "nan"
    if mutation != "missing":
        data["controls"][case.name] = "#JSON# " + json.dumps(payload)
    with pytest.raises(probe.ProbeError):
        probe.parse_controls(data, "a" * 64)


def test_comparison_requires_every_case_and_native_execution():
    controls = probe.parse_controls(bundle(), "a" * 64)
    candidate = {"arch": "arm64", "translated": 0, "results": {case.name: 1 for case in probe.CASES}}
    assert probe.compare(controls, candidate, "arm64")["verdict"] == "pass"
    candidate["results"][probe.CASES[0].name] = 2
    assert probe.compare(controls, candidate, "arm64")["verdict"] == "fail"
    candidate["results"] = {}
    assert probe.compare(controls, candidate, "arm64")["verdict"] == "fail"
    candidate["results"] = {case.name: 1 for case in probe.CASES}
    candidate["translated"] = 1
    assert probe.compare(controls, candidate, "arm64")["verdict"] == "fail"
    candidate["translated"] = 0
    assert probe.compare(controls, candidate, "x86_64 arm64")["verdict"] == "fail"


@requires_arm64
def test_shipped_clamp_overloads_match_linux_control(tmp_path):
    control_path = probe.DEFAULT_OUT / "linux-controls.json"
    if not probe.ne.DEFAULT_SO.exists() or not control_path.exists():
        pytest.skip("needs local shipped Linux binary and captured native-calls controls")
    source = json.loads(control_path.read_text())
    digest = probe.ne.sha256(probe.ne.DEFAULT_SO)
    controls = probe.parse_controls(source, digest)
    cache_path = probe.DEFAULT_OUT / "pcode-cache.jsonl"
    if cache_path.exists():
        (tmp_path / "pcode-cache.jsonl").write_bytes(cache_path.read_bytes())
    candidate, archs, build = probe.build_and_run(probe.ne.DEFAULT_SO, controls, tmp_path, digest)
    report = probe.compare(controls, candidate, archs)
    assert report["verdict"] == "pass", report
    assert len(build["bodies"]) == 2
    candidate["results"][probe.CASES[0].name] = 999
    assert probe.compare(controls, candidate, archs)["verdict"] == "fail"
