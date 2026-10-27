---
id: TASK-007.07
title: Verify editor object editing on the Hell map
status: To Do
assignee: []
created_date: '2026-10-27T22:13:00Z'
labels:
  - level-editor
dependencies:
  - TASK-007.06
parent_task_id: TASK-007
priority: low
ordinal: 94000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up to TASK-007.06. Hell is `EMapType.ProceduralMesh` (`MapHell`, `eMap=64`), so the editor takes the same terrain path as Desert: raycast against `MapGenerator.mesh`'s `MeshCollider`, kill floor from the collider's lowest point, object ops only. That path has only been run on Desert. Confirm in the running game that Hell has a populated `proceduralMapMeshGenerator` and a `MeshCollider` on its mesh, and fix whatever differs from Desert. Docs currently say the Hell terrain collider has not been checked.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Relaunch with map 64 enters the editor and logs KillFloor: armed from terrain height
- [ ] #2 Object place, move, remove, undo/redo, save and reload work on Hell
- [ ] #3 Any difference from Desert (missing collider, null generator, floor height) is fixed or documented
- [ ] #4 docs/development.md no longer says the Hell terrain collider is unchecked
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
