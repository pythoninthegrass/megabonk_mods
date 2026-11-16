---
id: TASK-080.12.05
title: Preserve exception propagation through lifted arm64 code
status: To Do
assignee: []
created_date: '2026-11-16T19:04:00Z'
updated_date: '2026-11-16T19:05:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.02
references:
  - scripts/pcode_lift.py
  - scripts/eh_probe.py
  - TASK-080.07
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 272000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The census found exception tables on 8,373 game-section bodies and 103,628 landing-pad entries. Current lifted code ignores their unwinding semantics, so successfully compiling a throwing method cannot count as correctness. This task establishes interoperable exception propagation for the native runtime, including interaction with native callers; it does not remeasure the already recorded census. Original binary exception metadata remains local-only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Lifted code matches the shipped reference for caught throws, nested propagation, cleanup/finally execution, rethrow and an uncaught exception's reported outcome.
- [ ] #2 Exceptions crossing required native/lifted boundaries unwind correctly without corrupting stack or register state.
- [ ] #3 Required exception-bearing bodies and metadata in the selected runtime image are accounted for; unsupported unwind cases are rejected rather than emitted as apparently runnable code.
- [ ] #4 Regression tests execute on native arm64, include cleanup ordering and failure cases, and docs state the verified unwind contract and coverage.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
