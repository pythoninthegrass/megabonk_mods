---
id: TASK-021.10
title: Anchor collectible items to the extracted Warehouse surfaces
status: Done
assignee:
  - '@claude'
created_date: '2026-10-28 02:41'
updated_date: '2026-10-28T19:09:00Z'
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
modified_files:
  - scripts/warehouse_surface.py
  - scripts/build_thps_level.py
  - tests/test_warehouse_surface.py
  - tests/test_build_thps_level.py
  - docs/thps-warehouse-layout.md
  - levels/thps.mblevel.json
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
- [x] #1 Tests written first fail before the change: every item's base is within 0.1 unit of the surface below it
- [x] #2 A test checks that no item's bounds overlap collider triangles other than the one it stands on
- [x] #3 A test checks that each item is within a stated distance of its source node in x and z
- [x] #4 COLLECTIBLES is derived from warehouse_nodes.json rather than hand-written coordinates
- [x] #5 In-game close-up screenshots of all 14 items show none floating or clipping, including the tape chest from below
- [x] #6 Teleporting the player onto each item's surface settles at the predicted height
- [x] #7 docs/thps-warehouse-layout.md lists any approved deviations from the source positions
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
1. New scripts/warehouse_surface.py: parse .tools/thps1/warehouse/warehouse.obj the way ThpsPack.cs does (y negated, quads split, centred on the x/z bounds, scaled by WAREHOUSE_SCALE, lifted by WAREHOUSE_LIFT) into world triangles; downward ray (highest hit at or below a point); triangle-vs-oriented-box overlap (SAT); Unity euler from an up-vector so the item's up follows the surface normal.
2. Item metrics measured in the live game (query_objects Mesh/MeshRenderer bounds on the placed items): pivot-to-base is 0.50 for chest and chestFree, 0.12/0.05/0.05/0.02/0.13 for forest/shrines/0..4; half extents per prefab for the footprint and overlap box.
3. Tests first (fail against the hand-written table): base within 0.1 of the surface below; no overlap with collider triangles other than the support plane; each item within a stated x/z distance of its source node; COLLECTIBLES derived from warehouse_nodes.json (box piles -> chests, letters -> shrines by letter, tape and the three 100 nodes 15/30/31 -> chestFree; the 100/200/500 cluster nodes 148-150 stay unplaced, as before). Tests skip when .tools/ is absent.
4. Generator: COLLECTIBLES becomes a function derived from the nodes; each item drops to the surface under its node, nudged horizontally only as far as needed for a supported, non-overlapping footprint (node 43 sits on a platform edge at x=140 with no floor beyond); pitch 270 composed with the surface tilt.
5. Rebuild levels/thps.mblevel.json, relaunch, close-up screenshots of all 14 (tape chest from below), teleport onto each surface and compare the settled height with the prediction.
6. Deviations from the source nodes (y drop to the surface, any x/z nudges) listed in docs/thps-warehouse-layout.md for approval; replace the old collectible table there.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Design decisions approved by Lance: items slide in x/z up to 10.5 units to the nearest supported, clear spot on a surface no steeper than 45 degrees; T stands on the half pipe floor below its node as the task states.

Verification in game (levels/thps.mblevel.json, pack 2.0.19): placed mesh bounds sit on the predicted surface within 0.05; player teleported over each base settles at the predicted height (R1 +0.04; the two 100 chests on the 34 degree ramp rest about 0.1 above the model at the ramp foot after the player slides). Close-ups in .tools/evidence/021_10_item_*.png, tape chest underside in 021_10_item_Tape_below.png.

Harness note: with editor mode on, the camera tool has no effect on the screenshot; turn the editor off first. relaunch leaves spawns on, and a level-up dialog freezes the run, so send spawns off straight after.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Collectibles are now derived from the extracted warehouse_nodes.json. scripts/warehouse_surface.py reads warehouse.obj as the pack importer does and provides the downward ray, a triangle-vs-oriented-box overlap test and the surface-tilt rotation. build_thps_level.py replaces the hand-written COLLECTIBLES table with collectibles(): box piles to chests, letters to shrines, tape and nodes 15/30/31 to free chests, each dropped onto the surface below its node with the measured pivot-to-base offset, tilted to the surface normal, and slid at most 10.5 units (surface at most 45 degrees) when the node sits on an edge or over a quarter pipe. Tests cover base-on-surface within 0.1, no overlap with other collider triangles, the shift cap, the mapping and the generated edits (they skip when .tools/thps1/warehouse is absent). In game, all 14 bases match the predicted heights and close-ups show none floating or clipping. docs/thps-warehouse-layout.md lists the deviations from the source nodes."
<!-- SECTION:FINAL_SUMMARY:END -->
