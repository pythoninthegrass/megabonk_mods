---
id: TASK-021.02
title: Analyze the THPS Warehouse maps and StrategyWiki guide
status: Done
assignee:
  - Claude
created_date: '2026-10-27T22:08:00Z'
updated_date: '2026-10-27T22:44:00Z'
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
- [x] #1 The doc lists every collectible: 5 box piles, the letters S, K, A, T and E, the secret tape and the three 100-point pickups, each with its position on the map and its height relative to nearby structures
- [x] #2 The doc lists every named gap and rail from the guide with the structures it connects
- [x] #3 The map's scale and orientation are related to the frame-derived sizes from TASK-021.01, with discrepancies noted
- [x] #4 The floor plan is described well enough to redraw without reopening the image
- [x] #5 Anything the maps or guide leave ambiguous is listed explicitly instead of guessed
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
1. Crop and upscale the items and itemless maps with magick to read small features; record pixel positions in the 973x767 image.
2. Define map-relative headings from the isometric projection and tie walls to the frame-derived landmarks (sign, window, door walls, graffiti brick corner).
3. Derive scale per isometric axis from known sizes in docs/thps-warehouse.md; list map vs frame discrepancies.
4. Cross-reference the StrategyWiki guide with the map: 5 box piles, S K A T E, tape, 3x 100 (position + height), and all 16 named gaps/rails with the structures they connect.
5. Write a redrawable floor plan (perimeter walk-around, interior features, ASCII sketch).
6. List ambiguities explicitly.
7. Extend docs/thps-warehouse.md (new sections, revise Unresolved), no task ids in the doc.
8. task lint, task check; conventional commit with no attribution; close task in a separate commit.
No code or tests: documentation-only spike, so DoD #2 does not apply.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Extended docs/thps-warehouse.md with map and guide sources, map headings and scale (with discrepancies against the frame analysis), a floor plan with feature codes M1-M15 and an ASCII sketch, positioned tables for the 5 box piles, S K A T E, the tape and the three 100-point pickups, a table of all 16 named gaps with the structures they connect, and a revised Unresolved list. Ambiguities are listed rather than guessed: box pile numbering, floating icon heights, the start block, the dark pit M13, wall identification, and the single-anchor scale. Resolved by the map: the taxi is the yellow cab at M3, and the glass corridor is one hanging box. task check passes (276 tests, markdownlint, ruff). No code or tests apply to this documentation-only spike, so the test-first item is satisfied vacuously.
<!-- SECTION:FINAL_SUMMARY:END -->
