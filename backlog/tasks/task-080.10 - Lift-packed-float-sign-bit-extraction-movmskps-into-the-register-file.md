---
id: TASK-080.10
title: Lift packed float sign-bit extraction (movmskps) into the register file
status: To Do
assignee: []
created_date: '2026-11-16T07:38:00Z'
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
ordinal: 265000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two 15,000-body samples (seeds 81 and 82, 5,000 per size class) draw nine bodies carrying a CALLOTHER hole for the movmskps userop: seven in seed 81 and two in seed 82, with 0x4906740 at 43 B the smallest carrier and 0x48da5c0 at 45,834 B the largest, drawn by both seeds. Seed 80's 3,000-body sample never reached the instruction, which is why it stayed unlisted until the census. Those bodies lift, verify and compile for arm64, but they are not fully lifted: the operation is recorded as a hole and its semantics are missing.

MOVMSKPS writes bit 31 of each of the four packed floats into bits 0 through 3 of a general-purpose register, lane 0 to bit 0 and so on. That destination shape is why the existing CALLOTHER lane rule does not cover it: the rule fires only when the destination and both sources are 16-byte varnodes, and here the destination is a general-purpose register. Establish the varnode shape the binary actually emits before writing the rule: which space and size Ghidra gives the destination, whether the source arrives as one 16-byte xmm varnode, and what the id in the first input is. The new rule must handle that shape without loosening the existing 16-byte guard, because a destination whose width is not checked is how a wrong lift slips past the verifier.

Prior art: TASK-080 built the lift probe and TASK-080.03, TASK-080.04 and TASK-080.05 established the shape to follow. Read the "Lifting the shipped code to arm64" section of docs/development.md first, then scripts/pcode_lift.py (the CALLOTHER branch of `lift_op` records a `CALLOTHER:<name>` hole from the Ghidra userop name in the op's `user` field, and lifts one only when `out`, `in[1]` and `in[2]` are all 16 bytes with `in[1]` the same varnode as `out`), tests/test_pcode_lift.py, and tests/test_pcode_lift_differential.py with its fixture tests/fixtures/lift/diff.c. The census rows are already on disk in .tools/lift-probe-81/bodies.jsonl and .tools/lift-probe-82/bodies.jsonl; find the carriers in their `holes` lists, then re-dump those bodies through scripts/lift_holes.py or scripts/lift_probe/LiftDump.java (needs .tools/megabonk-linux-native/Megabonk/GameAssembly.so, Ghidra and radare2 from brew, and the keg-only brew LLVM at /opt/homebrew/opt/llvm/bin, which is not on PATH). Regenerate a sample with `task re:lift-probe LIFT_PER_CLASS=5000 LIFT_SEED=81 LIFT_OUT=.tools/lift-probe-81 LIFT_EXTRA="--r2-per-class 0 --tool-timeout 600"`. Run the Python tests with `uv run pytest tests/test_pcode_lift.py tests/test_lift_probe.py tests/test_pcode_lift_differential.py`.

Repo rules that apply: write the failing test first; no section-banner or multi-paragraph comments; docs/*.md must not cite task ids; no personal names, hostnames, addresses or home paths in tracked files; commit messages are conventional with no attribution trailers.

Out of scope: pshuflw (a separate task). movmskpd, movntps and the other mask and streaming-store ops, and minss, maxss, minpd and maxpd, none of which have appeared in a sampled body: if one turns up as a hole it belongs in its own task rather than being added on speculation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Unit tests written first cover movmskps lifting to IR that passes `opt -passes=verify` with no `CALLOTHER:movmskps` hole recorded, for the varnode shape this binary emits.
- [ ] #2 A test pins the lane-to-bit mapping and the destination width: bit 31 of lane i becomes bit i of a 32-bit result written to the register file, with all-zeros, NaN lanes and signed zeros among the cases, against an explicit reference written in the test.
- [ ] #3 The existing 16-byte CALLOTHER guard still rejects what it rejected before, so a test shows a mismatched-width or non-destination source pair stays a hole rather than lifting.
- [ ] #4 The differential test gains a C function using `_mm_movemask_ps` so the x86-64 build emits the instruction itself, and the lifted side matches it on 2,000 inputs including NaN and signed-zero lanes.
- [ ] #5 Rerunning `task re:lift-probe LIFT_PER_CLASS=5000` on seeds 81 and 82 shows no `CALLOTHER:movmskps` hole, the hole-kind table in the "Lifting the shipped code to arm64" section of docs/development.md records that, and `task check` passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
