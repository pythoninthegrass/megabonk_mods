---
id: TASK-086.02
title: 'Convert the KF1 export into terrain, meshes and placements'
status: To Do
assignee: []
created_date: '2026-11-27 08:20'
updated_date: '2026-11-27 18:27'
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
- [ ] #1 Unit tests cover the T3D parser, the coordinate transform, the heightmap-to-mesh conversion and placement floor-dropping, and pass
- [ ] #2 Walkable-outline and wall code is shared with Conker, not duplicated, and the Conker tests still pass
- [ ] #3 Running the script writes mesh.json and a level JSON that validates against docs/level-format.md
- [ ] #4 No new level-JSON field is added without a matching runtime setting
<!-- AC:END -->



## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
