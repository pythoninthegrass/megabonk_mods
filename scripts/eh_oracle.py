#!/usr/bin/env -S uv run --script
"""Record the class and message a shipped method throws on the Linux runtime.

Runs scripts/native_bind_probe/host.c headless on an SSH host with `--expect-throw`, so a throw
is the expected outcome and its exception class is the reference for lifted code. The report
stays local under .tools/eh-oracle and is bound to the host's platform, a loader-free process
and the method that threw.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOST_SOURCE = REPO / "scripts/native_bind_probe/host.c"
DEFAULT_OUT = REPO / ".tools/eh-oracle"
SAFE = re.compile(r"[A-Za-z0-9_./@:-]+")


class OracleError(Exception):
    pass


@dataclass(frozen=True)
class Oracle:
    image: str
    class_name: str
    method: str


ORACLES = (Oracle("mscorlib.dll", "System.ThrowHelper", "ThrowInvalidOperationException_InvalidOperation_NoValue"),)


def host_command(game_dir: str, oracle: Oracle) -> list[str]:
    return [
        "./host", "--dylib", f"{game_dir}/GameAssembly.so", "--data-dir", f"{game_dir}/Megabonk_Data/il2cpp_data",
        "--leg", "leg2", "--invoke-image", oracle.image, "--invoke-class", oracle.class_name,
        "--invoke-method", oracle.method, "--invoke-ret", "void", "--invoke-expected", "", "--expect-throw",
    ]  # fmt: skip


def parse_report(stdout: str, oracle: Oracle) -> dict:
    line = next((line for line in stdout.splitlines() if line.startswith("#JSON#")), None)
    if line is None:
        raise OracleError("host printed no report")
    report = json.loads(line.removeprefix("#JSON#"))
    if report.get("status") != "pass":
        raise OracleError(f"host failed: {report.get('reason')}")
    evidence = report["evidence"]
    if evidence.get("platform") != "linux" or evidence.get("loader_images") != 0:
        raise OracleError("report is not from a loader-free Linux process")
    if evidence.get("method_name") != oracle.method or evidence.get("invoke_class") != oracle.class_name:
        raise OracleError("report names a different method")
    if not evidence.get("exception_class"):
        raise OracleError("report records no exception class")
    return {key: evidence[key] for key in ("exception_class", "exception_message")}


def capture(host: str, game_dir: str, out: Path) -> dict:
    for value in (host, game_dir):
        if not SAFE.fullmatch(value) or value.startswith("-"):
            raise OracleError(f"unsafe value {value!r}")
    remote = "eh-oracle"

    def ssh(command: str, **kwargs) -> str:
        done = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", host, command], capture_output=True, text=True, timeout=300, **kwargs
        )
        if done.returncode != 0:
            raise OracleError(f"ssh failed ({done.returncode}): {(done.stderr or done.stdout)[-800:]}")
        return done.stdout

    ssh(f"mkdir -p {remote}")
    ssh(f"cat > {remote}/host.c", input=HOST_SOURCE.read_text())
    ssh(f"cd {remote} && cc -O1 -o host host.c -ldl -lm")
    binary = f"{game_dir}/GameAssembly.so"
    digest = ssh(f"sha256sum {shlex.quote(binary)}").split()[0]
    results = {}
    for oracle in ORACLES:
        stdout = ssh(f"cd {remote} && {shlex.join(host_command(game_dir, oracle))}")
        results[f"{oracle.class_name}::{oracle.method}"] = parse_report(stdout, oracle)
    bundle = {"schema": 1, "binary_sha256": digest, "oracles": results}
    out.mkdir(parents=True, exist_ok=True)
    (out / "oracles.json").write_text(json.dumps(bundle, indent=2) + "\n")
    return bundle


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", required=True, help="ssh host running the shipped Linux build")
    ap.add_argument("--linux-game-dir", required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    try:
        bundle = capture(args.host, args.linux_game_dir, args.out)
    except OracleError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(bundle["oracles"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
