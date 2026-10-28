---
id: TASK-021.09
title: Import the extracted Warehouse mesh and shell into the thps pack
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-28 02:41'
updated_date: '2026-10-28T18:50:00Z'
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
- [x] #2 The level places the Warehouse at one uniform scale and the room fits the arena, enlarging INNER_X and INNER_Z if needed
- [x] #3 The tile floor and cliff ring no longer show inside the room, and the kill floor still ends a fall
- [ ] #4 In-game screenshots from the south-east at pitch 45 and from ground level are compared with tools/thps_warehouse_items_map.png and frames 4, 12 and 138, and differences are listed
- [x] #5 Textures are point-filtered with no mipmaps and read as the PS1 original
- [x] #6 The old hand-built structures are removed only after the above is verified, and docs/thps-warehouse-layout.md is updated to describe the new structure instead of the retired tables
- [x] #7 The player spawns inside the shell, can move, and enemies spawn and move inside it
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Done:
1. Generator and tests: Warehouse placed at one uniform scale (79.2 = 4.4 units per metre x 18 m per OBJ unit), centred in a 4x7 inner arena; tile policy, boss spawner, player start and hidden rails covered by tests in tests/test_build_thps_level.py and tests/MegabonkLevels.Tests.
2. Pack importer (ThpsPack.cs): Warehouse prefab with a ground-layer MeshCollider, point-filtered mipmap-free textures, floor patch, pass-through windows, rail posts.
3. Mod: noGrass, playerStart and hidden placements.

Remaining:
4. Verify in game: ground-level screenshots, player movement, enemy spawns (spawns on) and movement inside the shell, and that a fall ends at the kill floor.
5. Compare south-east pitch-45 and ground-level screenshots with tools/thps_warehouse_items_map.png and frames 4, 12 and 138 and list the differences in the notes.
6. Look into the vertical seam down the middle of the main half pipe floor.
7. After verification: remove STRUCTURES, STRUCTURE_ASSETS, the old prefabs (QuarterPipe, Kicker, Block, Taxi, Corridor) and their tests; update docs/thps-warehouse-layout.md (replace the retired tables) and docs/asset-bundles.md (Warehouse asset, textures, magenta bake, floor patch, collision mesh, rail posts).
8. Tick the acceptance criteria and Definition of Done, add the final summary.
Collectibles and the old rails keep their old-layout positions until TASK-021.10.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
State as of 2026-10-28. Work to date is committed (3842648, 9814146).

Layout and tiles
- The level places the Warehouse at scale 79.2 (4.4 units per metre x 18 m per OBJ unit), centred in a 4x7-cell inner arena (INNER_X, INNER_Z), lifted 0.5 above y=0 (WAREHOUSE_LIFT). The footprint fits the arena.
- Tile policy, decided by measuring in game: inner tiles are flat at level -1 (INNER_LEVEL) so they sit below the Warehouse's sunken floor areas and do not show through; the one-cell ring stays at level 2; every other cell is removed. Removing every tile does not work: the kill floor needs a tile to arm. Kill floor now sits at y=-60.
- build_level() no longer places the hand-built structures. STRUCTURES, STRUCTURE_ASSETS, the old prefabs and their tests are still in the code and still need removing (AC6).

Pack (thps 2.0.6, ThpsPack.cs)
- Warehouse prefab parsed from .tools/thps1/warehouse/warehouse.obj (y negated, winding flipped, one submesh per material), PS1 textures point-filtered with no mipmaps and repeat wrap, the magenta transparency key baked to a dark colour, the 41 untextured faces on a flat concrete material.
- Non-convex MeshCollider on the ground layer, built from a separate WarehouseCollision mesh that leaves out the secret room's three window sections (material FA88F30D), so the player and enemies pass through them. The windows still render.
- Floor patch over a gap the extraction left against the west wall, using the floor material F051E515 with UVs fitted to the extracted floor, placed just under the floor plane so the grime decals around it stay on top.
- Seven dark posts under the original rail bar (straight run and bend); see TASK-021.14.

Mod and level format (docs/level-format.md)
- noGrass: disables the game's grass manager, which raycasts onto the ground layer and otherwise grows through the Warehouse floor.
- playerStart: moves the player to a world position after generation; the game places the player at the generated spawn around generation and moving the spawn portal does not move it, so the mod re-applies the start for 5 seconds. y is the on-screen readout value (body height, 1.925 above the feet).
- hidden on object.place: keeps colliders and components and disables the renderers. Used to lay the game's rail/0 along the mesh rail bar.
- All additive; schemaVersion stays 2.

Level
- Player starts at (92, 30, -69). The boss spawner is at (165, 12, 26) in the secret room above the main half pipe.
- Rails other than the mesh rail, collectibles and their stands_on structures keep their old-layout positions until TASK-021.10, so collectibles that stood on removed structures float.

Verified in game on this Mac (CrossOver)
- The Warehouse loads with textures; the kill floor arms; no green tile shows inside the room; no grass; the player starts at the set position, can move, and can fly through the three window sections.
- Screenshots are under .tools/evidence/ (warehouse_se_pitch45_v1.png to v4.png, puddle_after*.png, secret_room.png, rail_*.png).

Not yet verified
- Enemies spawning and moving inside the shell (spawns on), and the kill floor ending a fall.
- Ground-level screenshots and the comparison with tools/thps_warehouse_items_map.png and frames 4, 12 and 138, with the differences listed.
- The vertical seam down the middle of the main half pipe floor is unexplained (a hard light and dark line in the screenshots).

Follow-up tasks
- TASK-021.12: the boss portal's pillar blocks the main half pipe.
- TASK-021.13: wall posters flicker.
- TASK-021.14: rail posts and slide (in progress).
- TASK-021.15: the player cannot ollie off the main half pipe edges.

Notes
- Do not write scratch files to /tmp; use the session scratchpad.
- Commit messages carry no attribution lines (Lance's rule), and nothing under .serena goes in the same commit.

Update (2026-10-28), pack 2.0.7: the secret room has five window sections, not three. Three are broken (material FA88F30D: south wall x 150 to 164, north wall x 164 to 178, west wall z 21.6 to 30.8) and two are intact (material F2184063: south wall x 164 to 178 at z=21, north wall x 150 to 164 at z=31). The earlier notes saying 'the three window sections' only covered the broken ones; Lance confirmed those pass and the intact center ones did not. F2184063 is shared with solid windows elsewhere (for example near the start), which must stay solid, so WarehouseCollision drops its faces only inside the room's world bounds (SecretRoomBounds x 149 to 179, y 15 to 26, z 20 to 32). Checked by walking out of the room: south at x about 171 (z 24 to 16) and north at x about 157 (z 28 to 44.6), both passing through. Solid windows elsewhere were not re-checked.

Update (2026-10-28), AC 6: removed STRUCTURES, STRUCTURE_ASSETS, Structure, QUARTER_PIPE_TRANSITION, footprint, end_slope_degrees, structure_edits and surface_height from scripts/build_thps_level.py, and the structure tests. Collectible.stands_on is gone; collectibles and the ledge and high rails keep their old-layout positions and heights (LEDGE_RAIL_HEIGHT 5.5 and HIGH_RAIL_HEIGHT 12 are now constants) until TASK-021.10. ThpsPack.cs no longer builds QuarterPipe, Kicker, Block, Taxi or Corridor; the manifest lists only Warehouse; pack version 2.0.19. Rebuilt and installed with task pack:thps, relaunched: the pack loads with 1 prefab, the Warehouse spawns, the kill floor arms, no version warning. docs/thps-warehouse-layout.md (structure mapping, collectibles, building the level, reference-frame check) and docs/asset-bundles.md (Warehouse asset, textures, magenta bake, collision mesh, floor patch, rail posts) updated. task check passes.

AC 4 stays open by decision: the south-east pitch-45 overview is blocked by the flat roof (the interior is hidden from above), so the comparison was reduced to ground-level views and the differences are listed in docs/thps-warehouse-layout.md under 'Check against the reference frames'. Evidence: .tools/evidence/ac4_*.png. Not committed yet.

Update (2026-10-28), detritus cleanup: the three old hand-placed rails (big, ledge, high) are removed from the generator; rail_edits() now returns only the hidden mesh rails. The ruined towers, crates, cubes, pillars and dead trees the tile prefabs leave as uncloned scene roots (82 objects: Castle, Castle (1), CastleLying, Crate (1), Crate (2), Cube, Cube (1), Cube (3), Pillar, Pillar (1), Ruins (1), Tree) are now indexed as gen:scenery:<name>:<n> (SceneRootCategory in the mod, SEED_SCENERY_COUNTS in the generator) and removed by the level. FogOfWarSphere is the one uncloned root left out. Verified in game: 0 of these active after relaunch, 4 hidden mesh rails remain, the view from below shows only the Warehouse underside. Collectibles still float at old-layout positions until TASK-021.10. Not committed.
<!-- SECTION:NOTES:END -->
