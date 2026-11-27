---
id: TASK-086.04
title: Build the kf1 asset pack and wire the task chain and docs
status: To Do
assignee: []
created_date: '2026-11-27 08:20'
updated_date: '2026-11-27 23:42'
labels:
  - level
  - kf1
dependencies:
  - TASK-086.02
  - TASK-086.03.01
documentation:
  - docs/kf1-mountain-pass.md
  - taskfiles/conker.yml
  - taskfiles/pack.yml
parent_task_id: TASK-086
priority: medium
ordinal: 303000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add `unity/pack-authoring/Assets/Editor/Kf1MountainPassPack.cs` (reusing `PackBuilder.cs`), `unity/pack-authoring/packs/kf1/manifest.json` (id `kf1`, asset `MountainPass`), and `taskfiles/kf1.yml` with verify, export, convert, pack and install, included from `Taskfile.yml` beside the Conker and THPS includes. The export stage reproduces the UCC and umodel steps recorded in docs/kf1-mountain-pass.md from a Killing Floor 1 install. Keep docs/kf1-mountain-pass.md current and add it to the wiki allowlist only if it should be public. Then verify in the running game: relaunch with the new level, enter editor mode, and screenshot the spawn, shop spots, map edges and a drop past the edge so walls and the kill floor are exercised. Confirm the log has no `pack 'kf1' is not installed` line.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `task kf1` runs verify, export, convert, pack and install end to end
- [ ] #2 The level loads in game with no pack-missing placeholder
- [ ] #3 Screenshots show the player, shrines, chests and boss spawner on the ground
- [ ] #4 A drop past the map edge is stopped by walls or the kill floor
- [ ] #5 docs/kf1-mountain-pass.md documents the full chain
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
From TASK-086.02: the stock Forest backdrop (a 960 by 960 Mesh at the origin, Water planes at y=-129 and y=6) appears in the KF1 level exactly as in the Warehouse, so the map shows a patch of land and sea until the terrain exists. Whether to hide or cover it is deferred until the map is filled out.

From TASK-086.02: the runtime raised killFloorY from -200 to -72, and 0.1% of the terrain (min -137) is below that; set KILL_FLOOR_Y to -72 or shift the world up when the terrain is built. The level JSON has no packs entry or bundle placement yet; mesh.json materials hold only a name and base color.

Shipped as built: the pack id is `kf1` with asset `MountainPass`, matching the description. It shipped first as `kf1preview`, the name carried over from the throwaway script that made the first bundle, and was renamed before publication because the id is baked into saved levels: the `packs` map keys on it and each placement payload carries `bundle:kf1/MountainPass`, so a level saved under the old id logs `pack 'kf1preview' is not installed` and renders a placeholder cube. The rename covered the builder constant, manifest and its directory, `taskfiles/kf1.yml`, the converter's pack constants, both kf1 test files, the generated preview level and the docs; the hand-built original at `.tools/kf1/kf1preview` keeps the old name because it predates the change.

`taskfiles/kf1.yml` carries `pack` and `install` only: verify is the `verify-pack` verb of scripts/kf1_mountain_pass.py, convert is `prepare`, and export stays the umodel steps in the doc, which run on the box that holds the KF1 install. The pack builds on the box that has Unity 2023.2.22f1 and reads its `.tools/kf1` inputs off disk, so there is no remote build leg and no KF1_UNITY_HOST; criteria #1 cannot pass end to end on a build box, which has neither the KF1 install nor umodel.

One build run produces both `windows` and `linux` bundles, so the editor needs the windows-mono, linux-mono and linux-il2cpp modules. The `windows` bundle is the deliverable and the one verified in game; `linux` is a byproduct and its native-build trial is only worth doing if that target matters. Both Macs now have 2023.2.22f1 and each builds from its own `.tools/kf1`.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
