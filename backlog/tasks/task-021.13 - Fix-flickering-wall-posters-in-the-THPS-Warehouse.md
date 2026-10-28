---
id: TASK-021.13
title: Fix flickering wall posters in the THPS Warehouse
status: To Do
assignee: []
created_date: '2026-10-28 04:12'
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
- [ ] #1 The cause of the flicker is identified and written in the task notes
- [ ] #2 No poster or graffiti flickers when the camera moves along the walls, at close and far range, in the game on this Mac
- [ ] #3 The posters keep the same position, size and texture as before
- [ ] #4 Textures stay point-filtered with no mipmaps
- [ ] #5 Before and after screenshots are saved under .tools/evidence/
- [ ] #6 The pack version is bumped, and docs/asset-bundles.md or docs/thps-warehouse-layout.md records the fix if it changes how the mesh is imported
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
