---
id: TASK-005.01
title: 'Editor mode entry, freeze gameplay, free-fly camera'
status: To Do
assignee: []
created_date: '2026-10-06 21:43'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-005
priority: high
type: feature
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-005 first for full context.

Implement entering/exiting an editor overlay mode via a keybind (e.g. F8, confirm it doesn't collide with an existing game binding via Rewired's input map). On entry: pause the stage timeline and enemy spawning, disable player control/damage, and switch the active camera to a free-fly camera (detached from the player, mouse-look + WASD + vertical movement) so the player can survey/navigate the whole map. On exit: restore the previous camera and gameplay state cleanly (no lingering paused state if the player exits without saving).

This subtask is pure mode-management plumbing — no editing tools yet (that's TASK-005.02-.04). Verify entering and exiting repeatedly doesn't leak state (e.g. multiple free-fly cameras stacking, gameplay staying paused after exit).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A keybind toggles editor mode on/off without colliding with existing game bindings
- [ ] #2 Entering editor mode pauses the stage timeline, enemy spawning, and player control/damage
- [ ] #3 Entering editor mode switches to a free-fly camera with mouse-look and WASD+vertical movement
- [ ] #4 Exiting editor mode restores the prior camera and resumes gameplay cleanly, verified across multiple enter/exit cycles with no leaked state
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
