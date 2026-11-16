---
id: TASK-080.03
title: 'Lift packed float and double division (divps, divpd) in the pcode emitter'
status: Done
assignee: []
created_date: '2026-11-16T02:08:00Z'
updated_date: '2026-11-16T03:31:00Z'
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
modified_files:
  - scripts/pcode_lift.py
  - tests/test_pcode_lift.py
  - tests/test_pcode_lift_differential.py
  - tests/fixtures/lift/diff.c
  - docs/development.md
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
- [x] #1 Unit tests written first show divps (four float lanes) and divpd (two double lanes) lifting to IR that passes `opt -passes=verify`, with no hole recorded for either userop.
- [x] #2 The differential test gains C functions that divide 16-byte vectors (clang vector_size types) and matches native arm64 on 2,000 inputs per function, including zero, infinity and NaN lanes.
- [x] #3 Rerunning `task re:lift-probe LIFT_PER_CLASS=1000` shows no divps or divpd hole in the seed-80 sample, and the new no-hole count is recorded in the "Lifting the shipped code to arm64" section of docs/development.md.
- [x] #4 All existing tests still pass and `task check` passes.
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
1. Unit tests first for the packed-division lowering: four float lanes for divps, two double lanes for divpd, the destination as the dividend, the result stored back to the destination, and every other userop or unexpected width still recorded as a hole.
2. Implement the lowering in scripts/pcode_lift.py: a PACKED_DIVISION table keyed by the Ghidra userop name, a shape guard requiring a 16-byte destination with in[1] identical to out and a 16-byte source, then per-lane extract, bitcast, fdiv, bitcast and insert. minps, maxps and every other CALLOTHER stay holes.
3. Extend tests/fixtures/lift/diff.c with vector_size(16) float and double division (register and memory operand), and the differential harness with 16-byte vector arguments and per-lane comparison over zero, signed zero, infinity and qNaN/sNaN lanes.
4. Re-run the probe on the seed-80, 1,000-per-class sample, confirm no CALLOTHER:divps or CALLOTHER:divpd hole remains, and record the new no-hole count in docs/development.md.
5. task check green, docs updated, conventional commit with no attribution.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Packed division lifts. CALLOTHER now has semantics for the divps and divpd shapes: a PACKED_DIVISION table keyed on Ghidra's userop name, gated by is_packed_division (out, in[1] and in[2] all 16 bytes, in[1] the same varnode as out). BodyLifter.packed_division reads both operands as i128, splits four float or two double lanes, emits one fdiv per lane, and stitches the quotients back into a single store i128. Any other userop, and any divps/divpd whose shape does not match, still records CALLOTHER:<name>.

Tests first: 13 new tests in tests/test_pcode_lift.py cover the lane counts, the destination-as-dividend order, the single store back to the destination, a unique-space divisor, verify and llc -O2 for arm64, and that wrong widths, a mismatched destination, and minps/maxps stay holes.

The differential test gained f_divpd, f_divps and f_divps_mem (clang vector_size(16), register and memory divisor) with a per-lane compare that treats two NaNs as equal; lanes are drawn from zero, signed zero, plus/minus infinity and qNaN/sNaN. The harness assigns integer and SSE argument registers independently, because a 16-byte vector argument takes an xmm register without consuming an integer one.

That test caught a second bug, not division: Ghidra reads a 16-byte unique temp back as four sub-varnode offsets (unique,X+4, +8, +12) and the emitter's unique map allocated a fresh slot per distinct offset, so lanes 1-3 of a memory divisor read uninitialised stack and lifted f_divps_mem returned inf where IEEE wanted NaN. unique_block now maps a temp onto %uniq by byte range so a sub-varnode lands inside its parent, and the %uniq alloca is sized from the bytes actually claimed. Three new tests pin the mapping.

Probe, same seed 80 and 1,000 per class: 2,976 of 3,000 lift with no hole (was 2,956; 986 tiny, 992 small, 998 large). 20 of the 21 division-hole bodies cleared; bodies with holes are now 24, and the only CALLOTHER holes left are minps and maxps, 12 sites in 2 bodies, which belong to TASK-080.04.

Verified: uv run pytest (1,971 passed, 1 skipped), ruff check and format, task check green.
<!-- SECTION:FINAL_SUMMARY:END -->
