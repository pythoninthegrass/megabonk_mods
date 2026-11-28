---
id: TASK-086.03.09
title: 'Keep Mountain Pass shrine, power-up and spawn spots reachable'
status: To Do
assignee: []
created_date: '2026-11-28T06:28:00Z'
updated_date: '2026-11-28T06:28:00Z'
labels:
  - level
  - kf1
dependencies:
  - TASK-086.03.02
parent_task_id: TASK-086.03
priority: medium
type: bug
ordinal: 314000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The first shop volume of the compiled Mountain Pass is a sealed room with no exit: KF1 door movers are not in the BSP export, so carved pods are closed shells and the converter still places shrine, power-up and spawn candidates inside them. A player teleported or spawned there cannot leave. Limit those candidates to spots reachable from the player spawn (for example a flood fill over walkable floor), or open the interior doorways. Texture and material fidelity is tracked separately in TASK-086.03.05 (brush textures: Architecture_T roof 557 faces, Architecture_T2 stucco 117, SheetMetal_combiner 7, Engine.BlackTexture 393), TASK-086.03.06 (static mesh material slots, e.g. the gray helicopter), TASK-086.03.07 and TASK-086.03.08.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The converter reports which anchors are unreachable from the player spawn
- [ ] #2 Shrine, power-up and spawn candidates are limited to reachable spots, or the interior doorways are opened
- [ ] #3 The player can leave every interior in the running game, checked by walking at least the four shop volumes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
