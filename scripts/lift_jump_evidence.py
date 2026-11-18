"""Recover jump-table evidence for explicit body addresses without regenerating baseline pcode."""

import argparse
import hashlib
import json
import lift_probe as lp
import subprocess
import tempfile
from lift_image import read_shard, shard_identity, write_shard
from pathlib import Path

SCRIPT = Path(__file__).with_name("lift_jump_evidence") / "LiftJumpEvidence.java"


def recover(bodies, out, identity, dump, batch_size):
    out.mkdir(parents=True, exist_ok=True)
    pending, records = [], {}

    def key(body):
        return out / f"{body.start:x}.jsonl"

    def save(body, row):
        write_shard(key(body), identity, [row])
        records[body.start] = row

    for body in bodies:
        cached = read_shard(key(body), identity, [body])
        if cached:
            records[body.start] = cached[0]
        else:
            pending.append(body)
    while pending:
        part = pending[:batch_size]
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            finished = dump(part, work)
            for body in part:
                path = work / f"{body.start:x}.json"
                if path.exists():
                    row = json.loads(path.read_text())
                    if (row["start"], row["size"]) != (body.start, body.size):
                        raise ValueError(f"unexpected evidence row for {body.start:#x}")
                    save(body, row)
            missing = [body for body in part if body.start not in records]
            if missing:
                active = work / "active"
                if finished or not active.exists() or active.read_text().strip() != f"{missing[0].start:x}":
                    raise ValueError("evidence batch exited without completing or identifying its active body")
                body = missing[0]
                save(body, {"start": body.start, "size": body.size, "status": "batch_timeout", "jt": []})
        pending = [body for body in pending if body.start not in records]
    return [records[body.start] for body in bodies]


def dump_batch(so, part, work, function_timeout, batch_timeout, emit_c, output_log):
    ranges = work / "ranges.txt"
    ranges.write_text("".join(f"{b.start:x} {b.size}\n" for b in part))
    project = work / "project"
    project.mkdir()
    cmd = [
        lp.find_ghidra(), project, "evidence", "-import", so.resolve(), "-noanalysis",
        "-scriptPath", SCRIPT.parent, "-postScript", SCRIPT.name, ranges, work,
        str(function_timeout), str(emit_c).lower(),
    ]
    try:
        result = lp.run_tool(cmd, env=lp.ghidra_env(), timeout=batch_timeout, text=True)
    except subprocess.TimeoutExpired as exc:
        output_log.write_text(lp.as_text(exc.stdout) + lp.as_text(exc.stderr))
        return False
    output_log.write_text(result.stdout + result.stderr)
    if result.returncode != 0:
        raise ValueError(f"Ghidra exited {result.returncode}; see {output_log}")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("addresses", type=lambda value: int(value, 0), nargs="+")
    parser.add_argument("--so", type=Path, default=lp.DEFAULT_SO)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--function-timeout", type=int, default=5)
    parser.add_argument("--batch-timeout", type=int, default=90)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--emit-c", action="store_true", help="enable C output for a comparison run")
    args = parser.parse_args()
    if min(args.function_timeout, args.batch_timeout, args.batch_size) <= 0:
        parser.error("timeouts and batch size must be positive")
    selected = set(args.addresses)
    frames = lp.parse_fdes(lp.run_tool([lp.LLVM / "llvm-dwarfdump", "--eh-frame", args.so], text=True, check=True).stdout)
    bodies = sorted((b for b in frames if b.size > 0 and b.start in selected), key=lambda b: b.start)
    if len(bodies) != len(selected) or {b.start for b in bodies} != selected:
        parser.error("each address must identify exactly one nonempty frame body")
    settings = json.dumps([args.function_timeout, args.batch_timeout, args.batch_size, args.emit_c])
    fingerprint = hashlib.sha256(Path(__file__).read_bytes() + SCRIPT.read_bytes()).hexdigest()
    identity = shard_identity(lp.sha256(args.so), fingerprint, lp.ghidra_version(), bodies, settings)

    def dump(part, work):
        print(f"Recovering jump tables for: {', '.join(hex(b.start) for b in part)}", flush=True)
        return dump_batch(
            args.so, part, work, args.function_timeout, args.batch_timeout, args.emit_c,
            args.out / f"batch-{part[0].start:x}.log",
        )

    try:
        rows = recover(bodies, args.out, identity, dump, args.batch_size)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
    (args.out / "evidence.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    print(f"Recorded evidence for {len(rows)} bodies in {args.out / 'evidence.jsonl'}")
    return int(any(row["status"] != "complete" for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
