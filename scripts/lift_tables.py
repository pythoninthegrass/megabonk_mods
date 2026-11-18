"""Table-byte evidence: what the image's own bytes say a switch's cases are, independent of Ghidra's case list."""

from __future__ import annotations

import bisect
import re
import struct
import subprocess
from pathlib import Path

MAX_CASES = 4096

_GPR64 = ["rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp"] + [f"r{i}" for i in range(8, 16)]
_LOW32 = dict(zip(_GPR64, ["eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"] + [f"r{i}d" for i in range(8, 16)]))
_LOW16 = dict(zip(_GPR64, ["ax", "bx", "cx", "dx", "si", "di", "bp", "sp"] + [f"r{i}w" for i in range(8, 16)]))
_LOW8 = dict(zip(_GPR64, ["al", "bl", "cl", "dl", "sil", "dil", "bpl", "spl"] + [f"r{i}b" for i in range(8, 16)]))


def _register(operand):
    """The 64-bit name of a general-purpose register operand, so %eax and %rax are read as one register."""
    text = operand.strip()
    if not text.startswith("%"):
        return None
    name = text[1:].lower().split()[0].rstrip(",")
    for reg in _GPR64:
        if name in (reg, _LOW32[reg], _LOW16[reg], _LOW8[reg]):
            return reg
    return None


def _operands(text):
    """Splits an operand list on its top-level commas, so a memory operand's own commas stay inside it."""
    parts, depth, current = [], 0, ""
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
            continue
        current += char
    parts.append(current)
    return [part.strip() for part in parts if part.strip()]


def _index_write(text, index):
    """Classifies what an instruction does to the switch index, or None when it destroys the bounded value.

    Returns ("kept" | "self" | "load", source operand): "self" is a move within the index register, "load"
    is a move from `source` into it. Only the compared operand may feed a load into the index.
    """
    mnemonic, _, rest = re.sub(r"\s+#.*", "", text).partition(" ")
    parts = _operands(rest)
    if len(parts) == 1:
        if mnemonic.rstrip("bwlq") in ("inc", "dec", "neg", "not") and _register(parts[0]) == index:
            return None
        return "kept", None
    destination = parts[-1]
    if _register(destination) != index:
        return "kept", None
    if not mnemonic.startswith("mov"):
        return None
    source = parts[0]
    if _register(source) == index:
        return "self", source
    return "load", source


def _writes_operand(text, operand):
    """Whether an instruction stores to the guard's compared memory operand, which would make the guard stale."""
    _, _, rest = re.sub(r"\s+#.*", "", text).partition(" ")
    parts = _operands(rest)
    return len(parts) > 1 and parts[-1] == operand


def _bounds_index(lines, guard, entry_load, index, operand):
    """Whether the compared operand is the switch index: the register itself, or the memory a move brings into it.

    The value the guard bounded has to still be the index at the indexed load, so a move within the index
    register is allowed, a move of the compared operand into it is what ties a memory guard to the switch,
    and any other write to the index leaves the switch unbounded.
    """
    if index is None:
        return False
    memory_guard = _register(operand) is None
    tied = _register(operand) == index
    for m in range(guard + 1, entry_load):
        text = lines[m][1]
        if text.startswith("call"):
            return False
        if re.match(r"(cmp|test)\w*\s", text):
            continue
        if memory_guard and _writes_operand(text, operand):
            return False
        verdict = _index_write(text, index)
        if verdict is None:
            return False
        kind, source = verdict
        if kind == "load":
            tied = source == operand
    return tied


def parse_table_pattern(text, site):
    """Reads the jump-table base, entry size and case count off the lea/movslq/add/jmp sequence at one site."""
    lines = []
    for line in text.splitlines():
        match = re.match(r"^\s*([0-9a-f]+):\s*(.*)$", line)
        if match and match.group(2).strip():
            lines.append((int(match.group(1), 16), re.sub(r"\s+", " ", match.group(2).strip())))
        elif line.strip():
            lines.append((None, re.sub(r"\s+", " ", line.strip())))
    for i in range(len(lines) - 1, -1, -1):
        addr, body = lines[i]
        if addr != site:
            continue
        site_match = re.fullmatch(r"jmpq?\s+\*\s*%(\w+)", body)
        if not site_match:
            return None
        reg = site_match.group(1)
        for j in range(i - 1, max(i - 10, -1), -1):
            entry = re.fullmatch(r"movs(l?)q\s+\(%(\w+),%(\w+),([48])\),\s*%(\w+)", lines[j][1])
            if not entry or entry.group(5) != reg:
                continue
            base_reg, index_reg, scale = entry.group(2), _register(f"%{entry.group(3)}"), int(entry.group(4))
            if index_reg is None:
                continue
            if scale == 4:
                added = re.fullmatch(r"addq\s+%(\w+),\s*%(\w+)", lines[j + 1][1]) if j + 1 < i else None
                if not added or added.groups() != (base_reg, reg):
                    continue
            table = None
            for k in range(j - 1, max(j - 14, -1), -1):
                table = re.fullmatch(r"lea\S*\s+.*\(%rip\),\s*%(\w+)\s+#\s*(0x[0-9a-f]+)\b.*", lines[k][1])
                if table and table.group(1) == base_reg:
                    if any(f"%{base_reg}" in lines[m][1] for m in range(k + 1, j)):
                        return None
                    break
                table = None
            if not table:
                continue
            count = None
            for m in range(j - 1, max(k - 10, -1), -1):
                bound = re.fullmatch(r"cmp[bwlq]?\s+\$(0x[0-9a-f]+),\s*(.+)", lines[m][1])
                taken = m + 1 < j and re.fullmatch(r"ja(?:e)?\s+\S+.*", lines[m + 1][1])
                if not (bound and taken):
                    continue
                operand = re.sub(r"\s+#.*", "", bound.group(2)).strip()
                if not _bounds_index(lines, m, j, index_reg, operand):
                    continue
                entries = int(bound.group(1), 16) + 1
                count = entries if entries <= MAX_CASES else None
                break
            return {"base": int(table.group(2), 16), "scale": scale, "count": count}
    return None


def window_for(boundaries, at, context=24):
    """Picks a disassembly window that starts on an instruction boundary Ghidra itself reported."""
    if not boundaries:
        return (max(0, at - 8 * context), at + 2)
    index = bisect.bisect_right(boundaries, at) - 1
    if index < 0:
        return (max(0, at - 8 * context), at + 2)
    return (boundaries[max(0, min(index, len(boundaries) - 1) - context)], at + 2)


def direct_branch_targets(row):
    """Addresses the body reaches by an unconditional or conditional direct branch in its own pcode."""
    targets = set()
    for insn in row.get("insns", []):
        for op in insn.get("ops", []):
            if op["op"] not in ("BRANCH", "CBRANCH") or not op.get("in"):
                continue
            if op["in"][0].startswith("ram,"):
                targets.add(int(op["in"][0].split(",")[1], 16))
    return targets


def decode_table(pattern, count, read):
    """Decodes `count` entries of the table the pattern names; 4-byte entries are base-relative."""
    raw = read(pattern["base"], count * pattern["scale"])
    if pattern["scale"] == 4:
        return [pattern["base"] + e for e in struct.unpack(f"<{count}i", raw)]
    return list(struct.unpack(f"<{count}Q", raw))


def elf_reader(path):
    """Returns one shared vaddr-to-bytes reader per image, so a run reads the ELF once."""
    key = str(Path(path))
    if key not in _READERS:
        _READERS[key] = _load_elf_reader(path)
    return _READERS[key]


_READERS: dict[str, object] = {}


def _load_elf_reader(path):
    data = Path(path).read_bytes()
    phoff, = struct.unpack_from("<Q", data, 0x20)
    phentsize, phnum = struct.unpack_from("<HH", data, 0x36)
    loads = []
    for index in range(phnum):
        off = phoff + index * phentsize
        if struct.unpack_from("<I", data, off)[0] == 1:
            offset, vaddr = struct.unpack_from("<QQ", data, off + 8)
            filesz, = struct.unpack_from("<Q", data, off + 32)
            loads.append((vaddr, offset, filesz))

    def read(vaddr, n):
        for base, offset, size in loads:
            if base <= vaddr and vaddr + n <= base + size:
                return data[offset + vaddr - base: offset + vaddr - base + n]
        raise ValueError(f"0x{vaddr:x} is not backed by file bytes")

    return read


def objdump_disassembler(so, objdump):
    cache = {}

    def disassemble(window):
        if window not in cache:
            result = subprocess.run(
                [
                    str(objdump), "-d", "--no-show-raw-insn",
                    f"--start-address={window[0]:#x}", f"--stop-address={window[1]:#x}", str(so),
                ],
                capture_output=True,
                text=True,
            )
            cache[window] = result.stdout
        return cache[window]

    return disassemble


class TableEvidence:
    """Answers what the image's table bytes say about one switch site, and reads the image only when asked."""

    def __init__(self, so, objdump):
        self.so = Path(so)
        self.objdump = objdump
        self._read = None
        self._disassemble = None

    def raw_cases(self, boundaries, site):
        """Case addresses the table at `site` holds, or None unless the pattern and its case bound are both present."""
        if self._read is None:
            self._read = elf_reader(self.so)
            self._disassemble = objdump_disassembler(self.so, self.objdump)
        pattern = parse_table_pattern(self._disassemble(window_for(boundaries, site)), site)
        if pattern is None or pattern["count"] is None:
            return None
        try:
            return decode_table(pattern, pattern["count"], self._read)
        except ValueError:
            return None
