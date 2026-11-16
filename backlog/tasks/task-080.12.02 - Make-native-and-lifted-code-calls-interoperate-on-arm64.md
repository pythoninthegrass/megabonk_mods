---
id: TASK-080.12.02
title: Make native and lifted code calls interoperate on arm64
status: To Do
assignee: []
created_date: '2026-11-16T19:04:00Z'
updated_date: '2026-11-16T19:05:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.01
references:
  - scripts/pcode_lift.py
  - tests/test_pcode_lift_differential.py
  - scripts/native_bind_probe/host.c
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 269000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Lifted functions currently share a register-state pointer, while Unity, IL2CPP and native imports use native calling conventions. A single successful constant-return method does not establish calls with arguments, nested calls or callbacks. This task delivers the calling-interface contract needed by the rebuilt runtime; image/data relocation and exception unwinding are separate sibling tasks. The shipped Linux runtime remains the reference, and unsupported signatures must be visible rather than silently accepted.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Bidirectional native-to-lifted and lifted-to-native calls preserve arguments and results for the signature classes required by the chosen runtime integration, including integer, pointer, floating-point, vector and stack-passed cases.
- [ ] #2 Nested calls, indirect dispatch and a native callback into lifted code execute correctly with register/stack state preserved on return.
- [ ] #3 Supported aggregate and variadic behaviour is explicitly verified where required; unsupported cases are diagnosed before execution rather than invoked with a guessed signature.
- [ ] #4 Automated native arm64 execution tests include shipped-code comparisons, and developer docs record the supported calling contract and remaining exclusions.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
