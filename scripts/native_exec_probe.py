#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# ///

"""
Executes one lifted shipped game method natively on arm64 and compares it with the shipped Linux runtime.

The lift probe shows sampled bodies verify and compile; this is the first time a real shipped body
runs. The target is InventoryUtility.GetWeaponMaxLevel in the Linux GameAssembly.so. Its identity
comes from the shipped runtime itself: the Linux control starts the Il2Cpp runtime headless through
its exported C API, looks the method up by name, and reports the body's RVA, the value
il2cpp_runtime_invoke returns, and the three words of runtime state the body reads. The body is then
lifted from that same ELF (Ghidra pcode through scripts/pcode_lift.py), compiled for arm64, linked
into a small host and run on this machine. The two results are compared automatically.

Usage:
    uv run --script scripts/native_exec_probe.py [--linux-control <raw host output>] [options]
    uv run --script scripts/native_exec_probe.py --capture-linux-host <ssh host> [options]

Note:
    The lifted body reads runtime state (an init guard, the class's init flag and a static field), so
    the host models exactly that state and the Linux control observes the same three words; a
    mismatch fails the run. Every other call the lifted code can make is a stub that fails the run
    if reached. --candidate-override replaces the arm64 result before comparison and must fail. See
    "Executing a lifted shipped method" in docs/development.md.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lift_probe  # noqa: E402
import pcode_lift  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DEFAULT_SO = lift_probe.DEFAULT_SO
DEFAULT_OUT = REPO / ".tools/native-exec"
HARNESS_SOURCE = Path(__file__).resolve().parent / "native_exec_probe" / "harness.c"
HOST_SOURCE = Path(__file__).resolve().parent / "native_bind_probe" / "host.c"
CLANG = Path("/usr/bin/clang")
LIPO = Path("/usr/bin/lipo")
SSH = Path("/usr/bin/ssh")
IL2CPP_SECTION = "il2cpp"
JSON_MARKER = "#JSON# "
SCHEMA = 1
SHIPPED_SOURCE = "frozen shipped Linux GameAssembly.so run through the il2cpp C API"
HEX_DIGEST = re.compile(r"[0-9a-f]{64}")


class ProbeError(Exception):
    pass


@dataclass(frozen=True)
class Target:
    image: str
    namespace: str
    class_name: str
    method: str
    ret: str

    @property
    def qualified(self) -> str:
        return f"{self.namespace}.{self.class_name}"

    @property
    def short(self) -> str:
        return f"{self.class_name}.{self.method}"


TARGET = Target("Assembly-CSharp.dll", "Assets.Scripts.Inventory__Items__Pickups", "InventoryUtility", "GetWeaponMaxLevel", "int")
# Addresses the body reads, as ELF virtual addresses (the image base is zero): the init guard byte in .bss and the class's slot in .got.
GUARD_VA = 0x5357B2C
CLASS_SLOT_VA = 0x506CAB0
STATE_CHAINS = (f"{GUARD_VA:x}", f"{CLASS_SLOT_VA:x}:0,e4", f"{CLASS_SLOT_VA:x}:0,b8,8")


@dataclass(frozen=True)
class Control:
    image: str
    method: str
    rva: int
    returned: int
    state: dict[str, bool]


@dataclass(frozen=True)
class HarnessRun:
    arch: str
    proc_translated: int
    rva: int
    result: int | None
    stubs_reached: list[str]
    state: dict[str, bool]
    result_overridden: bool = False


def last_json_line(text: str) -> dict | None:
    payload = None
    for line in text.splitlines():
        if line.startswith(JSON_MARKER):
            try:
                payload = json.loads(line[len(JSON_MARKER) :])
            except json.JSONDecodeError:
                continue
    return payload


def parse_hex(value: object, field: str) -> int:
    try:
        return int(str(value), 16)
    except ValueError as exc:
        raise ProbeError(f"{field} is not a hex address: {value!r}") from exc


def state_words(evidence: dict, key: str) -> list[int]:
    if key not in evidence:
        raise ProbeError(f"control report has no {key}: rerun the control with the state chains")
    tokens = str(evidence[key]).split(",")
    if "stopped-at-null" in tokens:
        raise ProbeError(f"{key} ended at a null pointer before the last word: {evidence[key]}")
    return [parse_hex(token, key) for token in tokens]


def parse_control(text: str) -> Control:
    payload = last_json_line(text)
    if payload is None:
        raise ProbeError("no host report in the control output")
    if payload.get("status") != "pass":
        raise ProbeError(f"control run did not pass: {payload.get('reason') or payload.get('status')}")
    evidence = payload.get("evidence", {})
    if evidence.get("platform") != "linux":
        raise ProbeError("control is not the shipped Linux runtime")
    if "method_rva" not in evidence:
        raise ProbeError("control report has no method_rva")
    rva = parse_hex(evidence["method_rva"], "method_rva")
    try:
        returned = int(evidence["returned"])
    except (KeyError, ValueError) as exc:
        raise ProbeError(f"control returned is not an integer: {evidence.get('returned')!r}") from exc
    guard, initialised, instance = (state_words(evidence, f"state{i}") for i in range(3))
    state = {
        "guard_set": guard[0] & 0xFF != 0,
        "class_initialised": initialised[-1] & 0xFFFFFFFF != 0,
        "instance_null": instance[-1] == 0,
    }
    return Control(evidence.get("image", ""), evidence.get("method_name", ""), rva, returned, state)


def parse_harness(text: str) -> HarnessRun:
    payload = last_json_line(text)
    if payload is None:
        raise ProbeError("no harness report in the harness output")
    return HarnessRun(
        arch=payload["arch"],
        proc_translated=payload["proc_translated"],
        rva=parse_hex(payload["rva"], "rva"),
        result=payload.get("result"),
        stubs_reached=list(payload.get("stubs_reached", [])),
        state=dict(payload.get("state", {})),
    )


def apply_result_override(run: HarnessRun, value: int) -> HarnessRun:
    return replace(run, result=value, result_overridden=True)


def check(name: str, passed: bool, detail: str) -> dict:
    return {"name": name, "passed": passed, "detail": detail}


def build_report(
    control: Control, run: HarnessRun, *, binary_sha256: str, target: Target = TARGET, executable_archs: str | None = None
) -> dict:
    checks = [
        check("result_matches", run.result == control.returned, f"arm64 {run.result}, shipped Linux {control.returned}"),
        check(
            "body_identity",
            run.rva == control.rva and control.method == target.method and control.image == target.image,
            f"lifted body {run.rva:#x}, shipped Linux {control.rva:#x} ({control.image} {control.method})",
        ),
        check("binary_identity", bool(HEX_DIGEST.fullmatch(binary_sha256)), f"GameAssembly.so sha256 {binary_sha256}"),
        check(
            "native_arm64",
            run.arch == "arm64" and run.proc_translated == 0,
            f"arch {run.arch}, sysctl.proc_translated {run.proc_translated}",
        ),
        check(
            "no_unmodelled_calls",
            not run.stubs_reached,
            "no stubbed callee was reached" if not run.stubs_reached else f"reached {', '.join(run.stubs_reached)}",
        ),
        check("state_matches", run.state == control.state, f"modelled {run.state}, observed on Linux {control.state}"),
    ]
    return {
        "schema": SCHEMA,
        "verdict": "pass" if all(c["passed"] for c in checks) else "fail",
        "candidate": {
            "method": target.short,
            "image": target.image,
            "rva": f"{run.rva:#x}",
            "result": run.result,
            "result_overridden": run.result_overridden,
        },
        "checks": checks,
        "evidence": {
            "shipped_game": {
                "source": SHIPPED_SOURCE,
                "binary_sha256": binary_sha256,
                "image": control.image,
                "method": control.method,
                "rva": f"{control.rva:#x}",
                "result": control.returned,
                "observed_state": control.state,
            },
            "lifted_arm64_harness": {
                "arch": run.arch,
                "proc_translated": run.proc_translated,
                "executable_archs": executable_archs,
                "result": run.result,
                "stubs_reached": run.stubs_reached,
                "modelled_state": run.state,
            },
            "probe_player": None,
        },
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fde_table(so: Path) -> list[lift_probe.Fde]:
    dump = lift_probe.run_tool([lift_probe.LLVM / "llvm-dwarfdump", "--eh-frame", so], text=True).stdout
    return lift_probe.parse_fdes(dump)


def body_bounds(fdes: list[lift_probe.Fde], address: int) -> lift_probe.Fde:
    for fde in fdes:
        if fde.start == address:
            return fde
    raise ProbeError(f"no .eh_frame body starts at {address:#x}")


def select_bodies(
    fdes: list[lift_probe.Fde], entry: int, depth: int, window: tuple[int, int], externs_of
) -> list[lift_probe.Fde]:
    """The entry body plus callees within `depth` calls that live in the game-code section."""
    chosen = {entry: body_bounds(fdes, entry)}
    frontier = [entry]
    for _ in range(depth):
        callees = {a for body in frontier for a in externs_of(body)}
        frontier = [a for a in sorted(callees) if window[0] <= a < window[1] and a not in chosen]
        for address in frontier:
            chosen[address] = body_bounds(fdes, address)
    return list(chosen.values())


def stub_source(addresses: list[int]) -> str:
    lines = ["extern void stub_hit(const char *name);"]
    lines += [f'void sub_{a:x}(unsigned char *reg) {{ (void)reg; stub_hit("sub_{a:x}"); }}' for a in sorted(addresses)]
    return "\n".join(lines) + "\n"


def section_named(sections: list[dict], name: str) -> dict:
    for section in sections:
        if section["name"] == name:
            return section
    raise ProbeError(f"ELF section {name} not found")


def run_checked(command: list, **kwargs) -> subprocess.CompletedProcess:
    completed = subprocess.run([str(c) for c in command], capture_output=True, text=True, **kwargs)
    if completed.returncode != 0:
        raise ProbeError(
            f"{Path(str(command[0])).name} failed ({completed.returncode}): {(completed.stderr or completed.stdout)[-1500:]}"
        )
    return completed


def lift_and_build(so: Path, control: Control, work: Path, depth: int) -> tuple[Path, dict]:
    """Lifts the control's body (and callees within `depth`), compiles for arm64 and links the host."""
    fdes = fde_table(so)
    readelf = lift_probe.run_tool([lift_probe.LLVM / "llvm-readelf", "-S", so], text=True).stdout
    window = lift_probe.parse_exec_sections(readelf)[IL2CPP_SECTION]
    entry = body_bounds(fdes, control.rva)
    (work / "entry").mkdir()
    rows, sections = lift_probe.dump_pcode(so, [entry], work / "entry")
    lifted = {control.rva: pcode_lift.lift_body(rows[0], sections)}

    def externs_of(address: int) -> set[int]:
        return lifted[address].externs

    chosen = select_bodies(fdes, control.rva, depth, window, externs_of) if depth else [entry]
    pending = [b for b in chosen if b.start not in lifted]
    if pending:
        (work / "callees").mkdir()
        more_rows, _ = lift_probe.dump_pcode(so, pending, work / "callees")
        lifted.update({row["start"]: pcode_lift.lift_body(row, sections) for row in more_rows})
        chosen = select_bodies(fdes, control.rva, depth, window, externs_of)
    bodies = [lifted[b.start] for b in chosen]
    holes = {hex(b.start): b.holes for b in bodies if b.holes}
    if holes:
        raise ProbeError(f"lifted bodies carry holes: {holes}")
    ir_path, obj_path = work / "lifted.ll", work / "lifted.o"
    module = pcode_lift.module_for(bodies)
    ir_path.write_text(module)
    run_checked([lift_probe.LLVM / "opt", "-passes=verify", "-disable-output", ir_path])
    run_checked([lift_probe.LLVM / "llc", "-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", obj_path, ir_path])
    defined = {b.start for b in bodies}
    stubbed = sorted(set().union(*(b.externs for b in bodies)) - defined)
    stubs_path = work / "stubs.c"
    stubs_path.write_text(stub_source(stubbed))
    bss, got = section_named(sections, "_bss"), section_named(sections, "_got")
    exe = work / "harness"
    run_checked(
        [
            CLANG,
            "-arch",
            "arm64",
            "-O1",
            f"-DENTRY_SYM=sub_{control.rva:x}",
            f"-DENTRY_RVA={control.rva:#x}ULL",
            f"-DBSS_SIZE={bss['size']}",
            f"-DGOT_SIZE={got['size']}",
            f"-DGUARD_OFFSET={GUARD_VA - bss['va']}",
            f"-DSLOT_OFFSET={CLASS_SLOT_VA - got['va']}",
            "-o",
            exe,
            HARNESS_SOURCE,
            stubs_path,
            obj_path,
        ]
    )
    summary = {
        "lifted_bodies": [{"rva": f"{b.start:#x}", "size": b.size} for b in chosen],
        "stubbed_callees": [f"{a:#x}" for a in stubbed],
        "ir_sha256": hashlib.sha256(module.encode()).hexdigest(),
    }
    return exe, summary


def capture_linux_control(host: str, game_dir: str, raw_out: Path) -> None:
    """Runs the shipped Linux runtime headless on `host` and stores the host's raw report."""
    for value in (host, game_dir):
        if not re.fullmatch(r"[A-Za-z0-9_./@:-]+", value):
            raise ProbeError(f"unsafe value {value!r}")
    remote_dir = "native-exec"
    run_checked([SSH, host, f"mkdir -p {remote_dir}"])
    run_checked([SSH, host, f"cat > {remote_dir}/host.c"], input=HOST_SOURCE.read_text())
    run_checked([SSH, host, f"cd {remote_dir} && cc -O1 -o host host.c -ldl -lm"])
    chains = " ".join(f"--state-chain {chain}" for chain in STATE_CHAINS)
    command = (
        f"cd {remote_dir} && ./host --dylib {game_dir}/GameAssembly.so --data-dir {game_dir}/Megabonk_Data/il2cpp_data "
        f"--leg leg2 --invoke-image {TARGET.image} --invoke-class {TARGET.qualified} --invoke-method {TARGET.method} "
        f"--invoke-ret {TARGET.ret} --invoke-expected '' {chains}"
    )
    completed = subprocess.run([str(SSH), host, command], capture_output=True, text=True, timeout=300)
    raw_out.parent.mkdir(parents=True, exist_ok=True)
    raw_out.write_text(completed.stdout)
    if completed.returncode != 0:
        raise ProbeError(f"Linux control exited {completed.returncode}: {completed.stderr[-800:]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--so", type=Path, default=DEFAULT_SO, help="the shipped Linux GameAssembly.so to lift from")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--linux-control", type=Path, help="raw host output from the shipped Linux runtime (default: <out>/linux-control.raw)"
    )
    parser.add_argument("--capture-linux-host", help="ssh host running the shipped Linux build; captures a fresh control first")
    parser.add_argument(
        "--linux-game-dir", help="shipped Linux build directory on that host (required with --capture-linux-host)"
    )
    parser.add_argument("--depth", type=int, default=1, help="callee levels lifted with the entry body; the rest are stubs")
    parser.add_argument("--candidate-override", type=int, help="replace the arm64 result before comparing; the run must fail")
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    control_path = args.linux_control or args.out / "linux-control.raw"
    try:
        if args.capture_linux_host:
            if not args.linux_game_dir:
                raise ProbeError("--capture-linux-host needs --linux-game-dir")
            capture_linux_control(args.capture_linux_host, args.linux_game_dir, control_path)
        if not args.so.exists():
            raise ProbeError(f"no ELF at {args.so}")
        if not control_path.exists():
            raise ProbeError(f"no Linux control at {control_path}; pass --capture-linux-host")
        control = parse_control(control_path.read_text())
        kept = args.out / "run"
        shutil.rmtree(kept, ignore_errors=True)
        # Ghidra refuses a project path with a dot-prefixed element, so build outside the repo's .tools directory.
        with tempfile.TemporaryDirectory(prefix="native-exec-") as scratch:
            work = Path(scratch)
            exe, build = lift_and_build(args.so, control, work, args.depth)
            completed = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
            (work / "harness-output.txt").write_text(completed.stdout + completed.stderr)
            archs = run_checked([LIPO, "-archs", exe]).stdout.strip()
            shutil.copytree(work, kept, ignore=shutil.ignore_patterns("ghidra"))
        run = parse_harness(completed.stdout)
        if args.candidate_override is not None:
            run = apply_result_override(run, args.candidate_override)
        report = build_report(control, run, binary_sha256=sha256(args.so), executable_archs=archs)
        report["build"] = build
    except ProbeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "checks": {c["name"]: c["passed"] for c in report["checks"]},
                "report": str(args.out / "report.json"),
            }
        )
    )
    return 0 if report["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
