---
id: TASK-080.01
title: Classify the unresolved computed jumps left in the lift sample
status: Done
assignee: []
created_date: '2026-11-16T02:08:00Z'
updated_date: '2026-11-16T02:39:00Z'
labels:
  - lift
  - small-model
dependencies: []
references:
  - docs/development.md
  - scripts/pcode_lift.py
  - scripts/lift_probe.py
  - taskfiles/re.yml
parent_task_id: TASK-080
priority: high
type: spike
ordinal: 256000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In the 3,000-body lift sample (seed 80, 1,000 per size class) 21 bodies still carry a BRANCHIND hole with no recovered jump table, and 1 body has a jump-table case outside its own body. Nobody knows whether these are real switches the decompiler failed to recover, indirect tail calls the straight-line rule misses, or something else. Until they are classified, the 98.5% no-hole figure cannot be improved on purpose, and a wrong guess in the emitter could silently produce bad code. This task only finds out what they are; it does not change how they are lifted.

Prior art: TASK-080 built the lift probe. Read the "Lifting the shipped code to arm64" section of docs/development.md first, then scripts/pcode_lift.py (Ghidra raw pcode to LLVM IR emitter), scripts/lift_probe.py (sampler, scorer, driver) and tests/test_pcode_lift.py. Run the probe with `task re:lift-probe LIFT_PER_CLASS=1000` (needs .tools/megabonk-linux-native/Megabonk/GameAssembly.so, Ghidra and radare2 from brew, and the keg-only brew LLVM at /opt/homebrew/opt/llvm/bin, which is not on PATH). It writes summary.json and bodies.jsonl to .tools/lift-probe; each row has `holes`, `start` and `size`. Run the Python tests with `uv run pytest tests/test_pcode_lift.py tests/test_lift_probe.py`.

Repo rules that apply: write the failing test first for any helper code; no section-banner or multi-paragraph comments; docs/*.md must not cite task ids; no personal names, hostnames, addresses or home paths in tracked files; commit messages are conventional with no attribution trailers.

Out of scope: changing pcode_lift.py behaviour, and any new lifting rule. Record what a rule would need to match, nothing more.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A documented command or script lists every body in the seed-80, 1,000-per-class sample whose holes include BRANCHIND or JUMPTABLE_TARGET, with start address and size.
- [x] #2 Each listed body has a category (unrecovered switch, indirect tail call, indirect call target, other) backed by the instruction sequence that leads to its BRANCHIND, written to a file under .tools/lift-probe and summarised as per-category counts in the "Lifting the shipped code to arm64" section of docs/development.md.
- [x] #3 For every category with three or more bodies, docs/development.md states the instruction pattern that identifies it.
- [x] #4 Any helper code added has tests written first and `uv run pytest tests/test_pcode_lift.py tests/test_lift_probe.py` passes.
- [x] #5 scripts/pcode_lift.py behaviour is unchanged and `task check` passes.
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
1. Re-run the sample to regenerate the artifacts the task reads (they are gitignored and were absent): `task re:lift-probe LIFT_PER_CLASS=1000` (r2 leg skipped with LIFT_EXTRA="--r2-per-class 0"; it does not affect the sample) -> .tools/lift-probe/{summary.json,bodies.jsonl}. Confirmed against TASK-080's notes: 3000 decoded/verified/arm64, 2956 clean, 21 BRANCHIND, 1 JUMPTABLE_TARGET.
2. New scripts/lift_holes.py (pcode_lift.py untouched). Pure, unit-tested helpers: select_hole_rows (rows whose holes include BRANCHIND or JUMPTABLE_TARGET), branchind_sites (the ops of every BRANCHIND-bearing instruction), def_chain (backward COPY/LOAD/arithmetic trace for a varnode, written locally rather than reusing BodyLifter so pcode_lift stays frozen), table_shape (is the target loaded from base+index*scale out of a non-exec section, with a const bounds compare upstream), parse_objdump (addr -> x86 text), reloc_targets (R_X86_64_RELATIVE slot -> addend from llvm-readelf), classify -> (category, evidence).
3. Categories, each backed by the recorded sequence: unrecovered switch (table load from a read-only section with a scaled index, no decompiler table at the site), indirect tail call (target loaded through a register-relative pointer, BRANCHIND ends the body, epilogue before it), indirect call target (target loaded from a fixed data slot that carries a relocation pointing into an exec section, i.e. GOT/thunk or function-pointer slot), other (recorded with its sequence, no rule claimed).
4. Driver: reads bodies.jsonl, redumps pcode for just those bodies through Ghidra (reuses lift_probe.dump_pcode/Fde), disassembles each body with llvm-objdump, reads relocations with llvm-readelf, writes .tools/lift-probe/jump_holes.jsonl (start, size, holes, category, evidence, x86 sequence, pcode ops) and prints per-category counts.
5. Wire it as `task re:lift-holes` in taskfiles/re.yml with LIFT_OUT/LIFT_SO/LIFT_SEED style vars, documented like re:lift-probe.
6. tests/test_lift_holes.py written before the helpers, on hand-built pcode records; keep `uv run pytest tests/test_pcode_lift.py tests/test_lift_probe.py tests/test_lift_holes.py` green, then `task check`.
7. docs/development.md, "Lifting the shipped code to arm64": per-category counts, the command, and the instruction pattern for every category with >= 3 bodies; state what a future rule would have to match, no rule added.
Risk: Ghidra's own jump-table recovery is the only oracle available, so "unrecovered switch" is evidence-based (pcode shape + no decompiler table), not proof; the sequence is recorded per body so the call can be re-checked by hand.

Rules as shipped (first match wins in classify_facts): a slot with an R_X86_64_RELATIVE addend pointing into executable code and no scaled index -> indirect call target; a non-executable base with a scaled index, or with two or more in-body arms and a bounds check in the x86 text -> unrecovered switch; two or more recovered table cases inside the body -> unrecovered switch; a load-kind target that is not scaled and is either register-relative or read from a fixed slot -> indirect tail call; else other. ends_body and epilogue are recorded as evidence only, because 16 of the 33 tail-call sites sit mid-body on a cold path.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Progress: sample regenerated (task re:lift-probe LIFT_PER_CLASS=1000, r2 leg skipped) and reproduces TASK-080 exactly: 3000 decoded/verified/arm64, 2956 clean, holes BRANCHIND 21, divps 20, minps 2, maxps 2, divpd 1, JUMPTABLE_TARGET 1, 193 tail-call bodies, 9.11x. Artifacts were absent from .tools/lift-probe before this run (gitignored).

New: scripts/lift_holes.py + tests/test_lift_holes.py (25 tests, written first) + task re:lift-holes. Categories come from SiteFacts rules (first match wins): relocated non-exec slot -> indirect call target; constant base in a non-exec section with a scaled index or >= 2 in-body arms, or >= 2 recovered table cases inside the body -> unrecovered switch; register-relative load with the jump ending the body -> indirect tail call; else other. Evidence per site: x86 sequence (llvm-objdump intel), traced pcode ops in program order, the decompiler's tables, the slot/base section, the RELATIVE addend, and the shape flags. pcode_lift.py untouched.

Classifier verdict on the shipped rules: 22 bodies / 34 indirect jump sites -> 21 bodies (33 sites) indirect tail call, 1 body (1 site) unrecovered switch, 0 indirect call target, 0 other. Independently cross-checked with llvm-objdump by hand: all 21 tail-call bodies call the same resolver 0x2056380 (exactly 21 occurrences) and jump through one global slot; the 21 slots span 0x53648e0-0x5369790 and all land in _bss; no relocation of any type lands in _bss at all (of 470,439 reloc rows: 245,671 .data.rel.ro, 168,006 .data, 55,006 .got, 1,756 .got.plt), so the targets are runtime-written and statically unnameable. The switch body (0x4dd8a20) calls no resolver: cmp rcx,0x8 / ja default / lea rdx,[rip] # 0xbfd278 / movsxd rsi,[rdx+4*rcx] / add rsi,rdx / jmp rsi, table in _rodata, 10 recovered cases with 1 outside the .eh_frame bound.

Four rule fixes driven by the real pcode, each with a failing test first: (1) Ghidra writes a fixed-address read as COPY reg <- ram,slot,8, not LOAD, so memory_read() now recognises both shapes (this is what took 21 bodies out of 'other'); (2) LOAD's pointer is in[1] (in[0] is a space id), so a stack pop no longer reports slot 0x1b1; (3) the base candidate ranks (memory space, address-sized, width) so a scale factor const stops winning, and registers are followed to their defining op unless that op is a memory read - a rip-relative lea lands in cptr space, which is a value not a read, so MEMORY_SPACES is ram only; (4) bounds_check now comes from the x86 text (compare against an immediate followed by ja/jae/jb/jbe) instead of any 1-byte pcode compare, and rule 2 needs scaled_index or (arms>=2 and bounds_check), because thunks reach arms=7 and the old arms-only rule would have called them switches. ends_body/epilogue remain recorded evidence only.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added scripts/lift_holes.py with `task re:lift-holes` and tests/test_lift_holes.py (39 tests, written before the helpers). scripts/lift_probe.py, scripts/pcode_lift.py and scripts/lift_probe/LiftDump.java are untouched, verified by an empty git diff before commit.

What the tool does: reads the probe's hole rows, re-dumps those bodies through headless Ghidra, traces each indirect jump target back through the ops that produced it, and names a category per site, recording as evidence the x86 sequence from llvm-objdump, the traced pcode, the section the target was loaded from, any R_X86_64_RELATIVE on that slot, and the jump tables the decompiler recovered. Output is .tools/lift-probe/jump_holes.jsonl, one row per body with start and size, plus printed per-category counts.

Verdict on the seed-80, 1,000-per-class sample (22 bodies, 34 indirect jump sites): 21 bodies / 33 sites are the il2cpp lazily-resolved invoke thunk, a target loaded from a fixed global slot in .bss with frame teardown immediately before the jump. All 21 call the same resolver (0x2056380, exactly 21 occurrences), the slots span 0x53648e0-0x5369790, and of the file's 470,439 relocation rows none lands in .bss at all, so nothing static can name those targets: a rule here can only lift them as indirect jumps and stop recording a hole, never turn them into direct branches. One body (0x4dd8a20) is a genuine position-independent switch over a self-relative table in _rodata with the bounds check ahead of it; the decompiler recovered all ten cases and one lands past the .eh_frame bound the body was cut from, so that hole is a short body boundary rather than an unrecoverable switch. Zero indirect call target and zero other, which is the useful result: none of the 34 sites had a target the emitter could have resolved statically.

Verification: uv run pytest tests/test_pcode_lift.py tests/test_lift_probe.py -> 32 passed; with tests/test_lift_holes.py -> 71 passed. task check exit 0 (build, installer:test, mod:test, scripts:test 1958 passed 1 skipped, markdownlint, ruff, deno fmt and lint). markdownlint clean on docs/development.md. An independent hand check with llvm-objdump and llvm-readelf agrees with the classifier on every body: 21 thunks and one switch, no slot relocation.

Four rule fixes were driven by the real pcode, each with a failing test first: Ghidra writes a fixed-address read as COPY from the ram space rather than LOAD; LOAD's pointer is its second operand, the first being a space id; the candidate table base must rank a memory space above a scale-factor constant, and a register must be followed to its defining op unless that op reads memory (a rip-relative lea lands in cptr space, a value not a read); and a bounds check has to come from the x86 text, a compare against an immediate followed by ja/jae/jb/jbe, because thunks reach seven arms and an arms-only rule would have called them switches.

Risks and follow-ups: the categories are structural, backed by pcode shape plus the decompiler's own table recovery, which is the only oracle available for real game code, so jump_holes.jsonl keeps per-site evidence for anyone to re-check a verdict. A lifting rule for the thunk shape is deliberately not added here, it is out of scope. The sample artifacts the classifier reads are gitignored, so re-run the probe first if they are absent; a classifier run costs three to four minutes of headless Ghidra.
<!-- SECTION:FINAL_SUMMARY:END -->
