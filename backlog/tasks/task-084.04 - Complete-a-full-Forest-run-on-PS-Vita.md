---
id: TASK-084.04
title: Complete a full Forest run on PS Vita
status: To Do
assignee: []
created_date: '2026-11-18T06:02:00Z'
updated_date: '2026-11-18T06:02:00Z'
labels:
  - ps-vita
  - vita-delivery
dependencies:
  - TASK-084.03
documentation:
  - .agents/skills/vita-port/SKILL.md
parent_task_id: TASK-084
type: feature
ordinal: 289000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Start only after the PCH-2000 swarm gate explicitly records GO. If it records NO-GO, close this task as Done with all acceptance criteria unchecked and cite the gate. Turn the graybox loop into the first end-to-end stage after an explicit GO. Use the pinned build as reference and keep all game-derived artifacts local.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 On a physical PCH-2000, a player can go from character selection through Forest traversal, combat and upgrades to a boss and normal run resolution.
- [ ] #2 Death and restart work, and earned offline progression survives a clean relaunch without touching desktop saves.
- [ ] #3 A representative full run records frame pacing, peak memory and any regressions against the GO benchmark.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
