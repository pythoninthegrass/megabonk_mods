#!/usr/bin/env -S uv run --script
"""Link the lifted arm64 bodies of a scored image into one dylib, with unresolved jumps turned into logged traps.

Reuses the pcode shards of a completed `lift_image.py --build` run. Each shard becomes one object, the data
sections the bodies reference (with every relocated word patched) become another, and the host helpers a third.
The baseline verdict is neither changed nor claimed: a body with a hole still links, and aborts if it is reached.
"""

from __future__ import annotations

import hashlib
import json
import lift_abi
import lift_image as li
import lift_imports
import lift_probe as lp
import lift_reloc as rl
import lift_runtime
import lift_sdk
import pcode_lift as pl
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

DYLIB = "libgameassembly.dylib"
LLC = ["-O2", "-mtriple=arm64-apple-macosx", "-filetype=obj", "-o", "-"]
NOBITS = 8


def link_fingerprint() -> str:
    """Identity of everything beyond the pcode that decides a shard's object: the lifter, relocator, ABI and LLVM."""
    import lift_tables

    stamp = hashlib.sha256()
    for path in (__file__, pl.__file__, rl.__file__, lift_abi.__file__, lp.__file__, lift_tables.__file__):
        stamp.update(Path(path).read_bytes())
    for tool in ("llc", "clang"):
        stamp.update(lp.run_tool([lp.LLVM / tool, "--version"], check=True).stdout)
    return stamp.hexdigest()


def write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def reusable(meta_path: Path, identity: str, object_path: Path) -> dict | None:
    """The stored record when its identity matches and its object is still the size it recorded."""
    try:
        record = json.loads(meta_path.read_text())
        return record if record["identity"] == identity and object_path.stat().st_size == record["bytes"] else None
    except (OSError, ValueError, KeyError):
        return None


def baseline_shard(index: int, part: list, ctx: dict) -> list[dict]:
    dump_id = li.shard_identity(ctx["sha"], ctx["fingerprint"], ctx["ghidra"], part, "")
    cached = li.read_shard(Path(ctx["baseline"]) / f"pcode-{index:04d}.jsonl", dump_id, part, pcode=True)
    if cached is None:
        raise ValueError(f"missing or invalid baseline pcode shard {index}; check --shard-size and dump identity")
    return cached


def compile_object(name: str, module: str, timeout: int) -> bytes:
    ok, payload, error = lp.run_tool_body("llc", [lp.LLVM / "llc", *LLC, *lp.EXTRA_ARGS], module, timeout)
    if not ok or payload is None:
        raise RuntimeError(f"{name}: {error}")
    return payload


def shard_object(index: int, part: list, ctx: dict) -> dict:
    """The arm64 object for one shard's bodies, reused while the baseline dump, lifter and toolchain are unchanged."""
    cached = baseline_shard(index, part, ctx)
    dump_id = li.shard_identity(ctx["sha"], ctx["fingerprint"], ctx["ghidra"], part, "")
    identity = li.shard_identity(
        ctx["sha"],
        f"{dump_id}:{ctx['link']}",
        ctx["ghidra"],
        part,
        json.dumps(["link", ctx["tool_timeout"], ctx.get("entries_id", "")]),
    )
    out = Path(ctx["out"])
    meta_path, object_path = out / f"link-{index:04d}.json", out / f"link-{index:04d}.o"
    record = reusable(meta_path, identity, object_path)
    if record is not None:
        return record
    sections, rows = cached[0]["sections"], cached[1:]
    evidence = li.table_evidence(ctx)
    lifted, failed = [], {}
    for row in rows:
        if row.get("error"):
            failed[str(row["start"])] = row["error"]
            continue
        try:
            lifted.append(pl.lift_body(row, sections, evidence=evidence, trap_holes=True, entries=ctx.get("entries")))
        except Exception as exc:
            failed[str(row["start"])] = f"lift raised {type(exc).__name__}: {exc}"
    payload = compile_object(f"shard {index}", pl.module_for(lifted), ctx["tool_timeout"])
    write_atomic(object_path, payload)
    record = {
        "identity": identity,
        "object": str(object_path),
        "bytes": len(payload),
        "bodies": len(lifted),
        "holes": {str(b.start): b.holes for b in lifted if b.holes},
        "failed": failed,
        "sections": sorted(set().union(*(b.data_sections for b in lifted))),
    }
    meta_path.write_text(json.dumps(record))
    return record


def section_images(elf, raw: bytes, sections: list[dict], names: set) -> dict[str, bytes]:
    """Initial bytes of each named section: its file contents, or zeros for NOBITS and sections with no ELF header."""
    images = {}
    for name in sorted(names):
        section = next(s for s in sections if s["name"] == name)
        header = next((h for h in elf.sections if h.addr == section["va"] and h.size == section["size"]), None)
        if header is None or header.type == NOBITS:
            images[name] = bytes(section["size"])
        else:
            images[name] = raw[header.offset : header.offset + header.size]
    return images


def data_object(ctx: dict, plan: rl.ImagePlan, records: list[dict], load_images) -> dict:
    """The object defining every data section the bodies reference or the relocation plan patches, once."""
    names = set().union(*(set(r["sections"]) for r in records)) | {p.section for p in plan.patches}
    names |= {p.target[0] for p in plan.patches if p.target}
    module = pl.module_for([], load_images(names), plan.patches, sorted(names))
    identity = hashlib.sha256(f"{ctx['sha']}\0{ctx['link']}\0{ctx['tool_timeout']}\0".encode() + module.encode()).hexdigest()
    out = Path(ctx["out"])
    meta_path, object_path = out / "link-data.json", out / "link-data.o"
    record = reusable(meta_path, identity, object_path)
    if record is not None:
        return record
    payload = compile_object("data sections", module, ctx["tool_timeout"])
    write_atomic(object_path, payload)
    record = {"identity": identity, "object": str(object_path), "bytes": len(payload), "sections": sorted(names)}
    meta_path.write_text(json.dumps(record))
    return record


def classify_undefined(nm_output: str) -> dict[str, list[str]]:
    """Groups undefined symbols by what binds them: a lifted body or import stub, a host helper, or anything else."""
    groups: dict[str, list[str]] = {"bodies": [], "lift": [], "other": []}
    for line in nm_output.splitlines():
        if not line.strip():
            continue
        name = line.split()[-1].removeprefix("_")
        groups["bodies" if name.startswith("sub_") else "lift" if name.startswith("lift_") else "other"].append(name)
    return {key: sorted(set(names)) for key, names in groups.items()}


def host_object(ctx: dict) -> Path:
    out = Path(ctx["out"])
    source, obj = out / "host.c", out / "host.o"
    source.write_text(ctx.get("host_source") or lift_abi.generate([], []))
    lp.run_tool([lp.LLVM / "clang", "-arch", "arm64", "-O2", "-c", source, "-o", obj], check=True)
    return obj


def link_image(ctx: dict, parts: list[list], plan: rl.ImagePlan, load_images, jobs: int = 1) -> dict:
    """Compiles every shard and the data sections, then links one dylib; unchanged inputs reuse the previous dylib."""
    started = time.monotonic()
    if jobs > 1:
        with ProcessPoolExecutor(jobs) as pool:
            records = list(pool.map(partial(shard_object, ctx=ctx), range(len(parts)), parts))
    else:
        records = [shard_object(i, part, ctx) for i, part in enumerate(parts)]
    data = data_object(ctx, plan, records, load_images)
    host = host_object(ctx)
    out = Path(ctx["out"])
    dylib, meta_path = out / DYLIB, out / "link.json"
    identity = hashlib.sha256(
        json.dumps([[r["identity"] for r in records], data["identity"], host.read_bytes().hex()]).encode()
    ).hexdigest()
    try:
        linked = json.loads(meta_path.read_text())
        reused = linked["identity"] == identity and dylib.exists()
    except (OSError, ValueError, KeyError):
        linked, reused = {}, False
    if not reused:
        objects = [Path(r["object"]) for r in records] + [Path(data["object"]), host]
        began = time.monotonic()
        lp.run_tool(
            [lp.LLVM / "clang", "-arch", "arm64", "-dynamiclib", "-o", dylib, *objects, "-Wl,-undefined,dynamic_lookup"]
            + ["-install_name", f"@rpath/{DYLIB}"],
            timeout=ctx.get("link_timeout", 7200),
            check=True,
        )
        nm = lp.run_tool([lp.LLVM / "llvm-nm", "-u", dylib], text=True, check=True).stdout
        linked = {
            "identity": identity,
            "undefined": classify_undefined(nm),
            "link_seconds": round(time.monotonic() - began, 1),
        }
        meta_path.write_text(json.dumps(linked))
    return {
        "dylib": str(dylib),
        "dylib_bytes": dylib.stat().st_size,
        "reused": reused,
        "shards": len(records),
        "bodies": sum(r["bodies"] for r in records),
        "object_bytes": sum(r["bytes"] for r in records),
        "data_object_bytes": data["bytes"],
        "holes": {start: holes for r in records for start, holes in r["holes"].items()},
        "failed": {start: why for r in records for start, why in r["failed"].items()},
        "undefined": linked["undefined"],
        "link_seconds": linked["link_seconds"],
        "wall_seconds": round(time.monotonic() - started, 1),
    }


def import_stubs(so: Path, image: rl.Image, entries) -> dict:
    """The host source defining every PLT stub, with the per-stub and per-import report it was built from."""
    view = lift_sdk.load()
    defined = {s.name: s.value for s in image.symbols if s.defined and s.name}
    plan = lift_imports.plan_stubs(view, lift_runtime.plt_names(so), defined, entries)
    aliased = sorted(set(plan.aliases.values()) & set(entries))
    source = lift_abi.generate([], plan.imports, callable_bodies=aliased, aliases=plan.aliases)
    source += "\n" + lift_imports.abort_source(plan.rows) + "\n" + lift_imports.abort_stubs(plan.rows) + "\n"
    return {
        "source": source,
        "counts": lift_imports.counts(plan.rows),
        "report": {
            "counts": lift_imports.counts(plan.rows),
            "stubs": plan.rows,
            "imports": lift_imports.import_report(view, plan.rows),
        },
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import elf_shim_probe

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("so", nargs="?", type=Path, default=lp.DEFAULT_SO)
    ap.add_argument("--baseline", type=Path, required=True, help="a completed lift_image.py --build directory")
    ap.add_argument("--out", type=Path, required=True, help="separate output directory for objects and the dylib")
    ap.add_argument("--shard-size", type=int, default=4000)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--tool-timeout", type=int, default=3600)
    args = ap.parse_args(argv)
    if args.out.resolve() == args.baseline.resolve():
        ap.error("--out must be separate from --baseline")
    inv = li.inventory(args.so, args.shard_size)
    args.out.mkdir(parents=True, exist_ok=True)
    ctx = {
        "so": args.so,
        "baseline": args.baseline,
        "out": args.out,
        "sha": inv["sha"],
        "fingerprint": lp.dump_script_fingerprint(),
        "ghidra": lp.ghidra_version(),
        "link": link_fingerprint(),
        "tool_timeout": args.tool_timeout,
    }
    parts = inv["parts"]
    entries = frozenset(f.start for f in inv["bodies"])
    ctx["entries"] = entries
    ctx["entries_id"] = hashlib.sha256(",".join(f"{a:x}" for a in sorted(entries)).encode()).hexdigest()
    sections = baseline_shard(0, parts[0], ctx)[0]["sections"]
    raw = args.so.read_bytes()
    elf = elf_shim_probe.parse_elf(args.so)
    image = rl.load_image(elf, raw, sections)
    plan = rl.plan_image(image, entries)
    stubs = import_stubs(args.so, image, entries)
    ctx["host_source"] = stubs["source"]
    summary = link_image(ctx, parts, plan, lambda names: section_images(elf, raw, sections, names), args.jobs)
    summary |= {
        "binary_sha256": inv["sha"],
        "relocations": {
            "patches": len(plan.patches),
            "function": sum(p.function is not None for p in plan.patches),
            "unbound": len(plan.unbound),
            "rejected": plan.rejected,
        },
    }
    summary["stubs"] = stubs["counts"]
    (args.out / "link-imports.json").write_text(json.dumps(stubs["report"], indent=2) + "\n")
    (args.out / "link-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: (len(v) if k in ("holes", "failed") else v) for k, v in summary.items() if k != "undefined"}, indent=2))
    print({k: len(v) for k, v in summary["undefined"].items()}, "undefined symbols")
    return 0 if not summary["failed"] and not summary["undefined"]["bodies"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
