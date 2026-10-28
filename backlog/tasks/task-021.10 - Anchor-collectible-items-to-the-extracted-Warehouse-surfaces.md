---
id: TASK-021.10
title: Anchor collectible items to the extracted Warehouse surfaces
status: To Do
assignee: []
created_date: '2026-10-28 02:41'
updated_date: '2026-10-28 02:41'
labels:
  - thps
  - level-editor
dependencies:
  - TASK-021.08
  - TASK-021.09
documentation:
  - docs/thps-warehouse-layout.md
  - scripts/build_thps_level.py
  - tests/test_build_thps_level.py
parent_task_id: TASK-021
priority: high
ordinal: 98000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Collectibles in levels/thps.mblevel.json look randomly placed and clip into geometry: the secret-tape chest pokes through the floating corridor's floor, the lane items are tilted or stand alone on grass, and the ledge rail runs through the R1 chest. Replace the hand-nudged COLLECTIBLES table in scripts/build_thps_level.py with positions read from the extracted warehouse_nodes.json, keeping the approved mapping (box piles to chests, letters to shrines, tape and the 100 pickups to free chests). Each item stands on the collider surface directly below its node, found by a downward ray against the imported mesh, with the item prefab's pivot-to-base offset applied and its tilt taken from the surface normal. Item pivots and bounds are read from the live game with query_objects. Depends on the extraction and mesh import tasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Tests written first fail before the change: every item's base is within 0.1 unit of the surface below it
- [ ] #2 A test checks that no item's bounds overlap collider triangles other than the one it stands on
- [ ] #3 A test checks that each item is within a stated distance of its source node in x and z
- [ ] #4 COLLECTIBLES is derived from warehouse_nodes.json rather than hand-written coordinates
- [ ] #5 In-game close-up screenshots of all 14 items show none floating or clipping, including the tape chest from below
- [ ] #6 Teleporting the player onto each item's surface settles at the predicted height
- [ ] #7 docs/thps-warehouse-layout.md lists any approved deviations from the source positions
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
