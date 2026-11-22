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


CALLEE_SAVED = ("rbx", "rbp", "r12", "r13", "r14", "r15")
RIP_LEA = r"lea\S*\s+.*\(%rip\),\s*%(\w+)\s+#\s*(0x[0-9a-f]+)\b.*"


def _mentions(text, reg):
    """Whether an instruction names a general-purpose register in any width."""
    return any(_register(token) == reg for token in re.findall(r"%\w+", re.sub(r"\s+#.*", "", text)))


def _writes_register(text, reg):
    """Whether an instruction stores to a register: its last operand, an exchange, or a one-operand writer."""
    mnemonic, _, rest = re.sub(r"\s+#.*", "", text).partition(" ")
    parts = _operands(rest)
    if mnemonic.startswith(("cmp", "test", "push", "j", "call", "nop", "bt")) or not parts:
        return False
    if mnemonic.startswith(("xchg", "xadd")):
        return any(_register(part) == reg for part in parts)
    return _register(parts[-1]) == reg


def _single_lea_base(body, reg):
    """The table address a callee-saved register holds when the body writes it once, by a rip-relative lea.

    A push or pop of the register only saves and restores the caller's value. Compiler-generated code
    that indexes a table through the register has that table's address in it on every path to the
    switch, so one write in the whole body names the table. Any other write, before or after the
    site, or a register a call could change, names nothing.
    """
    if reg not in CALLEE_SAVED:
        return None
    found = []
    for line in body.splitlines():
        match = re.match(r"^\s*([0-9a-f]+):\s*(.*)$", line)
        if not match:
            continue
        text = re.sub(r"\s+", " ", match.group(2).strip())
        lea = re.fullmatch(RIP_LEA, text)
        if lea and _register(f"%{lea.group(1)}") == reg:
            found.append(int(lea.group(2), 16))
        elif re.match(r"(push|pop)q?\s", text) and len(_operands(text.partition(" ")[2])) == 1:
            continue
        elif _writes_register(text, reg):
            return None
    return found[0] if len(found) == 1 else None


def _base_untouched(lines, lea, load, base_reg, alias):
    """Whether the table base survives from its lea to the indexed load, copied once to `alias` if the add reads a copy.

    Any other mention of the base ends the match. A copy is the base moved whole into a second register
    that nothing touches, and no call intervenes, before the add reads it.
    """
    copied = None
    for m in range(lea + 1, load):
        text = lines[m][1]
        if f"%{base_reg}" not in text:
            continue
        copy = re.fullmatch(rf"movq\s+%{base_reg},\s*%(\w+)", text)
        if alias is None or copied is not None or not copy or copy.group(1) != alias:
            return False
        copied = m
    if alias is None:
        return True
    if copied is None or alias == _register(f"%{base_reg}") or _register(f"%{alias}") is None:
        return False
    alias_reg = _register(f"%{alias}")
    return not any(lines[m][1].startswith("call") or _mentions(lines[m][1], alias_reg) for m in range(copied + 1, load + 1))


def parse_table_pattern(text, site, body=None):
    """Reads the jump-table base, entry size and case count off the lea/movslq/add/jmp sequence at one site."""
    pattern = match_table_pattern(text, site, body)
    return None if pattern is None else {key: value for key, value in pattern.items() if key != "window"}


def match_table_pattern(text, site, body=None):
    """The table pattern plus `window`, the address of the earlier of its bound compare and base lea.

    A guarded dispatch is only straight-line code from `window` to the jump, so a caller can refuse a
    site that something else branches into. With `body`, the whole body's disassembly, a base held in a
    callee-saved register that the window never sets is read from the body's one write to it, and the
    window then starts at the bound compare.
    """
    lines = []
    for line in text.splitlines():
        match = re.match(r"^\s*([0-9a-f]+):\s*(.*)$", line)
        if match and match.group(2).strip():
            lines.append((int(match.group(1), 16), re.sub(r"\s+", " ", match.group(2).strip())))
        elif line.strip():
            lines.append((None, re.sub(r"\s+", " ", line.strip())))
    for i in range(len(lines) - 1, -1, -1):
        addr, body_line = lines[i]
        if addr != site:
            continue
        site_match = re.fullmatch(r"jmpq?\s+\*\s*%(\w+)", body_line)
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
            alias = None
            if scale == 4:
                added = re.fullmatch(r"addq\s+%(\w+),\s*%(\w+)", lines[j + 1][1]) if j + 1 < i else None
                if not added or added.group(2) != reg:
                    continue
                alias = None if added.group(1) == base_reg else added.group(1)
            table, k = None, None
            for k in range(j - 1, max(j - 14, -1), -1):
                table = re.fullmatch(RIP_LEA, lines[k][1])
                if table and table.group(1) == base_reg:
                    if not _base_untouched(lines, k, j, base_reg, alias):
                        return None
                    break
                table = None
            base = int(table.group(2), 16) if table else None
            if not table:
                k = None
                far = _single_lea_base(body, _register(f"%{base_reg}")) if body is not None and alias is None else None
                if far is None:
                    continue
                base = far
            count, window = None, None
            for m in range(j - 1, max(k - 10, -1) if k is not None else max(j - 24, -1), -1):
                bound = re.fullmatch(r"cmp[bwlq]?\s+\$(0x[0-9a-f]+),\s*(.+)", lines[m][1])
                taken = m + 1 < j and re.fullmatch(r"ja(?:e)?\s+\S+.*", lines[m + 1][1])
                if not (bound and taken):
                    continue
                operand = re.sub(r"\s+#.*", "", bound.group(2)).strip()
                if not _bounds_index(lines, m, j, index_reg, operand):
                    continue
                entries = int(bound.group(1), 16) + 1
                count = entries if entries <= MAX_CASES else None
                if count is not None:
                    window = lines[m][0] if k is None else min(lines[k][0], lines[m][0])
                break
            return {"base": base, "scale": scale, "count": count, "window": window}
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
    (phoff,) = struct.unpack_from("<Q", data, 0x20)
    phentsize, phnum = struct.unpack_from("<HH", data, 0x36)
    loads = []
    for index in range(phnum):
        off = phoff + index * phentsize
        if struct.unpack_from("<I", data, off)[0] == 1:
            offset, vaddr = struct.unpack_from("<QQ", data, off + 8)
            (filesz,) = struct.unpack_from("<Q", data, off + 32)
            loads.append((vaddr, offset, filesz))

    def read(vaddr, n):
        for base, offset, size in loads:
            if base <= vaddr and vaddr + n <= base + size:
                return data[offset + vaddr - base : offset + vaddr - base + n]
        raise ValueError(f"0x{vaddr:x} is not backed by file bytes")

    return read


def objdump_disassembler(so, objdump):
    cache = {}

    def disassemble(window):
        if window not in cache:
            result = subprocess.run(
                [
                    str(objdump),
                    "-d",
                    "--no-show-raw-insn",
                    f"--start-address={window[0]:#x}",
                    f"--stop-address={window[1]:#x}",
                    str(so),
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

    def raw_table(self, boundaries, site):
        """The table at `site` as base, entry size, case count, decoded cases and guarded window, or None when unproven."""
        if self._read is None:
            self._read = elf_reader(self.so)
            self._disassemble = objdump_disassembler(self.so, self.objdump)
        text = self._disassemble(window_for(boundaries, site))
        pattern = match_table_pattern(text, site)
        if pattern is None and boundaries:
            pattern = match_table_pattern(text, site, body=self._disassemble((boundaries[0], boundaries[-1] + 15)))
        if pattern is None or pattern["count"] is None:
            return None
        try:
            return {**pattern, "cases": decode_table(pattern, pattern["count"], self._read)}
        except ValueError:
            return None

    def raw_cases(self, boundaries, site):
        """Case addresses the table at `site` holds, or None unless the pattern and its case bound are both present."""
        table = self.raw_table(boundaries, site)
        return None if table is None else table["cases"]
