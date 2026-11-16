---
id: TASK-080.01
title: Classify the unresolved computed jumps left in the lift sample
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
- [ ] #1 A documented command or script lists every body in the seed-80, 1,000-per-class sample whose holes include BRANCHIND or JUMPTABLE_TARGET, with start address and size.
- [ ] #2 Each listed body has a category (unrecovered switch, indirect tail call, indirect call target, other) backed by the instruction sequence that leads to its BRANCHIND, written to a file under .tools/lift-probe and summarised as per-category counts in the "Lifting the shipped code to arm64" section of docs/development.md.
- [ ] #3 For every category with three or more bodies, docs/development.md states the instruction pattern that identifies it.
- [ ] #4 Any helper code added has tests written first and `uv run pytest tests/test_pcode_lift.py tests/test_lift_probe.py` passes.
- [ ] #5 scripts/pcode_lift.py behaviour is unchanged and `task check` passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
