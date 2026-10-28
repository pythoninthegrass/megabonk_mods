---
id: TASK-021.05
title: Create new assets for THPS Warehouse features with no Megabonk equivalent
status: Done
assignee:
  - '@Claude'
created_date: '2026-10-27T22:08:00Z'
updated_date: '2026-10-28 00:36'
labels:
  - level-editor
  - thps
  - assets
dependencies:
  - TASK-021.03
  - TASK-021.04
documentation:
  - docs/asset-bundles.md
parent_task_id: TASK-021
priority: low
ordinal: 91000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Some warehouse features, such as quarter pipes, the half pipe or the taxi funbox, may have no close Megabonk prop. The layout spec from TASK-021.03 lists which ones. This task builds those as custom assets through the asset pack pipeline from TASK-007 (see `docs/asset-bundles.md`) and places them in the level from TASK-021.04, replacing any placeholders.

If the spec finds that existing assets cover everything acceptably, close this task with a note saying so rather than inventing work.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each feature the spec marks as needing a new asset exists as an asset in a pack that the mod loads
- [x] #2 Each new asset renders correctly in game, checked with a screenshot
- [x] #3 The assets are placed in the level at the specified positions and replace any placeholders
- [x] #4 The player can ride or walk on the new assets without clipping or falling through
- [x] #5 The authoring steps for the new assets are documented
- [ ] #6 If no new assets were needed, the task is closed with a note giving the reason
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
0. Spike: relaunch on levels/thps.mblevel.json; read PlayerMovement whatIsGround, whatIsGroundOnly, maxSlopeAngle and the tile collider layer with query_objects; measure jump height; build and place one QuarterPipe with a MeshCollider and confirm the player can stand on and climb it. Fix the layer in PackBuilder if grounding fails.
1. Tests first in tests/test_build_thps_level.py: map_px_to_local affine fit from the known collectible pixel/local pairs; structure_edits places every spec structure as bundle:thps/<Asset> inside the arena at the expected height; packs map is {thps: version}; structure placements come after clutter removals; high rail sits at the M1 bank lip height.
2. Assets in unity/pack-authoring: shared helpers split out of PackBuilder.cs, new Assets/Editor/ThpsPack.cs with QuarterPipe, Kicker, Block, Taxi and Corridor prefabs (procedural meshes, MeshColliders, flat colors, unit size with bottom-centre origin), bundle thps, manifest.json id thps version 1.0.0. Decorative items skipped.
3. taskfiles/pack.yml: METHOD var on pack:build, pack:thps, pack:install copying the platform bundle and manifest into UserData/LevelPacks/thps.
4. scripts/build_thps_level.py structure_edits() from a table of asset, map pixel box, height, yaw and scale; regenerate levels/thps.mblevel.json.
5. Docs: THPS pack section in docs/asset-bundles.md; update docs/thps-warehouse-layout.md with assets per structure, measured values and deviations.
Verify: task scripts:test red then green, task check, task pack:thps, relaunch with the level, screenshot each structure, teleport onto each deck/kicker/taxi/corridor and confirm y stays stable, climb one pipe and one kicker, ThpsLevelTests still passes. Conventional commits with no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Spike (step 0), 2026-10-27: layers read with query_objects on GameObject.layer. Tile ground (TileGround/TileSlope/TileWall, CombinedCollisionMesh) is layer 8, Player is layer 7, placed Rail prefabs are layer 0. LayerMask fields stringify to the type name in query_objects, so the mask bits themselves are not readable; PlayerMovement.maxSlopeAngle = 45. The running MCP server has no query_objects tool (the file has it), so I called run.request_result with build_query_objects_command directly.

Spike: ThpsPack.cs builds one QuarterPipe (profile y=z^2 in unit space, closed solid, non-convex MeshCollider, layer 8) into a bundle `thps`; installed by hand into UserData/LevelPacks/thps with manifest.json. Log: `Packs: loaded pack 'thps' with 1 prefab(s)`, no Missing warnings; palette 77 -> 78; the spawn log line shows the placement. Screenshot shows a plywood-coloured concave ramp. Collision works: a player teleported onto the steep top (about 56 deg) slid 17 units south to the floor; one teleported mid-ramp came to rest at about 15 deg slope. Still open: whether a running player can climb a 56 deg end, and jump height. The harness key tool is editor-only, so both need a manual run by Lance.

Built and committed (00ed84e, 50620e0): ThpsPack.cs generates QuarterPipe, Kicker, Block, Taxi and Corridor; task pack:thps builds and installs; the generator places 16 structures. Log shows `Packs: loaded pack 'thps' with 5 prefab(s)` and 16 `spawned 'bundle:thps/...'` lines with no Missing warnings. Screenshots of every asset: thps-structures-south.png, thps-west-side.png, thps-east-side-2.png (scratchpad). No placeholders existed in the level from TASK-021.04, so nothing was replaced.

Measured: jump apex about 7.8 units above the floor; ramps capped near 40 deg because a 56 deg test pipe could not be climbed past a body height of 8 to 10 (maxSlopeAngle 45). Teleport 4 units above each flat top settles at top + 1.925 for M2 (7.42), M3 taxi (6.92), M5 corridor (15.96), M9 (7.92), M10b (5.92) and M11 (5.92). Ramps: the player lands and slides on the steep ones and rests on the shallow ones; none fell through. A teleport 1 unit above a surface hovers with no gravity, so drop from several units.

Still open for AC #4: a run up each new pipe and kicker at speed by hand. Enemies, level-up and chest popups interfered with the automated checks; follow-up TASK-022 adds a harness command to turn enemy spawns off.

AC #4: Lance ran up the M1 west bank, the M6 channel pipe, a kicker and the half pipe into the corridor by hand, 2026-10-28, with no clipping or falling through.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added the `thps` asset pack and placed it in levels/thps.mblevel.json. ThpsPack.cs (Unity 2023.2.22f1) generates QuarterPipe, Kicker, Block, Taxi and Corridor in code on layer 8, the tile-ground layer, and `task pack:thps` builds the bundle and installs it with its manifest through the new `pack:install`. scripts/build_thps_level.py gained a STRUCTURES table that places 16 structures (west bank, platform, taxi, half pipe, hanging corridor, channel pipes, east deck with back pipe, south notch pipe and ledges, kicker pair) scaled per placement, and seats the ledge and high rails on the structures they belong to. Ramps are capped near 40 degrees because a test pipe whose face reached 56 degrees could not be climbed past a body height of 8 to 10 against PlayerMovement.maxSlopeAngle 45; the jump apex measured about 7.8 units, so decks and ledges are 6 or lower. Verified in game: the pack loads with 5 prefabs and 16 placements with no Missing warnings, every asset renders (screenshots), the player settles on every flat top at the surface plus 1.925, and Lance ran up the west bank, a channel pipe, a kicker and the half pipe into the corridor with no clipping or falling through. Documented the authoring steps and measurements in docs/asset-bundles.md and docs/thps-warehouse-layout.md. task check passes. Deviations: pipes stop at 40 degrees instead of going vertical, the half pipe is lower and shorter than the video, the channel pipes stand on the flat strip south of the lanes, and doors, windows, trusses, graffiti, cones, barricades and the corridor glass are not built. Follow-up TASK-022 covers a harness command to turn enemy spawns off.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
