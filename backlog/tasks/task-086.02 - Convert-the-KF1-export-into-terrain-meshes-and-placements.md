---
id: TASK-086.02
title: 'Convert the KF1 export into terrain, meshes and placements'
status: In Progress
assignee: []
created_date: '2026-11-27 08:20'
updated_date: '2026-11-27 19:33'
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
- [ ] #3 Running the script writes mesh.json and a level JSON that validates against docs/level-format.md
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
Shared module is scripts/level_geometry.py (outline, perimeter walls, floor_height, accessor reader, object_edit); conker_colors keeps wrappers binding its kill floor, pit floor and anchors. Conker tests: 6 pass, 6 skip before and after; the skips need the local ROM fixture, which is not on this box, so the pit-floor and kill-floor wall tests did not run against the refactor.

AC 3 left open: prepare writes mesh.json (40 MB) and the level JSON from the real export in about 5 s, uses only fields the Conker level already writes, and has the from-scratch required fields, but nothing here can run the C# loader, so it is unconfirmed until the level loads in game.

Anchors on BSP floors have no terrain floor and are skipped and listed: 17/157 ZombieVolume, 3/4 ShopVolume, 4/14 KFAmmoPickup, 6/14 KFRandomItemSpawn. The level therefore has one shrine spot, and the runtime needs more spots than shrines; this needs the BSP task or extra spots. Boss spawner is the farthest grounded ZombieVolume, a stand-in. SCALE 0.028 and the rotator roll sign are untuned.

No packs entry or bundle placement: those wait for the pack task. glTF materials are name and base color only.

Correction: with the Conker ROM and extractor available, all 12 Conker tests pass (the 6 that skipped earlier now run), and the Conker mesh.json and level JSON built by the pre-refactor script are byte-identical to the current output.

Smoke test (relaunch into .tools/kf1/kf1-mountain-pass.mblevel.json, editor mode, CrossOver build): the level loads, FromScratch builds the placeholder tile, the spawn and boss spawner place, all 8 chests spawn, the kill floor arms. ExtraShrines spawns 0 of 6 planned: the one authored spot finds no floor because there is no terrain collision without the pack, and only 1 spot exists. The runtime raised killFloorY from -200 to -72 (catch floor -80 plus clearance); 0.1% of terrain samples (min -137) lie below that, so KILL_FLOOR_Y should become -72 or the world should be shifted up. The screenshot tool returned an unreadable image, so nothing was inspected visually. The level shows no terrain or props until the pack task builds the bundle.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
