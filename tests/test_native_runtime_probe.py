import hashlib
import os
import platform
import pytest
import signal
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import native_runtime_probe as probe


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    reference = tmp_path / "GameAssembly.so"
    reference.write_bytes(b"reference")
    metadata = tmp_path / "global-metadata.dat"
    metadata.write_bytes(b"metadata")
    monkeypatch.setattr(probe, "REFERENCE_SHA256", hashlib.sha256(b"reference").hexdigest())
    monkeypatch.setattr(probe, "METADATA_SHA256", hashlib.sha256(b"metadata").hexdigest())
    return reference, metadata


def fixture_image(tmp_path, source):
    if sys.platform != "darwin" or platform.machine() != "arm64":
        pytest.skip("requires native macOS arm64")
    c_file = tmp_path / "fixture.c"
    c_file.write_text(source)
    image = tmp_path / "fixture.dylib"
    subprocess.run(
        ["/usr/bin/clang", "-arch", "arm64", "-dynamiclib", str(c_file), "-o", str(image)],
        check=True,
        timeout=30,
    )
    return image


def run(tmp_path, inputs, image, *, exports_only=False, timeout=3):
    return probe.run_gate(
        image,
        *inputs,
        expected_image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
        work_dir=tmp_path,
        timeout=timeout,
        exports_only=exports_only,
    )


def assert_host_reaped(result):
    with pytest.raises(ProcessLookupError):
        os.killpg(result["process"]["pid"], 0)


@pytest.mark.parametrize("missing", [True, False])
def test_bad_metadata_stops_before_launch(tmp_path, inputs, missing):
    reference, metadata = inputs
    if missing:
        metadata.unlink()
    else:
        metadata.write_bytes(b"wrong metadata")
    result = run(tmp_path, inputs, reference)
    assert result["status"] == ("metadata_missing" if missing else "metadata_mismatch")
    assert "process" not in result


def test_truncated_image_has_loader_diagnostic(tmp_path, inputs):
    if sys.platform != "darwin" or platform.machine() != "arm64":
        pytest.skip("requires native macOS arm64")
    image = tmp_path / "truncated.dylib"
    image.write_bytes(b"\xcf\xfa\xed\xfe")
    result = run(tmp_path, inputs, image)
    assert result["status"] == "image_load_failed"
    assert result["phase"] == "dlopen"
    assert result["stderr"]
    assert result["process"]["arch"] == "arm64"
    assert result["process"]["proc_translated"] == 0
    assert_host_reaped(result)


def dummy_exports(except_names=()):
    return "\n".join(f"void {name}(void) {{}}" for name in probe.REQUIRED_EXPORTS if name not in except_names)


def test_missing_export_is_fatal_before_initialization(tmp_path, inputs):
    missing = "il2cpp_runtime_invoke"
    image = fixture_image(tmp_path, dummy_exports((missing,)))
    result = run(tmp_path, inputs, image, exports_only=True)
    assert result["status"] == "exports_missing"
    assert result["missing_exports"] == [missing]
    assert set(result["exports"]) == set(probe.REQUIRED_EXPORTS) - {missing}
    assert_host_reaped(result)


def test_startup_abort_preserves_named_diagnostic_and_reaps_host(tmp_path, inputs):
    image = fixture_image(
        tmp_path,
        dummy_exports(("il2cpp_init",))
        + """
#include <stdio.h>
#include <stdlib.h>
int il2cpp_init(const char *name) {
    fputs("lift_import_refused: fixture_service: unavailable\\n", stderr);
    abort();
}
""",
    )
    result = run(tmp_path, inputs, image)
    assert result["status"] == "host_signal"
    assert result["phase"] == "il2cpp_init"
    assert result["signal"] == "SIGABRT"
    assert result["stop"] == "lift_import_refused: fixture_service: unavailable"
    assert_host_reaped(result)


def test_timeout_kills_host_and_helper(tmp_path, inputs):
    image = fixture_image(
        tmp_path,
        dummy_exports(("il2cpp_init",))
        + """
#include <stdio.h>
#include <unistd.h>
int il2cpp_init(const char *name) {
    int helper = fork();
    if (helper > 0) fprintf(stderr, "helper=%d\\n", helper);
    for (;;) pause();
}
""",
    )
    result = run(tmp_path, inputs, image, timeout=5)
    assert result["status"] == "host_timeout"
    assert result["phase"] == "il2cpp_init"
    child = result["stderr"].split("helper=")[1].splitlines()[0]
    listing = subprocess.run(["/bin/ps", "-p", child, "-o", "stat="], capture_output=True, text=True, timeout=5)
    assert not listing.stdout.strip() or listing.stdout.strip().startswith("Z")
    assert result["returncode"] == -signal.SIGKILL


def passing_report(system, arch):
    return {
        "status": "pass",
        "reference_sha256": probe.REFERENCE_SHA256,
        "image_sha256": probe.REFERENCE_SHA256,
        "metadata_sha256": probe.METADATA_SHA256,
        "runs": [
            {
                "status": "pass",
                "candidate": case.label,
                "assemblies": ["mscorlib.dll", "Assembly-CSharp.dll"],
                "process": {
                    "platform": system,
                    "arch": arch,
                    "proc_translated": 0,
                    "returned": value,
                    "shutdown": 1,
                },
            }
            for case, value in zip(probe.LADDER, ("7", "megabonk", "40"), strict=True)
        ],
    }


def test_comparison_requires_the_pinned_complete_ladder():
    reference = passing_report("linux", "x86_64")
    candidate = passing_report("macos", "arm64")
    assert probe.compare_reference(reference, candidate) == []
    candidate["runs"][-1]["process"]["returned"] = "41"
    assert "GetWeaponMaxLevel" in probe.compare_reference(reference, candidate)[0]
    reference["metadata_sha256"] = "wrong"
    assert probe.compare_reference(reference, candidate) == ["Linux reference identity mismatch"]


def test_comparison_rejects_partial_reference():
    reference = passing_report("linux", "x86_64")
    reference["runs"].pop()
    assert probe.compare_reference(reference, passing_report("macos", "arm64")) == [
        "Linux reference did not complete the full ladder"
    ]


def test_comparison_rejects_translated_candidate():
    candidate = passing_report("macos", "arm64")
    candidate["runs"][0]["process"]["proc_translated"] = 1
    assert probe.compare_reference(passing_report("linux", "x86_64"), candidate) == [
        "macOS candidate did not verify " + probe.LADDER[0].label
    ]
