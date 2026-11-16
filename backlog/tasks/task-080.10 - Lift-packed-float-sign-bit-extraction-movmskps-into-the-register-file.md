---
id: TASK-080.10
title: Lift packed float sign-bit extraction (movmskps) into the register file
status: Done
assignee: []
created_date: '2026-11-16T07:38:00Z'
updated_date: '2026-11-16T17:28:00Z'
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
- [x] #1 Unit tests written first cover movmskps lifting to IR that passes `opt -passes=verify` with no `CALLOTHER:movmskps` hole recorded, for the varnode shape this binary emits.
- [x] #2 A test pins the lane-to-bit mapping and the destination width: bit 31 of lane i becomes bit i of a 32-bit result written to the register file, with all-zeros, NaN lanes and signed zeros among the cases, against an explicit reference written in the test.
- [x] #3 The existing 16-byte CALLOTHER guard still rejects what it rejected before, so a test shows a mismatched-width or non-destination source pair stays a hole rather than lifting.
- [x] #4 The differential test gains a C function using `_mm_movemask_ps` so the x86-64 build emits the instruction itself, and the lifted side matches it on 2,000 inputs including NaN and signed-zero lanes.
- [x] #5 Rerunning `task re:lift-probe LIFT_PER_CLASS=5000` on seeds 81 and 82 shows no `CALLOTHER:movmskps` hole, the hole-kind table in the "Lifting the shipped code to arm64" section of docs/development.md records that, and `task check` passes.
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
1. Re-dump all movmskps carriers from the seed-81/82 census and record the actual CALLOTHER destination/source/id shape; preserve published baseline outputs.
2. Write and run failing unit tests for verified IR, lane-sign mapping and 32-bit register-file writes, plus malformed-shape rejection while retaining existing packed-lane guard tests.
3. Add an _mm_movemask_ps fixture and a portable explicit bit-reference oracle to the 2,000-input native/lifted differential harness; assert the x86 fixture emits movmskps.
4. Implement a separately shape-guarded movmskps lowering using integer sign-bit extraction, without changing the packed arithmetic guard.
5. Run focused tests, rerun both 15,000-body seeds into new output directories, update the development documentation with measured hole counts and semantics, and run task check.
6. Record objective results and remaining blockers in Backlog; finalize and make a conventional commit only after all acceptance criteria and completion checks pass.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Re-dumped the seven distinct carriers from seeds 81/82 (eight instruction sites). Every MOVMSKPS is CALLOTHER out=register,{0|8},4, in=[const,a1,4, same destination, register,{1200|1240},16]. Shape evidence saved locally in .tools/movmskps-shapes.json. Both seed samples share the same two carriers; the union is seven bodies, not nine distinct bodies.

Test-first evidence: new differential fixture failed both pipelines with CALLOTHER:movmskps; new focused unit run failed six positive tests and passed nine malformed-shape rejection cases before lowering was added. Separate shape guard implemented; packed arithmetic guard unchanged. Tests cover all 16 sign masks across zeros, quiet/signaling NaNs, finite values, infinity and subnormal lanes, with neighboring register bytes/source preserved.

Focused validation passes: 130 tests across test_pcode_lift.py, test_lift_probe.py and test_pcode_lift_differential.py. Rosetta checks the explicit reference against _mm_movemask_ps on 2,000 inputs; both plain and default<O2> lifted arm64 pass 2,000 inputs per function, including deterministic signed-zero and quiet/signaling-NaN sign masks.

task check passed: 2,858 .NET tests; 2,173 Python tests passed and one skipped; build, installer tests, markdownlint, ruff and site Deno format/lint all passed. Existing compiler nullability and pytest asyncio configuration warnings remain non-fatal. Both full 15,000-body census reruns are running in new .tools/lift-probe-movmskps-{81,82} directories, leaving published baselines untouched.

Seed 82 full rerun completed in .tools/lift-probe-movmskps-82: requested/scored 15,000; all decode, verify and compile for arm64; 14,852 hole-free (4,926 tiny / 4,946 small / 4,980 large); no failures or unsampled rows; no CALLOTHER:movmskps. Remaining holes: BRANCHIND 144, JUMPTABLE_TARGET 3, CALLOTHER:pshuflw 1. Compared every body address/size and hole list to the published baseline: exactly movmskps removed from 0x48da5c0 and 0x4dd04d0; all other hole lists unchanged. Seed 81 still pending.

Seed 81 full rerun completed in .tools/lift-probe-movmskps-81: requested/scored 15,000; all decode, verify and compile for arm64; 14,845 hole-free (4,900 tiny / 4,956 small / 4,989 large); no failures or unsampled rows; no CALLOTHER:movmskps. Remaining holes: BRANCHIND 152, JUMPTABLE_TARGET 2, CALLOTHER:pshuflw 1. Compared both reruns body-by-body to their baselines: address sets and sizes match exactly, and every hole list differs only by removal of movmskps from its original seven/two carriers. docs/development.md now preserves baseline counts alongside the new zero-hole results, records updated clean counts and documents the separate shape guard and bit semantics. Final task check rerun underway; log .tools/movmskps-task-check.log.

Final task check rerun hit one intermittent failure in unchanged test_dump_pcode_keeps_partial_rows_when_ghidra_times_out: partial rows/sections were recovered, but timeout diagnostics lacked the fake process's stderr line. The same test passed in the initial complete task check and passes immediately when rerun alone with -n 0 (1 passed). No unrelated code changed. Full task check retry running; log .tools/movmskps-task-check-retry.log.

Final full task check retry passed unchanged: 2,173 Python tests passed / one skipped, with build, installer/.NET tests and all lint stages passing. The timeout diagnostic test's isolated rerun also passed. All five acceptance criteria are verified; remaining completion step is the conventional commit.

Implementation and documentation committed as 03ec21b (feat(lift): lower packed float sign-bit masks), without attribution trailers. Published census baselines remain untouched.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented MOVMSKPS sign-mask lifting behind its own checked pcode shape: repeated 32-bit register destination and one 16-byte register source. Integer shifts map each lane sign to bits 0–3 and write exactly i32; existing packed-arithmetic guards are unchanged.

Tests were written and observed failing before implementation. Unit coverage checks lane mapping, NaNs/signed zeros, destination width, untouched neighboring/source bytes and malformed-shape rejection. The intrinsic fixture emits MOVMSKPS, the explicit oracle matches x86 on 2,000 inputs, and plain/O2 lifted arm64 differential runs pass.

Both 15,000-body census reruns fully decode, verify and compile for arm64 with zero MOVMSKPS holes. Hole-free totals improve to 14,845 (seed 81) and 14,852 (seed 82); body-by-body comparison confirms no other hole-list changes. Development documentation preserves baseline counts beside measured reruns and explains semantics.

Final task check passes: 2,173 Python tests passed and one skipped, plus .NET/build/installer and lint checks. One unchanged timeout-diagnostic test failed intermittently on the preceding rerun, then passed isolated and in the full retry. No unrelated code changed. Implementation commit: 03ec21b.
<!-- SECTION:FINAL_SUMMARY:END -->
