#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# ///

"""
Scores whether a standalone native host can bind an Il2Cpp runtime by exported symbol.

Route B re-hosts the shipped x86-64 Il2Cpp game code on macOS, and both of its shapes need one
primitive: a native host that reaches the runtime through its exported C API instead of through a
mod loader. The loader probe measured the loader half and stopped at a native detour crash, so this
probe takes the loader out of the process entirely. It compiles scripts/native_bind_probe/host.c,
runs it against a GameAssembly dylib or so, and scores three legs:

    leg1  dlopen plus exported-symbol calls (il2cpp_domain_get, il2cpp_method_get_name), with the
          process's own loaded-image list as proof no doorstop, BepInEx, Dobby or CoreCLR is present
    leg2  a static method chosen from dump.cs, reached by name through class handle, method lookup
          and il2cpp_runtime_invoke, printing the returned value
    leg3  a self-authored detour: an mmap'd trampoline replaying the target's own prologue, plus an
          mprotect'd absolute jump to a counting hook, then proof the patched export still returns
          correct values

Every leg runs in its own child process, so a crash costs one candidate rather than the whole run.
Each leg is scored pass, fail, crash or skipped with the evidence the host printed, which makes the
answer a measurement rather than an inference. Machine identifiers are redacted from everything
recorded, including the report.

Usage:
    uv run --script scripts/native_bind_probe.py --app <ProbePlayer.app> [options]
    uv run --script scripts/native_bind_probe.py --dylib <GameAssembly.so> --metadata <dir> [options]
    uv run --script scripts/native_bind_probe.py --linux-target x86_64 --linux-host <host> \
        --dylib <GameAssembly.so> --metadata <dir>

Note:
    --app expects a Unity IL2CPP macOS player bundle; the runtime is read from
    Contents/Frameworks/GameAssembly.dylib and the metadata from
    Contents/Resources/Data/il2cpp_data/Metadata. Il2Cpp exports only il2cpp_set_data_dir, so the
    metadata directory is staged behind both layouts libil2cpp spells (Metadata/ and
    il2cpp_data/Metadata/) by symlink. --arch x86_64 is the route B case, which runs that slice
    under Rosetta; --arch both adds the arm64 native control so a hooking failure can be attributed
    to Rosetta rather than to macOS. --linux-target runs legs 1 and 2 against the shipped native
    Linux build on a remote host as the control: same host source, real shipped game code. Any
    player started for a control run is headless (-batchmode -nographics -logFile) and stopped with
    SIGTERM only. Artifacts and summary.json land under --out.
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from pathlib import Path

SCHEMA = 1
PROBE_VERSION = "1"
JSON_MARKER = "#JSON# "
LEGS = ("leg1", "leg2", "leg3")
LEG_STATUS_ORDER = ("pass", "fail", "crash", "skipped", "not-run")
HOST_SOURCE = Path(__file__).resolve().parent / "native_bind_probe" / "host.c"
CLANG_MACOS = Path("/usr/bin/clang")
CLANG_LINUX = Path("/usr/bin/cc")
STRINGS = Path("/usr/bin/strings")
SSH = Path("/usr/bin/ssh")
RSYNC = Path("/usr/bin/rsync")
DOCKER = Path("/usr/bin/docker")
LOADER_MARKERS = (
    "doorstop",
    "bepinex",
    "dobby",
    "coreclr",
    "clrjit",
    "il2cppinterop",
    "0harmony",
    "melonloader",
    "funchook",
)
HOOKABLE_SYMBOLS = (
    "il2cpp_runtime_invoke",
    "il2cpp_method_get_name",
    "il2cpp_class_get_method_from_name",
    "il2cpp_domain_get",
)
VOID_RETURNING_HOOKS = frozenset(
    {
        "il2cpp_add_internal_call",
        "il2cpp_init",
        "il2cpp_set_data_dir",
        "il2cpp_thread_detach",
        "il2cpp_domain_unload_thread",
    }
)
THUNK_PROLOGUE = bytes([0x55, 0x48, 0x89, 0xE5, 0x58])
THUNK_PROLOGUE_RBP = bytes([0x55, 0x48, 0x89, 0xE5, 0x5D])
THUNK_PROLOGUES = (THUNK_PROLOGUE, THUNK_PROLOGUE_RBP)
THUNK_PROLOGUE_LEN = 5
THUNK_SLOT_BYTES = 16
DLOPEN_MODES = ("now", "lazy", "lazy_global")
TYPE_NAMES = {
    "System.Int32": "int",
    "Int32": "int",
    "System.Int64": "long",
    "Int64": "long",
    "System.Int16": "short",
    "Int16": "short",
    "System.Byte": "byte",
    "Byte": "byte",
    "System.UInt32": "uint",
    "UInt32": "uint",
    "System.Single": "float",
    "Single": "float",
    "System.Double": "double",
    "Double": "double",
    "System.Boolean": "bool",
    "Boolean": "bool",
    "System.String": "string",
    "String": "string",
    "System.Object": "object",
    "Object": "object",
    "System.Char": "char",
    "Char": "char",
}
ABSOLUTE_JUMP = bytes([0xFF, 0x25, 0x00, 0x00, 0x00, 0x00])
ARG_KINDS = {
    "int": "i",
    "long": "i",
    "short": "i",
    "byte": "i",
    "uint": "i",
    "System.Int32": "i",
    "float": "f",
    "double": "f",
    "System.Single": "f",
    "bool": "b",
    "System.Boolean": "b",
}
UNSAFE_CHARS = re.compile(r"[;&|`$<>\n\r\x00]")
SAFE_HOST = re.compile(r"^[-\w]+$")
REMOTE_DENY = re.compile(
    r"\b(rm\s+-[a-zA-Z]*r|sudo|mkfs|dd\s+if=|curl|wget|shutdown|reboot|chmod\s+-R|chown\s+-R|find\b.*-delete)\b"
)
CRASH_NOISE = re.compile(r"Assertion failed|IL2CPP|Fatal error|fatal|abort\(\)|error:", re.IGNORECASE)
NAMESPACE_LINE = re.compile(r"^// Namespace:\s*(.*)$")
CLASS_LINE = re.compile(
    r"^(?:public|internal)\s+(?:(?:static|sealed|abstract|partial|readonly|ref|nested)\s+)*"
    r"(?:class|struct|interface|enum)\s+([A-Za-z_0-9`.+<>]+)"
)
METHOD_LINE = re.compile(
    r"^\s*public static (?P<ret>[A-Za-z_0-9.<>\[\]]+) (?P<name>[A-Za-z_0-9_.]+)\((?P<params>[^)]*)\) \{ \}$"
)
RVA_LINE = re.compile(r"// RVA: (0x[0-9A-Fa-f]+)")
REDACTIONS = (
    (re.compile(r"/(?:Users|home)/[^/\s]+"), "<home>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "<ip>"),
    (re.compile(r"\b[-\w.]+\.(?:local|lan|ts\.net|home\.invalid)\b"), "<host>"),
)
ALLOWED_BINS = frozenset(
    {
        "clang",
        "cc",
        "gcc",
        "strings",
        "file",
        "nm",
        "rsync",
        "ssh",
        "docker",
        "sysctl",
        "sw_vers",
        "uname",
        "arch",
        "true",
    }
)
ALLOWED_PREFIXES = ("native_bind_host_",)
ALLOWED_FLAGS = {
    "clang": frozenset({"-arch", "-O0", "-g", "-Wall", "-Werror", "-std=c11", "-o", "-ldl", "-lm", "-framework"}),
    "cc": frozenset({"-arch", "-O0", "-g", "-Wall", "-Werror", "-std=c11", "-o", "-ldl", "-lm", "-framework"}),
    "gcc": frozenset({"-arch", "-O0", "-g", "-Wall", "-Werror", "-std=c11", "-o", "-ldl", "-lm", "-framework"}),
    "strings": frozenset({"-a", "-arch"}),
    "file": frozenset(),
    "nm": frozenset({"-gU", "--defined-only", "-U"}),
    "rsync": frozenset({"-a", "-z", "--exclude", "--delete-excluded", "-e"}),
    "ssh": frozenset({"-n", "-T", "-p", "-i"}),
    "docker": frozenset({"-f", "--format"}),
    "sysctl": frozenset(),
    "sw_vers": frozenset({"-productVersion"}),
    "uname": frozenset({"-sm"}),
    "arch": frozenset({"-arch", "-arch x86_64", "-x86_64", "-arm64"}),
    "true": frozenset(),
}


@dataclass(frozen=True)
class Candidate:
    """One static method from dump.cs to reach by name and invoke."""

    image: str
    namespace: str
    class_name: str
    method: str
    ret: str
    param_types: tuple[str, ...]
    args: tuple[str, ...]
    expected: str
    dylib: str = ""

    @property
    def qualified(self) -> str:
        return f"{self.namespace}.{self.class_name}" if self.namespace else self.class_name

    @property
    def label(self) -> str:
        return f"{self.image}!{self.qualified}::{self.method}({','.join(self.param_types)})"

    @property
    def invoke_class(self) -> str:
        return self.qualified

    @property
    def invoke_method(self) -> str:
        return self.method

    @property
    def invoke_ret(self) -> str:
        return self.ret

    @property
    def invoke_expected(self) -> str:
        return self.expected

    @property
    def invoke_args(self) -> tuple[str, ...]:
        return tuple(
            f"{ARG_KINDS.get(type_, 's')}:{value}"
            for type_, value in zip(self.param_types, self.args)
        )


DEFAULT_CANDIDATES = (
    Candidate("mscorlib.dll", "System", "Math", "Abs", "int", ("int",), ("-7",), "7"),
    Candidate("mscorlib.dll", "System", "BitConverter", "SingleToInt32Bits", "int", ("float",), ("1.0",), "1065353216"),
    Candidate("mscorlib.dll", "System", "Int32", "Parse", "int", ("string",), ("1234",), "1234"),
    Candidate("mscorlib.dll", "System", "Convert", "ToInt32", "int", ("float",), ("3.7",), "4"),
    Candidate("mscorlib.dll", "System", "String", "Concat", "string", ("string", "string"), ("mega", "bonk"), "megabonk"),
    Candidate("UnityEngine.CoreModule.dll", "UnityEngine", "Mathf", "Abs", "int", ("int",), ("-5",), "5"),
    Candidate("Rewired_Core.dll", "Rewired.Utils", "MathTools", "Abs", "int", ("int",), ("-42",), "42"),
    Candidate("Assembly-CSharp.dll", "Assets.Scripts.Inventory__Items__Pickups", "InventoryUtility", "GetWeaponMaxLevel", "int", (), (), ""),
    Candidate("Assembly-CSharp.dll", "", "ExplorerUtility", "IsLinux", "bool", (), (), ""),
    Candidate("Assembly-CSharp.dll", "Assets.Scripts.Managers", "MapController", "GetStageIndex", "int", (), (), ""),
)


class ProbeError(Exception):
    pass


@dataclass(frozen=True)
class Paths:
    """Inputs and destinations for one probe run."""

    dylib: Path
    metadata_dir: Path
    data_dir: Path
    out_dir: Path
    bundle: Path | None = None
    linux_target: str | None = None
    linux_host: str | None = None
    extra: dict = field(default_factory=dict)

    @property
    def requires_runtime_invoke_hook(self) -> bool:
        return "leg3" in self.extra.get("legs", LEGS)

    @property
    def requires_metadata(self) -> bool:
        return "leg2" in self.extra.get("legs", LEGS)

    @property
    def requires_player(self) -> bool:
        return bool(self.linux_target)


def clang_binary(platform: str) -> Path:
    return CLANG_MACOS if platform == "macos" else CLANG_LINUX


def host_arch() -> str:
    return "arm64" if subprocess.run(["/usr/bin/uname", "-sm"], capture_output=True, text=True).stdout.startswith("Darwin arm64") else "x86_64"


def have_rosetta() -> bool:
    """Measured, not inferred: the x86_64 slice actually runs on this machine."""
    if sys.platform != "darwin":
        return False
    try:
        return _run(["/usr/bin/arch", "-arch", "x86_64", "/usr/bin/true"], timeout=30).returncode == 0
    except (ProbeError, OSError):
        return False


def have_docker() -> bool:
    return shutil.which("docker") is not None


def host_id() -> str:
    """Anonymous host label: platform and CPU only, never the machine name."""
    info = os.uname()
    return f"{info.sysname.lower()}-{info.machine.lower()}"


def _validate_remote_command(text: str) -> None:
    if text.startswith("-o") or "proxycommand" in text.lower():
        raise ProbeError(f"flag {text[:24]!r} is not allowed for ssh")
    if UNSAFE_CHARS.search(text.replace(";", "").replace("&", "")):
        raise ProbeError("unsafe character in the remote command")
    if REMOTE_DENY.search(text):
        raise ProbeError("destructive pattern in the remote command")


def validate_invocation(argv: list[str], timeout: int | None = None) -> None:
    """Refuses anything outside the small binary and flag set the probe is allowed to run."""
    if timeout is None:
        raise ProbeError("every invocation needs a timeout")
    if not argv:
        raise ProbeError("empty invocation")
    binary = Path(str(argv[0]))
    name = binary.name
    own = name.startswith(ALLOWED_PREFIXES)
    if not own and name not in ALLOWED_BINS:
        raise ProbeError(f"binary {name} is not allowed")
    allowed = ALLOWED_FLAGS.get(name, frozenset())
    for index, element in enumerate(argv[1:], start=1):
        text = str(element)
        if name == "ssh" and index == 1:
            if not SAFE_HOST.match(text):
                raise ProbeError(f"unsafe ssh host {text[:40]!r}")
            continue
        if name == "ssh" and index >= 2:
            _validate_remote_command(text)
            continue
        if UNSAFE_CHARS.search(text):
            raise ProbeError(f"unsafe character in argument {text[:40]!r}")
        if not own and text.startswith("-") and text not in allowed:
            raise ProbeError(f"flag {text!r} is not allowed for {name}")


def _run(argv: list[str], *, timeout: int = 180, check: bool = False) -> subprocess.CompletedProcess:
    validate_invocation(argv, timeout=timeout)
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if check and completed.returncode != 0:
        raise ProbeError(f"{Path(str(argv[0])).name} exited {completed.returncode}: {completed.stderr.strip()[:200]}")
    return completed


def preflight_checks(
    platform: str,
    *,
    bundle: Path | None = None,
    dylib: Path | None = None,
    metadata_dir: Path | None = None,
    clang: Path | None = None,
    arches: tuple[str, ...] = ("x86_64",),
    host_arch: str | None = None,
    have_rosetta: bool | None = None,
    docker_image: str | None = None,
    need_docker: bool = False,
) -> list[str]:
    """Everything that must be true before a probe run, as messages rather than exceptions."""
    problems: list[str] = []
    compiler = clang or clang_binary(platform)
    if not os.access(compiler, os.X_OK):
        problems.append(f"clang not found at {compiler}")
    if bundle is not None:
        runtime = bundle / "Contents" / "Frameworks" / "GameAssembly.dylib"
        if not runtime.is_file():
            problems.append(f"no GameAssembly.dylib under {bundle}/Contents/Frameworks")
        if metadata_dir is None:
            metadata_dir = bundle / "Contents" / "Resources" / "Data" / "il2cpp_data" / "Metadata"
    if dylib is not None and not Path(dylib).is_file():
        problems.append(f"no runtime at {dylib}")
    if metadata_dir is None:
        if dylib is not None:
            problems.append("a metadata directory holding global-metadata.dat is required")
    elif not (Path(metadata_dir) / "global-metadata.dat").is_file():
        problems.append(f"no global-metadata.dat under {metadata_dir}")
    if platform == "macos" and "x86_64" in arches:
        arch = host_arch if host_arch is not None else globals()["host_arch"]()
        rosetta = have_rosetta if have_rosetta is not None else globals()["have_rosetta"]()
        if arch == "arm64" and not rosetta:
            problems.append("Rosetta 2 is not available to run the x86_64 slice")
    if need_docker and not have_docker():
        problems.append(f"docker is not available to check {docker_image}")
    return problems


def _dump_blocks(dump_text: str) -> dict[tuple[str, str], list[list[str]]]:
    blocks: dict[tuple[str, str], list[list[str]]] = {}
    namespace = ""
    pending: list[str] | None = None
    for line in dump_text.splitlines():
        found = NAMESPACE_LINE.match(line)
        if found:
            namespace = found.group(1).strip()
            continue
        if pending is not None:
            if line == "}":
                pending = None
                continue
            pending.append(line)
            continue
        declared = CLASS_LINE.match(line)
        if declared:
            name = declared.group(1).split("<")[0].split(".")[-1]
            pending = []
            blocks.setdefault((namespace, name), []).append(pending)
    return blocks


def _param_types(params: str) -> tuple[str, ...]:
    types = []
    for part in [item.strip() for item in params.split(",") if item.strip()]:
        head = part.split("=")[0].strip()
        token = head.split()[0] if head.split() else head
        types.append(token.replace("in ", "").replace("out ", "").replace("ref ", ""))
    return tuple(types)


def verify_candidates(candidates: list[Candidate] | tuple[Candidate, ...], dump_text: str) -> list[dict]:
    """Checks each candidate's signature exists in dump.cs and reports its RVA."""
    blocks = _dump_blocks(dump_text)
    rows = []
    for candidate in candidates:
        row = {"candidate": candidate.label, "found": False, "rva": None, "signature": None}
        for block in blocks.get((candidate.namespace, candidate.class_name), []):
            last_rva: str | None = None
            for line in block:
                rva = RVA_LINE.search(line)
                if rva:
                    last_rva = rva.group(1)
                    continue
                method = METHOD_LINE.match(line)
                if not method or method.group("name") != candidate.method:
                    continue
                if method.group("ret") != candidate.ret or _param_types(method.group("params")) != candidate.param_types:
                    continue
                row.update(
                    found=True,
                    rva=last_rva,
                    signature=f"public static {candidate.ret} {candidate.method}({', '.join(candidate.param_types)})",
                )
                break
            if row["found"]:
                break
        rows.append(row)
    return rows


def build_host_command(source: Path, out: Path, arch: str | None, platform: str) -> list[str]:
    compiler = str(clang_binary(platform))
    argv = [compiler, "-std=c11", "-O0", "-g", "-Wall", "-Werror"]
    if platform == "macos":
        if arch is None:
            raise ProbeError("macOS builds need an explicit -arch")
        argv += ["-arch", arch]
    else:
        argv += ["-ldl", "-o", str(out), str(source), "-lm"]
        return argv
    argv += ["-o", str(out), str(source)]
    return argv


def host_argv(
    host: Path,
    *,
    dylib: Path,
    data_dir: Path | None,
    leg: str,
    invoke: Candidate | None = None,
    hook: str | None = None,
    dlopen_mode: str | None = None,
    preloads: list[Path] | tuple[Path, ...] = (),
) -> list[str]:
    argv: list[str] = [str(host), "--dylib", str(dylib), "--leg", leg]
    if data_dir is not None:
        argv += ["--data-dir", str(data_dir)]
    if dlopen_mode is not None:
        argv += ["--dlopen-mode", dlopen_mode]
    argv += preload_argv(preloads)
    if leg in ("leg2", "leg3") or invoke is not None:
        if invoke is None:
            raise ValueError(f"{leg} needs a candidate to invoke")
        argv += [
            "--invoke-image",
            invoke.image,
            "--invoke-class",
            invoke.qualified,
            "--invoke-method",
            invoke.method,
            "--invoke-ret",
            invoke.ret,
            "--invoke-expected",
            invoke.expected,
        ]
        argv += [value for token in invoke.invoke_args for value in ("--invoke-arg", token)]
        argv += [value for token in invoke.param_types for value in ("--invoke-arg-type", type_name(token))]
    if leg == "leg3":
        if hook is None:
            raise ValueError("leg3 needs a hook target")
        argv += ["--hook", hook]
    return argv


def parse_host_output(stdout: str) -> dict | None:
    payload: dict | None = None
    for line in (stdout or "").splitlines():
        if not line.startswith(JSON_MARKER):
            continue
        try:
            parsed = json.loads(line[len(JSON_MARKER) :])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            payload = parsed
    return payload


def value_matches(ret: str, got: str, expected: str) -> bool:
    if expected == "":
        return got != ""
    if ret == "bool":
        return (got.strip().lower() in ("true", "1")) == (expected.strip().lower() in ("true", "1"))
    if ret == "float":
        try:
            left, right = float(got), float(expected)
        except ValueError:
            return False
        return abs(left - right) <= 1e-4 * max(1.0, abs(right))
    if ret in ("int", "long", "short", "byte", "uint"):
        try:
            return int(got) == int(expected)
        except ValueError:
            return False
    return got.strip() == expected.strip()


def find_loader_images(images: list[str]) -> list[str]:
    return [image for image in images if any(marker in image.lower() for marker in LOADER_MARKERS)]


def score_runs(runs: list[dict], legs: tuple[str, ...] = LEGS) -> dict:
    """Best status per leg across candidate and hook ladders, with the evidence that earned it."""
    legs_present: dict[str, dict] = {}
    for run in runs:
        leg = run.get("leg")
        if leg not in legs:
            continue
        status = run.get("status", "crash")
        if status not in LEG_STATUS_ORDER:
            status = "crash"
        current = legs_present.get(leg)
        if current is None or LEG_STATUS_ORDER.index(status) < LEG_STATUS_ORDER.index(current["status"]):
            legs_present[leg] = {
                "status": status,
                "evidence": run.get("evidence", {}),
                "returncode": run.get("returncode"),
                "signature": run.get("signature"),
                "candidate": run.get("candidate"),
                "hook": run.get("hook"),
            }
    for leg in legs:
        legs_present.setdefault(leg, {"status": "not-run", "evidence": {}, "returncode": None, "signature": None})
    overall = "pass" if legs and all(legs_present[leg]["status"] == "pass" for leg in legs) else "fail"
    return {"schema": SCHEMA, "overall": overall, "legs": legs_present}


def crash_signature(returncode: int, stderr: str) -> str:
    if returncode == 0:
        return ""
    if returncode < 0:
        number = -returncode
        try:
            base = f"signal={signal.Signals(number).name}"
        except ValueError:
            base = f"signal={number}"
    else:
        base = f"exit={returncode}"
    for line in (stderr or "").splitlines():
        if CRASH_NOISE.search(line):
            return f"{base} | {line.strip()[:200]}"
    return base


def run_from_output(leg: str, completed: subprocess.CompletedProcess, command: list[str]) -> dict:
    """Turns one host invocation into a scored run record."""
    payload = parse_host_output(completed.stdout or "") or {}
    status = payload.get("status")
    if status not in ("pass", "fail"):
        status = "crash"
    evidence = dict(payload.get("evidence") or {})
    stderr = (completed.stderr or "").strip()
    if stderr:
        evidence["stderr_tail"] = stderr[-2000:]
    run = {
        "leg": leg,
        "status": status,
        "reason": payload.get("reason"),
        "evidence": redact_report(evidence),
        "returncode": completed.returncode,
        "command": [str(part) for part in command],
    }
    signature = crash_signature(completed.returncode, stderr)
    if not signature and status == "crash":
        signature = f"exit={completed.returncode} no host payload"
    if signature:
        run["signature"] = redact(signature)
    return run


def run_host(argv: list[str], leg: str, *, log_path: Path | None = None, timeout: int = 180) -> dict:
    try:
        validate_invocation(argv, timeout=timeout)
    except ProbeError as error:
        return {
            "leg": leg,
            "status": "crash",
            "reason": None,
            "evidence": {},
            "returncode": None,
            "command": [str(part) for part in argv],
            "signature": redact(str(error)),
        }
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {
            "leg": leg,
            "status": "crash",
            "reason": None,
            "evidence": {},
            "returncode": None,
            "command": [str(part) for part in argv],
            "signature": f"timeout after {timeout}s",
        }
    except FileNotFoundError:
        return {
            "leg": leg,
            "status": "crash",
            "reason": None,
            "evidence": {},
            "returncode": None,
            "command": [str(part) for part in argv],
            "signature": f"not found: {argv[0]}",
        }
    run = run_from_output(leg, completed, argv)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"$ {' '.join(str(part) for part in argv)}\n--- stdout ---\n{completed.stdout or ''}\n--- stderr ---\n{completed.stderr or ''}\n")
    return run


def hook_needs_verify(symbol: str) -> bool:
    return symbol.startswith("il2cpp_") and symbol not in VOID_RETURNING_HOOKS


def encode_absolute_jump(target: int) -> bytes:
    return ABSOLUTE_JUMP + int(target).to_bytes(8, "little")


def thunk_prologue(head: bytes) -> bytes | None:
    """The prologue an exported il2cpp entry starts with, when the slot is a thunk.

    Shipped exports replay push rbp; mov rbp,rsp and then pop either rax or rbp before the jmp.
    """
    if len(head) <= THUNK_PROLOGUE_LEN or head[THUNK_PROLOGUE_LEN] != 0xE9:
        return None
    for prologue in THUNK_PROLOGUES:
        if head[:THUNK_PROLOGUE_LEN] == prologue:
            return prologue
    return None


def encode_trampoline(prologue: bytes, impl: int) -> bytes:
    if prologue[:THUNK_PROLOGUE_LEN] not in THUNK_PROLOGUES:
        raise ValueError("prologue is not the expected il2cpp api thunk shape")
    return prologue[:THUNK_PROLOGUE_LEN] + encode_absolute_jump(impl)


def is_thunk_shape(head: bytes) -> bool:
    return thunk_prologue(head) is not None


def thunk_impl_offset(head: bytes) -> int:
    if not is_thunk_shape(head):
        raise ValueError("not an il2cpp api thunk")
    return THUNK_PROLOGUE_LEN + 5


def thunk_impl_delta(head: bytes) -> int:
    if not is_thunk_shape(head):
        raise ValueError("not an il2cpp api thunk")
    start = THUNK_PROLOGUE_LEN + 1
    rel32 = int.from_bytes(head[start : start + 4], "little", signed=True)
    return rel32 + thunk_impl_offset(head)


def type_name(param_type: str) -> str:
    """The name the host's type table understands for a dump.cs parameter type."""
    if param_type in TYPE_NAMES:
        return TYPE_NAMES[param_type]
    if "[" in param_type or "." not in param_type:
        simple = param_type
    else:
        simple = param_type.rsplit(".", 1)[-1]
    return TYPE_NAMES.get(simple, simple)


def dlopen_mode_ladder(mode: str) -> list[str]:
    """dlopen modes to try, eager first: a shipped runtime can carry lazy Unity symbols."""
    if mode == "auto":
        return list(DLOPEN_MODES)
    if mode not in DLOPEN_MODES:
        raise ProbeError(f"unknown dlopen mode {mode!r}")
    return [mode]


def preload_argv(preloads: list[Path] | tuple[Path, ...]) -> list[str]:
    return [value for path in preloads for value in ("--preload", str(path))]


def redact(text: str) -> str:
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def redact_report(value: object) -> object:
    if isinstance(value, dict):
        return {key: redact_report(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_report(item) for item in value]
    if isinstance(value, str):
        return redact(value)
    return value


def chainloader_conclusion(legs: dict) -> dict:
    """What the run says about driving the runtime by symbol without the chainloader trigger."""
    leg3 = legs.get("leg3", {})
    evidence = leg3.get("evidence") or {}
    if leg3.get("status") == "not-run" or not evidence.get("hook"):
        return {
            "by_symbol_invoke_available": None,
            "evidence": "the detour leg was not run, so the chainloader trigger is unmeasured",
        }
    invoke_hooked = evidence.get("hook") == "il2cpp_runtime_invoke"
    fired = bool(evidence.get("hook_calls"))
    available = leg3.get("status") == "pass" and invoke_hooked and fired
    return {
        "by_symbol_invoke_available": available,
        "evidence": f"leg3={leg3.get('status')} hook={evidence.get('hook')} hook_calls={evidence.get('hook_calls')}",
    }


def select_candidates(
    candidates: list[Candidate] | tuple[Candidate, ...], only: list[str] | tuple[str, ...]
) -> list[Candidate]:
    """Ladder subset whose label mentions one of the patterns; empty patterns keep all."""
    patterns = [pattern for pattern in only if pattern]
    if not patterns:
        return list(candidates)
    return [row for row in candidates if any(pattern in row.label for pattern in patterns)]


def attempt_rows(runs: list[dict]) -> list[dict]:
    """One compact row per attempt so a ladder shows what failed, not only what passed."""
    rows = []
    for run in runs:
        rows.append(
            {
                "arch": run.get("arch"),
                "leg": run.get("leg"),
                "status": run.get("status"),
                "candidate": run.get("candidate"),
                "hook": run.get("hook"),
                "returncode": run.get("returncode"),
                "signature": run.get("signature"),
            }
        )
    return rows


def linux_result_from_remote(returncode: int, stdout: str, stderr: str) -> dict:
    """Scores the control leg from the report the player host printed for itself."""
    payload: dict | None = None
    for line in (stdout or "").splitlines():
        if line.startswith("{"):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
    if payload is None:
        return {
            "status": "crash",
            "returncode": returncode,
            "signature": redact(crash_signature(returncode, stderr) or "no remote report"),
            "stdout_tail": redact((stdout or "")[-4000:]),
            "stderr_tail": redact((stderr or "")[-4000:]),
        }
    result = {
        "status": "pass" if returncode == 0 and payload.get("overall") == "pass" else "fail",
        "returncode": returncode,
        "legs": redact_report(payload.get("legs")),
        "attempts": redact_report(payload.get("attempts")),
        "stdout_tail": redact((stdout or "")[-4000:]),
        "stderr_tail": redact((stderr or "")[-4000:]),
    }
    if result["status"] != "pass":
        result["signature"] = redact(crash_signature(returncode, stderr) or str(payload.get("overall")))
    return result


def emit_payload(report: dict, json_path: Path) -> dict:
    """The one line printed for a caller: scores plus the ladder, without raw evidence."""
    return {
        "overall": report.get("overall"),
        "legs": report.get("legs"),
        "attempts": report.get("attempts"),
        "out": str(json_path),
    }


def combine_overall(legs_overall: str, linux: dict | None, *, remote_only: bool) -> str:
    """A remote-only run has no local legs, so the control leg decides the verdict."""
    if remote_only and linux:
        return linux.get("status", "not-run")
    return legs_overall


def build_report(
    runs: list[dict],
    *,
    platform: str,
    arches: tuple[str, ...],
    runtime: Path,
    host_id: str,
    legs: tuple[str, ...] = LEGS,
    hooks: tuple[str, ...] = (),
    data_dir: Path | None = None,
    candidates: list[dict] | None = None,
    linux: dict | None = None,
) -> dict:
    kept = [run for run in runs if run.get("leg") in legs]
    primary = arches[0] if arches else None
    score = score_runs([run for run in kept if run.get("arch", primary) == primary], legs=legs)
    return {
        "schema": SCHEMA,
        "probe_version": PROBE_VERSION,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "platform": platform,
        "arches": list(arches),
        "host_id": host_id,
        "runtime": str(runtime),
        "data_dir": str(data_dir) if data_dir else None,
        "legs_requested": list(legs),
        "hooks": list(hooks),
        "candidates": candidates or [],
        "runs": kept,
        "attempts": attempt_rows(kept),
        "summary": score,
        "overall": score["overall"],
        "legs": score["legs"],
        "chainloader": chainloader_conclusion(score["legs"]),
        "linux": linux,
    }


def stage_data_dir(metadata_dir: Path, out_dir: Path) -> Path:
    """Links the real metadata directory in behind both path layouts libil2cpp can spell."""
    metadata_dir = Path(metadata_dir).absolute()
    if not (metadata_dir / "global-metadata.dat").is_file():
        raise FileNotFoundError(f"no global-metadata.dat under {metadata_dir}")
    (out_dir / "il2cpp_data").mkdir(parents=True, exist_ok=True)
    for link in (out_dir / "Metadata", out_dir / "il2cpp_data" / "Metadata"):
        if link.is_symlink():
            if os.readlink(link) == str(metadata_dir):
                continue
            link.unlink()
        elif link.exists():
            raise ProbeError(f"{link} exists and is not a symlink")
        link.symlink_to(metadata_dir, target_is_directory=True)
    return out_dir


def resolve_paths(
    app: Path | None,
    dylib: Path | None,
    metadata_dir: Path | None,
    out_dir: Path,
    *,
    legs: tuple[str, ...] = LEGS,
    linux_target: str | None = None,
    linux_host: str | None = None,
) -> Paths:
    if app is not None:
        bundle = Path(app).expanduser()
        runtime = bundle / "Contents" / "Frameworks" / "GameAssembly.dylib"
        if not bundle.is_dir():
            raise ProbeError(f"no bundle at {bundle}")
        if not runtime.is_file():
            raise ProbeError(f"no GameAssembly.dylib under {bundle}/Contents/Frameworks")
        resolved_metadata = Path(metadata_dir).expanduser() if metadata_dir else (
            bundle / "Contents" / "Resources" / "Data" / "il2cpp_data" / "Metadata"
        )
    elif dylib is not None:
        bundle = None
        runtime = Path(dylib).expanduser()
        if not runtime.is_file():
            raise ProbeError(f"no runtime at {runtime}")
        if metadata_dir is None:
            raise ProbeError("--metadata is required with --dylib")
        resolved_metadata = Path(metadata_dir).expanduser()
    else:
        raise ProbeError("--app or --dylib is required")
    if not (resolved_metadata / "global-metadata.dat").is_file():
        raise ProbeError(f"no global-metadata.dat under {resolved_metadata}")
    out = Path(out_dir).expanduser()
    return Paths(
        dylib=runtime,
        metadata_dir=resolved_metadata,
        data_dir=out / "probe_data",
        out_dir=out,
        bundle=bundle,
        linux_target=linux_target,
        linux_host=linux_host,
        extra={"legs": legs},
    )


def player_argv(executable: Path, log_path: Path) -> list[str]:
    return [str(executable), "-batchmode", "-nographics", "-logFile", str(log_path)]


def stop_player(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def linux_build_pull_command(local_dir: Path, remote_host: str, remote_dir: str) -> list[str]:
    """Copies the shipped Linux build, leaving any loader tree and managed dlls behind."""
    return [
        str(RSYNC),
        "-a",
        "-z",
        "--exclude",
        "BepInEx/",
        "--exclude",
        "dotnet/",
        "--exclude",
        "MonoBleedingEdge/",
        "--exclude",
        "*.dll",
        f"{remote_host}:{remote_dir}/",
        str(local_dir),
    ]


def linux_probe_sync_command(local_scripts: Path, remote_host: str, remote_dir: str) -> list[str]:
    """Copies the driver and host source to the player host so the control leg runs the same code."""
    if UNSAFE_CHARS.search(remote_dir):
        raise ProbeError(f"unsafe path {remote_dir!r}")
    if not SAFE_HOST.match(remote_host):
        raise ProbeError(f"unsafe ssh host {remote_host[:40]!r}")
    return [
        str(RSYNC),
        "-a",
        "-z",
        "--exclude",
        "__pycache__/",
        "--exclude",
        ".venv/",
        f"{local_scripts}/",
        f"{remote_host}:{remote_dir}/scripts/",
    ]


def linux_prepare_dir_command(host: str, remote_dir: str) -> list[str]:
    """rsync only creates the last path component, so the probe directory is made first."""
    if UNSAFE_CHARS.search(remote_dir):
        raise ProbeError(f"unsafe path {remote_dir!r}")
    if not SAFE_HOST.match(host):
        raise ProbeError(f"unsafe ssh host {host[:40]!r}")
    return [str(SSH), host, f"mkdir -p {remote_dir}/scripts {remote_dir}/out"]


def remote_host_identity_command(host: str, target: str) -> list[str]:
    return [str(SSH), host, f"uname -sm; file {target}; ls -l {target}"]


def docker_image_check_command(image: str) -> list[str]:
    return [str(DOCKER), "image", "inspect", image]


def linux_remote_command(
    *,
    probe_dir: str,
    venv_path: str,
    target: str,
    out_dir: str,
    host: str,
    arch: str = "x86_64",
    only: list[str] | tuple[str, ...] = (),
) -> list[str]:
    """Runs the same probe driver on the Linux player host over ssh, legs 1 and 2 only."""
    for path in (probe_dir, venv_path, out_dir, *only):
        if UNSAFE_CHARS.search(path):
            raise ProbeError(f"unsafe path {path!r}")
    script = f"{probe_dir}/scripts/native_bind_probe.py"
    host_script = f"{probe_dir}/scripts/native_bind_probe/host.c"
    dylib = f"{target}/GameAssembly.so"
    metadata = f"{target}/Megabonk_Data/il2cpp_data/Metadata"
    ladder = "".join(f" --only {pattern}" for pattern in only if pattern)
    inner = (
        "set -eu; "
        f"test -f {metadata}/global-metadata.dat; "
        f"{venv_path} {script} --dylib {dylib} --metadata {metadata} --out {out_dir} "
        f"--platform linux --arch {arch} --legs leg1,leg2 --host-source {host_script}{ladder}"
    )
    return [str(SSH), host, inner]


def build_host_binary(command: list[str]) -> tuple[bool, str]:
    try:
        completed = _run(command, timeout=300)
    except ProbeError as error:
        return False, str(error)
    if completed.returncode != 0:
        return False, (completed.stderr or "").strip()[:4000]
    return True, ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score the by-symbol Il2Cpp runtime binding spike.")
    parser.add_argument("--app", help="macOS IL2CPP player bundle to probe")
    parser.add_argument("--dylib", help="GameAssembly.dylib or .so to bind (overrides --app)")
    parser.add_argument("--metadata", help="directory holding global-metadata.dat")
    parser.add_argument("--out", default=".tools/native-bind", help="where to write artifacts")
    parser.add_argument("--arch", default="x86_64", choices=("x86_64", "arm64", "both"), help="slice to build and run")
    parser.add_argument("--platform", default=None, choices=("macos", "linux"), help="defaults to the running OS")
    parser.add_argument("--legs", default=",".join(LEGS), help="comma list of legs to run")
    parser.add_argument("--hooks", default=",".join(HOOKABLE_SYMBOLS[:2]), help="comma list of leg3 hook targets")
    parser.add_argument("--dump", default=".tools/il2cpp_dump/dump.cs", help="Il2CppDumper dump.cs for candidates")
    parser.add_argument("--host-source", default=None, help="host.c to compile (default scripts/native_bind_probe/host.c)")
    parser.add_argument("--limit", type=int, default=0, help="cap the leg2 candidate ladder")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="keep only leg2 candidates whose label contains this text (repeatable)",
    )
    parser.add_argument("--json-path", default=None, help="summary.json destination (default <out>/summary.json)")
    parser.add_argument("--linux-target", choices=("x86_64",), help="run the control leg against the shipped Linux build")
    parser.add_argument("--linux-host", help="ssh host running the Linux player")
    parser.add_argument("--dlopen-mode", default="auto", help="dlopen mode, or auto to try now, lazy, lazy_global")
    parser.add_argument("--preload", action="append", default=[], help="library to dlopen before the runtime (repeatable)")
    parser.add_argument("--linux-python", default="python3", help="interpreter on the Linux player host")
    parser.add_argument("--linux-probe-dir", default="~/native-bind-probe", help="probe directory on the Linux player host")
    parser.add_argument("--linux-target-dir", default=None, help="shipped Linux build directory on the player host")
    parser.add_argument("--remote-only", action="store_true", help="run only the Linux control leg on the player host")
    parser.add_argument("--skip-preflight", action="store_true", help="run even when preflight reports problems")
    parser.add_argument("--quiet", action="store_true", help="suppress per-run evidence lines on stderr")
    args = parser.parse_args(argv)

    platform = args.platform or ("macos" if sys.platform == "darwin" else "linux")
    legs = tuple(leg for leg in args.legs.split(",") if leg in LEGS)
    hooks = tuple(hook for hook in args.hooks.split(",") if hook)
    arches = ("x86_64", "arm64") if args.arch == "both" else (args.arch,)

    if args.linux_target and not (args.linux_host and args.dylib and args.metadata):
        print(
            "error: --linux-target needs --linux-host, --dylib and --metadata "
            "(rsync the shipped Linux build first)",
            file=sys.stderr,
        )
        return 2
    try:
        dlopen_modes = dlopen_mode_ladder(args.dlopen_mode)
    except ProbeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if platform != "macos" and "leg3" in legs:
        legs = tuple(leg for leg in legs if leg != "leg3")
        print("note: leg3 skipped, the detour question is the macOS one", file=sys.stderr)
    if not legs:
        print("error: no legs to run", file=sys.stderr)
        return 2

    try:
        paths = resolve_paths(
            Path(args.app) if args.app else None,
            Path(args.dylib) if args.dylib else None,
            Path(args.metadata) if args.metadata else None,
            Path(args.out),
            legs=legs,
            linux_target=args.linux_target,
            linux_host=args.linux_host,
        )
    except ProbeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    problems = preflight_checks(
        platform,
        bundle=paths.bundle,
        dylib=None if paths.bundle else paths.dylib,
        metadata_dir=paths.metadata_dir,
        arches=arches,
    )
    if problems and not args.skip_preflight:
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        return 2

    paths.out_dir.mkdir(parents=True, exist_ok=True)
    try:
        data_dir = stage_data_dir(paths.metadata_dir, paths.data_dir)
    except (ProbeError, FileNotFoundError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    source = Path(args.host_source).expanduser() if args.host_source else HOST_SOURCE
    if not source.is_file():
        print(f"error: no host source at {source}", file=sys.stderr)
        return 2

    candidates = select_candidates(
        list(DEFAULT_CANDIDATES[: args.limit] if args.limit else DEFAULT_CANDIDATES), args.only
    )
    dump_path = Path(args.dump).expanduser()
    candidate_rows: list[dict] = []
    if dump_path.is_file():
        candidate_rows = verify_candidates(candidates, dump_path.read_text(encoding="utf-8", errors="replace"))

    hosts: dict[str, Path] = {}
    for arch in () if args.remote_only else arches:
        host = paths.out_dir / f"native_bind_host_{platform}_{arch}"
        ok, message = build_host_binary(build_host_command(source, host, arch if platform == "macos" else None, platform))
        if not ok:
            print(f"error: building {host.name}: {message[:2000]}", file=sys.stderr)
            return 2
        hosts[arch] = host

    linux: dict | None = None
    if paths.linux_target:
        host = paths.linux_host or ""
        probe_dir = args.linux_probe_dir
        target = args.linux_target_dir or str(paths.dylib.parent)
        linux = {"host_kind": "player-host", "target": redact(target)}
        try:
            _run(linux_prepare_dir_command(host, probe_dir), timeout=120)
            sync = _run(linux_probe_sync_command(HOST_SOURCE.parent.parent, host, probe_dir), timeout=600)
            linux["sync"] = "pass" if sync.returncode == 0 else "fail"
            linux["sync_tail"] = redact((sync.stderr or "")[-800:])
        except ProbeError as error:
            linux["sync"] = "crash"
            linux["signature"] = redact(str(error))
        if linux["sync"] == "pass":
            try:
                identity = _run(remote_host_identity_command(host, f"{target}/GameAssembly.so"), timeout=120)
                linux["identity"] = redact((identity.stdout or "").strip()[-500:])
            except ProbeError as error:
                linux["identity"] = redact(str(error))
            command = linux_remote_command(
                probe_dir=probe_dir,
                venv_path=args.linux_python,
                target=target,
                out_dir=f"{probe_dir}/out",
                host=host,
                arch=paths.linux_target,
                only=args.only,
            )
            try:
                completed = _run(command, timeout=900)
            except ProbeError as error:
                linux["status"] = "crash"
                linux["signature"] = redact(str(error))
            else:
                linux.update(
                    linux_result_from_remote(
                        completed.returncode, completed.stdout or "", completed.stderr or ""
                    )
                )

    runs: list[dict] = []

    def emit(arch: str, leg: str, invoke: Candidate | None, hook: str | None, *, skip_init: bool = False) -> dict:
        argv_host = host_argv(
            hosts[arch],
            dylib=paths.dylib,
            data_dir=data_dir,
            leg=leg,
            invoke=invoke,
            hook=hook,
            dlopen_mode=args.dlopen_mode,
            preloads=[Path(item) for item in args.preload],
        )
        if skip_init:
            argv_host.append("--skip-init")
        log = paths.out_dir / "logs" / f"{arch}_{leg}_{(invoke.method if invoke else 'x')}_{hook or 'x'}{'.skipinit' if skip_init else ''}.log"
        run = run_host(argv_host, leg, log_path=log)
        run["arch"] = arch
        if invoke is not None:
            run["candidate"] = invoke.label
        if hook is not None:
            run["hook"] = hook
        runs.append(run)
        if not args.quiet:
            suffix = f" {run['candidate']}" if run.get("candidate") else ""
            print(f"{arch} {leg} {run['status']}{suffix}", file=sys.stderr)
            for key, value in (run.get("evidence") or {}).items():
                print(f"    {key}={value}", file=sys.stderr)
        return run

    winners: dict[str, str | None] = {}
    chosen_hooks: dict[str, str | None] = {}
    for arch in () if args.remote_only else arches:
        winners[arch] = None
        chosen_hooks[arch] = None
        if "leg1" in legs:
            first = emit(arch, "leg1", None, None)
            if first["status"] == "crash":
                emit(arch, "leg1", None, None, skip_init=True)
        winner: Candidate | None = None
        if "leg2" in legs:
            for candidate in candidates:
                run = emit(arch, "leg2", candidate, None)
                if winner is None and run["status"] == "pass":
                    winner = candidate
        winners[arch] = winner.label if winner else None
        if "leg3" in legs:
            probe = winner or candidates[0]
            for hook in hooks:
                hook_run = emit(arch, "leg3", probe, hook)
                if hook_run["status"] == "pass" and chosen_hooks[arch] is None:
                    chosen_hooks[arch] = hook

    report = build_report(
        runs,
        platform=platform,
        arches=arches,
        runtime=paths.dylib,
        host_id=host_id(),
        legs=legs,
        hooks=hooks,
        data_dir=data_dir,
        candidates=candidate_rows,
        linux=linux,
    )
    report["winners"] = winners
    report["hooks_passed"] = chosen_hooks
    report["preflight"] = problems
    report["remote_only"] = bool(args.remote_only)
    report["overall"] = combine_overall(report["overall"], linux, remote_only=bool(args.remote_only))
    json_path = Path(args.json_path).expanduser() if args.json_path else paths.out_dir / "summary.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(redact_report(report), indent=1, default=str) + "\n")
    print(json.dumps(redact_report(emit_payload(report, json_path))))
    return 0 if report["overall"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
