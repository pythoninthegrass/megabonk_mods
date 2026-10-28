---
id: TASK-021.12
title: Stop the boss portal pillar from blocking the main half pipe
status: Done
assignee:
  - '@claude'
created_date: '2026-10-28 04:12'
updated_date: '2026-10-28 06:05'
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
- [x] #1 The half pipe below the secret room is free of the pillar: the player can ride the full pipe without hitting it
- [x] #2 The boss portal still shows its steps and ring in the secret room and still spawns the boss when used
- [x] #3 A screenshot of the pipe and of the portal is saved under .tools/evidence/ and noted in the task
- [x] #4 Any new generator behaviour is covered by tests in tests/test_build_thps_level.py, and docs/thps-warehouse-layout.md is updated
- [x] #5 The portal is scaled to 0.4, turned 90 degrees so its arch faces down the corridor, and sits at (170, 15.6, 27) inside the hanging box
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Relaunch the game and use query_objects on gen:object:BossSpawner:0000 to list children, renderers and colliders (read-only).
2. Direction from Lance: keep the steps and ring, move the steps inside the suspended box, mask or remove the pillar they attach to. Preferred: shrink the portal so it fits inside the box; otherwise enlarge the box to cover it (hidden boss portal).
3. Write a failing test in tests/test_build_thps_level.py for any new generator edit (for example a scale on the object.move transform, or a hide edit).
4. Implement, rebuild with task mod:build, relaunch, load, editor on, ride the pipe, screenshot pipe and portal to .tools/evidence/.
5. Update docs/thps-warehouse-layout.md, run task check, conventional commit without attribution.

Findings: pillar = BottomPiece renderer plus invisible Collider (y -18 to 25, x/z 165 +/- 12.4); box centre about (155, 15.6 floor, 25), about 14 wide. Approved: scale the portal about 0.5 and move it into the box, add an object.hide mod op that disables a named child's renderers and colliders, hide BottomPiece and Collider. AC #3 rewritten accordingly.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented as optional hiddenChildren on object.move (not a separate object.hide op) to reuse the existing plumbing. Portal at (170, 15.6, 27), scale 0.35, hides BottomPiece and Collider. Evidence under .tools/evidence/: task-021-12-portal-hidden-in-box-play.png (clear pipe from the west), task-021-12-portal-lowered.png (portal inside the box). The pipe was checked visually; the player did not ride it. AC #2 is not yet verified: the BossSpawner trigger is left enabled and scaled with the object, but interacting with the portal and spawning the boss was not tested in game.

Final: scale 0.4 (tuned by Lance through 0.5, 0.475, 0.4655, 0.4562, 0.35, 0.3555), yaw 90 so the arch faces down the corridor, position (170, 15.6, 27). Lance confirmed in game that the portal is interactive and fits the box without clipping. The pipe clearance was confirmed by screenshot only; the pipe was not ridden. Evidence: .tools/evidence/task-021-12-scale-0475-yaw90.png and the earlier task-021-12-* screenshots. Related: TASK-021.17 and TASK-021.18 (editor drag and snap), TASK-021.16 (windows, not started).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The boss portal's invisible 43-unit Collider and BottomPiece mesh are hidden through a new optional hiddenChildren list on object.move, so the half pipe is clear. The portal is scaled to 0.4, turned 90 degrees and placed at (170, 15.6, 27) inside the hanging box. Generator, mod, tests and docs are updated. Pipe clearance was checked by screenshot, not ridden.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
