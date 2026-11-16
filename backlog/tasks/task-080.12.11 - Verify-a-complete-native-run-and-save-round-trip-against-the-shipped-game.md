---
id: TASK-080.12.11
title: Verify a complete native run and save round trip against the shipped game
status: To Do
assignee: []
created_date: '2026-11-16T19:05:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.09
  - TASK-080.12.10
  - TASK-081
references:
  - TASK-081
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: task
ordinal: 278000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Launching and rendering cannot detect a port that quietly changes gameplay. TASK-081 supplies the frozen shipped-build scenario corpus and self-consistency checks; this task applies that oracle to the native build and adds an actual complete-run and save/reload acceptance gate. Do not invent a second golden-corpus format or use Wine/CrossOver performance or behaviour as the justification for native equivalence. Any permitted numeric or rendering tolerance must be explicit and not mask gameplay differences.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The same controlled scenarios run on the frozen shipped reference and native candidate through TASK-081's harness, with recorded candidate identity and machine-readable field differences.
- [ ] #2 A complete native gameplay run exercises stage transitions, combat, rewards, death/retry and normal exit without unresolved runtime failures.
- [ ] #3 Saving and reloading an isolated profile preserves the verified progression/settings and leaves the reference profile untouched, including failure or interrupted-write coverage.
- [ ] #4 The report has no unexplained gameplay differences, states justified tolerances explicitly, and docs/tests reproduce the comparison and full-run acceptance gate.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
