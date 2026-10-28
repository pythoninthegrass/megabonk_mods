---
id: TASK-021.14
title: 'Make the mesh rail near (75, 3, 28) grindable with posts'
status: Done
assignee: []
created_date: '2026-10-28 04:12'
updated_date: '2026-10-28T18:29:00Z'
labels:
  - thps
  - level-editor
dependencies: []
documentation:
  - docs/thps-warehouse-layout.md
  - scripts/build_thps_level.py
parent_task_id: TASK-021
priority: medium
ordinal: 102000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Warehouse mesh's rail at world x 75 (z 3 to 53, then a bend to about (81.5, 60.6)) floated with no posts and no Rail component, so the player could not grind it. The bar is kept as extracted, seven posts stand under it (ThpsPack.cs, RailPosts) and two hidden game rails lie along it (MESH_RAILS in scripts/build_thps_level.py). The original title and description said the rail was near (76, 2, 21) and had no pillars; the findings are in the implementation notes and docs/thps-warehouse-layout.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Pillars stand on the floor along the rail at about (76, 2, 21), matching the original Warehouse rail
- [x] #2 The player can slide on the pillars the same way as on the existing rails
- [x] #3 The pillars do not block the player or enemies elsewhere
- [x] #4 The level generator places them and tests in tests/test_build_thps_level.py cover the placement
- [x] #5 A screenshot and a short note on how the slide was checked are saved with the task
- [x] #6 docs/thps-warehouse-layout.md is updated
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Findings (2026-10-28):
- The rail is part of the extracted Warehouse mesh, not a game object: a thin flat bar at world x=75, height 3.17 to 3.44, running z 3.13 to 53.13, then a diagonal bend to about (81.5, 60.6). It floated, with no posts and no Rail component, so nothing held it up and it could not be ground.
- Kept the original bar (size and look as extracted). Replacing it with a visible game rail was tried and rejected: a visible rail/0 stacked over the bar, and rail/1 is a sloped rail, not a flat one.
- Pillars: seven dark box posts added under the bar in ThpsPack.cs (AddRailPosts; RailPosts lists five on the straight run and two on the bend). Pack version 2.0.6.
- Slideable: two hidden game rails of rail/0 laid along the bar (MESH_RAILS in scripts/build_thps_level.py), one over the straight run (yaw 90, scale 1.786, centre z 28.13) and one over the bend (yaw 310.5, scale 0.352). Height is -1.25 on the run and 2.407 on the bend (bar centre 3.3 minus 2.55 times the scale; the bend first used -1.25 and sat about 2 units under its bar) so the game rail's bar sits at the mesh bar's height. They are hidden through the new optional hidden flag on object.place (documented in docs/level-format.md), which makes the mod disable the object's renderers and keep its colliders and components.
- Alignment was measured from top-down and side screenshots under .tools/evidence/ (rail_align_top2.png, rail0_top.png, rail0_side.png, rail_hidden_top.png).
- Slide check: dropping the player onto the bar from above (teleport to (75, 9, 30)) gave samples at x=75.006 / 74.994 with z 47.8 then 57.9, so the player travelled along the bar. The bend piece was not confirmed to carry the player round the bend: the sample after the straight run was still at x=75.
- Lance's hands-on check: the rail does not activate on its own; it behaves like any other grind surface that is hard to time. Whether the rail needs a different approach angle, speed or jump timing to catch is not investigated.

Branch feat/task-021.14-rail-pillars: docs/thps-warehouse-layout.md documents the kept bar, posts and hidden rails (AC 6). The earlier PR (#4) merged into fix/task-021.16-start-windows, so the code did not reach main; PR #8 (this branch into main) carries it, together with the 021.19 PR (#5) merged into this branch. The bend height was fixed in commit 5c89bf4; after it Lance grind-tested the run and the bend by hand and reported them working.

Handoff (2026-10-28): a grind ran off the bend onto the run, or the run onto the bend, only in one direction at a time, whichever gap was left between the hidden rails. Cause: a game rail's collider stops about 3.5% of its length short of its spline at each end (the run's collider spans z 4.90 to 51.37 against a spline from 3.13 to 53.13), so a player leaving one rail at the joint was outside the other rail's catch. RailHandoffPatch (src/MegabonkLevels.Mod/rail_handoff_patch.cs) postfixes PlayerMovement.StopRail on custom levels and starts the nearest other rail within 3.5 units when a grind runs off an end. The bend's hidden rail is back at its full length.

Lance walked around the posts and rails with spawns on (AC 3) and grind-tested all three mesh rails from both sides (AC 2). AC 5 is checked without a new screenshot; the slide checks are the teleport samples above and the hand tests.
<!-- SECTION:NOTES:END -->
