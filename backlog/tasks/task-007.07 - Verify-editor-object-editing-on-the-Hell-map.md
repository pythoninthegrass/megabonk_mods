---
id: TASK-007.07
title: Verify editor object editing on the Hell map
status: Done
assignee:
  - Claude
created_date: '2026-10-27T22:13:00Z'
updated_date: '2026-10-27T22:25:00Z'
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
- [x] #1 Relaunch with map 64 enters the editor and logs KillFloor: armed from terrain height
- [x] #2 Object place, move, remove, undo/redo, save and reload work on Hell
- [x] #3 Any difference from Desert (missing collider, null generator, floor height) is fixed or documented
- [x] #4 docs/development.md no longer says the Hell terrain collider is unchecked
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Rebuild/deploy the mod (`task mod:build`), then `relaunch` with map=64 and check the log for `EditorMode: entered` and `KillFloor: armed ... (terrain low y=...)`.
2. Query the running game for `MapGenerator.mesh` / `proceduralMapMeshGenerator` and its `MeshCollider` on Hell, compare with Desert (floor height, null generator).
3. In the editor on Hell: place, move, remove, undo/redo, save, reload the saved level; check the log for faults.
4. If anything differs from Desert, write a failing test where logic is testable, then fix; otherwise document.
5. Update docs/development.md (drop the "not checked" sentence, record the Hell findings), run `task check`, commit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Hell has a populated MapGenerator.mesh with a MeshCollider: KillFloor armed at y=-12 (terrain low y=-6.31, catch floor -20). Place, rotate, drag-move, remove, undo/redo, save (3 edits) and reload via relaunch all verified in the running game (CrossOver). One difference from Desert: CatalogPrefabs.FindMap read DataManager.maps, which omits Hell, so placing threw 'No MapData for map Hell'. Fixed by looking maps up through Resources.FindObjectsOfTypeAll<MapData>() (CatalogPrefabs.TryFindMap), shared with LevelLoader. The fix is Il2Cpp-bound and has no C# unit-test project, so DoD #2 is unchecked.

Correction: the repo does have a C# test project (tests/MegabonkLevels.Tests, 1024 tests passing). DoD #2 stays unchecked because TryFindMap calls Resources.FindObjectsOfTypeAll and needs the running game, not because no test project exists.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Hell's editor terrain path works like Desert's (populated mesh and MeshCollider, kill floor from terrain height). The only fault was prefab lookup via DataManager.maps, which omits Hell and made object placement throw; CatalogPrefabs now resolves MapData through Resources.FindObjectsOfTypeAll, shared with LevelLoader. Verified in the running game: relaunch with map 64, place, rotate, drag-move, delete, undo/redo, save and reload. task check passes (276 tests). docs/development.md updated.
<!-- SECTION:FINAL_SUMMARY:END -->
