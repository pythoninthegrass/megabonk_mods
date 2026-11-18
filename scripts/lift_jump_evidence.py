"""Recover jump-table evidence for explicit body addresses without regenerating baseline pcode."""

import argparse
import hashlib
import json
import lift_probe as lp
import subprocess
import tempfile
from lift_image import read_shard, shard_identity, write_shard
from lift_tables import decode_table, direct_branch_targets, elf_reader, objdump_disassembler, parse_table_pattern, window_for
from pathlib import Path

SCRIPT = Path(__file__).with_name("lift_jump_evidence") / "LiftJumpEvidence.java"


def audit_row(body, row, disassemble, read):
    """Decodes the jump-table bytes behind each recovered table and keeps Ghidra's extras as unverified."""
    boundaries = sorted({i["a"] for i in row.get("insns", [])})
    direct = direct_branch_targets(row)
    unverified = unaudited = unexplained = 0
    tables = []
    for table in row["jt"]:
        entry = dict(table)
        pattern = parse_table_pattern(disassemble(window_for(boundaries, table["at"])), table["at"])
        if pattern is None:
            unaudited += 1
        else:
            count = pattern["count"] if pattern["count"] is not None else len(table["cases"])
            raw = decode_table(pattern, count, read)
            entry["raw"] = raw
            entry["raw_matches"] = raw == table["cases"]
            if not entry["raw_matches"]:
                unverified += 1
                extras = [case for case in table["cases"] if case not in raw]
                entry["extra_cases"] = extras
                entry["missing_cases"] = [case for case in raw if case not in table["cases"]]
                entry["extra_direct_edges"] = [case for case in extras if case in direct]
                rest = [case for case in extras if case not in direct]
                entry["extra_outside_body"] = [
                    case for case in rest if not body.start <= case < body.start + body.size
                ]
                entry["extra_unexplained"] = [
                    case for case in rest if body.start <= case < body.start + body.size
                ]
                unexplained += len(entry["extra_unexplained"])
        tables.append(entry)
    return {
        **row, "jt": tables,
        "tables_unverified": unverified, "tables_unaudited": unaudited, "extra_unexplained": unexplained,
    }


def check_table_bounds(body, row):
    def inside(address):
        return body.start <= address < body.start + body.size

    outside = []
    for table in row["jt"]:
        cases = [address for address in table["cases"] if not inside(address)]
        if cases or not inside(table["at"]):
            outside.append({"at": table["at"], "cases": cases})
    if not outside:
        return row
    status = "unresolved_bounds" if row["status"] == "complete" else row["status"]
    return {**row, "status": status, "out_of_body": outside}


def recover(bodies, out, identity, dump, batch_size, audit=None):
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
                    if audit:
                        row = audit(body, row)
                    save(body, check_table_bounds(body, row))
            missing = [body for body in part if body.start not in records]
            if missing:
                active = work / "active"
                if finished or not active.exists() or active.read_text().strip() != f"{missing[0].start:x}":
                    raise ValueError("evidence batch exited without completing or identifying its active body")
                body = missing[0]
                save(body, {"start": body.start, "size": body.size, "status": "batch_timeout", "jt": []})
        pending = [body for body in pending if body.start not in records]
    return [records[body.start] for body in bodies]


def dump_batch(so, part, work, function_timeout, batch_timeout, emit_c, bounded, output_log):
    ranges = work / "ranges.txt"
    ranges.write_text("".join(f"{b.start:x} {b.size}\n" for b in part))
    project = work / "project"
    project.mkdir()
    cmd = [
        lp.find_ghidra(), project, "evidence", "-import", so.resolve(), "-noanalysis",
        "-scriptPath", SCRIPT.parent, "-postScript", SCRIPT.name, ranges, work,
        str(function_timeout), str(emit_c).lower(), str(bounded).lower(),
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


def audit_baseline(so, shards, out, addresses=None):
    """Audits every baseline row with jump tables against the ELF bytes, no Ghidra involved."""
    read = elf_reader(so)
    disassemble = objdump_disassembler(so, lp.LLVM / "llvm-objdump")
    selected, totals = [], {"rows": 0, "matched": 0, "unverified": 0, "unaudited": 0}
    for path in sorted(shards.glob("pcode-*.jsonl")):
        with path.open() as handle:
            for line in handle:
                if not line.startswith('{"start": '):
                    continue
                row = json.loads(line)
                if not row.get("jt") or (addresses is not None and row["start"] not in addresses):
                    continue
                audited = audit_row(lp.Fde(row["start"], row["size"]), row, disassemble, read)
                totals["rows"] += 1
                if audited["tables_unaudited"]:
                    totals["unaudited"] += 1
                elif audited["tables_unverified"]:
                    totals["unverified"] += 1
                else:
                    totals["matched"] += 1
                selected.append(audited)
    (out / "audit.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (out / "audit.jsonl").write_text("".join(json.dumps(row) + "\n" for row in selected))
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("addresses", type=lambda value: int(value, 0), nargs="*")
    parser.add_argument("--so", type=Path, default=lp.DEFAULT_SO)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--baseline", type=Path, help="audit jump tables in a pcode shard directory instead of running Ghidra")
    parser.add_argument("--function-timeout", type=int, default=5)
    parser.add_argument("--batch-timeout", type=int, default=90)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--emit-c", action="store_true", help="enable C output for a comparison run")
    parser.add_argument("--bounded", action="store_true", help="assign the exact frame range as the Ghidra function body")
    args = parser.parse_args()
    if args.baseline is not None:
        totals = audit_baseline(args.so, args.baseline, args.out, set(args.addresses) or None)
        (args.out / "audit-summary.json").write_text(json.dumps(totals) + "\n")
        print(f"Audited {totals['rows']} table-bearing rows in {args.out / 'audit.jsonl'}: {totals}")
        return 0
    if not args.addresses:
        parser.error("give body addresses or --baseline DIR")
    if min(args.function_timeout, args.batch_timeout, args.batch_size) <= 0:
        parser.error("timeouts and batch size must be positive")
    selected = set(args.addresses)
    frames = lp.parse_fdes(lp.run_tool([lp.LLVM / "llvm-dwarfdump", "--eh-frame", args.so], text=True, check=True).stdout)
    bodies = sorted((b for b in frames if b.size > 0 and b.start in selected), key=lambda b: b.start)
    if len(bodies) != len(selected) or {b.start for b in bodies} != selected:
        parser.error("each address must identify exactly one nonempty frame body")
    settings = json.dumps([args.function_timeout, args.batch_timeout, args.batch_size, args.emit_c, args.bounded])
    fingerprint = hashlib.sha256(Path(__file__).read_bytes() + SCRIPT.read_bytes()).hexdigest()
    identity = shard_identity(lp.sha256(args.so), fingerprint, lp.ghidra_version(), bodies, settings)

    def dump(part, work):
        print(f"Recovering jump tables for: {', '.join(hex(b.start) for b in part)}", flush=True)
        return dump_batch(
            args.so, part, work, args.function_timeout, args.batch_timeout, args.emit_c, args.bounded,
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
