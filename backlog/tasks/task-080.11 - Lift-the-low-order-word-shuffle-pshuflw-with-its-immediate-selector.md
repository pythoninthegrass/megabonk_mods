---
id: TASK-080.11
title: Lift the low-order word shuffle (pshuflw) with its immediate selector
status: To Do
assignee: []
created_date: '2026-11-16T07:38:00Z'
updated_date: '2026-11-16T16:46:00Z'
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
  - 'https://www.felixcloutier.com/x86/pshuflw'
parent_task_id: TASK-080
priority: medium
type: enhancement
ordinal: 266000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Each of the two 15,000-body samples draws exactly one body carrying a CALLOTHER hole for the pshuflw userop: 0x3ab7dc0 in seed 81 and 0x42f4cb0 in seed 82, both 513 B. It is rare, one body per 15,000, but it is in the shipped binary and seed 80's 3,000-body sample never reached it. The body lifts, verifies and compiles for arm64 with the operation recorded as a hole, so its semantics are missing.

PSHUFLW permutes the four low-order 16-bit words of the source into the destination's low four words, taking each output word from the corresponding 2-bit field of an 8-bit immediate, and copies source bits 64 through 127 unchanged into the destination's upper 64 bits. Two things follow for the rule. The immediate is a constant among the op's inputs and has to be read and folded at lift time, because the lifted IR carries no selector operand. And the destination is a 16-byte xmm whose top half must be copied from the source, not zeroed or retained from the old destination, which may or may not satisfy the existing CALLOTHER guard requiring `out`, `in[1]` and `in[2]` all 16 bytes with `in[1]` the same varnode as `out`: settle that from the pcode of the two carriers before deciding whether this needs a new branch or the current shape already admits it.

Prior art: TASK-080 built the lift probe and TASK-080.03, TASK-080.04 and TASK-080.05 established the shape to follow. Read the "Lifting the shipped code to arm64" section of docs/development.md first, then scripts/pcode_lift.py (the CALLOTHER branch of `lift_op` records a `CALLOTHER:<name>` hole from the Ghidra userop name in the op's `user` field, and lifts one only when `out`, `in[1]` and `in[2]` are all 16 bytes with `in[1]` the same varnode as `out`), tests/test_pcode_lift.py, and tests/test_pcode_lift_differential.py with its fixture tests/fixtures/lift/diff.c. The census rows are already on disk in .tools/lift-probe-81/bodies.jsonl and .tools/lift-probe-82/bodies.jsonl; find the carriers in their `holes` lists, then re-dump those bodies through scripts/lift_holes.py or scripts/lift_probe/LiftDump.java (needs .tools/megabonk-linux-native/Megabonk/GameAssembly.so, Ghidra and radare2 from brew, and the keg-only brew LLVM at /opt/homebrew/opt/llvm/bin, which is not on PATH). Regenerate a sample with `task re:lift-probe LIFT_PER_CLASS=5000 LIFT_SEED=81 LIFT_OUT=.tools/lift-probe-81 LIFT_EXTRA="--r2-per-class 0 --tool-timeout 600"`. Run the Python tests with `uv run pytest tests/test_pcode_lift.py tests/test_lift_probe.py tests/test_pcode_lift_differential.py`.

Repo rules that apply: write the failing test first; no section-banner or multi-paragraph comments; docs/*.md must not cite task ids; no personal names, hostnames, addresses or home paths in tracked files; commit messages are conventional with no attribution trailers.

Out of scope: movmskps (a separate task). pshufd, pshufhw, shufps and the other shuffles, and minss, maxss, minpd and maxpd, none of which have appeared in a sampled body: if one turns up as a hole it belongs in its own task rather than being added on speculation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Unit tests written first cover pshuflw lifting to IR that passes `opt -passes=verify` with no `CALLOTHER:pshuflw` hole recorded, for the varnode shape this binary emits.
- [ ] #2 A test pins the immediate selector and upper-half preservation: each 2-bit field selects a low source word for that output lane and destination bits 64 through 127 equal the source's, including duplicated selections and nonzero upper halves distinct from the old destination, against an explicit reference.
- [ ] #3 The differential test gains a C function using `_mm_shufflelo_epi16` so the x86-64 build emits the instruction itself, and the lifted side matches it on 2,000 inputs including nonzero source high halves, comparing all 128 result bits.
- [ ] #4 Rerunning `task re:lift-probe LIFT_PER_CLASS=5000` on seeds 81 and 82 shows no `CALLOTHER:pshuflw` hole, the hole-kind table in the "Lifting the shipped code to arm64" section of docs/development.md records that, and `task check` passes.
- [ ] #5 All existing tests still pass.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
