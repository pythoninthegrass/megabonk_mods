---
id: TASK-032.06
title: Port the THPS Warehouse to a from-scratch level
status: To Do
assignee: []
created_date: '2026-11-04 20:37'
updated_date: '2026-11-04 20:37'
labels: []
dependencies:
  - TASK-032.03
  - TASK-032.04
parent_task_id: TASK-032
priority: high
ordinal: 159000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Parent TASK-032. The shipped Warehouse (levels/thps.mblevel.json) and the piece-assembled variant (levels/thps-editable.mblevel.json) get their blank slate by deleting the stock Forest piece by piece: 224 tile.remove and 966 object.remove out of 1241 edits. The builders hardcode per-seed object counts, keep a hidden spawn cell at (10,7), and keep the generated PlayerSpawnPortal and BossSpawner.

Regenerate both levels as from-scratch files from scripts/build_thps_level.py and scripts/build_thps_editable_level.py: emit the authored grid (only the floor actually needed, or none if the mesh carries everything), spawn, bossSpawner and the existing placements, and drop the tile and clutter removals, the seed object counts, the kept object categories and the hidden spawn cell. Keep gameplay identical: rails, shrines, chests, boombox, music and the boss redirect. Check whether the generated ForestParticles that the old level kept needs an explicit placement.

The preservation baseline (tests/fixtures/thps-preservation.json, scripts/check_thps_preservation.py) pins the old output byte for byte; regenerate it deliberately and explain why in the commit body. Write the builder tests first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Both regenerated Warehouse levels are from-scratch files containing no gen: targets and no tile edit ops, and carrying spawn and bossSpawner
- [ ] #2 Builder tests written first assert those properties for both builders
- [ ] #3 The preservation baseline is regenerated and the reason is in the commit body
- [ ] #4 The shipped Warehouse loads, starts at the spawn without a reset or Forest flash, and plays through to the boss and portal, verified in the running game
- [ ] #5 The piece-assembled variant loads and its placements match the pre-port set
- [ ] #6 Load time on the Warehouse is not slower than before, with before and after timings recorded in the task
- [ ] #7 docs/thps-warehouse-layout.md no longer describes the hidden spawn cell or the removal counts
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
