---
id: TASK-008.02
title: Add dev-only on-screen player position and grid cell readout
status: In Progress
assignee: []
created_date: '2026-10-08 05:14'
updated_date: '2026-10-08 06:08'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-008
priority: medium
ordinal: 44000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a text readout, drawn only when the dev harness is enabled, that shows the player's world position, the tile grid cell the player is over and the kill-floor height with a flag when the player is below it, for example "cell (13,7) h1  pos (240, 22, 0)  floor -72". Cell coordinates follow the live map layout: cell (x, z) is at world (-280 + 40x, 20 * height, -280 + 40z) on the 15x15 Forest map, with spacing read from StageData.mapParameters (scaledTileWidth, scaledTileHeight) at runtime. The world-to-cell conversion and the below-floor text are pure logic. The player position is already read in src/MegabonkLevels.Mod/kill_floor_watcher.cs, and the gate is the same one the other dev harness commands use (docs/development.md). First confirm that MelonLoader's OnGUI draws in this IL2CPP build; if it does not, use a text label on the game's canvas. Out of scope: the game's own minimap (separate sibling research task), and enemy or boss positions in the readout (follow-up if wanted).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 With the harness enabled, the readout shows the player's world x, y, z and grid cell in a mod-loaded level and updates as the player moves
- [ ] #2 The readout shows the kill-floor height and marks when the player is below it
- [ ] #3 The readout is not drawn when the harness is disabled or in a vanilla level
- [x] #4 The world-to-cell conversion is pure logic with unit tests written before the implementation, including cells at the grid edges and positions outside the grid
- [ ] #5 Verified in the running game with a screenshot that shows the readout, and the cell shown matches the position of a known edited cell in a scratch level
- [ ] #6 docs/development.md documents the readout
<!-- AC:END -->



## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
