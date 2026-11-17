#!/usr/bin/env -S uv run --script
"""Account for every byte of the shipped image's executable sections.

A complete lift starts from knowing what the image holds: the `.eh_frame` bodies, the bytes between
them (alignment padding, zero fill, or code no frame record covers) and the frame-less stub sections.
"""

from __future__ import annotations

from lift_probe import Fde

NOP_PREFIXES = {0x66, 0x2E}
SINGLE_BYTE_PADDING = {0x90, 0xCC}


def _nop_length(gap: bytes, i: int) -> int:
    """Length of the nop instruction at `i`, or 0 when the bytes there are not a nop."""
    if gap[i] in SINGLE_BYTE_PADDING:
        return 1
    j = i
    while j < len(gap) and gap[j] in NOP_PREFIXES:
        j += 1
    if j < len(gap) and gap[j] == 0x90:
        return j - i + 1
    if j + 2 < len(gap) and gap[j] == 0x0F and gap[j + 1] == 0x1F:
        modrm = gap[j + 2]
        mod, rm = modrm >> 6, modrm & 7
        if mod == 3:
            return 0
        length = j - i + 3
        if rm == 4:
            length += 1
        length += {0: 4 if rm == 5 else 0, 1: 1, 2: 4}[mod]
        sib_base_disp = 4 if rm == 4 and mod == 0 and j + 3 < len(gap) and gap[j + 3] & 7 == 5 else 0
        length += sib_base_disp
        return length if i + length <= len(gap) else 0
    return 0


def classify_gap(gap: bytes) -> str:
    """`padding` when the gap decodes to nops only, `zero_fill` when all zero, else `other`."""
    if gap and not any(gap):
        return "zero_fill"
    i = 0
    while i < len(gap):
        n = _nop_length(gap, i)
        if n == 0:
            return "other"
        i += n
    return "padding"


def gaps(fdes: list[Fde], start: int, end: int) -> list[tuple[int, int]]:
    """Byte ranges of [start, end) that no body covers, as (address, size)."""
    out = []
    pos = start
    for fde in sorted(fdes, key=lambda f: f.start):
        if fde.start >= end:
            break
        if fde.start > pos:
            out.append((pos, fde.start - pos))
        pos = max(pos, min(fde.start + fde.size, end))
    if pos < end:
        out.append((pos, end - pos))
    return out


def account_section(name: str, start: int, end: int, data: bytes, fdes: list[Fde], stubs: bool) -> dict:
    """Every byte of one executable section: body, padding, zero fill, stub or unaccounted."""
    inside = [f for f in fdes if start <= f.start < end]
    gap_list = gaps(inside, start, end)
    acct = {
        "name": name,
        "start": start,
        "size": end - start,
        "bodies": len(inside),
        "body_bytes": sum(min(f.start + f.size, end) - f.start for f in inside),
        "gap_bytes": {"padding": 0, "zero_fill": 0, "other": 0},
        "stub_bytes": 0,
        "unaccounted": [],
    }
    for addr, size in gap_list:
        if stubs:
            acct["stub_bytes"] += size
            continue
        kind = classify_gap(data[addr - start : addr - start + size])
        acct["gap_bytes"][kind] += size
        if kind == "other":
            acct["unaccounted"].append({"start": addr, "size": size})
    return acct


def coverage_complete(sections: dict[str, dict]) -> bool:
    return not any(acct["unaccounted"] for acct in sections.values())


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import lift_probe as lp
    import subprocess

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("so", nargs="?", type=lp.Path, default=lp.DEFAULT_SO)
    ap.add_argument("--out", type=lp.Path, default=lp.REPO / ".tools/lift-image")
    args = ap.parse_args(argv)
    if not args.so.exists():
        raise SystemExit(f"no ELF at {args.so}")
    readelf = lp.run_tool([lp.LLVM / "llvm-readelf", "-S", args.so], text=True).stdout
    frames = lp.parse_fdes(lp.run_tool([lp.LLVM / "llvm-dwarfdump", "--eh-frame", args.so], text=True).stdout)
    data = args.so.read_bytes()
    stub_sections = {".plt"}
    report = {"binary_sha256": lp.sha256(args.so), "sections": {}}
    for name, (start, end) in lp.parse_exec_sections(readelf).items():
        report["sections"][name] = account_section(name, start, end, data[start:end], frames, name in stub_sections)
    outside = [f for f in frames if not any(s["start"] <= f.start < s["start"] + s["size"] for s in report["sections"].values())]
    report["bodies_outside_executable_sections"] = [hex(f.start) for f in outside]
    report["coverage_complete"] = coverage_complete(report["sections"]) and not outside
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "coverage.json").write_text(json.dumps(report, indent=2) + "\n")
    for acct in report["sections"].values():
        print(
            f"{acct['name']:8} {acct['size']:>10} B  bodies {acct['bodies']:>7}  body {acct['body_bytes']:>10}  "
            f"padding {acct['gap_bytes']['padding']:>8}  stub {acct['stub_bytes']:>6}  unaccounted {len(acct['unaccounted'])}"
        )
    return 0 if report["coverage_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
