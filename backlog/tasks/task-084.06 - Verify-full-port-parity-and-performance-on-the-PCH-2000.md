---
id: TASK-084.06
title: Verify full-port parity and performance on the PCH-2000
status: To Do
assignee: []
created_date: '2026-11-18T06:02:00Z'
updated_date: '2026-11-18T06:02:00Z'
labels:
  - ps-vita
  - vita-delivery
dependencies:
  - TASK-084.05
  - TASK-084.03
references:
  - TASK-081
documentation:
  - .agents/skills/vita-port/references/measurement.md
  - docs/performance.md
parent_task_id: TASK-084
type: task
ordinal: 291000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Start only after the PCH-2000 swarm gate explicitly records GO. If it records NO-GO, close this task as Done with all acceptance criteria unchecked and cite the gate. A playable port can still drift from the shipped game or hitch late in a run. Compare the native Vita candidate against the pinned shipped build before packaging.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Repeatable shipped-versus-Vita scenarios cover movement, combat, upgrades, bosses, unlocks and save/reload; known differences are recorded and gameplay-affecting deviations require maintainer approval.
- [ ] #2 On physical PCH-2000 hardware, representative early/late runs, dense swarms and boss encounters are checked against the GO frame-time and memory budgets under documented conditions.
- [ ] #3 Real controller, audible output, suspend/resume and quit/relaunch checks pass without corrupting the isolated Vita profile.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
