---
id: TASK-080.11
title: Lift the low-order word shuffle (pshuflw) with its immediate selector
status: Done
assignee: []
created_date: '2026-11-16T07:38:00Z'
updated_date: '2026-11-16T18:41:00Z'
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
modified_files:
  - scripts/pcode_lift.py
  - tests/test_pcode_lift.py
  - tests/test_pcode_lift_differential.py
  - tests/fixtures/lift/diff.c
  - docs/development.md
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
- [x] #1 Unit tests written first cover pshuflw lifting to IR that passes `opt -passes=verify` with no `CALLOTHER:pshuflw` hole recorded, for the varnode shape this binary emits.
- [x] #2 A test pins the immediate selector and upper-half preservation: each 2-bit field selects a low source word for that output lane and destination bits 64 through 127 equal the source's, including duplicated selections and nonzero upper halves distinct from the old destination, against an explicit reference.
- [x] #3 The differential test gains a C function using `_mm_shufflelo_epi16` so the x86-64 build emits the instruction itself, and the lifted side matches it on 2,000 inputs including nonzero source high halves, comparing all 128 result bits.
- [x] #4 Rerunning `task re:lift-probe LIFT_PER_CLASS=5000` on seeds 81 and 82 shows no `CALLOTHER:pshuflw` hole, the hole-kind table in the "Lifting the shipped code to arm64" section of docs/development.md records that, and `task check` passes.
- [x] #5 All existing tests still pass.
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
1. Inspect the two shipped carriers with LiftDump; retain local pcode evidence. Both emit out=XMM0, inputs=[const bb/4, XMM0/16, XMM0/16, const e0/8]. Use a dedicated four-input guard built on the packed shape plus a constant byte-range selector; leave unexpected shapes as named holes.
2. Write failing unit tests for this shape, all 256 selectors, source/destination aliasing and distinct registers, nonzero upper halves, and rejected shapes. Add a _mm_shufflelo_epi16 C fixture and differential coverage comparing all 128 bits on 2,000 inputs; assert x86 disassembly contains pshuflw.
3. Fold the immediate at lift time; select four low i16 lanes and copy source high four lanes, merge into a single i128 store without reading the old destination.
4. Run focused unit/probe/differential tests (plain and O2), then full 15,000-body seed-81 and seed-82 probes into new .tools/lift-probe-pshuflw-{81,82} directories without replacing baselines. Compare complete body/hole lists and retain evidence.
5. Correct the stale upper-half description and update the hole table and measured results in docs/development.md. Run all Python tests and task check, record objective results, and finalize only criteria actually verified.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Re-dumped both 513-byte carriers: 0x3ab7dc0 at instruction 0x3ab7e95 and 0x42f4cb0 at instruction 0x42f4d85 emit identical pshuflw shapes with immediate e0 (8-byte const varnode). Local evidence: .tools/pshuflw-carriers.json. Required LLVM, Ghidra and binary are present; working tree was clean before starting.

Test-first evidence: uv run pytest tests/test_pcode_lift.py -k pshuflw failed as expected with 4 failures (named CALLOTHER:pshuflw holes) and 8 rejected-shape passes before emitter changes. After implementation, focused unit/probe/differential suite passed 142 tests, including all 256 selectors with aliased/distinct source and destination and plain/O2 arm64 execution of the intrinsic fixture. An additional x86 reference check has since been added and will be covered by the full check. Full seed-81/82 probes are running sequentially in fresh output directories.

task check passed (build, installer tests, mod tests, Python tests and repository/site lint). Python result: 2,186 passed, 1 skipped, including the added Rosetta pshuflw reference check. Log: .tools/pshuflw-task-check.log. Full 15,000-body seed reruns remain pending; task not yet finalized.

Both full probes completed successfully. Each requested/scored/decoded/verified/compiled all 15,000 bodies, with no failures or missing rows. Seed 81: 14,846 clean (4,900 tiny / 4,956 small / 4,990 large), holes BRANCHIND=152 and JUMPTABLE_TARGET=2. Seed 82: 14,853 clean (4,926 / 4,946 / 4,981), holes BRANCHIND=144 and JUMPTABLE_TARGET=3. Asserted all 15,000 ordered (address,size) pairs match the sign-mask rerun per seed and exactly one hole-list change per seed: 0x3ab7dc0 / 0x42f4cb0 lose only CALLOTHER:pshuflw. Evidence: .tools/lift-probe-pshuflw-{81,82}/{summary.json,bodies.jsonl}. Published baselines untouched. Updated docs semantics, hole table and rerun results. A final task check after the measured-result doc update is underway; conventional commit remains pending.

Final task check after the measured-results documentation update passed again: 2,186 Python tests passed, 1 skipped; build, installer/mod tests, markdownlint, Ruff and site checks passed. Log: .tools/pshuflw-task-check-final.log. Implementation and documentation committed as 2cf00be (feat(lift): implement pshuflw immediate word shuffle).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented guarded PSHUFLW lifting with a compile-time immediate selector, four low-word selections and preservation of the source's upper 64 bits. Re-dumped both shipped carriers before test-first development. Tests cover every selector, aliasing and separate source/destination registers, neighboring-byte preservation, malformed shapes, verifier acceptance and 2,000-input plain/O2 arm64 differential execution; a Rosetta test checks the explicit reference against the x86 intrinsic. Both 15,000-body seed reruns verify/compile fully, eliminate exactly one pshuflw hole each and leave every other hole list unchanged. Updated docs semantics, hole table and measured results. Final task check passed (2,186 Python tests passed, 1 skipped, plus build, installer/mod tests and lint). Commit: 2cf00be. Only existing control-flow holes remain in these two samples.
<!-- SECTION:FINAL_SUMMARY:END -->
