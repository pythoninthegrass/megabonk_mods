---
id: TASK-086.01
title: Export the Killing Floor 1 Mountain Pass data
status: Done
assignee: []
created_date: '2026-11-27 08:20'
updated_date: '2026-11-27 18:27'
labels:
  - level
  - kf1
dependencies: []
references:
  - 'https://store.steampowered.com/app/1250/Killing_Floor/'
documentation:
  - docs/kf1-mountain-pass.md
parent_task_id: TASK-086
priority: medium
ordinal: 300000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Get everything the converter needs out of the Killing Floor 1 install into gitignored `.tools/kf1/`: the level actors as T3D text and the terrain heightmap through the Killing Floor SDK's `UCC.exe` (Steam app 1260, installs into the game folder), and the placed static meshes and their textures through a source build of umodel. UCC splits its own path at spaces, so it must run from a path without spaces such as a junction. The KF2 workshop attempt that preceded this is recorded in docs/kf1-mountain-pass.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The level exports as T3D with every actor, brush polygon and property (1,810 static mesh actors, 12 player starts, 157 zombie volumes, 462 brushes)
- [x] #2 The terrain heightmap exports as a 16-bit image and its world scale is fitted against ground-resting actors
- [x] #3 Every static mesh the level places exports as glTF with its textures (157 of 157)
- [x] #4 docs/kf1-mountain-pass.md records the commands, the UCC path gotcha and the measurements
<!-- AC:END -->



## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Exported with UCC.exe batchexport (Level to t3d, Texture to bmp for Terrain_Main) from a junction path, and umodel (source build) for 14 stock mesh packages plus the map package: 573 MB of glTF and TGA. All 157 distinct placed meshes resolve. Heightmap scale fitted at 64 units per sample horizontally and (value - 32768) / 256 * 64 vertically (residual SD 4.7 units over 609 path nodes). Findings are in docs/kf1-mountain-pass.md.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
