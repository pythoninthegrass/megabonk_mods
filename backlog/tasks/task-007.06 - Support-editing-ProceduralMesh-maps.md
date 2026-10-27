---
id: TASK-007.06
title: Support editing ProceduralMesh maps
status: To Do
assignee: []
created_date: '2026-10-27 06:02'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-007
priority: low
ordinal: 73000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up to TASK-007.05.01. Maps with `EMapType.ProceduralMesh` (Desert) generate one heightmap mesh through `MapGenerator` and never fill `ProceduralTileGeneration.proceduralTiles`, so the editor refuses them. Add object editing on those maps: raycast the cursor against the mesh collider, define how a world position maps to the level format's grid cell (or extend the format), take the kill-floor height from the terrain, and decide what happens to the tile tools (disabled on these maps). Needs a design decision on the level format before implementation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A design note decides how objects on a ProceduralMesh map are keyed in the level format and how they are replayed on load
- [ ] #2 The editor enters on Desert, the cursor targets the terrain, and the kill floor arms from terrain height
- [ ] #3 Object place, move, remove, undo/redo, save and reload work on Desert; the tile tools are disabled with a clear message
- [ ] #4 Forest behaviour is unchanged
- [ ] #5 Unit tests cover the Unity-free logic
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
