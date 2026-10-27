---
id: TASK-007.05.03
title: Verify editor placement on Graveyard
status: To Do
assignee: []
created_date: '2026-10-27 05:47'
updated_date: '2026-10-27 06:07'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-007.05
priority: low
ordinal: 72000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found while verifying TASK-007.05: Graveyard is `EMapType.Tiles` and generates with a 19x19 grid and an armed kill floor (`KillFloor: armed at y=-192`), so the editor should work there. Verify it in the running game and fix whatever fails, such as the crypt/exit structures in `MapGenerationController`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A Graveyard level loads through `run.py relaunch` with the kill floor armed and the player on a grid cell
- [ ] #2 In the editor on Graveyard, selecting a palette entry (including a pack entry) and clicking a tile places the object, and undo/redo and save work
- [ ] #3 A level saved on Graveyard reloads with its edits
- [ ] #4 Anything that fails is fixed or recorded with its cause
- [ ] #5 Forest behaviour is unchanged
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Context added 2026-10-27: Graveyard was only loaded with `run.py load` into a running game, which logged `mapType=0`, `proceduralTiles.Length=19`, `occupiedCells=361` and `KillFloor: armed at y=-192`. Placement, save and reload were not tried there. The editor refusal for non-Tiles maps (commit d183a25) does not affect it. The pack entries are already in the palette on every supported map (commit f322bde).
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
