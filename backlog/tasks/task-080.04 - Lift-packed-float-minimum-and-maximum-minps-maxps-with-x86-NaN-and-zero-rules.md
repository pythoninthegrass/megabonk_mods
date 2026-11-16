---
id: TASK-080.04
title: >-
  Lift packed float minimum and maximum (minps, maxps) with x86 NaN and zero
  rules
status: Done
assignee: []
created_date: '2026-11-16T02:08:00Z'
updated_date: '2026-11-16T05:06:00Z'
labels:
  - lift
  - small-model
dependencies: []
references:
  - docs/development.md
  - scripts/pcode_lift.py
  - tests/test_pcode_lift_differential.py
  - tests/fixtures/lift/diff.c
modified_files:
  - scripts/pcode_lift.py
  - tests/test_pcode_lift.py
  - tests/test_pcode_lift_differential.py
  - tests/fixtures/lift/diff.c
  - docs/development.md
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
- [x] #1 Unit tests written first cover minps and maxps lifting to IR that passes `opt -passes=verify`, with no hole recorded for either userop.
- [x] #2 A test checks the NaN case (second source returned when either lane is NaN) and the signed-zero case (second source returned when both lanes are zero) for both operations, against an explicit reference written in the test.
- [x] #3 The differential test gains C functions using lane-wise `a < b ? a : b` and `a > b ? a : b` on 16-byte vectors and matches native arm64 on 2,000 inputs per function including NaN and signed-zero lanes.
- [x] #4 Rerunning `task re:lift-probe LIFT_PER_CLASS=1000` shows no minps or maxps hole in the seed-80 sample, and the figure is recorded in the "Lifting the shipped code to arm64" section of docs/development.md.
- [x] #5 All existing tests still pass and `task check` passes.
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
Measurements done: the shipped pcode lowers minps/maxps as CALLOTHER out=X, in=[const 0x9d/0x9b, X, Y] with all 16-byte varnodes, same out==in[1] shape as the already-lowered divps; only two sampled bodies carry them (0x279f830, 0x4c86c70).
Tests first: replace the minps/maxps hole test with no-hole/verify/lane-count/operand/store/width tests using the real userop ids, plus lane-value tests that drive the register file and compare against an in-test reference for the strict-less-else-second rule (NaN on either side and signed-zero pairs pick the second source).
Emitter: PACKED_MINMAX table keyed by user name with lanes, lane bytes and predicate; shared 16-byte packed-shape check; per-lane fcmp olt/ogt plus select reusing the divps shift/or merge tail.
Differential: add packed min/max C functions in the vectorized array-loop form (the form that emits real minps/minpd at -O1) with 2,000 inputs each including NaN and signed-zero lanes.
Rerun task re:lift-probe LIFT_PER_CLASS=1000 in seed 80, record the new clean count and hole census in docs/development.md.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Ghidra prints a CALLOTHER's userop id as the varnode's offset, so the dump text is hex: minps is const,9d,4 and maxps const,9b,4 (the shipped bodies always compare a destination against xmm0). The emitter never reads in[0], so tests pass whatever that literal is: changing it is invisible, and the only way to get it right is to dump real pcode. divps and divpd print 97 and 96, which the docs quote verbatim.

The register file slots a test writes to must be the ones the emitter's varnodes name. xmm1 is 0x1240 and xmm2 is 0x1280: writing the second operand to 0x1240 while the pcode says register,1280,16 leaves it reading zeros, and a min/max test then reports the second source's value as wrong in a way that looks like an emitter bug.

Getting the fixture to emit the packed instruction at -O1 took measurement, not guesswork. A ternary on vector types does not compile (the comparison's type is a vector of ints), __builtin_elementwise_binary does not exist in clang 23.1.3, __builtin_fminf lowers to fminnm (the wrong rule, and an arm64 oracle that would agree with the mistake), and a plain element loop scalarizes to minss/maxss at -O1 while -O2 packs it. The form that works at both optimization levels is a memcpy to arrays, an element loop under '#pragma clang loop vectorize(enable) interleave(enable)', and a memcpy back; on arm64 the same source lowers to fcmgt plus bif, which is the ternary's own semantics and so a valid oracle.

A select on floats is a candidate for the optimizer to rewrite into a floating-point max, which does not carry the x86 NaN and zero rules. Selecting between the lanes' integer bit patterns removes the question and copies the winner unchanged.

The differential's NaN tolerance (two NaNs count as matching) is right for operations that compute a value and wrong for operations that return one of their operands: for minps it would forgive picking the wrong source whenever both lanes are NaN. STRICT_LANES opts those functions into a bit-exact lane comparison.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Packed min/max lifts. CALLOTHER now gives semantics to minps and maxps as well as the packed divisions: a PACKED_MINMAX table keyed on Ghidra's userop name (lanes, lane bytes, predicate), gated by the shared is_packed_lane_op shape check (out, in[1] and in[2] all 16 bytes, in[1] the same varnode as out). Each lane gets fcmp olt (minps) or fcmp ogt (maxps) and a select between the two lanes' bit patterns as integers, then the same shift-and-or merge the packed division emitter already had, factored out as merge_lanes. Anything else, and any minps/maxps whose shape does not match, still records CALLOTHER:<name>.

Why not minnum/maxnum: x86 keeps the first source only while that lane strictly compares to the second, so the second source is what a lane returns when either side is NaN and when both are zeros of either sign. llvm.minnum and llvm.maxnum return whichever operand is not NaN and leave the choice between two zeros unspecified, so they differ on a NaN payload and on the sign of a zero. Selecting the integers rather than the floats also keeps the optimizer from rewriting the pair into a floating-point max, and copies the winner's bits unchanged.

Tests (14 cases): no-hole, lane-and-predicate counts, operand and store origins, the shape the shipped bodies use, and width/destination shape guards; value tests that drive lanes through the register file against a reference written in the test; a hand-written second-source table for +0/-0 and every NaN pairing, asserting the second vector's exact bits; and a Rosetta-gated test that holds the reference to the instruction itself before the lifted side is judged by it.

Differential: f_minps and f_maxps added to the fixture, each compared on 2,000 inputs whose lanes include zero, signed zero, both infinities and two NaN payloads. They are in a new STRICT_LANES set compared bit for bit, because those operations return an operand rather than compute a value, so the tolerant two-NaNs-match rule would hide picking the wrong source. Mutating the minps predicate from olt to ole fails the differential on a signed-zero lane at input 14, which is the check that the comparison actually discriminates.

Probe: task re:lift-probe LIFT_PER_CLASS=1000 on seed 80 now reports 3,000 decoded, 3,000 verified, 3,000 compiled for arm64 and 2,978 clean (986 tiny, 992 small, 1,000 large). The hole census is BRANCHIND 21 and JUMPTABLE_TARGET 1: every minps and maxps instance is gone, and every remaining hole is a control-flow gap rather than an instruction. Both hole-carrying bodies had been in the large class, which is why large went from 998 to 1,000.

task check passes (2,070 passed, 1 skipped). Committed as feat(re): lift packed float minps and maxps with the x86 lane rule.
<!-- SECTION:FINAL_SUMMARY:END -->
