---
id: TASK-080.08
title: Classify the ELF relative relocations by what they point at
status: Done
assignee: []
created_date: '2026-11-16T02:09:00Z'
updated_date: '2026-11-16T04:10:00Z'
labels:
  - lift
  - small-model
dependencies: []
references:
  - docs/development.md
  - scripts/elf_shim_probe.py
  - scripts/lift_probe.py
modified_files:
  - scripts/reloc_probe.py
  - tests/test_reloc_probe.py
  - taskfiles/re.yml
  - docs/development.md
parent_task_id: TASK-080
priority: medium
type: spike
ordinal: 263000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Pointers stored in data (vtables, method tables, string literal tables) hold x86 addresses. To rebuild the game code for arm64 those pointers must become references to the lifted functions and to the rebuilt data sections. The shipped GameAssembly.so has 466,320 base-relative relocations that identify exactly these pointers, but nobody has classified them: how many point at a function entry (rewritable to a lifted function symbol), into the middle of a function (harder), at read-only data, writable data or bss, or at nothing known. That split says how mechanical the data rewrite can be.

Prior art: TASK-080 built the lift probe. Read the "Lifting the shipped code to arm64" section of docs/development.md first, and the "Loading and shimming the Linux ELF runtime" section, which already counts the relocations. scripts/elf_shim_probe.py has a stdlib ELF reader and a relocation parser that can be reused. scripts/lift_probe.py shows how function entries are derived from the .eh_frame records (`llvm-dwarfdump --eh-frame` from the keg-only brew LLVM at /opt/homebrew/opt/llvm/bin, not on PATH). The binary is .tools/megabonk-linux-native/Megabonk/GameAssembly.so. Run the Python tests with `uv run pytest tests/`.

Repo rules that apply: write the failing test first for any helper code; no section-banner or multi-paragraph comments; docs/*.md must not cite task ids; no personal names, hostnames, addresses or home paths in tracked files; commit messages are conventional with no attribution trailers.

Out of scope: rewriting any relocation or emitting any data, and changing the emitter.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A reproducible command (a task in taskfiles/re.yml or a documented script invocation) classifies every base-relative relocation by the kind of address it points at: exact function entry, inside a function, read-only data, writable data, bss, other loaded memory, outside every section.
- [x] #2 The same report breaks the relocations down by the section that holds the pointer (for example the relocation-protected data section, the data section, the GOT).
- [x] #3 The relocation total printed by the report equals the figure already documented, and a test written first on a hand-built fixture covers the classifier.
- [x] #4 The counts are recorded in docs/development.md in the "Lifting the shipped code to arm64" section, with one sentence on what the split implies for rewriting data pointers, and `task check` passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first in tests/test_reloc_probe.py: build Section/Segment/Rela/Frame records by hand (the way tests/test_elf_shim_probe.py builds Elf records) and pin the classifier for a function entry, a function interior, read-only data, writable data, bss, memory inside a PT_LOAD with no section, and an address outside every segment; plus the slot-section breakdown and the bucket-sum-equals-total invariant.
2. Implement scripts/reloc_probe.py as a stdlib census reusing elf_shim_probe.parse_elf for sections, segments and Rela records and eh_probe.parse_frames for the .eh_frame body ranges that bound functions. For each R_X86_64_RELATIVE the addend is the pre-relocation target, so classify the addend; bucket it as function_entry, function_interior, read_only_data, writable_data, bss, other_loaded or outside, and break the same relocations down by the section holding the slot (r.offset).
3. Keep the seven buckets exactly as the task names them and report what they cannot express as separate metrics rather than folding it away: an other_loaded detail split between executable code no FDE covers and genuinely unsectioned memory, and a first-byte census over the entry targets that names any entry opening on zero padding.
4. Add a taskfiles/re.yml entry re:reloc-probe next to re:eh-probe, with RELOC_SO/RELOC_OUT/RELOC_EXTRA vars and a precondition on the binary existing.
5. Cross-check: the printed RELATIVE total must equal the 466,320 already documented in the Loading and shimming section, and the whole-file body fold must reproduce the 196,137 bodies the exception census counts inside il2cpp; both are asserted over the shipped binary when it is present.
6. Record the split, one sentence on what it implies for rewriting data pointers, and the command in the Lifting the shipped code to arm64 section of docs/development.md; task check green; conventional commit with no attribution, then the backlog record commit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Function bounds come from eh_probe.parse_frames over the whole file rather than one section, because relocations point into .text as well as il2cpp: 259,101 FDE records, 6 with an empty range, folding to 259,095 bodies with no two overlapping. Scoped to il2cpp that fold is the exception census's 196,137 exactly, which is the cross-check the probe asserts.
Entry vs interior is decided by exact membership of the start set plus merged coverage intervals, not by the first record whose range contains the address: FDEs nest, and a containment test over unmerged records would let a nested record mislabel an entry as an interior.
The finding is that function_interior is zero. That is a claim about the binary, so a test proves containment live on a shipped body (a body's first byte is an entry, a byte 32 in and the last byte are interiors) rather than trusting the fixtures alone.
An invented prologue-prefix threshold was measured and dropped: a generous instruction-start set covers only 98.5% of entry targets, and the four bytes it misses (66, 69, b0, f2) are all legitimate instruction starts (operand-size prefix, imul, mov al, scalar-SSE prefix). 43% of entry targets also happen to carry four printable ASCII bytes, so a string-likeness check is worthless on code. The probe reports the raw first-byte histogram, the bytes it cannot explain, and any entry opening on zero padding instead of gating on a made-up share.
One relocation is neither code nor ordinary data: a .got slot at 0x50d7278 holding 0x4e26440, the first byte of .plt. It is reported as other_loaded with the executable_no_frame detail rather than folded into the entry bucket.
Every slot falls inside a named section (0 without one), all records live in .rela.dyn, and the 466,320 rows name 409,941 distinct addresses.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added scripts/reloc_probe.py and task re:reloc-probe, which classify all 466,320 R_X86_64_RELATIVE fixups in the shipped Linux GameAssembly.so by the address their addend names, with function bounds taken from the same .eh_frame records the lift probe cuts bodies from. The split: 247,358 (53.0%) name an exact function entry, 0 land inside a function body, 38,850 (8.3%) point at read-only data, 180,093 (38.6%) at writable data, 18 into .bss, 1 at a .plt stub, and 0 outside every section; read by holding section the slots are .data.rel.ro 243,666, .data 167,996, .got 54,631, .init_array 21 and .ctors 6. What it implies is that rewriting the pointers is two jobs: the 53% are mechanical symbol references at known addresses, while the 47% name memory the code lift never touches and so has to be rebuilt and relocated along with it. Verification: 33 tests in tests/test_reloc_probe.py (written first and confirmed red), the printed total equals the documented 466,320, the whole-file body fold reproduces the exception census's 196,137 bodies inside il2cpp, every entry opens on a byte an instruction can start with and none on zero padding, and task check passes with 2040 tests. Risk and follow-up: nothing rewrites a relocation yet, and the zero-interior result rests on .eh_frame being the whole truth about body starts — a body the unwinder does not describe would read as other_loaded rather than as an entry, which is why the one such row is reported by address rather than bucketed away.
<!-- SECTION:FINAL_SUMMARY:END -->
