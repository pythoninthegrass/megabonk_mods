---
id: TASK-080.03
title: 'Lift packed float and double division (divps, divpd) in the pcode emitter'
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
  - tests/test_pcode_lift.py
  - tests/test_pcode_lift_differential.py
  - tests/fixtures/lift/diff.c
parent_task_id: TASK-080
priority: medium
type: enhancement
ordinal: 258000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In the 3,000-body lift sample (seed 80, 1,000 per size class) 21 bodies carry a CALLOTHER hole for the divps or divpd userop (20 and 1). The emitter records the hole but has no semantics for them, so those bodies are not fully lifted. Packed division is a per-lane IEEE division of a 16-byte register by a 16-byte operand: four float lanes for divps, two double lanes for divpd.

Prior art: TASK-080 built the lift probe. Read the "Lifting the shipped code to arm64" section of docs/development.md first, then scripts/pcode_lift.py (the CALLOTHER branch of `lift_op` records `CALLOTHER:<name>` holes; the Ghidra userop name arrives in the op's `user` field), tests/test_pcode_lift.py and tests/test_pcode_lift_differential.py with its fixture tests/fixtures/lift/diff.c. To see real pcode for the userop, run the probe and look at a body whose holes contain `CALLOTHER:divps` in .tools/lift-probe/bodies.jsonl, then dump its pcode with scripts/lift_probe/LiftDump.java. Run the probe with `task re:lift-probe LIFT_PER_CLASS=1000`; it needs .tools/megabonk-linux-native/Megabonk/GameAssembly.so, Ghidra and radare2 from brew, and the keg-only brew LLVM at /opt/homebrew/opt/llvm/bin (not on PATH). Run the Python tests with `uv run pytest tests/test_pcode_lift.py tests/test_lift_probe.py tests/test_pcode_lift_differential.py`.

Repo rules that apply: write the failing test first; no section-banner or multi-paragraph comments; docs/*.md must not cite task ids; no personal names, hostnames, addresses or home paths in tracked files; commit messages are conventional with no attribution trailers.

Out of scope: minps, maxps and every other userop (separate tasks), and float-to-integer conversion.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Unit tests written first show divps (four float lanes) and divpd (two double lanes) lifting to IR that passes `opt -passes=verify`, with no hole recorded for either userop.
- [ ] #2 The differential test gains C functions that divide 16-byte vectors (clang vector_size types) and matches native arm64 on 2,000 inputs per function, including zero, infinity and NaN lanes.
- [ ] #3 Rerunning `task re:lift-probe LIFT_PER_CLASS=1000` shows no divps or divpd hole in the seed-80 sample, and the new no-hole count is recorded in the "Lifting the shipped code to arm64" section of docs/development.md.
- [ ] #4 All existing tests still pass and `task check` passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
