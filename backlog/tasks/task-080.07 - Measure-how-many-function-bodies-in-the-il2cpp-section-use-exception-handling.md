---
id: TASK-080.07
title: Measure how many function bodies in the il2cpp section use exception handling
status: Done
assignee: []
created_date: '2026-11-16T02:09:00Z'
updated_date: '2026-11-16T03:48:00Z'
labels:
  - lift
  - small-model
dependencies: []
references:
  - docs/development.md
  - scripts/lift_probe.py
  - scripts/elf_shim_probe.py
modified_files:
  - scripts/eh_probe.py
  - tests/test_eh_probe.py
  - taskfiles/re.yml
  - docs/development.md
  - AGENTS.md
parent_task_id: TASK-080
priority: medium
type: spike
ordinal: 262000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The lift emitter ignores C++ exception unwinding entirely: lifted code cannot catch or run cleanups for exceptions. The shipped GameAssembly.so has a 1.1 MB .gcc_except_table and an .eh_frame CIE that names a personality routine, and IL2CPP raises managed exceptions through the C++ runtime, so unwinding is certainly in use. What is not known is how much: if only a small fraction of bodies have landing pads, the problem is contained, and if most do, exception lifting is the dominant remaining cost. This number decides how urgent that work is.

Prior art: TASK-080 built the lift probe. Read the "Lifting the shipped code to arm64" section of docs/development.md first. scripts/lift_probe.py already derives the function list from .eh_frame with `llvm-dwarfdump --eh-frame` (the keg-only brew LLVM at /opt/homebrew/opt/llvm/bin, not on PATH), but that output does not show each frame's exception-table pointer, so a different way of reading it is needed. scripts/elf_shim_probe.py has a stdlib ELF reader that can be reused. The binary is .tools/megabonk-linux-native/Megabonk/GameAssembly.so; the il2cpp section holds 196,137 bodies (75,845 tiny, 100,919 small, 19,373 large). Run the Python tests with `uv run pytest tests/`.

Repo rules that apply: write the failing test first for any parsing code; no section-banner or multi-paragraph comments; docs/*.md must not cite task ids; no personal names, hostnames, addresses or home paths in tracked files; commit messages are conventional with no attribution trailers.

Out of scope: lifting exceptions, and changing the emitter.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A reproducible command (a task in taskfiles/re.yml or a documented script invocation) reports, for the 196,137 bodies of the il2cpp section, how many have an exception-table (LSDA) pointer, broken down by tiny, small and large.
- [x] #2 For the bodies that have one, the report also gives the distribution of landing-pad counts (for example none-through-one, two to four, five or more) taken from the exception table.
- [x] #3 Any parsing helper has unit tests written first, using a small hand-built byte fixture, and `uv run pytest` passes.
- [x] #4 The results are recorded in the "Lifting the shipped code to arm64" section of docs/development.md, replacing the unquantified statement about exception handling, and `task check` passes.
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
1. Write tests first for the .eh_frame and LSDA parsers in tests/test_eh_probe.py against hand-built byte fixtures (CIEs with zR and zPLR augmentations, FDEs with and without an LSDA, call-site tables in both ULEB and fixed-width forms).
2. Implement scripts/eh_probe.py: reuse elf_shim_probe.parse_elf for section bytes, walk .eh_frame CIEs and FDEs to bound the il2cpp bodies the same way lift_probe does, read each LSDA in .gcc_except_table, and report LSDA presence per size class plus the landing-pad distribution.
3. Add a taskfile/re.yml entry (re:eh-probe) so the census is reproducible the way re:lift-probe is.
4. Cross-check the numbers against an independent oracle (llvm-dwarfdump --eh-frame) and against semantic invariants (landing pads inside their own body, tables filling their declared length).
5. Record the results in the Lifting the shipped code to arm64 section of docs/development.md, replacing the unquantified exception statement, then task check green and a conventional commit with no attribution.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The exception census is measured, and the answer is that unwinding is contained but concentrated. `task re:eh-probe` (scripts/eh_probe.py, stdlib only, writing .tools/eh-probe/summary.json) bounds the same 196,137 il2cpp bodies the lift probe uses, reads each FDE's LSDA pointer, and walks that table in .gcc_except_table.

Of the 196,137 bodies, 8,373 (4.3%) carry an LSDA and all 8,373 point inside .gcc_except_table (1,110,448 B at 0xfba378); tables are never shared, so distinct tables equal bodies with one. Split by class: tiny 0 of 75,845, small 2,642 of 100,919 (2.6%), large 5,731 of 19,373 (29.6%). Among bodies with a table none has a single pad: 2,795 have two to four distinct landing pads and 5,578 have five or more. In total 144,668 call-site entries, 103,628 with a nonzero pad, resolving to 84,257 distinct pads; the largest body has 931. A 3,000-body stratified sample should hold about 322 LSDA-bearing bodies, and the lift probe reports no exception numbers at all.

Cross-checked against llvm-dwarfdump --eh-frame, which agrees exactly on the 196,137 bodies, the 75,845/100,919/19,373 size split, all 9,424 LSDA addresses, and the 8,373 in-section FDEs of an LSDA-bearing CIE. Of the file's three CIEs, 0x0 is "zR" with 249,677 FDEs and no LSDA encoding, 0x9b9dd8 is "zPLR" with 9,424, and 0xa71910 is "zPLR" with none, so it is unreferenced. Semantic checks: all 103,628 pads fall strictly inside their own body, no table has an out-of-order call site, all 9,424 tables fill their declared length exactly, and the call-site encoding is 0x01 everywhere with TType encodings 0x9c (8,596) and 0x9b (174) and 654 bodies with none.

Three parser bugs had to be found to get there, each now pinned by a test: an FDE's range is the code pointer's own fixed-width form named by the CIE's R augmentation, not the ULEB128 .debug_frame uses (reading it as ULEB desynchronises every later record and skewed the size classes by 800 bodies); an FDE's CIE pointer is backward, so the CIE sits at entry + 4 - field; and the LSDA header is LPStart encoding plus value, TType encoding plus a ULEB offset rather than an encoded pointer, then the call-site encoding and a ULEB byte length that bounds the table, with a fourth ULEB action field on every entry and no terminator, so the length and not a zero entry decides where the table ends.

Tests first: 36 tests in tests/test_eh_probe.py over hand-built CIE/FDE and LSDA fixtures, written before the parsers and confirmed red. Landing pads are counted as distinct offsets, because each becomes its own block in the emitter; distinct tables are reported separately from bodies with a pointer.

Consequence for the lift: 95.7% of bodies need nothing, but for the 4.3% the emitter lifts no table, so such a body compiles and cannot unwind, and two thirds of them need five or more landing pads, which a one-pad implementation does not cover. Whether a TType-bearing table also calls a shared runtime helper is unmeasured, because resolving those pointers needs the image loaded and this probe deliberately does not load it.

Verified: uv run pytest (2,007 passed, 1 skipped), ruff check and format, task check green.
<!-- SECTION:FINAL_SUMMARY:END -->
