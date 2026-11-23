"""Run the shipped IL2CPP runtime gate in a separate, bounded native process."""

import argparse
import hashlib
import json
import math
import native_bind_probe as bind
import os
import platform
import re
import signal
import subprocess
import sys
import tempfile
from contextlib import suppress
from pathlib import Path

REFERENCE_SHA256 = "a86fd434619dafb328ec741b6bc285992ee1f52e69533b2db8f35185c2ed5ba1"
METADATA_SHA256 = "53ca3fd0c07051c949329c03d377efdf7de556f97024cca82748e93ac8bc480e"
REQUIRED_EXPORTS = tuple(
    "il2cpp_" + name
    for name in re.findall(r"\bEXPORT\((\w+)\)", bind.HOST_SOURCE.read_text().split("\n\nstatic int runtime_gate")[0])
)
LADDER = tuple(
    candidate
    for candidate in bind.DEFAULT_CANDIDATES
    if candidate.label.startswith(("mscorlib.dll!System.Math::Abs", "mscorlib.dll!System.String::Concat"))
    or candidate.method == "GetWeaponMaxLevel"
)


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def native_process(evidence, system):
    return evidence.get("platform") == system and (
        evidence.get("arch") == "arm64" and evidence.get("proc_translated") == 0
        if system == "macos"
        else evidence.get("arch") == "x86_64"
    )


def execute_host(argv, work_dir, timeout):
    env = {key: str(work_dir) for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "TMPDIR")}
    with (
        tempfile.TemporaryFile(dir=work_dir) as stdout,
        tempfile.TemporaryFile(dir=work_dir) as stderr,
        subprocess.Popen(
            argv, cwd=work_dir, env=env, stdout=stdout, stderr=stderr, start_new_session=True
        ) as process,
    ):
        timed_out = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        stdout.seek(0)
        stderr.seek(0)
        return process.returncode, timed_out, stdout.read().decode(errors="replace"), stderr.read().decode(errors="replace")


def score_host(returncode, timed_out, stdout, stderr, native_platform):
    payload = bind.parse_host_output(stdout) or {}
    evidence = payload.get("evidence", {})
    phase = "launch"
    exports, missing, assemblies = {}, [], []
    stop = None
    for line in stderr.splitlines():
        if line.startswith("[host] phase="):
            phase = line.split("=", 1)[1]
        elif line.startswith("[host] export="):
            name, offset = line.removeprefix("[host] export=").split(" offset=")
            exports[name] = offset
        elif line.startswith("[host] missing_export="):
            missing.append(line.split("=", 1)[1])
        elif line.startswith("[host] assembly="):
            assemblies.append(line.split("=", 1)[1])
        elif stop is None and line.startswith(("lift_import_refused:", "lift_hole:", "lift_dispatch:")):
            stop = line
    result = {
        "returncode": returncode,
        "process": evidence,
        "phase": phase,
        "exports": exports,
        "missing_exports": missing,
        "assemblies": assemblies,
        "stderr": stderr,
        "reason": payload.get("reason"),
    }
    if stop:
        result["stop"] = stop
    if timed_out:
        status = "host_timeout"
    elif returncode < 0:
        status = "host_signal"
        result["signal"] = signal.Signals(-returncode).name
    elif payload.get("reason") == "dlopen failed":
        status = "image_load_failed"
    elif missing:
        status = "exports_missing"
    elif not native_process(evidence, native_platform):
        status = "native_process_unverified"
    elif returncode or payload.get("status") != "pass" or phase != "complete":
        status = "host_failed"
    else:
        status = "pass"
    return {"status": status, **result}


def run_gate(
    image, reference, metadata, *, expected_image_sha256, work_dir, timeout=15, exports_only=False, linux_reference=False
):
    image, reference, metadata = (path.resolve() for path in (image, reference, metadata))
    identity = {"image": str(image), "reference": str(reference), "metadata": str(metadata)}
    for name, path, expected in (
        ("reference", reference, REFERENCE_SHA256),
        ("metadata", metadata, METADATA_SHA256),
        ("image", image, expected_image_sha256),
    ):
        if not path.is_file():
            return {**identity, "status": f"{name}_missing"}
        actual = identity[f"{name}_sha256"] = sha256(path)
        if actual != expected:
            return {**identity, "status": f"{name}_mismatch", "expected_sha256": expected}
    native_platform, arch = ("linux", "x86_64") if linux_reference else ("macos", "arm64")
    if (sys.platform, platform.machine()) != ("linux" if linux_reference else "darwin", arch):
        return {**identity, "status": "wrong_host_platform"}
    if linux_reference and image != reference:
        return {**identity, "status": "wrong_reference_image"}
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")
    with tempfile.TemporaryDirectory(prefix="il2cpp-gate-", dir=work_dir) as directory:
        work = Path(directory)
        host = work / "native_bind_host_runtime"
        build = bind.build_host_command(bind.HOST_SOURCE, host, arch, native_platform)
        if linux_reference:
            build.remove("-ldl")
            build.append("-ldl")
        subprocess.run(build, check=True, timeout=30)
        staged = work / "input"
        staged.mkdir()
        staged_metadata = staged / "global-metadata.dat"
        staged_metadata.write_bytes(metadata.read_bytes())
        if sha256(staged_metadata) != METADATA_SHA256:
            return {**identity, "status": "metadata_changed"}
        data = bind.stage_data_dir(staged, work / "data")
        results = []
        for candidate in (None,) if exports_only else LADDER:
            if sha256(reference) != REFERENCE_SHA256 or sha256(image) != expected_image_sha256:
                return {**identity, "status": "image_changed", "runs": results}
            leg = "exports" if exports_only else "runtime"
            argv = bind.host_argv(host, dylib=image, data_dir=data, leg=leg, invoke=candidate, dlopen_mode="now")
            result = score_host(*execute_host(argv, work, timeout), native_platform)
            if sha256(image) != expected_image_sha256 or sha256(staged_metadata) != METADATA_SHA256:
                result["status"] = "inputs_changed"
            if exports_only:
                return {**identity, **result}
            result["candidate"] = candidate.label
            results.append(result)
            if result["status"] != "pass":
                break
        return {**identity, **results[-1], "runs": results}


def compare_reference(reference, candidate):
    if (
        reference.get("reference_sha256") != REFERENCE_SHA256
        or reference.get("image_sha256") != REFERENCE_SHA256
        or reference.get("metadata_sha256") != METADATA_SHA256
    ):
        return ["Linux reference identity mismatch"]
    labels = [case.label for case in LADDER]
    for name, system, report in (("Linux reference", "linux", reference), ("macOS candidate", "macos", candidate)):
        runs = report.get("runs", [])
        if report.get("status") != "pass" or [row["candidate"] for row in runs] != labels:
            return [f"{name} did not complete the full ladder"]
        for row in runs:
            evidence = row["process"]
            if (
                row["status"] != "pass"
                or not native_process(evidence, system)
                or evidence.get("shutdown") != 1
                or not evidence.get("returned")
                or not {"mscorlib.dll", "Assembly-CSharp.dll"}.issubset(row["assemblies"])
            ):
                return [f"{name} did not verify {row['candidate']}"]
    return [
        f"{case.label}: got {native['process']['returned']!r}, Linux returned {control['process']['returned']!r}"
        for case, control, native in zip(LADDER, reference["runs"], candidate["runs"], strict=True)
        if not bind.value_matches(case.ret, native["process"]["returned"], control["process"]["returned"])
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--image-sha256", required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--verdict", type=Path, help="lift verdict directory used to build the candidate")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--exports-only", action="store_true")
    parser.add_argument("--linux-reference", action="store_true")
    parser.add_argument("--control", type=Path, help="report from a native Linux reference run")
    args = parser.parse_args()
    if not args.linux_reference and args.verdict is None:
        parser.error("--verdict is required for a rebuilt image")
    if not args.linux_reference and not args.exports_only and args.control is None:
        parser.error("--control is required for the managed ladder")
    args.out.mkdir(parents=True, exist_ok=True)
    report = run_gate(
        args.image,
        args.reference,
        args.metadata,
        expected_image_sha256=args.image_sha256,
        work_dir=args.out.resolve(),
        timeout=args.timeout,
        exports_only=args.exports_only,
        linux_reference=args.linux_reference,
    )
    if args.verdict is not None:
        report["verdict"] = str(args.verdict)
    if args.control is not None and report["status"] == "pass" and not args.exports_only:
        try:
            raw_control = args.control.read_bytes()
            report["control_sha256"] = hashlib.sha256(raw_control).hexdigest()
            control = json.loads(raw_control)
            errors = compare_reference(control, report)
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
            errors = [f"invalid control report: {error}"]
        report["comparison_errors"] = errors
        if errors:
            report["status"] = "reference_comparison_failed"
    report = bind.redact_report(report)
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['status']}: {args.out / 'report.json'}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    def stop(signum, _frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, stop)
    sys.exit(main())
