#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13,<3.14"
# ///

"""Compare typed arm64 calls into shipped Clamp bodies with the Linux runtime.

Usage:
    uv run scripts/native_call_probe.py [--out .tools/native-calls]
    uv run scripts/native_call_probe.py --capture-linux-host HOST --linux-game-dir DIR

Args:
    --so selects the frozen Linux GameAssembly.so; --candidate-override tests failure.

Note:
    Only two pure shipped Mathf overloads are lifted, with no substituted callees or
    modelled runtime data. Controls, binary identity, pcode cache and build outputs
    stay local. This is a calling-contract probe, not a Unity boot or runtime port.
"""

import argparse
import json
import lift_abi as abi
import lift_probe as lp
import math
import native_exec_probe as ne
import pcode_lift as pl
import re
import shlex
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO / ".tools/native-calls"
ProbeError = ne.ProbeError


@dataclass(frozen=True)
class Case:
    name: str
    kind: str
    values: tuple[str, str, str]
    image: str = "UnityEngine.CoreModule.dll"
    class_name: str = "UnityEngine.Mathf"
    method: str = "Clamp"

    @property
    def return_type(self):
        return "int" if self.kind == "i32" else "float"

    @property
    def arg_kind(self):
        return "i" if self.kind == "i32" else "f"


CASES = tuple(
    Case(f"{kind}_{name}", kind, values)
    for kind in ("i32", "f32")
    for name, values in (("below", ("-2", "1", "3")), ("inside", ("2", "1", "3")), ("above", ("5", "1", "3")))
)


def parse_controls(bundle: dict, digest: str) -> dict:
    if bundle.get("schema") != 1 or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ProbeError("invalid control schema or binary digest")
    if bundle.get("binary_sha256") != digest:
        raise ProbeError("control binary digest differs from local GameAssembly.so")
    parsed = {}
    for case in CASES:
        payload = ne.last_json_line(bundle.get("controls", {}).get(case.name, ""))
        if not payload or payload.get("status") != "pass":
            raise ProbeError(f"{case.name}: missing or failed Linux control")
        evidence = payload.get("evidence", {})
        required = {
            "platform": "linux",
            "arch": "x86_64",
            "loader_images": 0,
            "image": case.image,
            "invoke_class": case.class_name,
            "method_name": case.method,
            "param_count": 3,
            "return_type": case.return_type,
            **{f"arg{i}_kind": f"{case.arg_kind}={v}" for i, v in enumerate(case.values)},
            **{f"param{i}_type": case.return_type for i in range(3)},
        }
        if any(evidence.get(key) != value for key, value in required.items()):
            raise ProbeError(f"{case.name}: control identity, inputs or signature mismatch")
        try:
            rva = int(evidence["method_rva"], 16)
            result = int(evidence["returned"]) if case.kind == "i32" else float(evidence["returned"])
        except (KeyError, ValueError, TypeError) as error:
            raise ProbeError(f"{case.name}: invalid body or result") from error
        if not 0 < rva < 1 << 64 or not math.isfinite(result):
            raise ProbeError(f"{case.name}: invalid body or nonfinite result")
        parsed[case.name] = {"rva": rva, "result": result}
    for kind in ("i32", "f32"):
        if len({parsed[c.name]["rva"] for c in CASES if c.kind == kind}) != 1:
            raise ProbeError(f"{kind}: controls resolve inconsistent bodies")
    return parsed


def compare(controls: dict, candidate: dict, archs: str) -> dict:
    checks = {"native_arm64": candidate.get("arch") == "arm64" and candidate.get("translated") == 0 and archs.strip() == "arm64"}
    for case in CASES:
        checks[case.name] = candidate.get("results", {}).get(case.name) == controls[case.name]["result"]
    return {
        "schema": 1,
        "verdict": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "shipped_controls": controls,
        "arm64": candidate,
    }


def atomic_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as sink:
        temporary = Path(sink.name)
        try:
            json.dump(data, sink, indent=2)
            sink.write("\n")
            sink.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def capture(host: str, game_dir: str, out: Path) -> dict:
    if host.startswith("-"):
        raise ProbeError("invalid SSH host")
    remote = "native-call-probe"

    def ssh(command, **kwargs):
        return ne.run_checked(["ssh", "-o", "BatchMode=yes", host, command], timeout=300, **kwargs).stdout

    ssh(f"mkdir -p {remote}")
    ssh(f"cat > {remote}/host.c", input=ne.HOST_SOURCE.read_text())
    ssh(f"cc -O1 -o {remote}/host {remote}/host.c -ldl -lm")
    binary = f"{game_dir}/GameAssembly.so"
    digest = ssh(f"sha256sum {shlex.quote(binary)}").split()[0]
    controls = {}
    for case in CASES:
        command = [
            f"./{remote}/host",
            "--dylib",
            binary,
            "--data-dir",
            f"{game_dir}/Megabonk_Data/il2cpp_data",
            "--leg",
            "leg2",
            "--invoke-image",
            case.image,
            "--invoke-class",
            case.class_name,
            "--invoke-method",
            case.method,
            "--invoke-ret",
            case.return_type,
            "--invoke-expected",
            "",
        ]
        for value in case.values:
            command += ["--invoke-arg", f"{case.arg_kind}:{value}", "--invoke-arg-type", case.return_type]
        controls[case.name] = ssh(shlex.join(command))
    if ssh(f"sha256sum {shlex.quote(binary)}").split()[0] != digest:
        raise ProbeError("Linux binary changed during capture")
    bundle = {"schema": 1, "binary_sha256": digest, "controls": controls}
    parse_controls(bundle, digest)
    atomic_json(out / "linux-controls.json", bundle)
    return bundle


def harness_source(controls: dict) -> str:
    lines = [
        '#include "adapters.c"',
        "#include <stdio.h>",
        "#include <sys/sysctl.h>",
        "int main(void) {",
        "  int translated = -1;",
        "  size_t size = sizeof translated;",
        '  sysctlbyname("sysctl.proc_translated", &translated, &size, NULL, 0);',
        '#if defined(__aarch64__)',
        '  const char *arch = "arm64";',
        '#else',
        '  const char *arch = "other";',
        '#endif',
        r'  printf("{\"arch\":\"%s\",\"translated\":%d,\"results\":{", arch, translated);',
    ]
    for index, case in enumerate(CASES):
        args = ", ".join(case.values) + ", NULL"
        lines.append(f'  printf("{"," if index else ""}\\"{case.name}\\":%.9g", (double)entry_{case.kind}({args}));')
    lines += [r'  printf("}}\n");', "  return 0;", "}"]
    return "\n".join(lines) + "\n"


def build_and_run(so: Path, controls: dict, out: Path, digest: str) -> tuple[dict, str, dict]:
    fdes = ne.fde_table(so)
    addresses = sorted({row["rva"] for row in controls.values()})
    chosen = [ne.body_bounds(fdes, address) for address in addresses]
    key = lp.cache_key(digest, chosen)
    cache = lp.PcodeCache.load(out / "pcode-cache.jsonl", digest, key, lp.dump_script_fingerprint(), lp.ghidra_version())
    with tempfile.TemporaryDirectory(prefix="native-calls-") as scratch:
        rows, sections = lp.dump_pcode_cached(so, chosen, Path(scratch), cache)
        cache.save()
    if len(rows) != len(chosen) or any(row.get("undecoded", 0) for row in rows):
        raise ProbeError("incomplete pcode decode")
    bodies = [pl.lift_body(row, sections, call_dispatch=True) for row in rows]
    if any(b.holes or b.externs or b.indirect_calls or b.data_sections or b.unmapped_refs for b in bodies):
        raise ProbeError("Clamp body is not a self-contained pure lift; refusing substituted calls or data")
    ir, obj = out / "lifted.ll", out / "lifted.o"
    ir.write_text(pl.module_for(bodies))
    ne.run_checked([lp.LLVM / "opt", "-passes=verify", "-disable-output", ir])
    ne.run_checked([lp.LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", ir, "-o", obj])
    exports = [
        abi.Binding(controls[f"{kind}_below"]["rva"], f"entry_{kind}", abi.Signature((kind,) * 3 + ("ptr",), kind))
        for kind in ("i32", "f32")
    ]
    (out / "adapters.c").write_text(abi.generate(exports, []))
    harness = out / "harness.c"
    harness.write_text(harness_source(controls))
    exe = out / "harness"
    ne.run_checked([ne.CLANG, "-arch", "arm64", "-O1", harness, obj, "-o", exe])
    completed = ne.run_checked([exe], timeout=30)
    (out / "harness-output.json").write_text(completed.stdout)
    archs = ne.run_checked([ne.LIPO, "-archs", exe]).stdout.strip()
    return json.loads(completed.stdout), archs, {"bodies": [b.__dict__ for b in chosen], "cache": cache.summary()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--so", type=Path, default=ne.DEFAULT_SO)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--capture-linux-host")
    parser.add_argument("--linux-game-dir")
    parser.add_argument("--candidate-override", type=int)
    args = parser.parse_args(argv)
    try:
        args.out.mkdir(parents=True, exist_ok=True)
        if args.capture_linux_host:
            if not args.linux_game_dir:
                raise ProbeError("--capture-linux-host requires --linux-game-dir")
            bundle = capture(args.capture_linux_host, args.linux_game_dir, args.out)
        else:
            bundle = json.loads((args.out / "linux-controls.json").read_text())
        digest = ne.sha256(args.so)
        controls = parse_controls(bundle, digest)
        candidate, archs, build = build_and_run(args.so, controls, args.out, digest)
        if args.candidate_override is not None:
            candidate["results"][CASES[0].name] = args.candidate_override
        report = compare(controls, candidate, archs)
        report.update(
            binary_sha256=digest,
            build=build,
            candidate_override=args.candidate_override,
            source="frozen shipped Linux GameAssembly.so; no probe player or substituted runtime state",
        )
        atomic_json(args.out / "report.json", report)
        print(json.dumps({"verdict": report["verdict"], "checks": report["checks"], "report": str(args.out / "report.json")}))
        return 0 if report["verdict"] == "pass" else 1
    except (ProbeError, abi.AbiError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
