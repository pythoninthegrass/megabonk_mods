---
id: TASK-008
title: Show player position in game while developing levels
status: Done
assignee: []
created_date: '2026-10-08 05:13'
updated_date: '2026-10-08 06:21'
labels:
  - level-editor
dependencies: []
priority: medium
ordinal: 42000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Finding the kill floor and the Forest boss (Lil Bark) escaping through a removed-tile hole during a manual playthrough of a scratch level was slow because nothing in the game shows where the player is. Level edits are keyed on grid cells (cell (x, z) is at world (-280 + 40x, 20 * height, -280 + 40z) on the 15x15 Forest map), so a level author needs the world position and the grid cell on screen. Two pieces of work: (1) research whether the game's own minimap can carry the position, and (2) ship the simplest dev-only on-screen readout, which does not depend on the research. Unity's ground plane is x and z; y is height.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
