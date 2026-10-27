---
id: TASK-021.03
title: Write the Megabonk layout spec for the THPS Warehouse
status: To Do
assignee: []
created_date: '2026-10-27T22:08:00Z'
labels:
  - level-editor
  - thps
dependencies:
  - TASK-021.01
  - TASK-021.02
documentation:
  - docs/level-format.md
  - docs/runtime-map-structure.md
  - docs/asset-bundles.md
parent_task_id: TASK-021
priority: medium
type: spike
ordinal: 89000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Before building, the THPS analysis has to be translated into what the Megabonk editor can actually place. This task turns the structure and collectible inventory from TASK-021.01 and TASK-021.02 into a concrete build spec, so the geometry, asset and item tasks do not each make their own guesses.

Constraints to carry in: the editor works on tile-grid maps and refuses ProceduralMesh maps such as Desert (see `docs/level-format.md`, `docs/runtime-map-structure.md` and `docs/asset-bundles.md` for the grid, catalog IDs and asset packs). Collectibles stay as normal Megabonk items (chests, shrines and similar) rather than becoming THPS pickups. The collectible-to-item mapping is a judgment call that needs Lance's sign-off before items are placed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A doc records the chosen base map and stage, with the reason, and excludes ProceduralMesh maps
- [ ] #2 THPS dimensions are mapped onto the Megabonk tile grid, with the scale factor and the player-reachable heights stated
- [ ] #3 Every structure from the analysis names the existing catalog ID it will reuse, or is marked as needing a new asset with a reason
- [ ] #4 A proposed collectible-to-item mapping covers the box piles, the letters S, K, A, T and E, the tape and the 100-point pickups, each with a target grid position
- [ ] #5 Lance has confirmed or changed the collectible-to-item mapping, and the doc records the final version
- [ ] #6 Open questions or risks that need Lance's input are flagged explicitly
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
