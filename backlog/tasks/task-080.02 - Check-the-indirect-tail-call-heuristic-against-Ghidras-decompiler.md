---
id: TASK-080.02
title: Check the indirect tail-call heuristic against Ghidra's decompiler
status: To Do
assignee: []
created_date: '2026-11-16T02:08:00Z'
labels:
  - lift
  - small-model
dependencies: []
references:
  - docs/development.md
  - scripts/pcode_lift.py
  - scripts/lift_probe/LiftDump.java
  - scripts/lift_probe.py
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
- [ ] #1 For every body counted in bodies_with_tail_calls in the seed-80, 1,000-per-class sample, a record exists with the heuristic's classification and the decompiler's view (number of jump tables it recovered, and whether its decompiled C contains a switch).
- [ ] #2 The numbers of agreeing and disagreeing bodies are recorded in the "Lifting the shipped code to arm64" section of docs/development.md, and every disagreeing body is listed with its start address.
- [ ] #3 For each disagreement that is a real misclassification, the minimal pcode sequence that reproduces it is recorded in the task notes.
- [ ] #4 Any helper code added has tests written first and `uv run pytest tests/test_pcode_lift.py tests/test_lift_probe.py` passes.
- [ ] #5 scripts/pcode_lift.py classification behaviour is unchanged and `task check` passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
