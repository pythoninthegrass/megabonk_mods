---
id: TASK-084.07
title: Package a reproducible local VPK for the full Vita port
status: To Do
assignee: []
created_date: '2026-11-18T06:02:00Z'
updated_date: '2026-11-18T06:02:00Z'
labels:
  - ps-vita
  - vita-delivery
dependencies:
  - TASK-084.06
  - TASK-084.03
documentation:
  - .agents/skills/vita-port/references/toolchain.md
parent_task_id: TASK-084
type: task
ordinal: 292000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Start only after the PCH-2000 swarm gate explicitly records GO. If it records NO-GO, close this task as Done with all acceptance criteria unchecked and cite the gate. The final handoff must be reproducible from an owned copy without distributing commercial content, game-derived code or Sony modules.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Document the pinned input build, toolchain, exact install/data paths and any prerequisites; unsupported or missing inputs produce a clear error.
- [ ] #2 A clean local build produces a validated VPK with the correct LiveArea and executable metadata, with no proprietary material published or tracked.
- [ ] #3 A fresh install on a physical PCH-2000 boots, loads local game data, starts a run and preserves its save on restart.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
