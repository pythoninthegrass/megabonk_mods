# THPS Warehouse layout spec

What the Megabonk editor can place, and how the THPS Warehouse (see [thps-warehouse.md](thps-warehouse.md)) maps onto it. The structure inventory and map coordinates come from that doc; the grid, scale and catalog facts come from [level-format.md](level-format.md), [runtime-map-structure.md](runtime-map-structure.md) and [asset-bundles.md](asset-bundles.md), plus values read from the running game (build 1.0.69, CrossOver) with `query_objects` and the editor palette.

## Base map and stage

Forest, stage 0, `ParamForest1`, debug seed `20261007` (the seed the repo's regression levels use, so generation is known to be reproducible).

- `EMapType.Tiles` maps are the only ones with a tile grid, so they are the only ones where terrain can be shaped with `SetTileHeight`, `SetTileSlope`, `AddTile` and `RemoveTile`. Forest and Graveyard are the Tiles maps.
- Desert and Hell are `ProceduralMesh`: one heightmap mesh, no `proceduralTiles`, and the editor refuses tile tools there (objects only). They are excluded, as is Dungeon, which is a room-based generator and not a tile grid.
- Forest over Graveyard: its smallest grid step. `ParamForest1` is 15x15 at 40 units per tile, `ParamForest2` 15x15 at 44, `ParamForest3` 16x16 at 48, `ParamGraveyard` 19x19 at 40. Forest also has no crypt dungeon, and its palette (75 entries) has been walked end to end.
- Stage 0 rather than 1 or 2: it has the smallest scale (a step of 20 units against 22 and 24), and every existing regression level uses it.

## Scale and grid

| Quantity | Value | Source |
| --- | --- | --- |
| Player capsule | 3.85 units tall, 0.6 radius | `CapsuleCollider` named `Player`, live |
| Tile width | 40 units (`scaledTileWidth`) | `ParamForest1`, live |
| Height step | 20 units per level (`scaledTileHeight`) | `ParamForest1`, live |
| Grid | 15x15 tiles, cell (0,0) at world (-280,-280), world = (-280 + 40x, -280 + 40z) | runtime-map-structure.md |
| Skater | 1.8 m | thps-warehouse.md |

The skater is 1.8 m and the player is 3.85 units, so true scale is about 2.1 units per THPS metre. At that scale a tile is about 19 m wide and one height level is about 9 m, which is far coarser than the warehouse: its 2-3 m ramps are 4-6 units, a quarter of one level. Tiles can therefore only supply the floor and the enclosure. Every ramp, deck, ledge and kicker comes from the placed Warehouse mesh.

### Chosen scale

4.4 units per THPS metre, about 2.1 times true player scale, so the playable footprint fills a whole number of tiles.

- The extracted Warehouse mesh measures about 2.0 by 3.1 OBJ units (about 158 x 248 units at the placed scale of 79.2).
- A block of 4 tiles east by 7 tiles north (160 x 280 units) holds it.
- A 2-3 m ramp becomes 9-13 units, about 2.5-3.5 player heights, and one height level (20 units) is about 4.5 m.

### Grid orientation

- Map north is grid +Z and map east is grid +X, the same as `SlopeDirection` (`North` is +Z, `East` is +X). Block-local coordinates below are units from the block's south-west corner, `x` east and `z` north.
- The inner block sits at cells x 8-11, z 4-10 so it contains the generated spawn cell (10, 7). It is surrounded by a ring of cells raised two levels so the generated cliff pieces act as walls; the rest of the grid is removed (`RemoveTile`) and the kill floor ends a fall.

### Player-reachable heights

Measured in the running game (build 1.0.69, CrossOver):

- A plain jump from the floor peaks at about 7.8 units above it (the capsule centre reaches about 9.7 with a resting centre height of 1.925). The jump is stat-driven (`GetJumpForce`), so a run with different items can differ. 
- `PlayerMovement.maxSlopeAngle` is 45. A ramp face steeper than that cannot be run up: on a test pipe reaching 56 degrees the player stalled between a body height of 8 and 10. The extracted Warehouse half pipes go well past that: their faces run 31, 34, 54, 77 and 85 degrees up to the lip (measured from the mesh near (142, -3, 32)), so the level raises the limit instead, see "Slope limit on the half pipes".
- Anything taller than a jump is reached by running up a ramp or by launching off one, the same way the skater uses quarter pipes.
- The game has a `JumpPad`, `Ladder`, wall climbing and rail grinding (`railSpeed`, `canJumpOffRailTime`), so higher spots can also be reached through those.

## Structure to catalog mapping

The Warehouse is one `bundle:thps/Warehouse` placement built from the extracted mesh (see [asset-bundles.md](asset-bundles.md)): the floor, banks, half pipes, decks, ledges, walls, windows, doors and trusses are all in that mesh, so no structure needs its own catalog entry. The Megabonk catalog supplies what the mesh does not:

| Feature | How it is built |
| --- | --- |
| Arena floor and enclosure | tile ops: the inner cells are flat at level -1 so they sit below the Warehouse's sunken floor areas, a one-cell ring is raised to level 2, and every other cell is removed with the kill floor under them |
| Grind rails on the mesh bars | hidden `interactable/rail/0` objects laid along each mesh bar (see "Mesh rail near (75, 3, 28)") |
| Box piles and the tape | `interactable/chest` and `interactable/chestFree` |
| Letters | `forest/shrines/0` to `4` |
| Boss portal | the game's boss spawner, moved into the hanging box above the main half pipe |

Catalog IDs follow level-format.md. `rail/0` is a straight bar about 28 units long at scale 1; `rail/1` is about 50 units long with a bend; `rail/2` to `5` are curved variants not yet placed.

## Collectible mapping (confirmed)

Confirmed as written: box piles are chests, letters are shrines, the tape and the three 100 pickups are free chests. The 4.4 units per THPS metre scale is confirmed too.

Collectibles stay as normal Megabonk items. The Forest palette has `interactable/chest`, `interactable/chestFree` and five shrines `forest/shrines/0` to `4`, which is exactly one shrine per letter.

The positions come from `warehouse_nodes.json` (the extraction in thps-warehouse.md), not from a hand-written table. `collectibles()` in `scripts/build_thps_level.py` maps each node and anchors it with `scripts/warehouse_surface.py`, which reads `warehouse.obj` the way the pack importer does:

- Box piles (nodes 43, 107, 109, 111, 113) are `interactable/chest`, in node order as R1 to R5. Letters are `forest/shrines/0` to `4` for S, K, A, T, E. The tape (node 16) and the three lane 100 pickups (nodes 15, 30, 31, `LANE_BONUS_NODES`) are `interactable/chestFree`. The 100, 200 and 500 cluster at nodes 148 to 150 has no item in the confirmed mapping and stays unplaced.
- An item stands on the highest collider surface at or below its node, found by a downward ray. Its tilt is the surface normal, and its pivot sits `base_offset` above the surface along that normal (`ITEM_METRICS`, measured from the placed items' mesh bounds with `query_objects`: 0.5 for both chests, 0.12, 0.05, 0.05, 0.02 and 0.13 for `forest/shrines/0` to `4`).
- The spot has to be supported (the corners of half the item's bounds land on the same plane within 0.3), on a surface no steeper than 45 degrees (`MAX_SURFACE_TILT`), and clear of every collider triangle except the one it stands on (a box of the item's bounds starting 0.1 above its base). A node that fails slides in x and z by the least distance that passes, up to 10.5 units (`MAX_NODE_SHIFT`).
- Tests check the base within 0.1 of the surface below, no overlap, the shift cap and the mapping. They skip when `.tools/thps1/warehouse` is absent.

Deviations from the source node positions (y is the node height, and "drop" is how far the item stands below it):

| Item | Node | Megabonk item | Node x, y, z | Base x, y, z | Slide | Drop | Tilt (deg) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | 43 | `interactable/chest` | 139.9, 30.7, -82.5 | 137.4, 27.8, -82.5 | 2.5 | 2.9 | 0 |
| R2 | 107 | `interactable/chest` | 50.7, 11.5, -49.1 | 50.7, 8.6, -49.1 | 0 | 2.9 | 0 |
| R3 | 109 | `interactable/chest` | 28.5, 6.7, 13.8 | 28.5, 3.8, 13.8 | 0 | 2.9 | 0 |
| R4 | 111 | `interactable/chest` | 84.0, 11.5, 96.8 | 82.5, 8.6, 96.8 | 1.5 | 2.9 | 0 |
| R5 | 113 | `interactable/chest` | 174.5, 6.7, 69.6 | 174.5, 3.8, 69.6 | 0 | 2.9 | 0 |
| S | 28 | `forest/shrines/0` | 45.3, 8.7, 55.1 | 45.3, 0.5, 55.1 | 0 | 8.2 | 0 |
| K | 29 | `forest/shrines/1` | 108.0, 20.7, 120.0 | 108.0, 0.5, 110.0 | 10.0 | 20.2 | 0 |
| A | 17 | `forest/shrines/2` | 128.1, 8.8, 78.9 | 125.1, 2.4, 82.9 | 5.0 | 6.4 | 19 |
| T | 13 | `forest/shrines/3` | 129.6, 18.9, 26.2 | 129.6, -4.9, 26.2 | 0 | 23.8 | 0 |
| E | 12 | `forest/shrines/4` | 60.6, 12.5, -46.2 | 60.6, 8.6, -46.2 | 0 | 3.9 | 0 |
| Tape | 16 | `interactable/chestFree` | 156.9, 20.4, 26.2 | 156.9, 15.6, 26.2 | 0 | 4.7 | 0 |
| 100 | 15 | `interactable/chestFree` | 129.6, 20.7, -26.5 | 129.6, 4.5, -26.5 | 0 | 16.2 | 34 |
| 100 | 30 | `interactable/chestFree` | 90.2, 20.7, -26.5 | 90.2, 4.5, -26.5 | 0 | 16.2 | 34 |
| 100 | 31 | `interactable/chestFree` | 52.7, 20.7, 100.4 | 52.7, 8.6, 101.9 | 1.5 | 12.2 | 0 |

Hand-arranged items. Items moved in the editor are recorded in `scripts/thps_item_overrides.json` (item code to world `position` and euler `rotation`), and `collectibles()` applies them over the anchored transform, so regenerating the level reproduces them. The surface, overlap and node-distance tests skip these items, because the arrangement is deliberate. To record a new arrangement, save the level from the editor and run `uv run scripts/extract_thps_item_overrides.py <game>/UserData/Levels/thps.mblevel.json`; it takes the last move of each collectible placement and writes only the items that differ from the anchored transform, replacing the file. K, A, T, E, the tape and the two lane 100 chests at nodes 15 and 30 are currently overridden, so the table above shows their anchored starting points, not where they end up. The overrides are not checked against the mesh: at the last extraction A overlapped three collider triangles and the node 30 chest two, and T had a pitch of 0 rather than the upright 270.

- R1 (node 43) sits on the very edge of the platform at x 140 with no floor beyond, so it slides 2.5 units onto the platform. R4 and the third 100 slide 1.5 units to clear a wall or an edge.
- K hovers 20 units above the foot of the north quarter pipe, where the surface is steeper than the limit and the platform on top is too shallow for a shrine, so it stands on the flat floor 10 units south. A slides 5 units to a 19 degree slope.
- T stands on the main half pipe floor, 23.8 units below its node, as the node's letter hovers in the air above the pipe.
- The two lane 100 pickups stand on a 34 degree ramp, so their chests tilt with it, and a player standing there slides off.
- Checked in game: every item's bounds sit on the predicted surface (bounds bottom within 0.05 of it), and the player dropped onto each base settles at the predicted height. R1 settles 0.04 above, and the two ramp chests rest about 0.1 above the model at the ramp foot after the player slides down. Close-ups of all 14 show none floating or clipping, and the tape chest's room shows no chest through its underside.

- The chest, shrine and merchant prefabs are authored lying down (the prefab asset's euler X is 270), so a placement at rotation 0 renders them on their side. Items are placed at X 270 on flat ground, and the surface tilt is composed on top of that on a slope (`item_rotation` in `warehouse_surface.py`).
- `forest/shrines/3` is the `ShadyGuy` prefab, the merchant NPC, not a shrine, and `forest/shrines/0` to `2` and `4` are the Challenge, Magnet, Maoi and Cursed shrines. The mapping stays one catalog entry per letter.

## Windows opened to the player

The pack builds the Warehouse collision mesh without the faces of some windows (`ThpsPack.cs`, `SaveCollisionMesh`). The `FA88F30D` windows are dropped by material. The `F2184063` windows share their material with solid windows elsewhere, so only faces whose world position lies inside one of the `OpenedWindowBounds` boxes (x, y, z min and max) are dropped, and the rendered mesh is untouched:

| Window | Bounds |
| --- | --- |
| Secret room, intact sections | x 149 to 179, y 15 to 26, z 20 to 32 |
| Top of the starting slope, two panes at z -73.3 | x 80 to 140, y 27 to 38, z -75 to -72 |

The half pipe behind the starting slope windows is reached through them. Other `F2184063` windows keep their collision.

## See-through textures

The PS1 transparency key (magenta) is baked to alpha 0 in every texture that carries it (22 of the 99), and those textures are listed in `SeeThroughTextures` in `ThpsPack.cs`. Their materials use `Sprites/Default` so the scene shows through, because the pack's toon shader is opaque and its alpha-clip variant is not in the game build (with `_MK_ALPHA_CLIPPING` on, the albedo map is ignored). They are the ceiling chains, the crane hooks, the posters and graffiti, the chain-link fence, the lamp and the two window textures (`F2184063`, `FA88F30D`), whose keyed pixels are the broken panes. `Sprites/Default` is unlit, so these materials ignore the scene lighting.

## Open questions and risks

- **Interaction is only partly verified.** The collectibles spawn through the same catalog path as generated chests, and a player standing at the R5 chest shows the chest's 30 gold price label. Opening one needs the `Interact` key and gold, which the harness cannot send.
- **Shrine effects on the letters.** The mapping is confirmed, but shrines change a run when used, so whether the effect suits a letter is worth a look once they are placed.
- **Generated clutter.** The seed spawns trees, rocks and shrines inside the block, which are removed with `RemoveObject` (`gen:` ids) from the per-category counts the seed produces (`SEED_OBJECT_COUNTS`, `SEED_TILE_OBJECTS` and `SEED_SCENERY_COUNTS`). The scenery category covers the ruined towers, crates, cubes, pillars and dead trees the tile prefabs leave as uncloned scene roots, which sit under and around the arena once its tiles are removed.
- **Rail grinding is unconfirmed.** `rail/0` and `rail/1` place and render at a scaled size, but nobody has grinded them in a run.
- **The structure map itself is low confidence.** Box pile numbering, the start block's role and the exact positions are ambiguous in the source analysis; see its Unresolved list.

## Building the level

`levels/thps.mblevel.json` is generated, not hand-edited: `scripts/build_thps_level.py` writes it (`uv run scripts/build_thps_level.py`) and `tests/test_build_thps_level.py` covers the generator. `ThpsLevelTests` in `tests/MegabonkLevels.Tests` replays the saved file through `EditStack` and `ReachabilityValidator` and checks that every arena tile is reachable from the generated spawn cell. Regenerate and reload with `uv run scripts/build_thps_level.py` then `relaunch(level="levels/thps.mblevel.json")`.

What the file contains:

- A 4 tile by 7 tile inner arena at cells x 8-11, z 4-10 (`INNER_X`, `INNER_Z`), flat at level -1 (`INNER_LEVEL`), wrapped by a one-cell ring at level 2. Every other cell of the 15x15 grid is removed. Each kept cell gets an explicit `SetTileHeight` and `SetTileSlope`, so nothing depends on the generated heights. Removing every tile does not work, because the kill floor needs a tile to arm; it sits at y=-60.
- One `bundle:thps/Warehouse` placement at uniform scale 79.2 (4.4 units per metre times 18 metres per OBJ unit), centred on the arena and lifted 0.5 above y=0 (`WAREHOUSE_LIFT`). The footprint fits the arena (a test checks it). The level records `packs: {"thps": "<version>"}`, so the version check in asset-bundles.md applies; the pack has to be installed (`task pack:thps`) and the game relaunched before the level loads, or the placement shows a `Missing:` cube.
- `noGrass`: the game's grass manager raycasts onto the ground layer and otherwise grows through the Warehouse floor.
- `playerStart` (`PLAYER_START`): the game places the player at the generated spawn and moving the spawn portal does not move it, so the mod re-applies the start position for 5 seconds after generation. `y` is the on-screen readout value, 1.925 above the feet.
- Removal of every generator object except the spawn portal, the boss spawner and the particles, from the per-category counts the seed produces. The boss spawner is moved into the hanging glass box above the main half pipe, scaled to 0.4 and turned 90 degrees so its arch faces down the corridor, and its `BottomPiece` pillar mesh and the 43-unit-tall invisible `Collider` are hidden (`hiddenChildren` on the `object.move`); that collider otherwise reaches down into the pipe and blocks it. The box's size is estimated from screenshots, so the position and scale are tuned by eye.
- The hidden mesh rails below, the only rails the level places.
- The collectibles in the table above.

Findings:

- **Spawn.** The player is placed at the generator's spawn before edits apply, so the arena has to contain the generated spawn cell (10, 7); a test checks it.
- **Flat-tile prefabs are whole tiles.** `forest/stage0/stageTilePrefabs/flat/7` placed a flat slab with a ruined stone tower and blocks, not a crate. The palette thumbnail was misleading. Do not use the flat-tile entries as props.
- **Rails.** `rail/0` places with a `PlaceObject` and honours rotation and uniform scale. The earlier hand-placed big, ledge and high rails stood in the old layout and were removed with it.
- **Editor camera.** In editor mode the editor owns the camera, so the harness `camera` command has no effect there. For screenshots call `editor(on=false)`, `freeze()` and then `camera(...)`.
- **Validate.** The editor's Validate button produces no visible result in the toolbar or the log on this level, so reachability is checked by `ThpsLevelTests` instead.
- **Save names.** The editor save writes to `UserData/Levels/<name>.mblevel.json`; use a new name so no existing custom level is overwritten.

### Mesh rail near (75, 3, 28)

The extracted Warehouse mesh carries its own rail: a thin flat bar at world x 75, height 3.17 to 3.44, running z 3 to 53 and then bending diagonally to about (81.5, 60.6). The extraction left it floating, with no posts and no `Rail` component, so it could not be ground.

- **Bar kept.** The bar stays as extracted. A visible `rail/0` laid over it stacked on the bar, and `rail/1` is a sloped rail, so neither replaces it.
- **Posts.** `ThpsPack.cs` (`AddRailPosts`, `RailPosts`) adds seven dark box posts under the bar, five along the straight run and two on the bend. The posts are part of the mesh and its collision.
- **Grind.** `MESH_RAILS` in `scripts/build_thps_level.py` lays two hidden `interactable/rail/0` objects along the bar, one over the straight run (yaw 90, scale 1.786, centre z 28.13) and one over the bend (yaw 310.5, scale 0.352), at pivot heights -1.25 (run) and 2.41 (bend), the bar's centre height of 3.3 minus 2.55 times the scale, so the game rail's bar sits at the mesh bar's height. They are placed with the `hidden` flag, described in `level-format.md`, so the game rail's collider and `Rail` component stay live and nothing draws.
- **Alignment.** Measured from top-down and side screenshots under `.tools/evidence/` (`rail_align_top2.png`, `rail0_top.png`, `rail0_side.png`, `rail_hidden_top.png`).
- **Slide check.** Dropping the player onto the bar from above, at (75, 9, 30), carried it along the bar: samples at x 75.006 and 74.994 with z 47.8 then 57.9. The bend was not confirmed to carry the player round the corner.
- **Handoff.** The game ends a grind by launching the player along the rail's tangent, and its catch only sees a rail the player is already touching, so a rail meeting another at an angle drops the player at the joint. The bend and the run met at about 40 degrees: with the hidden rails touching, the run chained onto the bend but not back, and any gap between them broke one direction or the other. `RailHandoffPatch` (`rail_handoff_patch.cs`) postfixes `PlayerMovement.StopRail`: on a custom level, when a grind ran off either end of a rail, it starts the nearest other rail within `RailHandoff.SearchRadius` (3.5 units) that is not on cooldown. A jump off the middle of a rail does not hand off. The radius is that large because a game rail's collider stops short of its spline by about 3.5% of its length at each end: the run's collider spans z 4.90 to 51.37 against a spline from 3.13 to 53.13, so a player leaving the bend at the junction is about 2.2 units from it, outside both the game's catch and a 2 unit search. That inset is the real cause of the failures above.
- **Open.** The rail does not activate on its own; like the game's other rails it needs the right approach and timing. Whether it needs a different approach angle, speed or jump timing to catch is not investigated.

### Mesh rails near (129, 27, 121) and (176, 8, 61)

The Warehouse mesh has two more bars on the same material (`A53322CF`), handled the same way as the first:

- **Wall rod, x 116.3 to 143.0 at z 120.8, height 27.3 to 27.55.** The rod the SKATEBOARDING banner hangs from, with a short bracket at each end running back to the wall (z 120.8 to 123.9). The brackets are real supports and are kept, so this rod gets a hidden game rail and no posts.
- **Deck rail, z 47.9 to 74.7 at x 175.66, height 8.31 to 8.56.** Three posts (the two ends and the middle) in `RailPosts`, up from the floor to the bar. A hidden game rail lies along it.
- **Hidden rails.** The third and fourth entries of `MESH_RAILS`: the wall rod at yaw 0, scale 0.954, centre (129.64, 24.997, 120.84), and the deck rail at yaw 90, scale 0.955, centre (175.66, 5.995, 61.295). Height is the bar's centre height minus 2.55 times the scale (`RAIL0_BAR_HEIGHT`), since the game rail's bar sits higher above its pivot the larger the scale. The first rail's 4.55 offset only fits its 1.786 scale; applying it to these two put the grind about 2 units under the visible bar. Checked in the game: the grind sparks and the player sit on both visible bars.
- **Floating leftovers.** Each post position on the first and deck rails carries a small plate (about 0.46 by 0.25) on the rail material, well below the bar (height 1.5 to 1.8 on the first rail, 5.7 to 6.1 on the deck rail). They are what is left of the original posts and float once the posts are missing. `RailLeftoverBounds` in `ThpsPack.cs` drops the rail-material faces inside two boxes around them; the bars are far above those boxes and are untouched. The wall rod has no such plates.
- **Evidence.** `.tools/evidence/task-021.19-rail1-before.png` and `-after.png`, `-rail2-before.png`, `-rail3-after.png`. The thin diagonal line left beside the first rail's middle post in the after shot is not on the rail material and was not removed.

### Coping rails on the half pipes and wall quarter pipes

The yellow-and-black coping of the main half pipe near (142, -3, 32), and the yellow and grey-brown lips on the wall quarter pipes, each have a hidden game rail so they grind like the mesh rails above. `COPING_LIPS` in `scripts/build_thps_level.py` (`MAIN_PIPE_LIPS` plus `WALL_PIPE_LIPS`) lists the lips and `rail_along` turns each into a `rail/0` placement: the bar runs from start to end, pitched along a falling lip, with its centre on the lip. They are placed through `COPING_RAILS` with the `hidden` flag, the same way as the mesh rails.

| Lip | From | To | Length |
| --- | --- | --- | --- |
| Main pipe, north | (119.78, 5.76, 8.59) | (178.95, 5.76, 8.59) | 59.2 |
| Main pipe, south | (119.78, 5.76, 43.81) | (178.95, 5.76, 43.81) | 59.2 |
| Main pipe, north west diagonal | (119.78, 5.76, 8.59) | (100.06, 0.5, 3.51) | 21.0 |
| Main pipe, south west diagonal | (119.78, 5.76, 43.81) | (100.06, 0.5, 48.87) | 21.0 |
| North wall tiers, height 8.56 | x 40.89 to 80.34, 100.06 to 119.78 and 139.5 to 178.95 | at z -27.1 | 39.5, 19.7, 39.4 |
| North wall upper tier, height 16.63 | (40.89, 16.63, -70.03) | (80.34, 16.63, -70.03) | 39.5 |
| South wall, height 8.56 | (21.17, 8.56, 101.06) | (64.48, 8.56, 101.06) | 43.3 |
| South wall pocket and run | 64.48, 101.06 round the U-shaped pocket near (80, 8.56, 86), down to (96.19, 8.56, 120.63) | 10 segments, the tip as two chords | 4.7 to 19.6 each |
| South wall to east wall | (96.19, 8.56, 120.63) | (162.92, 8.56, 120.63), then round to (175.66, 8.56, 108.04) and up to (175.66, 8.56, 79.77) | 66.7, then 3 curve segments and 28.3 |

- **Measuring.** `lip_runs` in `scripts/warehouse_surface.py` finds the edges where two faces fall away from each other (a ridge) and where a ramp meets a flat deck, with a grade of at most 0.3, merged into straight runs. It returns every lip above, and `tests/test_build_thps_level.py` checks each `COPING_LIPS` entry against it when the extraction is present.
- **Diagonals.** The west end of the main pipe is a hip: each lip bends down along a 21 unit diagonal to the floor corner, so `rail_along` pitches those rails and the grind chains onto them through `RailHandoffPatch`, the same long run and short bend as the mesh rail near (77, 2, 28).
- **Pocket tip.** The lip turns about 174 degrees round the pocket's rounded tip in four 2.5 unit mesh edges. Rails that short all sit within `RailHandoff.SearchRadius` of every joint, so the handoff bounced between them until all were on cooldown and dropped the player (the bail near (78, 3, 79)). The tip is two chords, (77.05, 8.56, 88.32) to (80.34, 8.56, 85.03) and on to (83.62, 8.56, 88.32), and `tests/test_build_thps_level.py` keeps every coping rail at least as long as the search radius.
- **Handoff direction.** At a sharp joint the game started the next rail at its end with its direction multiplier at +1, so the grind stopped at once. `RailHandoffPatch` now sets `railDirectionMultiplier` after `StartRail` to run toward the far end (`RailHandoff.DirectionAwayFromNearestEnd`), and the log line for each handoff prints the progress and direction. Checked in game across the tip from both sides.
- **Wall ends.** A grind off the end of a rail launches the player along the rail, so a rail that ends on a wall launches the player into it. The ends in `WALL_ENDS`, found by probing the mesh from each lip end, stop `WALL_MARGIN` (12) units short of the wall. Dropped on the north tier, the player still coasts along the flat lip into the wall, so the margin does not stop that; it only moves where the launch starts.
- **Not coped.** The two wooden kickers near (45, 3.3, 47) and (45, 3.3, 62), the taxi funbox plywood near (120 to 137, 2 to 5, 75 to 83), the three earlier mesh rails, and the vertical-faced tops at heights 45 to 51, which have no ramp face.
- **Checked in game.** Dropped onto the main pipe lips, the north tier, the south wall and the pocket, the player grinds with sparks on the coping, and from the north lip the grind carries onto the west diagonal. The harness injects no gameplay input, so a drop only ever grinds west: an eastbound grind into the east wall, ollies off the lips, and grinding from a run up a pipe were not exercised.

### Slope limit on the half pipes

The player could not ollie off the main half pipe edges near (142, -3, 32). The cause is the movement limit, not the collision mesh: the pipe face passes 45 degrees about 3 units up its 8 unit rise, so above that the player is not grounded and cannot ride to the lip. The level file therefore sets `maxSlopeAngle` (`MAX_SLOPE_ANGLE` in `scripts/build_thps_level.py`, 88), which the mod applies to `PlayerMovement.maxSlopeAngle` for the run only (see `level-format.md`); Forest and every level without the key keep the game's 45. Vertical faces (90 degrees) stay unclimbable, so walls still block. The mod logs `LiveEdit: max slope angle 45 -> 88` when it applies. Open: how the raised limit feels on the other ramps and whether a lower value rides the pipes as well.

### Check against the reference frames

The frames in `tools/thps_warehouse_frames/` come from the 2020 remake, so the textures and lighting differ from the PS1 mesh by design. Compared with frames 4, 12 and 138 and the items map:

- Present: the walled room, the main half pipe and its hanging box, the banks, decks and ledges, the rail bars, the windows and the boss portal.
- Roof: the pack adds a flat dark roof (see "Warehouse roof" in asset-bundles.md), so a view from above the room shows the roof and not the interior; the items map and frame 12 are cut-away or interior views.
- Lighting: the level uses Forest's fog and lighting, which tints the room teal and has none of the remake's window light shafts. Surfaces read grey-green and dark.
- Not compared: a pitch-45 south-east overview matching the items map, because of the roof.
