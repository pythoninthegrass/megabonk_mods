---
id: TASK-080.05
title: Make float-to-integer conversion match x86 on overflow and NaN
status: Done
assignee: []
created_date: '2026-11-16T02:09:00Z'
updated_date: '2026-11-16T04:22:00Z'
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
ordinal: 260000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The emitter lowers the pcode TRUNC op (x86 cvttss2si and cvttsd2si) to LLVM fptosi. fptosi gives a poison value for NaN and for out-of-range inputs, while x86 returns the "integer indefinite" value there: 0x80000000 for a 32-bit destination and 0x8000000000000000 for a 64-bit one. The same game code would therefore behave differently after lifting on exactly the inputs where it overflows. The existing differential test hides this: f_f2i in tests/fixtures/lift/diff.c clamps its input to avoid it. Note that native arm64 saturates instead, so comparing against a natively compiled cast cannot be the oracle for these inputs.

Prior art: TASK-080 built the lift probe. Read the "Lifting the shipped code to arm64" section of docs/development.md first, then scripts/pcode_lift.py (the TRUNC branch of `float_op`), tests/test_pcode_lift.py and tests/test_pcode_lift_differential.py. Run the Python tests with `uv run pytest tests/test_pcode_lift.py tests/test_pcode_lift_differential.py`; the differential test needs the keg-only brew LLVM at /opt/homebrew/opt/llvm/bin (not on PATH), Ghidra from brew and an arm64 macOS host.

Repo rules that apply: write the failing test first; no section-banner or multi-paragraph comments; docs/*.md must not cite task ids; no personal names, hostnames, addresses or home paths in tracked files; commit messages are conventional with no attribution trailers.

Out of scope: unsigned conversions beyond what TRUNC covers, float-to-float conversion, and NaN payload propagation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Unit tests written first show a TRUNC from a 4-byte and an 8-byte float to a 4-byte and an 8-byte integer lifting to IR that passes `opt -passes=verify` and that yields the integer-indefinite value for NaN and for values outside the destination range.
- [x] #2 The differential test compares the lifted result with an explicit C reference implementing the x86 rule, not with a native cast, on 2,000 inputs per function that include NaN, positive and negative infinity, and values just inside and just outside each destination range.
- [x] #3 The unclamped conversion functions are added to tests/fixtures/lift/diff.c and the existing clamped f_f2i keeps passing.
- [x] #4 docs/development.md no longer lists out-of-range float-to-int conversion as unmeasured, and states what was verified.
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
1. Measure the real instruction first: compile cvttss2si/cvttsd2si (32- and 64-bit destinations) with the keg-only clang for x86-64, run under arch -x86_64, and record what happens at 2^31-1, 2^31, -2^31, -2^31-0.5, -2^31-1, 2^63-2^40, 2^63, -2^63, -2^63-1024, +-inf, quiet and signalling NaN. This decides the guard's constants rather than guessing them.
2. Tests first in tests/test_pcode_lift.py: one case table per (source width, destination width) shape covering 4-byte and 8-byte floats to 4-byte and 8-byte integers, each case being source bits plus the expected result bits. A helper compiles the lifted module with llc for arm64, links it to a tiny C driver that writes the input into the register file at the xmm0 slot, calls sub_1000 and reads rax, so the unit test checks the value the IR computes, not the IR's shape. Assert no hole, opt -passes=verify passes, and exactly one fptosi.
3. Pin the tables to hardware with a second test that is skipped unless an x86-64 runtime works: compile the same table of inputs through the real SSE2 intrinsics for x86-64, run it under arch -x86_64, and assert the instruction returns exactly the expected bits. Native arm64 saturates, so the expectation tables need an oracle that is not arm64.
4. Implement in scripts/pcode_lift.py: TRUNC emits a guard instead of a bare fptosi. fcmp uno for NaN, fcmp oge against +2^(bits-1), fcmp olt against -2^(bits-1); the three flags or together, select replaces the float operand with +0.0 where the flag is set so fptosi never sees a value it would call poison, and a second select replaces the converted integer with -(2^(bits-1)), the integer indefinite value. All four constants are powers of two, so they are exact in float and double and no threshold can round.
5. Extend the differential test per the acceptance criteria: unclamped conversion functions in tests/fixtures/lift/diff.c plus a sibling C reference in the same file that implements the x86 rule explicitly, an oracle map so the harness compares the lifted result with the reference rather than with a native cast, and input pickers that draw NaN, both infinities, and values just inside and just outside each destination range, 2000 inputs per function. Keep the clamped f_f2i passing.
6. Record in docs/development.md that out-of-range float-to-int conversion is no longer unmeasured and what was verified, drop it from the unmeasured list, task check green, conventional commit with no attribution, then the backlog record commit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The x86-64 expectation tables need a hardware oracle and Rosetta is one: compile the table with the keg-only clang under -arch x86_64, run it with `arch -x86_64`, and assert the intrinsic returns exactly the expected bits. Without that step the tables encode what the author believed, and in this case two of them were wrong (floor instead of truncation toward zero) and one used 1e9 as an out-of-range int32 value when it is comfortably in range.

Do not write a bit pattern into a C double column as a hex integer literal: 0x43dfffffffffffff rounds to 0x43e0000000000000 on the way in, so the case silently tests a different value. Store the bits in a uint64_t column and memcpy from its address; the same field then serves both the register-file write and the intrinsic's bitcast.

A helper in a test module must not start with test_: pytest collects it, fails to supply its arguments, and the run reports an error that has nothing to do with the code under test.

The differential harness picks scalar arguments by argument kind, and kinds f and v already meant packed float and double vectors, so a scalar float needed a new kind (s) rather than a reuse of f.

The guard's shape matters as much as its bounds: selecting over the float operand keeps fptosi total, which avoids selecting over a poison integer value, an IR shape whose behaviour LLVM does not promise.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
TRUNC (x86 cvttss2si/cvttsd2si) no longer lowers to a bare fptosi. The emitter now guards it: `fcmp uno a, a` for NaN, `fcmp oge` against +2^(bits-1) and `fcmp olt` against -2^(bits-1), the three flags OR'd into one, a `select` that substitutes +0.0 for the float operand where the flag is set (so fptosi never sees a value it would call poison, and no select is needed over a poison integer), and a second `select` that substitutes -(2^(bits-1)), the integer indefinite value. Exactly one fptosi per TRUNC, which the shape test asserts, so the guard costs no extra conversion.

What measurement, not assumption, decided:

- The bounds are inclusive below and exclusive above: -2^31 is a valid result and 2^31 is not. A naive -2^31-1 lower threshold would round to -2^31 in float and wrongly mark the valid -2^31 indefinite, so the guard uses -2^(bits-1) exclusively. All four constants are powers of two, hence exact in float and double, so no bound can round.
- In the window (-2^31-1, -2^31) truncation and the indefinite value are the same bits, so that boundary is unobservable and no test can distinguish the two rules there.
- Truncation is toward zero, not floor: -0.9999999 and -0.5 both give 0. The expectation tables initially said -1 and the Rosetta oracle rejected them.
- float->i64 of 1e18 gives 999999984306749440, the truncation of the float's own value, which the table pins.

Tests (tests/test_pcode_lift.py): four shapes (float and double to i32 and i64), each with a bit-pattern case table covering zero and signed zero, negative fractions, both bounds and one step outside each, both infinities, quiet and signalling NaN. Each shape is asserted to lift with no hole and exactly one fptosi, to pass `opt -passes=verify`, and to compute the expected bits when llc-compiled for arm64 and driven through the register file. A Rosetta-gated test runs the same tables through the SSE2 intrinsics on an x86-64 build, which is what pins the expectations: native arm64 saturates, so it cannot be the oracle.

Differential (tests/fixtures/lift/diff.c, tests/test_pcode_lift_differential.py): four unclamped conversions f_d2i32, f_d2i64, f_f2i32 and f_f2i64 are lifted and compared against explicit-rule C references r_* in the same fixture rather than against the native build, on 2,000 inputs each drawn from a picker that includes NaN, both infinities, signed zero and literals just inside and just outside each destination range. The clamped f_f2i is unchanged and keeps comparing against the native build.

Verified, not assumed: reverting the guard to a bare fptosi makes all four differential comparisons fail at the first inputs (f_d2i32 mismatch 7, f_d2i64 mismatch 2, f_f2i32 mismatch 2, f_f2i64 mismatch 0), so the comparison is discriminating rather than vacuous. task check green: 2056 passed, 1 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->
