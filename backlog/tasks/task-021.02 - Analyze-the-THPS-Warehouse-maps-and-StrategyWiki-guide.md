---
id: TASK-021.02
title: Analyze the THPS Warehouse maps and StrategyWiki guide
status: To Do
assignee: []
created_date: '2026-10-27T22:08:00Z'
updated_date: '2026-10-27T22:08:00Z'
labels:
  - level-editor
  - thps
dependencies: []
references:
  - tools/thps_warehouse_strategywiki.md
  - tools/thps_warehouse_items_map.png
  - tools/thps_warehouse_itemless_map.png
parent_task_id: TASK-021
priority: medium
type: spike
ordinal: 88000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The top-down maps and the StrategyWiki guide give the warehouse's floor plan and every collectible and gap, which the video frames do not show cleanly. The layout spec needs a complete, positioned inventory to work from.

Sources: `tools/thps_warehouse_items_map.png` (with collectibles) and `tools/thps_warehouse_itemless_map.png` (without), both gitignored and only present on machines that have them, and `tools/thps_warehouse_strategywiki.md` (five box piles, S-K-A-T-E letters, secret tape, three 100-point pickups, and the named gaps). The doc started by TASK-021.01 is extended with this inventory.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The doc lists every collectible: 5 box piles, the letters S, K, A, T and E, the secret tape and the three 100-point pickups, each with its position on the map and its height relative to nearby structures
- [ ] #2 The doc lists every named gap and rail from the guide with the structures it connects
- [ ] #3 The map's scale and orientation are related to the frame-derived sizes from TASK-021.01, with discrepancies noted
- [ ] #4 The floor plan is described well enough to redraw without reopening the image
- [ ] #5 Anything the maps or guide leave ambiguous is listed explicitly instead of guessed
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
