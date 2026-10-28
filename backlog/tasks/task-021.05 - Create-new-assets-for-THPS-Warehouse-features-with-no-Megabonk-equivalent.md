---
id: TASK-021.05
title: Create new assets for THPS Warehouse features with no Megabonk equivalent
status: In Progress
assignee:
  - '@Claude'
created_date: '2026-10-27T22:08:00Z'
updated_date: '2026-10-27 23:49'
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
- [ ] #1 Each feature the spec marks as needing a new asset exists as an asset in a pack that the mod loads
- [ ] #2 Each new asset renders correctly in game, checked with a screenshot
- [ ] #3 The assets are placed in the level at the specified positions and replace any placeholders
- [ ] #4 The player can ride or walk on the new assets without clipping or falling through
- [ ] #5 The authoring steps for the new assets are documented
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
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
