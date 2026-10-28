---
id: TASK-021.12
title: Stop the boss portal pillar from blocking the main half pipe
status: To Do
assignee: []
created_date: '2026-10-28 04:12'
labels:
  - thps
  - level-editor
dependencies: []
documentation:
  - docs/thps-warehouse-layout.md
  - scripts/build_thps_level.py
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
parent_task_id: TASK-021
priority: medium
ordinal: 100000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The boss portal (the game's BossSpawner object) stands in the secret room above the main half pipe at world (165, 12, 26). Its stone pillar, the part beneath the ring, protrudes into the half pipe below and blocks it. Keep the steps and the ring the player sees, but stop the pillar from obstructing the half pipe. Either hide the pillar (mask it) or replace the portal with a clone that has only the steps and the ring. The boss spawner position is set in scripts/build_thps_level.py (BOSS_SPAWN_LOCAL, BOSS_SPAWN_Y) through an object.move edit on gen:object:BossSpawner:0000. The pillar geometry belongs to the game's prefab, so check what the mod can change at runtime versus what needs a pack prefab.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The half pipe below the secret room is free of the pillar: the player can ride the full pipe without hitting it
- [ ] #2 The boss portal still shows its steps and ring in the secret room and still spawns the boss when used
- [ ] #3 The portal still sits at the same position in the secret room
- [ ] #4 A screenshot of the pipe and of the portal is saved under .tools/evidence/ and noted in the task
- [ ] #5 Any new generator behaviour is covered by tests in tests/test_build_thps_level.py, and docs/thps-warehouse-layout.md is updated
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
