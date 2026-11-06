---
id: TASK-006.07
title: >-
  Let a level supply its own Map Selection name and biome icon, starting with
  the Warehouse
status: To Do
assignee: []
created_date: '2026-11-06 23:41'
updated_date: '2026-11-06 23:42'
labels:
  - thps-warehouse
  - map-selection
dependencies: []
references:
  - TASK-006.05
  - TASK-006.06
  - src/MegabonkLevels.Mod/map_selection_patch.cs
  - src/MegabonkLevels.Mod/level_thumbnail_sidecar.cs
  - scripts/build_player_package.py
  - docs/level-format.md
parent_task_id: TASK-006
priority: low
type: feature
ordinal: 172000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
With the Warehouse thumbnail in place (TASK-006.05, TASK-006.06), Map Selection still labels the selected Warehouse as "Forest" at the top right, and the biome icon thumbnails down the right-hand side show the stock biome types rather than anything about the level.

Outcome: a level can supply its own display name and its own biome icon, and Map Selection shows them in the top-right name and the right-hand biome thumbnail. The Warehouse is the first user: it reads "Warehouse" and shows a halfpipe image (a single halfpipe picture is enough; it need not be a faithful render). Nothing in the mod may special-case the `thps` level or the name "Warehouse". A level that supplies neither keeps today's behaviour.

Proposed shape, to confirm before implementing: an optional display-name field on the level file, and an optional biome icon as a sidecar image beside the level (for example `thps.biome.png` next to `thps.mblevel.json`), following the thumbnail sidecar pattern in `LevelThumbnailSidecar` so the package builder from TASK-006.06 can ship it with a small extension.

Not yet investigated: where the name and biome icon come from today (the stock map data the custom entry borrows, versus fields on the level), how the sidecar naming must differ from the thumbnail so the two never collide, and whether the level-format schema needs a version bump for the name field. Record the decision in this task before implementing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Selecting the Warehouse on Map Selection shows "Warehouse" as the map name at the top right, not "Forest"
- [ ] #2 The Warehouse's biome thumbnail on the right-hand side is a halfpipe image
- [ ] #3 No code path special-cases the thps level or the name Warehouse; both values come from the level's own name field and sidecar icon
- [ ] #4 A second test level with a different name and icon shows both on Map Selection with no code change
- [ ] #5 A level with no name field and no icon sidecar, and every stock map, shows its existing name and biome icon unchanged
- [ ] #6 A missing, oversize or malformed icon falls back to the stock biome icon and logs a warning, matching how bad thumbnails are handled
- [ ] #7 The package builder bundles the biome icon next to its level and the installer places it in UserData/Levels, covered by a Python test
- [ ] #8 docs/level-format.md describes the name field and the biome icon sidecar, and docs/player-installer.md mentions the icon alongside the thumbnail
- [ ] #9 Verified in the running game with a screenshot of the Map Selection screen
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
