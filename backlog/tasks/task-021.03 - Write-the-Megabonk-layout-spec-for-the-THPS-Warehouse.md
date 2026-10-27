---
id: TASK-021.03
title: Write the Megabonk layout spec for the THPS Warehouse
status: Done
assignee:
  - Claude
created_date: '2026-10-27T22:08:00Z'
updated_date: '2026-10-27T22:50:00Z'
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
- [x] #1 A doc records the chosen base map and stage, with the reason, and excludes ProceduralMesh maps
- [x] #2 THPS dimensions are mapped onto the Megabonk tile grid, with the scale factor and the player-reachable heights stated
- [x] #3 Every structure from the analysis names the existing catalog ID it will reuse, or is marked as needing a new asset with a reason
- [x] #4 A proposed collectible-to-item mapping covers the box piles, the letters S, K, A, T and E, the tape and the 100-point pickups, each with a target grid position
- [x] #5 Lance has confirmed or changed the collectible-to-item mapping, and the doc records the final version
- [x] #6 Open questions or risks that need Lance's input are flagged explicitly
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Read level-format, runtime-map-structure, asset-bundles. Done.
2. Read stage and player facts from the live game (MapParameters, Player capsule, Forest palette via ui-tree). Done.
3. Write docs/thps-warehouse-layout.md: base map and stage, scale and grid, structure-to-catalog table, proposed collectible mapping, open questions. Draft written, lint passes.
4. Get Lance's confirmation or changes on the collectible mapping, record the final version (AC #5), then task check, conventional commit with no attribution, close.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Draft doc docs/thps-warehouse-layout.md is uncommitted. Waiting on Lance for AC #5 (collectible mapping sign-off). Game left running in editor mode on Forest.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added docs/thps-warehouse-layout.md: Forest stage 0 (ParamForest1, seed 20261007) as the base map with Desert, Hell and Dungeon excluded; measured scale facts (player capsule 3.85 u, tile 40 u, level step 20 u); a 4.4 u per THPS metre scale on a 4x3 tile block, confirmed by Lance; a structure-to-catalog table showing that only the floor, enclosure, raised north-east block, pit and rails reuse existing assets and the ramps, decks, ledges, kickers, taxi, half pipe and corridor need new assets; the collectible mapping (box piles = chest, letters = shrines 0-4, tape and 100s = chestFree) with block-local positions, confirmed by Lance; and open risks. Player jump height is unmeasured and stated as an assumption, and the 4x3 block location is still to be chosen from a height dump. task check passes. No code or tests apply, so the test-first item is satisfied vacuously.
<!-- SECTION:FINAL_SUMMARY:END -->
