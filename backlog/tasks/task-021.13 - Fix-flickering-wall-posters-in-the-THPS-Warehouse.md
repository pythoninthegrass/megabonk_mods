---
id: TASK-021.13
title: Fix flickering wall posters in the THPS Warehouse
status: Done
assignee: []
created_date: '2026-10-28 04:12'
updated_date: '2026-11-09 05:26'
labels:
  - thps
  - level-editor
dependencies: []
documentation:
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - docs/asset-bundles.md
parent_task_id: TASK-021
priority: medium
ordinal: 101000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Posters and graffiti on the Warehouse walls flicker in game. They are decal faces in the extracted mesh (unity/pack-authoring/Assets/Editor/ThpsPack.cs parses .tools/thps1/warehouse/warehouse.obj) that sit at or almost at the same depth as the wall behind them, which is the usual cause of z-fighting. Only the cause is a guess: confirm it in game first. The floor already uses the same idea in reverse, with a patch just under the floor plane so the grime decals stay on top. Find which faces flicker (screenshots from a few angles and distances), find the cause, and fix it in the pack importer without changing how the posters look.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The cause of the flicker is identified and written in the task notes
- [x] #2 No poster or graffiti flickers when the camera moves along the walls, at close and far range, in the game on this Mac
- [x] #3 The posters keep the same position, size and texture as before
- [x] #4 Textures stay point-filtered with no mipmaps
- [ ] #5 Before and after screenshots are saved under .tools/evidence/
- [x] #6 The pack version is bumped, and docs/asset-bundles.md or docs/thps-warehouse-layout.md records the fix if it changes how the mesh is imported
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add CoplanarLayering (unity/pack-authoring/Assets/Editor/CoplanarLayering.cs), a pure C# pass that lifts the on-top face of each coplanar, same-facing, overlapping face pair along its normal. Smaller area goes on top; equal area goes to the later OBJ face.
2. Write the xunit tests first (tests/MegabonkLevels.Tests/coplanar_layering_tests.cs), linking the source file into the test project.
3. Call the pass from ThpsPack.ParseWarehouseObj with the per-face corner lists, before the floor patches and origin shift.
4. Bump packs/thps/manifest.json version, rebuild and install the pack, verify in game, save before and after screenshots under .tools/evidence/.
5. Record the fix in docs/asset-bundles.md or docs/thps-warehouse-layout.md.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Cause (confirmed from warehouse.obj, not only the video): faces lie exactly in the same plane as another same-facing face, so depth ties. Posters: tris 248/249 (material 1EE84107, the twin Shorty's posters at world 178,10,115) coincide with wall tris 571/572 (1D972B2A) at x=178.9, plane gap 0.0000. Planks: the pile at world 89,2,26 is flat plank faces at y=0.674 from several materials (D783CF21 tris 1028/1029/1036/1037, 32BEE4A3 tri 2301, 2C383150 tris 2308/2309), all at gap 0.0000 and overlapping each other. The wood near the rail at 84,3,26 has no coplanar pairs within 6 units, so it is most likely the same plank pile. Video diff of consecutive full-rate frames showed the flicker as triangular patches on the planks only. Full-mesh scan for other pairs is still to do.

Fix: CoplanarLayering.Separate (Assets/Editor/CoplanarLayering.cs) lifts the on-top face of each coplanar, same-facing, overlapping pair along its normal by 0.0005 mesh units per level; the smaller face goes on top, the later OBJ face on ties. Called from ThpsPack.ParseWarehouseObj. On the real mesh it lifts 195 of 1345 faces, at most 3 levels. Pack version 2.0.8 in manifest.json, build_thps_level.py and levels/thps.mblevel.json. the maintainer flew the rebuilt pack in game and confirmed every poster and the plank piles no longer flicker. Docs: 'Warehouse mesh import' in docs/asset-bundles.md.

Evidence: before images from the recording (flicker diff map, crops, contact sheets) and one after screenshot are in .tools/evidence/task-021.13/. The after set is a single live view, not a matched pair at the flicker spots. Textures are untouched by the pass, so point filtering and no mipmaps are as before.

Closed by the maintainer with AC #5 only partly met: the before images and one live after view are saved, but there is no matched before/after pair at the flicker spots.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
