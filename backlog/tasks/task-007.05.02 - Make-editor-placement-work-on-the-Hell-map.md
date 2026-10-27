---
id: TASK-007.05.02
title: Fix Hell level loading (no MapData found)
status: To Do
assignee: []
created_date: '2026-10-27 05:47'
updated_date: '2026-10-27 06:08'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-007.05
priority: low
ordinal: 71000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found while verifying TASK-007.05: loading a level with `map: 4` (Hell) logs `LevelLoader: no MapData found for map=Hell` and never starts the map, so the editor cannot be used there. Desert is a ProceduralMesh map and Graveyard a Tiles map that loads; Hell's type is not yet known. Find why `LevelLoader` cannot find Hell's `MapData` (for example it is not loaded until unlocked or has another name) and fix it, then check whether Hell is a Tiles map.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The reason LevelLoader finds no MapData for Hell is identified and documented
- [ ] #2 A level with map Hell loads through `run.py relaunch`, or the reason it cannot is documented
- [ ] #3 Hell's `EMapType` is recorded; if it is Tiles the kill floor arms and the player has a grid cell, and if it is ProceduralMesh it is refused like Desert
- [ ] #4 If Hell is a Tiles map: in the editor, selecting a palette entry and clicking a tile places the object, and undo/redo and save work
- [ ] #5 Forest behaviour is unchanged
- [ ] #6 Unit tests cover any Unity-free logic added
- [ ] #7 `run.py relaunch` into a level whose map fails to start (such as `no MapData found`) fails fast with that reason instead of retrying until timeout
<!-- AC:END -->



## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Context added 2026-10-27: the editor refusal for non-Tiles maps is in commit d183a25, so if Hell turns out to be ProceduralMesh, AC #3 is already satisfied by it. `run.py relaunch` now stops early only on `KillFloor: armed` or `EditorMode: unsupported map`; a load that fails earlier (`LevelLoader: no MapData found for map=Hell`) emits neither line, so relaunch into Hell still retries five times and times out. Check Hell with `run.py load` plus the log until the loader is fixed.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
