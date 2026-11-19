"""Tests for bounded, resumable jump-table evidence recovery and the table-byte audit."""

import json
import lift_jump_evidence as evidence
import lift_tables as tables
import subprocess
from lift_probe import Fde
from pathlib import Path


def test_out_of_body_switch_evidence_is_preserved_but_unresolved():
    body = Fde(0x1000, 8)
    tables = [{"at": 0x1002, "cases": [0x1004, 0x1008]}, {"at": 0x1010, "cases": [0x1001]}]
    row = {"start": body.start, "size": body.size, "status": "complete", "jt": tables}
    assert evidence.check_table_bounds(body, row) == {
        **row, "status": "unresolved_bounds",
        "out_of_body": [{"at": 0x1002, "cases": [0x1008]}, {"at": 0x1010, "cases": []}],
    }
    clean = {**row, "jt": [{"at": 0x1002, "cases": [0x1007]}]}
    assert evidence.check_table_bounds(body, clean) == clean


PATTERN_TEXT = """
 4bd70f3:   \tcmpl\t$0x51, %edi
 4bd70f6:   \tja\t0x4bd710a <__start_il2cpp+0x2a7477a>
 4bd70f8:   \tmovb\t$0x1, %al
 4bd70fa:   \tleaq\t-0x3fdb239(%rip), %rcx  # 0xbfbec8
 4bd7101:   \tmovslq\t(%rcx,%rdi,4), %rdx
 4bd7105:   \taddq\t%rcx, %rdx
 4bd7108:   \tjmpq\t*%rdx
 4bd710a:   \txorl\t%eax
 4bd710c:   \tjmpq\t*%rax
"""

FAR_TABLE_TEXT = """
 2159d3e:   \tcmpl\t$0x10, 0x34(%rsp)
 2159d43:   \tleaq\t-0x119ff3e(%rip), %r15  # 0xfb9e0c <_ZTSSt12system_error+0x8c>
 2159d4a:   \tsete\t%dl
 2159d4d:   \tmovq\t0x10(%rax), %r12
 2159d51:   \tcmpq\t%r12, %r14
 2159d54:   \tsetb\t%al
 2159d57:   \txorl\t%r13d, %r13d
 2159d5a:   \tandl\t%eax, %edx
 2159d5c:   \tmovb\t%dl, 0x28(%rsp)
 2159d60:   \tcmpb\t$0x4, 0x5c(%rsp,%r13)
 2159d66:   \tja\t0x2159de6 <_ZNKSt9money_putIwE9_M_insertILb1EEE+0x2d2>
 2159d68:   \tmovzbl\t0x5c(%rsp,%r13), %eax
 2159d6e:   \tmovslq\t(%r15,%rax,4), %rax
 2159d72:   \taddq\t%r15, %rax
 2159d75:   \tjmpq\t*%rax
"""

STALE_TABLE_TEXT = FAR_TABLE_TEXT.replace(
    " 2159d68:   \tmovzbl\t0x5c(%rsp,%r13), %eax", " 2159d68:   \tmovq\t%rbx, %r15"
)

NO_GUARD_TEXT = """
 2126cdf:   \tcmpb\t$0x4, 0x5c(%rsp,%r13)
 2126ceb:   \tmovzbl\t0x5c(%rsp,%r13), %eax
 2126cf1:   \tleaq\t-0x116ec5c(%rip), %rdx  # 0xfb809c
 2126cf8:   \tmovslq\t(%rdx,%rax,4), %rax
 2126cfc:   \taddq\t%rdx, %rax
 2126cff:   \tjmpq\t*%rax
"""

ABSOLUTE_TEXT = """
 2000:   \tleaq\t-0x100(%rip), %rcx  # 0x2000
 2008:   \tmovsq\t(%rcx,%rdi,8), %rdx
 2010:   \tjmpq\t*%rdx
"""

SITE_TEXT = """
 1014:   \tcmp\t$0x1, %eax
 1016:   \tja\t0x1030
 1018:   \tleaq\t-0x20(%rip), %rcx  # 0x1000
 101c:   \tmovslq\t(%rcx,%rax,4), %rdx
 101e:   \taddq\t%rcx, %rdx
 1020:   \tjmpq\t*%rdx
"""


def test_table_pattern_reads_base_scale_and_case_count_at_the_site_only():
    assert evidence.parse_table_pattern(PATTERN_TEXT, 0x4BD7108) == {"base": 0xBFBEC8, "scale": 4, "count": 0x52}
    assert evidence.parse_table_pattern(ABSOLUTE_TEXT, 0x2010) == {"base": 0x2000, "scale": 8, "count": None}
    assert evidence.parse_table_pattern(FAR_TABLE_TEXT, 0x2159D75) == {"base": 0xFB9E0C, "scale": 4, "count": 5}
    assert evidence.parse_table_pattern(STALE_TABLE_TEXT, 0x2159D75) is None
    assert evidence.parse_table_pattern(PATTERN_TEXT, 0x4BD710C) is None
    assert evidence.parse_table_pattern(" 4bd70f8:   \tmovb\t$0x1, %al", 0x4BD70F8) is None


SYMBOL_ANNOTATED_TEXT = """
 2126cdf:      \tcmpb\t$0x4, 0x5c(%rsp,%r13)
 2126ce5:      \tja\t0x2126d93 <_ZNKSt7__cxx119money_putIcE9_M_insertILb1EEE+0x2f5>
 2126ceb:      \tmovzbl\t0x5c(%rsp,%r13), %eax
 2126cf1:      \tleaq\t-0x116ec5c(%rip), %rdx  # 0xfb809c <_ZNSt10money_base18_S_default_patternE+0x4>
 2126cf8:      \tmovslq\t(%rdx,%rax,4), %rax
 2126cfc:      \taddq\t%rdx, %rax
 2126cff:      \tjmpq\t*%rax
"""


def test_table_pattern_accepts_a_rip_comment_carrying_a_symbol():
    assert evidence.parse_table_pattern(SYMBOL_ANNOTATED_TEXT, 0x2126CFF) == {"base": 0xFB809C, "scale": 4, "count": 5}


def test_table_pattern_needs_a_taken_jump_after_the_bound():
    assert evidence.parse_table_pattern(NO_GUARD_TEXT, 0x2126CFF) == {"base": 0xFB809C, "scale": 4, "count": None}


UNTIED_BOUND_TEXT = SYMBOL_ANNOTATED_TEXT.replace("0x5c(%rsp,%r13), %eax", "0x5c(%rsp,%r13), %ecx")

CALLED_BOUND_TEXT = SYMBOL_ANNOTATED_TEXT.replace(
    " 2126ceb:      \tmovzbl",
    " 2126ceb:      \tcallq\t0x20565b0\n 2126cf0:      \tmovzbl",
)

CLOBBERED_BOUND_TEXT = SYMBOL_ANNOTATED_TEXT.replace(
    " 2126cf1:      \tleaq",
    " 2126cf0:      \txorl\t%eax, %eax\n 2126cf1:      \tleaq",
)


def test_the_case_bound_must_be_the_switch_index_and_nothing_else():
    assert evidence.parse_table_pattern(UNTIED_BOUND_TEXT, 0x2126CFF) == {"base": 0xFB809C, "scale": 4, "count": None}
    assert evidence.parse_table_pattern(CALLED_BOUND_TEXT, 0x2126CFF) == {"base": 0xFB809C, "scale": 4, "count": None}
    assert evidence.parse_table_pattern(CLOBBERED_BOUND_TEXT, 0x2126CFF) == {"base": 0xFB809C, "scale": 4, "count": None}


SELF_MOVING_BOUND_TEXT = """
 4e226fa:   \tcmpl\t$0x3, %eax
 4e226fd:   \tja\t0x4e22750 <__start_il2cpp+0x2cbfdc0>
 4e226ff:   \tmovl\t%eax, %eax
 4e22701:   \tleaq\t-0x4225304(%rip), %rcx  # 0xbfd404
 4e22708:   \tmovslq\t(%rcx,%rax,4), %rax
 4e2270c:   \taddq\t%rcx, %rax
 4e2270f:   \tjmpq\t*%rax
"""

WIDENED_BOUND_TEXT = """
 243cf70:   \tcmpb\t$0x3, %al
 243cf72:   \tja\t0x243d016 <__start_il2cpp+0x2da686>
 243cf78:   \tmovzbl\t%al, %eax
 243cf7b:   \tleaq\t-0x18ccfbe(%rip), %rcx  # 0xb6ffc4
 243cf82:   \tmovslq\t(%rcx,%rax,4), %rax
 243cf86:   \taddq\t%rcx, %rax
 243cf89:   \tjmpq\t*%rax
"""


def test_a_value_preserving_move_keeps_the_bound_and_an_unrelated_load_removes_it():
    assert evidence.parse_table_pattern(SELF_MOVING_BOUND_TEXT, 0x4E2270F) == {"base": 0xBFD404, "scale": 4, "count": 4}
    assert evidence.parse_table_pattern(WIDENED_BOUND_TEXT, 0x243CF89) == {"base": 0xB6FFC4, "scale": 4, "count": 4}
    rebound = WIDENED_BOUND_TEXT.replace("movzbl\t%al, %eax", "movl\t(%rdi), %eax")
    assert evidence.parse_table_pattern(rebound, 0x243CF89) == {"base": 0xB6FFC4, "scale": 4, "count": None}


def test_writing_the_guards_compared_memory_invalidates_the_bound():
    stale = SYMBOL_ANNOTATED_TEXT.replace(
        " 2126cf1:      \tleaq",
        " 2126cf0:      \tmovb\t%dl, 0x5c(%rsp,%r13)\n 2126cf1:      \tleaq",
    )
    assert evidence.parse_table_pattern(stale, 0x2126CFF) == {"base": 0xFB809C, "scale": 4, "count": None}


RIP_RELATIVE_BOUND_TEXT = """
 243cf4a:   \tcmpb\t$0x3, 0x2f1d6f9(%rip)   # 0x535a64a <_ZZ4mainE1x+0xa>
 243cf51:   \tja\t0x243d016 <__start_il2cpp+0x2da686>
 243cf53:   \tmovzbl\t0x2f1d6f9(%rip), %eax
 243cf7b:   \tleaq\t-0x18ccfbe(%rip), %rcx  # 0xb6ffc4
 243cf82:   \tmovslq\t(%rcx,%rax,4), %rax
 243cf86:   \taddq\t%rcx, %rax
 243cf89:   \tjmpq\t*%rax
"""


def test_a_rip_relative_guard_ties_to_the_index_by_its_operand_not_its_comment():
    assert evidence.parse_table_pattern(RIP_RELATIVE_BOUND_TEXT, 0x243CF89) == {
        "base": 0xB6FFC4,
        "scale": 4,
        "count": 4,
    }


def test_audit_separates_extras_from_another_frame_from_extras_on_the_bodys_own_code():
    body = Fde(0x1000, 0x40)
    row = {
        "start": 0x1000,
        "size": 0x40,
        "status": "complete",
        "insns": [{"a": a} for a in (0x1014, 0x1018, 0x101C, 0x1020, 0x1028)],
        "jt": [{"at": 0x1020, "cases": [0x1030, 0x1040, 0x1028, 0x900]}],
    }

    audited = evidence.audit_row(
        body, row, lambda window: SITE_TEXT, lambda vaddr, n: (0x30).to_bytes(4, "little") + (0x40).to_bytes(4, "little")
    )
    table = audited["jt"][0]
    assert table["extra_cases"] == [0x1028, 0x900]
    assert table["extra_direct_edges"] == []
    assert table["extra_outside_body"] == [0x900]
    assert table["extra_unexplained"] == [0x1028]
    assert audited["extra_unexplained"] == 1


def test_audit_baseline_sweeps_every_table_bearing_row_and_tallies_the_extras(tmp_path, monkeypatch):
    shards = tmp_path / "baseline"
    shards.mkdir()
    rows = [
        {"start": 0x1000, "size": 0x100, "status": "complete", "jt": [{"at": 0x1020, "cases": [0x1030, 0x1040]}]},
        {
            "start": 0x2000,
            "size": 0x100,
            "status": "complete",
            "jt": [{"at": 0x1020, "cases": [0x1030, 0x1040, 0x2050]}],
        },
        {"start": 0x3000, "size": 0x100, "status": "complete", "jt": [{"at": 0x3020, "cases": [0x3030]}]},
        {"start": 0x4000, "size": 0x100, "status": "complete", "jt": []},
    ]
    (shards / "pcode-0000.jsonl").write_text('{"identity": "x"}\n' + "".join(json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(evidence, "elf_reader", lambda so: (lambda vaddr, n: (0x30).to_bytes(4, "little") + (0x40).to_bytes(4, "little")))
    monkeypatch.setattr(
        evidence, "objdump_disassembler", lambda so, objdump: (lambda window: SITE_TEXT if window[1] == 0x1022 else "")
    )

    totals = evidence.audit_baseline(tmp_path / "GameAssembly.so", shards, tmp_path / "out")
    assert totals == {
        "rows": 3,
        "tables": 3,
        "matched": 1,
        "unverified": 1,
        "unaudited": 1,
        "extra_direct_edges": 0,
        "extra_outside_body": 0,
        "extra_unexplained": 1,
    }
    audited = [json.loads(line) for line in (tmp_path / "out" / "audit.jsonl").read_text().splitlines()]
    assert [row["start"] for row in audited] == [0x1000, 0x2000, 0x3000]


def test_audit_baseline_reads_only_shard_files(tmp_path, monkeypatch):
    shards = tmp_path / "baseline"
    shards.mkdir()
    row = {"start": 0x1000, "size": 0x100, "status": "complete", "jt": [{"at": 0x1020, "cases": [0x1030, 0x1040]}]}
    (shards / "pcode-0000.jsonl").write_text('{"identity": "x"}\n' + json.dumps(row) + "\n")
    for stray in ("pcode-0000.with-empty-fdes.jsonl", "pcode-0000.jsonl.bak", "scored-0000.jsonl"):
        (shards / stray).write_text('{"identity": "x"}\n' + json.dumps({**row, "start": 0x9000}) + "\n")
    monkeypatch.setattr(evidence, "elf_reader", lambda so: (lambda vaddr, n: (0x30).to_bytes(4, "little") + (0x40).to_bytes(4, "little")))
    monkeypatch.setattr(evidence, "objdump_disassembler", lambda so, objdump: (lambda window: SITE_TEXT))

    totals = evidence.audit_baseline(tmp_path / "GameAssembly.so", shards, tmp_path / "out")
    assert totals["rows"] == 1
    audited = [json.loads(line) for line in (tmp_path / "out" / "audit.jsonl").read_text().splitlines()]
    assert [row["start"] for row in audited] == [0x1000]


def test_audit_compares_recovered_cases_with_the_table_bytes_and_keeps_the_extras():
    body = Fde(0x1000, 0x100)
    row = {"start": 0x1000, "size": 0x100, "status": "complete", "jt": [{"at": 0x1020, "cases": [0x1030, 0x1040, 0x900]}]}

    def disassemble(window):
        assert window == (0xF60, 0x1022)
        return SITE_TEXT

    def read(vaddr, n):
        assert (vaddr, n) == (0x1000, 8)
        return (0x30).to_bytes(4, "little") + (0x40).to_bytes(4, "little")

    audited = evidence.audit_row(body, row, disassemble, read)
    table = audited["jt"][0]
    assert audited["status"] == "complete"
    assert table["raw"] == [0x1030, 0x1040]
    assert table["raw_matches"] is False
    assert table["extra_cases"] == [0x900]
    assert table["missing_cases"] == []
    assert audited["tables_unverified"] == 1
    assert audited["tables_unaudited"] == 0

    honest = {"start": 0x1000, "size": 0x100, "status": "complete", "jt": [{"at": 0x1020, "cases": [0x1030, 0x1040]}]}
    assert evidence.audit_row(body, honest, disassemble, read)["tables_unverified"] == 0

    def no_pattern(window):
        return " 1020:   \tjmpq\t*%rdx"

    unaudited = evidence.audit_row(body, row, no_pattern, read)
    assert "raw" not in unaudited["jt"][0]
    assert unaudited["tables_unaudited"] == 1


def test_audit_starts_the_disassembly_window_at_a_known_instruction_boundary():
    body = Fde(0x1000, 0x200)

    def row_for(insns, at):
        return {"start": 0x1000, "size": 0x200, "status": "complete", "insns": [{"a": a} for a in insns], "jt": [{"at": at, "cases": [0x1030]}]}

    windows = []

    def disassemble(window):
        windows.append(window)
        return SITE_TEXT

    def read(vaddr, n):
        return bytes(n)

    evidence.audit_row(body, row_for([0x1000, 0x1014, 0x1020], 0x1020), disassemble, read)
    dense = [0x1000 + 4 * i for i in range(40)]
    evidence.audit_row(body, row_for(dense, dense[-1]), disassemble, read)
    assert windows == [(0x1000, 0x1022), (0x103C, 0x109E)]


def test_the_table_bytes_are_read_from_the_image_once_and_shared(tmp_path, monkeypatch):
    so = tmp_path / "GameAssembly.so"
    calls = []

    def load(path):
        calls.append(str(path))
        return lambda vaddr, n: b""

    monkeypatch.setattr(tables, "_load_elf_reader", load)
    assert tables.elf_reader(so) is tables.elf_reader(so)
    assert tables.elf_reader(so) is tables.elf_reader(tmp_path / "GameAssembly.so")
    assert calls == [str(so)]


def test_the_disassembler_caches_the_exact_window_so_decoding_stays_aligned(tmp_path, monkeypatch):
    calls = []
    objdump = Path("/opt/homebrew/opt/llvm/bin/llvm-objdump")

    def run(command, capture_output, text):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(tables.subprocess, "run", run)
    so = tmp_path / "GameAssembly.so"
    so.write_bytes(b"")
    disassemble = tables.objdump_disassembler(so, objdump)
    disassemble((0x200, 0x222))
    disassemble((0x200, 0x222))
    disassemble((0x210, 0x232))
    assert [c[1:5] for c in calls] == [
        ["-d", "--no-show-raw-insn", "--start-address=0x200", "--stop-address=0x222"],
        ["-d", "--no-show-raw-insn", "--start-address=0x210", "--stop-address=0x232"],
    ]


def test_unverified_extras_are_explained_when_the_body_branches_there_directly():
    body = Fde(0x1000, 0x100)

    def row_with(ops, extra=0x900):
        return {
            "start": 0x1000, "size": 0x100, "status": "complete",
            "insns": [{"a": 0x1020, "ops": ops}, {"a": 0x1030, "ops": []}, {"a": 0x1040, "ops": []}],
            "jt": [{"at": 0x1020, "cases": [0x1030, 0x1040, extra]}],
        }

    def disassemble(window):
        return SITE_TEXT

    def read(vaddr, n):
        return (0x30).to_bytes(4, "little") + (0x40).to_bytes(4, "little")

    branch = [{"op": "BRANCH", "out": None, "in": ["ram,900,8"]}]
    explained = evidence.audit_row(body, row_with(branch), disassemble, read)["jt"][0]
    assert explained["extra_cases"] == [0x900]
    assert explained["extra_direct_edges"] == [0x900]
    assert explained["extra_unexplained"] == []

    conditional = [{"op": "CBRANCH", "out": None, "in": ["ram,900,8", "unique,1,1"]}]
    assert evidence.audit_row(body, row_with(conditional), disassemble, read)["jt"][0]["extra_direct_edges"] == [0x900]

    unexplained = evidence.audit_row(body, row_with([], 0x1050), disassemble, read)
    assert unexplained["jt"][0]["extra_unexplained"] == [0x1050]
    assert unexplained["extra_unexplained"] == 1

    outside = evidence.audit_row(body, row_with([]), disassemble, read)["jt"][0]
    assert outside["extra_outside_body"] == [0x900]
    assert outside["extra_unexplained"] == []


def test_recover_audits_fresh_rows_once_and_serves_them_from_cache(tmp_path):
    bodies = [Fde(0x1000, 8), Fde(0x2000, 12)]
    audited = []

    def dump(part, work):
        for body in part:
            row = {"start": body.start, "size": body.size, "status": "complete", "jt": []}
            (work / f"{body.start:x}.json").write_text(json.dumps(row))
        return True

    def audit(body, row):
        audited.append(body.start)
        return {**row, "audited": True}

    rows = evidence.recover(bodies, tmp_path, "identity", dump, batch_size=8, audit=audit)
    assert all(r["audited"] for r in rows)
    assert audited == [0x1000, 0x2000]
    assert all(r["audited"] for r in evidence.recover(bodies, tmp_path, "identity", dump, batch_size=8, audit=audit))
    assert audited == [0x1000, 0x2000]


def test_a_batch_timeout_names_the_active_body_and_preserves_finished_rows(tmp_path):
    bodies = [Fde(0x1000, 8), Fde(0x2000, 12), Fde(0x3000, 16)]
    calls = []

    def dump(part, work):
        calls.append(part)
        row = {"start": part[0].start, "size": part[0].size, "status": "complete", "jt": []}
        (work / f"{part[0].start:x}.json").write_text(json.dumps(row))
        if len(part) > 1:
            (work / "active").write_text(f"{part[1].start:x}")
            return False
        return True

    rows = evidence.recover(bodies, tmp_path, "identity", dump, batch_size=8)
    assert [r["status"] for r in rows] == ["complete", "batch_timeout", "complete"]
    assert calls == [bodies, bodies[2:]]
    assert evidence.recover(bodies, tmp_path, "identity", dump, batch_size=8) == rows
    assert calls == [bodies, bodies[2:]]
    assert evidence.recover(bodies, tmp_path, "new-deadline", dump, batch_size=8) == rows
    assert calls == [bodies, bodies[2:], bodies, bodies[2:]]

def test_raw_table_returns_the_guarded_pattern_with_its_decoded_cases():
    # The two facts an evidence-driven switch needs at once: the pattern (with its range guard) and the
    # entries the image holds. A pattern with no guard has no count, and no count means no cases.
    ev = tables.TableEvidence(Path("GameAssembly.so"), "llvm-objdump")
    blob = b"".join(o.to_bytes(4, "little", signed=True) for o in [-(0xFB809C - 0x20), 0x20, 0x24, 0x28, 0x2C])
    ev._disassemble = lambda window: SYMBOL_ANNOTATED_TEXT
    ev._read = lambda addr, n: blob[addr - 0xFB809C : addr - 0xFB809C + n]
    assert ev.raw_table([0x20, 0x40], 0x2126CFF) == {
        "base": 0xFB809C,
        "scale": 4,
        "count": 5,
        "cases": [0x20, 0xFB80BC, 0xFB80C0, 0xFB80C4, 0xFB80C8],
        "window": 0x2126CDF,
    }
    assert ev.raw_cases([0x20, 0x40], 0x2126CFF) == [0x20, 0xFB80BC, 0xFB80C0, 0xFB80C4, 0xFB80C8]
    ev._disassemble = lambda window: CLOBBERED_BOUND_TEXT
    assert ev.raw_table([0x20, 0x40], 0x2126CFF) is None
    assert ev.raw_cases([0x20, 0x40], 0x2126CFF) is None

WIDE_COPY_UNBOUND_TEXT = """
 4675ba9:   	cmpb	$0x5, %bl
 4675bac:   	ja	0x4675be8 <__start_il2cpp+0x2513258>
 4675bae:   	movl	%ebx, %eax
 4675bb0:   	leaq	-0x3a7bc27(%rip), %rcx  # 0xbf9f90
 4675bb7:   	movslq	(%rcx,%rax,4), %rax
 4675bbb:   	addq	%rcx, %rax
 4675bbe:   	jmpq	*%rax
"""


def test_a_byte_guard_on_another_register_leaves_a_wide_index_unbounded():
    # The shape the image ships for an enum switch (0x4675ba9): the guard compares %bl while the table is
    # indexed with %eax, written by a 32-bit movl. A byte bound on %bl says nothing about the top 24 bits
    # of the index, which are the caller's promise rather than the body's, so a case list taken from this
    # guard could omit a reachable entry. WIDENED_BOUND_TEXT is the accepted counterpart: there the index
    # is movzbl of the very byte the guard compared.
    assert evidence.parse_table_pattern(WIDE_COPY_UNBOUND_TEXT, 0x4675BBE) == {
        "base": 0xBF9F90,
        "scale": 4,
        "count": None,
    }



def test_raw_table_names_the_first_instruction_of_the_guarded_span():
    # The span runs from the earlier of the bound compare and the table-base lea to the jump; a lea
    # ahead of the compare starts it, which is where a loop-invariant base is loaded.
    ev = tables.TableEvidence(Path("GameAssembly.so"), "llvm-objdump")
    blob = b"".join(o.to_bytes(4, "little", signed=True) for o in [0, 4, 8, 12, 16])
    ev._read = lambda addr, n: blob[addr - 0xFB9E0C : addr - 0xFB9E0C + n]
    ev._disassemble = lambda window: FAR_TABLE_TEXT
    assert ev.raw_table([0x20, 0x40], 0x2159D75)["window"] == 0x2159D43
