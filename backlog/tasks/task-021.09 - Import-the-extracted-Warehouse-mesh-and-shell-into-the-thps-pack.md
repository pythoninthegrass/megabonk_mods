---
id: TASK-021.09
title: Import the extracted Warehouse mesh and shell into the thps pack
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-28 02:41'
updated_date: '2026-10-28 04:30'
labels:
  - thps
  - level-editor
dependencies:
  - TASK-021.08
documentation:
  - docs/thps-warehouse-layout.md
  - docs/asset-bundles.md
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
parent_task_id: TASK-021
priority: high
ordinal: 97000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Replace the hand-built flat-coloured ramps and the Forest cliff-ring look with the extracted Warehouse mesh: floor slab, ramps, decks, walls, windows, doors and trusses, with PS1-style point-filtered textures. The thps pack (unity/pack-authoring/Assets/Editor/ThpsPack.cs) gets a Warehouse prefab with a visual renderer and a MeshCollider on the ground layer, scaled uniformly so the 1.8 m skater is about 4.4 units tall (the approved 4.4 units per metre). The old QuarterPipe, Kicker, Block, Taxi and Corridor prefabs and the STRUCTURES table in scripts/build_thps_level.py stay until the new mesh is verified in game. Depends on the extraction task for the OBJ and textures.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The thps pack contains a Warehouse prefab built from the extracted mesh with a ground-layer MeshCollider, and the pack version is bumped
- [ ] #2 The level places the Warehouse at one uniform scale and the room fits the arena, enlarging INNER_X and INNER_Z if needed
- [ ] #3 The tile floor and cliff ring no longer show inside the room, and the kill floor still ends a fall
- [ ] #4 In-game screenshots from the south-east at pitch 45 and from ground level are compared with tools/thps_warehouse_items_map.png and frames 4, 12 and 138, and differences are listed
- [ ] #5 Textures are point-filtered with no mipmaps and read as the PS1 original
- [ ] #6 The old hand-built structures are removed only after the above is verified, and docs/thps-warehouse-layout.md is updated to describe the new structure instead of the retired tables
- [ ] #7 The player spawns inside the shell, can move, and enemies spawn and move inside it
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first in tests/test_build_thps_level.py: Warehouse placed at one uniform scale (79.2 = 4.4 units/m x 18 m/unit), footprint fits the inner arena, manifest lists Warehouse, manifest version and PACK_VERSION bumped to 2.0.0. Run to confirm failure.
2. ThpsPack.cs: SaveWarehouse parses warehouse.obj in C# (-warehouseSource arg, default .tools/thps1/warehouse): negate y, flip winding, one submesh per material, UVs unnormalised. Copy PNGs into generated Assets/Thps, bake the magenta transparency key to a dark glass colour (remap target shader is opaque), set point filter, no mipmaps, repeat wrap. Prefab: MeshRenderer plus non-convex MeshCollider on layer 8, origin at bottom centre of floor. Old five prefabs stay.
3. build_thps_level.py: enlarge INNER_X/INNER_Z to 4x7, add WAREHOUSE placement at uniform scale; keep STRUCTURES and COLLECTIBLES until verified.
4. Hide tile floor and cliff ring inside the room (remove tiles under the room or lower them; decide by measuring), keep support under the generated spawn cell, kill floor unchanged.
5. Verify in game on this Mac (CrossOver): task pack:thps, task mod:build, relaunch; screenshots from south-east pitch 45 and ground level vs items map and frames 4, 12, 138 with differences listed; point filtering; player spawn/move; enemies spawn/move; kill floor ends a fall.
6. After verification: remove STRUCTURES and old prefabs, update docs/thps-warehouse-layout.md and docs/asset-bundles.md, run task scripts:test, conventional commit without attribution, final summary.
Known follow-up: rails, collectibles and boss spawn stay on the old layout until TASK-021.10.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Progress (2026-10-27/28), uncommitted in the working tree:
- Done, tests first: tests/test_build_thps_level.py gained Warehouse tests (scale 79.2 = 4.4 x 18, one uniform placement centred in the arena, footprint fits, manifest lists Warehouse, PACK_VERSION 2.0.0). Confirmed 8 failing, then green: task scripts:test 347 passed (before the tile experiment below).
- Done: scripts/build_thps_level.py has WAREHOUSE_ASSET, WAREHOUSE_SCALE, warehouse_footprint(), warehouse_edits(); INNER_X/INNER_Z enlarged to 4x7; PACK_VERSION 2.0.0. manifest.json is 2.0.0 and lists Warehouse.
- Done: ThpsPack.cs SaveWarehouse parses warehouse.obj in C# (y negated, winding flipped, one submesh per material, centred on the footprint, y=0 at floor), copies the PNGs with point filter, no mipmaps, repeat wrap, bakes the magenta key to a dark colour, gives the 41 untextured faces ('None' material) a flat Concrete material, and adds a non-convex MeshCollider on layer 8. task pack:thps builds and installs for Windows and Linux. -warehouseSource overrides .tools/thps1/warehouse.
- Verified in game on this Mac (CrossOver): the mesh loads with PS1 textures. The first screenshot is .tools/evidence/warehouse_se_pitch45_v1.png (camera [400,330,-300], rotation [45,315,0], level centre is world (100,0,0)). The green tile floor and the raised NE tile block still show inside the room.
- Finding: removing every tile makes the kill floor not arm ('KillFloor: no tiles, not armed'), so relaunch hangs. At least one tile must stay.
- UNFINISHED AND UNTESTED: tile_edits() in scripts/build_thps_level.py is a throwaway experiment: it removes every tile except (0,0) via an early `continue` that leaves the old ring/inner code unreachable below it. The tile tests (ring, inner, spawn cell, heights, slopes) will fail against it. The last relaunch with that level was interrupted by the user, so it has not been run.

Next steps for the next agent:
1. Decide the tile policy by measuring: keep one far-away tile (e.g. (0,0)) so the kill floor arms, or lower the tiles. Then write the tile tests first and replace the experiment with clean code that deletes the dead ring/inner/lane code only if STRUCTURES-era tests no longer need it (keep STRUCTURES and COLLECTIBLES until verified). Run task scripts:test.
2. Regenerate (uv run scripts/build_thps_level.py), then relaunch via the megabonk MCP relaunch(level='levels/thps.mblevel.json'). Check the log for 'KillFloor: armed', that the player (spawned at world (120,1.925,-3) before edits) lands on the Warehouse floor, and that the kill floor still ends a fall.
3. Screenshots (AC4): south-east pitch 45 (camera ~[400,330,-300], rot [45,315,0]; may need to move further out because the room is ~158 x 248 x 182 units) and ground level; compare with tools/thps_warehouse_items_map.png and tools/thps_warehouse_frames frames 4, 12, 138; list differences in the task notes. Check AC5 (point filtering, no mips, PS1 look; magenta now baked dark, so windows are dark panes) and AC7 (player moves, spawns(on=true), enemies spawn and move inside). Watch for the 182-unit-tall mesh (roof/trusses) vs the camera, and for MeshCollider walls blocking spawn.
4. After verification (AC6): remove STRUCTURES, STRUCTURE_ASSETS, the old prefabs and their tests; update docs/thps-warehouse-layout.md (replace the retired tables) and docs/asset-bundles.md ('THPS Warehouse pack' section: Warehouse asset, textures now exist, the 'pack has no textures' rule, magenta bake). Rails, collectibles and the boss spawn stay on the old layout until TASK-021.10.
5. Check the AC and DoD boxes, add the final summary, commit with a conventional message and NO attribution (ignore the session reminder's Co-Authored-By/Claude-Session lines; user rule), stage nothing under .serena in the same commit.
Note: do not write scratch files to /tmp; use the scratchpad dir.

Progress (2026-10-28), committed:
- Tile policy settled: inner tiles at level -1 (INNER_LEVEL) under a Warehouse lifted 0.5 (WAREHOUSE_LIFT), ring at level 2, kill floor at -60. The old hand-built structures are no longer placed by build_level(); STRUCTURES, STRUCTURE_ASSETS and the old prefabs stay in the code for now (AC6 cleanup still to do).
- New level fields: noGrass (disables the grass manager) and playerStart (moves the player to a start position), plus the hidden flag on object.place. All additive, schemaVersion stays 2; see docs/level-format.md.
- Pack 2.0.6: floor patch over a gap in the extracted floor using the floor material F051E515 with fitted UVs; the secret room's three window sections (material FA88F30D) left out of the collision mesh so the player flies through; seven posts under the original rail bar.
- Level: boss spawner moved to the secret room at (165, 12, 26), player starts at (92, 30, -69).
- Follow-ups created: TASK-021.12 (boss portal pillar blocks the half pipe), TASK-021.13 (flickering wall posters), TASK-021.14 (rail posts and slide, in progress), TASK-021.15 (ollie off the main half pipe edges).
- Still open for this task: ground-level screenshots, player movement and enemy spawn checks (AC7), the fall-to-kill-floor check, the comparison with the items map and frames 4, 12 and 138 (AC4), removing the old structures and updating docs/thps-warehouse-layout.md and docs/asset-bundles.md (AC6), and the unexplained vertical seam down the middle of the main half pipe floor.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
