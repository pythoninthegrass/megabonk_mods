---
id: TASK-080.02
title: Check the indirect tail-call heuristic against Ghidra's decompiler
status: Done
assignee: []
created_date: '2026-11-16T02:08:00Z'
updated_date: '2026-11-16T06:01:00Z'
labels:
  - lift
  - small-model
dependencies: []
references:
  - docs/development.md
  - scripts/pcode_lift.py
  - scripts/lift_probe/LiftDump.java
  - scripts/lift_probe.py
modified_files:
  - scripts/lift_tail_calls.py
  - tests/test_lift_tail_calls.py
  - scripts/lift_probe/LiftDump.java
  - taskfiles/re.yml
  - docs/development.md
parent_task_id: TASK-080
priority: high
type: spike
ordinal: 257000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In the 3,000-body lift sample (seed 80, 1,000 per size class), 193 bodies are lifted as indirect tail calls by a straight-line rule: a BRANCHIND whose target traces back through COPY ops to a LOAD. That rule is an approximation, and a switch the decompiler failed to recover could be classified as a tail call without any error, producing wrong code that still verifies and compiles. Ghidra's decompiler is an independent second opinion that has not been consulted for these bodies.

Prior art: TASK-080 built the lift probe. Read the "Lifting the shipped code to arm64" section of docs/development.md first, then scripts/pcode_lift.py (see `defined_by_load` and `branch_indirect`), scripts/lift_probe.py, scripts/lift_probe/LiftDump.java (it already calls the decompiler for bodies containing a BRANCHIND and dumps the recovered jump tables) and tests/test_pcode_lift.py. Run the probe with `task re:lift-probe LIFT_PER_CLASS=1000`; it needs .tools/megabonk-linux-native/Megabonk/GameAssembly.so, Ghidra and radare2 from brew, and the keg-only brew LLVM at /opt/homebrew/opt/llvm/bin (not on PATH). bodies.jsonl in .tools/lift-probe has a `tail_calls` count per body. Run the Python tests with `uv run pytest tests/test_pcode_lift.py tests/test_lift_probe.py`.

Repo rules that apply: write the failing test first for any helper code; no section-banner or multi-paragraph comments; docs/*.md must not cite task ids; no personal names, hostnames, addresses or home paths in tracked files; commit messages are conventional with no attribution trailers.

Out of scope: changing the emitter's classification rule. Report disagreements and the pcode shape of each; a later task decides the fix.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 For every body counted in bodies_with_tail_calls in the seed-80, 1,000-per-class sample, a record exists with the heuristic's classification and the decompiler's view (number of jump tables it recovered, and whether its decompiled C contains a switch).
- [x] #2 The numbers of agreeing and disagreeing bodies are recorded in the "Lifting the shipped code to arm64" section of docs/development.md, and every disagreeing body is listed with its start address.
- [x] #3 For each disagreement that is a real misclassification, the minimal pcode sequence that reproduces it is recorded in the task notes.
- [x] #4 Any helper code added has tests written first and `uv run pytest tests/test_pcode_lift.py tests/test_lift_probe.py` passes.
- [x] #5 scripts/pcode_lift.py classification behaviour is unchanged and `task check` passes.
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
Prior art confirmed: scripts/lift_probe.py (dump_pcode, score_body), scripts/lift_holes.py (row selection + site evidence pattern to reuse), scripts/lift_probe/LiftDump.java (jumpTables() already decompiles every body holding a BRANCHIND and emits jt), scripts/pcode_lift.py BodyLifter.defined_by_load/branch_indirect (the heuristic under audit), and the 'Lifting the shipped code to arm64' section of docs/development.md. Inputs are on disk: .tools/lift-probe/bodies.jsonl for seed 80 at 1,000 per class, with 193 rows carrying tail_calls.
Step 1 - LiftDump.java: decompile a BRANCHIND body once and emit two extra keys next to the existing jt: sw (the decompiled C contains a switch) and dc (the decompile completed). jt keeps its exact shape so scripts/pcode_lift.py and scripts/lift_holes.py are unaffected.
Step 2 - scripts/lift_tail_calls.py plus a re:lift-tail-calls verb in taskfiles/re.yml: read LIFT_OUT/bodies.jsonl, keep rows with tail_calls, redump those bodies through lift_probe.dump_pcode, and per BRANCHIND site ask the emitter's own rule (BodyLifter.tables plus BodyLifter.defined_by_load, the code the lift uses, not a copy) whether it lowered the site as a tail call. Record the decompiler's view (tables, cases, sw, dc) and per-site evidence from lift_holes, and give the body one verdict: agrees, disagrees, mixed, or not decompiled. Writes tail_calls.jsonl and prints counts with the disagreeing start addresses.
Step 3 - Tests written first in tests/test_lift_tail_calls.py over hand-built pcode records in the shape LiftDump.java writes, so no Ghidra, ELF or LLVM is needed: row selection, decompiler view, the four verdicts including a table at the tail-call site versus a table belonging to another site, and the emitter-side classification.
Step 4 - Run task re:lift-tail-calls on the seed-80 sample. Record the agreeing/disagreeing counts and every disagreeing start address in docs/development.md, and the minimal pcode sequence for each real misclassification in the task notes.
Step 5 - Verify: uv run pytest tests/test_lift_tail_calls.py tests/test_lift_probe.py tests/test_pcode_lift.py, confirm scripts/pcode_lift.py is untouched in git diff, and run task check.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Audit result (seed-80 sample, 193 bodies, 198 indirect jump sites)

`.tools/lift-probe/tail_calls.jsonl` and `tail_calls_summary.json`; console log `.tools/lift-probe/tail-calls-run.log`.

Counts: agrees 186, disagrees 0, mixed 4, no tail call 0, switch beyond body 3, not decompiled 0.
Mixed: 0x32a1690, 0x3a98000, 0x4423a90, 0x4037a70. Switch beyond body: 0x405b3f0, 0x270bb60, 0x3c7fda0.

**No real misclassification.** The decompiler never recovered a jump table at a site the emitter tail-jumps. The emitter reads the same `jt` list and prefers it, so a table at a tail-call site is impossible by construction; the audit's content is therefore the negative side.

Two findings about the oracle:

1. `Could not recover jumptable at 0x… Treating indirect jump as call` fires at 190 of the 198 sites - it is what the decompiler prints for any indirect jump whose targets it cannot enumerate, so it cannot separate a vtable tail call from an unrecovered switch. Recorded per body in `decompiler.unrecoverable`; it deliberately does not decide a verdict.
2. The decompiled function is not the `.eh_frame` body. The three switch-beyond-body bodies have a `switch` in the C while every recovered table lies outside the bounds (3 tables/44 cases, 45/180, 2/34; `tables_in_body` and `cases_in_body` both 0). Hand check of the decompiled C for all three confirms the keyword belongs to code past the bounds; the bodies' own sites appear as calls through an object slot. `decompiler_view` therefore counts tables and cases in the dump and inside the body separately.

Minimal pcode per non-agreeing body (the emitter's tail-call spine is identical everywhere, and each mixed body pairs it with the switch spine):

```text
tail-call spine (all 198 sites, incl. every non-agreeing one)
  LOAD unique,23d00,8 <- const,1b1,4, <base>   # target's nearest definition is a LOAD
  COPY <reg> <- unique,23d00,8
  BRANCHIND <reg>

switch spine, present only in the four mixed bodies, at the other site of the same body
  LOAD unique,23c00,4 <- const,1b1,4, unique,9400,8
  INT_SEXT <reg> <- unique,23c00,4
  INT_ADD  <reg> <- <reg>, <reg>
  BRANCHIND <reg>
```

Per body:

- 0x32a1690 (487 B) mixed - table recovered at 0x32a16d3 (5 cases) for the switch spine; tail call at 0x32a1844 after `add rsp,0x18; pop rbx; pop r14`, `jmp rcx`.
- 0x3a98000 (803 B) mixed - table at 0x3a98070 (7 cases); tail call at 0x3a9823b, `jmp r9` after the epilogue.
- 0x4423a90 (960 B) mixed - table at 0x4423b94 (10 cases); tail call at 0x4423afd, `jmp rcx` after the epilogue.
- 0x4037a70 (555 B) mixed - table at 0x4037aca (21 cases); tail call at 0x4037c5c, `jmp rcx` after the epilogue.
- 0x405b3f0 (642 B) switch beyond body - tail call at 0x405b66b, `jmp rcx` after three pops; 3 tables/44 cases, all outside; decompiler warning at 0x405b66b.
- 0x270bb60 (994 B) switch beyond body - tail call at 0x270be7b, `jmp r8` after the epilogue; 45 tables/180 cases, all outside; warning at 0x270be7b.
- 0x3c7fda0 (605 B) switch beyond body - two tail calls, 0x3c7fef0 (`jmp rcx`) and 0x3c7ff1e (`jmp rdx`), both `mov <r>, [<obj> + 0x168]`; 2 tables/34 cases, all outside; warnings at both sites, and the C renders them as `UNRECOVERED_JUMPTABLE = *(code **)(*plVar24 + 0x168)`.

Population census that explains the result: 198/198 sites take the target from a register-relative fixed offset, 161 have frame teardown immediately before the jump, 5 carry a bounds check, 46 end the body, and the 61 whose traced chain contains a scaled index are interface dispatches (`mov rcx,[rax]; mov rdx,[rcx+0x168]; jmp rdx`) with the base a data-section offset such as 0x138 or 0x168 - not `[base + index*8]` table indexing, which is the shape the rule could mistake for a tail call.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added scripts/lift_tail_calls.py and task re:lift-tail-calls, which re-dump the 193 bodies the seed-80 probe counted as indirect tail calls (198 BRANCHIND sites), ask the emitter's own rule at each site - BodyLifter.tables plus BodyLifter.defined_by_load, the code the lift actually uses rather than a copy - and set it against what the same Ghidra decompile pass recovered. LiftDump.java keeps its jt shape and emits three more keys from that one decompile: sw for a switch in the C, dc for a completed decompile, and uw for the addresses its Could not recover jumptable warnings name. Verdicts per body: agrees 186, disagrees 0, mixed 4 (0x32a1690, 0x3a98000, 0x4423a90, 0x4037a70), no tail call 0, switch beyond body 3 (0x405b3f0, 0x270bb60, 0x3c7fda0), not decompiled 0. No real misclassification: the decompiler never recovered a table at a site the emitter tail-jumps, and each mixed body holds a genuine recovered switch at one site and a genuine vtable tail call at the other, which the emitter routes differently and correctly. Two findings about the oracle shaped the design. The generic Could not recover jumptable ... Treating indirect jump as call warning fires at 190 of the 198 sites, because that is what it prints for any indirect jump whose targets it cannot enumerate, so it is recorded per body and deliberately never decides a verdict; the first version of the audit made it one and classified 186 bodies as unrecovered switches. And the decompiled function is not the .eh_frame body: the three switch-beyond-body cases have a switch keyword while every recovered table and case lies outside the bounds, confirmed by reading the decompiled C for all three, so decompiler_view counts tables and cases in the dump and inside the body separately and a bare keyword with nothing inside to anchor it is its own verdict rather than a contradiction. What the rule survives on: 198/198 sites trace BRANCHIND <- COPY <- LOAD off a register-relative fixed offset, 161 with frame teardown before the jump and 5 with a bounds check, and the 61 whose traced chain contains a scaled index are interface dispatches with the base a data-segment offset such as 0x138 or 0x168, not [base + index*8] table indexing - the one shape the rule could mistake for a tail call, unexercised in this population. Verification: 29 tests in tests/test_lift_tail_calls.py written first and confirmed red, the four lift test files at 143 passed, a 7-body rerun reproducing the stored rows exactly, task check at 2099 passed with markdownlint, ruff and deno clean, and scripts/pcode_lift.py unchanged in git. Risk and follow-up: the population is the 193 bodies of one sample, and the audit can only compare against what Ghidra's recovery says, so a switch Ghidra also fails to see would be invisible here too; the census is what makes that unlikely.
<!-- SECTION:FINAL_SUMMARY:END -->
