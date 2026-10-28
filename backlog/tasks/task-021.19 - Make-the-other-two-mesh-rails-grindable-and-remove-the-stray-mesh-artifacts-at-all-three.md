---
id: TASK-021.19
title: >-
  Make the other two mesh rails grindable and remove the stray mesh artifacts at
  all three
status: In Progress
assignee: []
created_date: '2026-10-28 06:08'
updated_date: '2026-10-28 06:24'
labels:
  - thps
  - level-editor
dependencies:
  - TASK-021.14
documentation:
  - docs/thps-warehouse-layout.md
  - scripts/build_thps_level.py
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - docs/level-format.md
parent_task_id: TASK-021
priority: medium
ordinal: 107000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Warehouse mesh has three rails. The first, near world (81, 3, 27), was made grindable in TASK-021.14 by laying hidden game rails along the mesh bar (MESH_RAILS in scripts/build_thps_level.py, placed with the hidden flag on object.place) and adding pillars in ThpsPack.cs (AddRailPosts). Apply the same treatment to the other two, near (127, 22, 123) and (178, 8, 62), so all three match: a hidden game rail aligned to each mesh bar, and pillars where the first rail has them. All three rails also have stray mesh artifacts floating near each pillar; find what they are (leftover geometry from the extracted Warehouse mesh, or from the pillars) and clean them up on all three rails.

Positions are approximate. Measure each bar from top-down and side screenshots as in TASK-021.14 (evidence under .tools/evidence/, for example rail_align_top2.png). Grind activation on the first rail is a separate open question in TASK-021.14 and is not part of this task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The rails near (127, 22, 123) and (178, 8, 62) each have a hidden game rail aligned to the mesh bar, set up the same way as the rail near (81, 3, 27)
- [x] #2 Pillars match the first rail's pillars on the other two rails
- [ ] #3 The stray floating mesh artifacts near the pillars are gone on all three rails, with before and after screenshots saved under .tools/evidence/ and noted in the task
- [x] #4 The player can grind each of the three rails (checked in game, noting how the grind was checked)
- [x] #5 Any new generator or pack behaviour is covered by tests in tests/test_build_thps_level.py, and docs/thps-warehouse-layout.md is updated
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Branch feat/task-021.19-mesh-rails (commit 54c71c3, height fix 5c89bf4), merged through PR #5 into feat/task-021.14-rail-pillars; PR #8 carries it to main. All three rails use material A53322CF. Rail 2 is the rod the SKATEBOARDING banner hangs from (x 116.3-143.0, z 120.8, height 27.3-27.55) with a wall bracket at each end: it gets a hidden game rail (MESH_RAILS[2]) and no posts, and the brackets are kept because they are real supports. Rail 3 is the deck rail (x 175.66, z 47.9-74.7, height 8.31-8.56): hidden game rail (MESH_RAILS[3]) and three posts. Pack 2.0.10.

Stray artifacts: small plates (about 0.46 x 0.25) on the rail material at each post position, well below the bar (height 1.5-1.8 on rail 1, 5.7-6.1 on rail 3). They are what the extraction left of the original posts. RailLeftoverBounds in ThpsPack.cs drops them; rail 2 has none. A thin diagonal line beside rail 1's middle post remains and is not on the rail material.

Evidence in .tools/evidence/: task-021.19-rail1-before.png, task-021.19-rail1-after.png, task-021.19-rail2-before.png, task-021.19-rail3-after.png. No before shot of rail 3 and no after shot of rail 2 yet, so AC 3 is left unchecked.

Height fix (5c89bf4): the hidden rails were first placed with the first rail's fixed 4.55 offset below the bar centre, which only fits its 1.786 scale. At scale about 0.95 the wall rod and deck rail ground about 2 units under their visible bars, and the bend (scale 0.352) had the same fault. The offset scales with the rail: pivot y = bar centre minus 2.55 times scale (RAIL0_BAR_HEIGHT in scripts/build_thps_level.py), giving 24.997 for the rod and 5.995 for the deck rail. Seen in the running game after the fix: the grind sparks and the player sit on the visible bar for the bend, the wall rod and the deck rail (.tools/evidence/deck_rail_after_fix.png, wall_rod_after_fix_2.png, bend_rail_after_fix.png). Lance then grind-tested all three by hand and reported them fixed (AC 4).

Still open: AC 3, the before and after screenshots of the stray plates on all three rails, and checking the rod's brackets are not the artifacts the description meant.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
