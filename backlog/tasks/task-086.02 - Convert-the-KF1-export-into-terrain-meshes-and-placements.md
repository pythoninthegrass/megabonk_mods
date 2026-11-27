---
id: TASK-086.02
title: 'Convert the KF1 export into terrain, meshes and placements'
status: Done
assignee: []
created_date: '2026-11-27 08:20'
updated_date: '2026-11-27 19:42'
labels:
  - level
  - kf1
dependencies:
  - TASK-086.01
documentation:
  - docs/kf1-mountain-pass.md
  - scripts/conker_colors.py
  - docs/level-format.md
parent_task_id: TASK-086
priority: medium
ordinal: 301000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add `scripts/kf1_mountain_pass.py` and `tests/test_kf1_mountain_pass.py`, mirroring `scripts/conker_colors.py`. Parse the exported T3D actors (`StaticMeshActor`, `PlayerStart`, `ZombieVolume`, `ShopVolume`, `KFRandomItemSpawn`, `KFAmmoPickup`, `BlockingVolume`), build the terrain mesh from the 16-bit heightmap (64 units per sample centered on the origin; height is (value - 32768) / 256 * 64), place the exported glTF static meshes by `Location`, `Rotation` and `DrawScale3D`, and transform Unreal Engine 2 coordinates (Z up, left-handed, rotation in 65536 units per turn) to Megabonk space using the shape of `world_point()`. Derive the walkable outline and perimeter walls by reusing Conker's functions (share them through a module rather than copying), and write `mesh.json` and the `.mblevel.json` under `.tools/kf1/`. `PlayerStart` becomes the spawn, shop volumes and item spawns anchor shrine, chest and power-up spots, and every placement is dropped on the floor with the floor-height helper. Check `level_settings.cs`, `powerup_placement.cs` and `extra_shrines.cs` before inventing level-JSON fields. Tests come first for each function. The BSP geometry is a separate task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Unit tests cover the T3D parser, the coordinate transform, the heightmap-to-mesh conversion and placement floor-dropping, and pass
- [x] #2 Walkable-outline and wall code is shared with Conker, not duplicated, and the Conker tests still pass
- [x] #3 Running the script writes mesh.json and a level JSON that validates against docs/level-format.md
- [x] #4 No new level-JSON field is added without a matching runtime setting
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Refactor: move the generic geometry from scripts/conker_colors.py into scripts/level_geometry.py (floor_height, walkable_cells, playable_cells, perimeter, _fence and helpers, reverse_winding, read_accessor). Level-specific values (kill floor, pit floor, anchors, wall drop) become parameters; conker_colors re-exports the names so tests/test_conker_colors.py passes unchanged. Run the Conker tests before and after.
2. Tests first in tests/test_kf1_mountain_pass.py: T3D parser, UE2 to Megabonk transform (Z up, left-handed, 65536 per turn), 16-bit BMP heightmap to mesh (64 units per sample, (v - 32768) / 256 * 64), placement floor-dropping. Confirm each fails before implementing.
3. scripts/kf1_mountain_pass.py with a prepare command: parse actors, build terrain, place glTF meshes, derive outline and walls through level_geometry, write .tools/kf1/mesh.json and the .mblevel.json. PlayerStart is the spawn; ShopVolume and KFRandomItemSpawn anchor shrine, chest and power-up spots; every placement is floor-dropped.
4. Check level_settings.cs, powerup_placement.cs and extra_shrines.cs before using any level-JSON field; add none without a runtime setting.
5. Update docs/kf1-mountain-pass.md (T3D file name is KF-MountainPass.t3d, replace the converter TODO), run task check, commit as a refactor commit then a feat commit with no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Shared module is scripts/level_geometry.py; conker_colors keeps wrappers binding its kill floor, pit floor and anchors. With the Conker ROM and extractor in place all 12 Conker tests pass, and the Conker mesh.json and level JSON built by the pre-refactor script are byte-identical to the current output.

AC 3: prepare writes mesh.json (40 MB) and the level JSON from the real export in about 5 s. It uses only fields the Conker level already writes and has the from-scratch required fields. The mod's loader accepted the level on every load with no validation errors; the editor's Validate button was not pressed.

Smoke test (relaunch into .tools/kf1/kf1-mountain-pass.mblevel.json, editor mode, CrossOver build): the level loads, the placeholder tile builds, the spawn and boss spawner place, all 8 chests spawn and the kill floor arms. The boss portal is regular size with only BottomPiece hidden (the Warehouse shrank its portal for the glass box and hides Collider). ExtraShrines spawns 0 of 6: one authored spot, and no terrain collision without the pack. The screenshot tool returned an unreadable image, so the portal was judged from the log and by eye in the user's own screenshot.

Anchors on BSP floors are skipped and listed: 17/157 ZombieVolume, 3/4 ShopVolume, 4/14 KFAmmoPickup, 6/14 KFRandomItemSpawn. Boss spawner is the farthest grounded ZombieVolume, a stand-in. SCALE 0.028 and the rotator roll sign are untuned. The runtime raised killFloorY from -200 to -72. The stock Forest backdrop (960 by 960 Mesh, Water planes) appears here exactly as in the Warehouse. Follow-ups are recorded in TASK-086.03 and TASK-086.04.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added scripts/level_geometry.py, shared by the Conker and KF1 converters (walkable outline, perimeter walls, floor lookup, glTF accessor reader, object.place edit builder, boss portal hidden parts), and scripts/kf1_mountain_pass.py with 27 tests written first. `prepare` reads the T3D actors, the 16-bit heightmap and the umodel glTF meshes and writes .tools/kf1/mesh.json and kf1-mountain-pass.mblevel.json in about five seconds, using only level fields the Conker level already writes. Conker is unchanged: all 12 of its tests pass and its output is byte-identical to the pre-refactor script. The level loads in game with the spawn, boss portal (regular size, BottomPiece hidden) and 8 chests placed. Known gaps that belong to later tasks: anchors on BSP floors are skipped (one shrine spot remains), the level shows no terrain or props until the pack exists, and SCALE, the rotator roll sign and KILL_FLOOR_Y are untuned.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
