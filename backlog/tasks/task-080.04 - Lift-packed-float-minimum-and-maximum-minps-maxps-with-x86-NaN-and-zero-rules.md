---
id: TASK-080.04
title: >-
  Lift packed float minimum and maximum (minps, maxps) with x86 NaN and zero
  rules
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
  - tests/test_pcode_lift_differential.py
  - tests/fixtures/lift/diff.c
parent_task_id: TASK-080
priority: medium
type: enhancement
ordinal: 259000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In the 3,000-body lift sample (seed 80, 1,000 per size class) 4 bodies carry a CALLOTHER hole for the minps or maxps userop (2 each), so those bodies are not fully lifted. The x86 semantics are not the same as a plain IEEE minimum: per lane, MINPS returns the first source when it is strictly less than the second and the second source otherwise, which means the second source wins when either lane is NaN and when both lanes are zeros of either sign. MAXPS mirrors it with greater-than. A naive llvm.minnum or llvm.maxnum lowering would differ on exactly those cases.

Prior art: TASK-080 built the lift probe. Read the "Lifting the shipped code to arm64" section of docs/development.md first, then scripts/pcode_lift.py (the CALLOTHER branch of `lift_op` records `CALLOTHER:<name>` holes; the Ghidra userop name arrives in the op's `user` field), tests/test_pcode_lift.py and tests/test_pcode_lift_differential.py with its fixture tests/fixtures/lift/diff.c. Find real examples by looking for `CALLOTHER:minps` or `CALLOTHER:maxps` in .tools/lift-probe/bodies.jsonl after `task re:lift-probe LIFT_PER_CLASS=1000` (needs .tools/megabonk-linux-native/Megabonk/GameAssembly.so, Ghidra and radare2 from brew, and the keg-only brew LLVM at /opt/homebrew/opt/llvm/bin, which is not on PATH), then dump the pcode with scripts/lift_probe/LiftDump.java. Run the Python tests with `uv run pytest tests/test_pcode_lift.py tests/test_lift_probe.py tests/test_pcode_lift_differential.py`.

Repo rules that apply: write the failing test first; no section-banner or multi-paragraph comments; docs/*.md must not cite task ids; no personal names, hostnames, addresses or home paths in tracked files; commit messages are conventional with no attribution trailers.

Out of scope: divps and divpd (a separate task), scalar minss and maxss unless they appear as holes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Unit tests written first cover minps and maxps lifting to IR that passes `opt -passes=verify`, with no hole recorded for either userop.
- [ ] #2 A test checks the NaN case (second source returned when either lane is NaN) and the signed-zero case (second source returned when both lanes are zero) for both operations, against an explicit reference written in the test.
- [ ] #3 The differential test gains C functions using lane-wise `a < b ? a : b` and `a > b ? a : b` on 16-byte vectors and matches native arm64 on 2,000 inputs per function including NaN and signed-zero lanes.
- [ ] #4 Rerunning `task re:lift-probe LIFT_PER_CLASS=1000` shows no minps or maxps hole in the seed-80 sample, and the figure is recorded in the "Lifting the shipped code to arm64" section of docs/development.md.
- [ ] #5 All existing tests still pass and `task check` passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
