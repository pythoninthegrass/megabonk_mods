"""Run the pinned ELF startup hooks against a linked arm64 image in a bounded subprocess."""

import argparse
import elf_shim_probe
import hashlib
import json
import lift_reloc
import subprocess
from pathlib import Path


class StartupError(RuntimeError):
    """The linked image does not provide an executable startup plan."""


def startup_hooks(dynamic, sections, patches, entries: set[int]) -> list[int]:
    hooks = []
    if init := dynamic.get("INIT"):
        if init not in entries:
            raise StartupError(f"INIT target {init:#x} is not a lifted body")
        hooks.append(init)
    base, size = dynamic.get("INIT_ARRAY"), dynamic.get("INIT_ARRAYSZ")
    if base is None and size is None:
        return hooks
    if base is None or size is None:
        raise StartupError("incomplete INIT_ARRAY tags")
    word = lift_reloc.WORD
    if base <= 0 or base % word or size < 0 or size % word:
        raise StartupError("invalid INIT_ARRAY range")
    if not size:
        return hooks
    section = next((s for s in sections if s["va"] <= base and base + size <= s["va"] + s["size"]), None)
    if section is None:
        raise StartupError("INIT_ARRAY is not contained in one section")
    slots = {p.offset: p.function for p in patches if p.section == section["name"]}
    for site in range(base, base + size, word):
        target = slots.get(site - section["va"])
        if target not in entries:
            raise StartupError(f"INIT_ARRAY slot {site:#x} does not bind to a lifted body")
        hooks.append(target)
    return hooks


def run_probe(dylib: Path, hooks: list[int], out: Path, timeout: float) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    driver = out / "startup-probe"
    source = Path(__file__).with_name("native_bind_probe") / "startup.c"
    subprocess.run(["cc", "-arch", "arm64", "-Wall", "-Wextra", "-Werror", "-o", driver, source], check=True, timeout=30)
    command = [str(driver.resolve()), str(dylib.resolve()), *(f"{address:x}" for address in hooks)]
    try:
        process = subprocess.run(command, capture_output=True, timeout=timeout)
        stdout, stderr, returncode = process.stdout, process.stderr, process.returncode
    except subprocess.TimeoutExpired as error:
        stdout, stderr, returncode = error.stdout or b"", error.stderr or b"", None
    prefix = b"#STARTUP#"
    events = [
        json.loads(line.removeprefix(prefix))
        for line in stdout.splitlines(keepends=True)
        if line.startswith(prefix) and line.endswith(b"\n")
    ]
    expected = [
        {"event": event, "index": index, "address": address}
        for index, address in enumerate(hooks)
        for event in ("enter", "return")
    ]
    result = {
        "hooks": hooks,
        "events": events,
        "returncode": returncode,
        "timed_out": returncode is None,
        "complete": returncode == 0 and events == expected,
    }
    (out / "startup.stdout").write_bytes(stdout)
    (out / "startup.stderr").write_bytes(stderr)
    (out / "startup.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("so", type=Path)
    parser.add_argument("--link", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    if not 0 < args.timeout < float("inf"):
        parser.error("--timeout must be positive and finite")
    elf = elf_shim_probe.parse_elf(args.so)
    report = json.loads((args.link / "link-relocations.json").read_text())
    with args.so.open("rb") as binary:
        digest = hashlib.file_digest(binary, "sha256").hexdigest()
    if report["binary_sha256"] != digest:
        raise StartupError("the relocation report does not match the ELF")
    with (args.baseline / "bodies.jsonl").open() as rows:
        entries = {json.loads(row)["start"] for row in rows}
    sections = report["sections"]
    base = elf.dynamic.get("INIT_ARRAY", 0)
    end = base + elf.dynamic.get("INIT_ARRAYSZ", 0)
    section = next((s for s in sections if s["va"] <= base < s["va"] + s["size"]), None)
    patches = []
    if section:
        with (args.link / "link-relocation-map.jsonl").open() as rows:
            for line in rows:
                row = json.loads(line)
                if base <= row["site"] < end:
                    patches.append(
                        lift_reloc.Patch(
                            section["name"], row["site"] - section["va"], None, None, function=row["target"].get("function")
                        )
                    )
    hooks = startup_hooks(elf.dynamic, sections, patches, entries)
    result = run_probe(args.link / "libgameassembly.dylib", hooks, args.out, args.timeout)
    print(args.out / "startup.json")
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
