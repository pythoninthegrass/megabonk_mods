---
id: TASK-021.14
title: 'Make the mesh rail near (75, 3, 28) grindable with posts'
status: In Progress
assignee: []
created_date: '2026-10-28 04:12'
updated_date: '2026-10-28 06:24'
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
- [ ] #2 The player can slide on the pillars the same way as on the existing rails
- [ ] #3 The pillars do not block the player or enemies elsewhere
- [x] #4 The level generator places them and tests in tests/test_build_thps_level.py cover the placement
- [ ] #5 A screenshot and a short note on how the slide was checked are saved with the task
- [x] #6 docs/thps-warehouse-layout.md is updated
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Findings (2026-10-28):
- The rail is part of the extracted Warehouse mesh, not a game object: a thin flat bar at world x=75, height 3.17 to 3.44, running z 3.13 to 53.13, then a diagonal bend to about (81.5, 60.6). It floated, with no posts and no Rail component, so nothing held it up and it could not be ground.
- Kept the original bar (size and look as extracted). Replacing it with a visible game rail was tried and rejected: a visible rail/0 stacked over the bar, and rail/1 is a sloped rail, not a flat one.
- Pillars: seven dark box posts added under the bar in ThpsPack.cs (AddRailPosts; RailPosts lists five on the straight run and two on the bend). Pack version 2.0.6.
- Slideable: two hidden game rails of rail/0 laid along the bar (MESH_RAILS in scripts/build_thps_level.py), one over the straight run (yaw 90, scale 1.786, centre z 28.13) and one over the bend (yaw 310.5, scale 0.352). Height is -1.25 so the game rail's bar sits at the mesh bar's height. They are hidden through the new optional hidden flag on object.place (documented in docs/level-format.md), which makes the mod disable the object's renderers and keep its colliders and components.
- Alignment was measured from top-down and side screenshots under .tools/evidence/ (rail_align_top2.png, rail0_top.png, rail0_side.png, rail_hidden_top.png).
- Slide check: dropping the player onto the bar from above (teleport to (75, 9, 30)) gave samples at x=75.006 / 74.994 with z 47.8 then 57.9, so the player travelled along the bar. The bend piece was not confirmed to carry the player round the bend: the sample after the straight run was still at x=75.
- Lance's hands-on check: the rail does not activate on its own; it behaves like any other grind surface that is hard to time. Whether the rail needs a different approach angle, speed or jump timing to catch is not investigated.

Open:
- Confirm the grind and the bend by hand, and decide whether the activation timing needs any change (the game's Rail uses a SplineContainer and a renderCollider; bodies are native).
- Check that the posts and hidden rails do not block the player or enemies elsewhere.
- Update docs/thps-warehouse-layout.md for the kept bar, posts and hidden rails.
- The task title and description still say the rail is near (76, 2, 21) and has no pillars.

Branch feat/task-021.14-rail-pillars (commit 2de2217): docs/thps-warehouse-layout.md now documents the kept bar, posts and hidden rails (AC 6). Code was already on main. Still open and needs hands-on play: grind check and the bend (AC 2), posts and hidden rails not blocking the player or enemies elsewhere (AC 3), and the screenshot and slide note for AC 5.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
