---
id: TASK-080.05
title: Make float-to-integer conversion match x86 on overflow and NaN
status: To Do
assignee: []
created_date: '2026-11-16T02:09:00Z'
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
- [ ] #1 Unit tests written first show a TRUNC from a 4-byte and an 8-byte float to a 4-byte and an 8-byte integer lifting to IR that passes `opt -passes=verify` and that yields the integer-indefinite value for NaN and for values outside the destination range.
- [ ] #2 The differential test compares the lifted result with an explicit C reference implementing the x86 rule, not with a native cast, on 2,000 inputs per function that include NaN, positive and negative infinity, and values just inside and just outside each destination range.
- [ ] #3 The unclamped conversion functions are added to tests/fixtures/lift/diff.c and the existing clamped f_f2i keeps passing.
- [ ] #4 docs/development.md no longer lists out-of-range float-to-int conversion as unmeasured, and states what was verified.
- [ ] #5 All existing tests still pass and `task check` passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
