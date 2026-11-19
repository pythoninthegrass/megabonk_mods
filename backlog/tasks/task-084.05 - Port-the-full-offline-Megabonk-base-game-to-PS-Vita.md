---
id: TASK-084.05
title: Port the full offline Megabonk base game to PS Vita
status: To Do
assignee: []
created_date: '2026-11-18T06:02:00Z'
updated_date: '2026-11-19T08:21:00Z'
labels:
  - ps-vita
  - vita-delivery
dependencies:
  - TASK-084.04
  - TASK-084.03
references:
  - 'https://github.com/pythoninthegrass/megabonk_data'
  - ~/git/megabonk_data
documentation:
  - .agents/skills/vita-port/SKILL.md
parent_task_id: TASK-084
type: feature
ordinal: 290000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Start only after the PCH-2000 swarm gate explicitly records GO. If it records NO-GO, close this task as Done with all acceptance criteria unchecked and cite the gate. After GO, extend the playable Forest run to the pinned release's complete offline base game, rather than shipping a demo. Steam network services and mod/editor compatibility are not part of the offline port.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An inventory from the pinned reference accounts for every offline stage/tier, character, enemy and boss, weapon, tome, item, unlock and quest; all are available through the intended progression paths.
- [ ] #2 Offline menus, HUD, audio, controls, map generation, combinations and save/progression behavior are covered by documented checks.
- [ ] #3 The local content build validates supported source inputs and does not require distributing game-derived assets or proprietary runtime modules.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
