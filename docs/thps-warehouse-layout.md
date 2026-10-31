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

The skater is 1.8 m and the player is 3.85 units, so true scale is about 2.1 units per THPS metre. At that scale a tile is about 19 m wide and one height level is about 9 m, which is far coarser than the warehouse: its 2-3 m ramps are 4-6 units, a quarter of one level. Tiles are therefore too coarse to build anything in the level, and the level keeps just one of them out of sight; every floor, ramp, deck, ledge, wall and kicker comes from the placed Warehouse mesh.

### Chosen scale

4.4 units per THPS metre, about 2.1 times true player scale, so the playable footprint fills a whole number of tiles.

- The extracted Warehouse mesh measures about 2.0 by 3.1 OBJ units (about 158 x 248 units at the placed scale of 79.2).
- A block of 4 tiles east by 7 tiles north (160 x 280 units) holds it.
- A 2-3 m ramp becomes 9-13 units, about 2.5-3.5 player heights, and one height level (20 units) is about 4.5 m.

### Grid orientation

- Map north is grid +Z and map east is grid +X, the same as `SlopeDirection` (`North` is +Z, `East` is +X). Block-local coordinates below are units from the block's south-west corner, `x` east and `z` north.
- The Warehouse block covers cells x 8-11, z 4-10, which contains the generated spawn cell (10, 7). Only that one cell is kept as a tile, flat at level -1 and hidden under the Warehouse floor; every other cell of the grid is removed (`RemoveTile`) and the authored kill floor ends a fall. The mesh floats like a native island and its own walls enclose the arena, so no tile terrain is needed to hold the playfield in.

### Player-reachable heights

Measured in the running game (build 1.0.69, CrossOver):

- A plain jump from the floor peaks at about 7.8 units above it (the capsule centre reaches about 9.7 with a resting centre height of 1.925). The jump is stat-driven (`GetJumpForce`), so a run with different items can differ. 
- `PlayerMovement.maxSlopeAngle` is 45. A ramp face steeper than that cannot be run up: on a test pipe reaching 56 degrees the player stalled between a body height of 8 and 10. The extracted Warehouse half pipes go well past that: their faces run 31, 34, 54, 77 and 85 degrees up to the lip (measured from the mesh near (142, -3, 32)), so the level raises the limit instead, see "Slope limit on the half pipes".
- Anything taller than a jump is reached by running up a ramp or by launching off one, the same way the skater uses quarter pipes.
- The game has a `JumpPad`, `Ladder`, wall climbing and rail grinding (`railSpeed`, `canJumpOffRailTime`), so higher spots can also be reached through those.

## Structure to catalog mapping

For the additive editable kit, see the [construction piece inventory](thps-warehouse-pieces.md).
The mapping below describes the unchanged shipped level, not the separate kit assembly.

The Warehouse is one `bundle:thps/Warehouse` placement built from the extracted mesh (see [asset-bundles.md](asset-bundles.md)): the floor, banks, half pipes, decks, ledges, walls, windows, doors and trusses are all in that mesh, so no structure needs its own catalog entry. The Megabonk catalog supplies what the mesh does not:

| Feature | How it is built |
| --- | --- |
| Arena floor and enclosure | the placed Warehouse mesh: its floor, banks and walls are all in it, and the game's ground-layer spawn raycasts land enemies on its floor. The tile grid keeps only the generated spawn cell, flat at level -1 under the mesh, so the player has somewhere to stand while the edits apply; every other cell is removed and the authored kill floor (`killFloorY` -35) ends a fall |
| Grind rails on the mesh bars | hidden `interactable/rail/0` objects laid along each mesh bar (see "Mesh rail near (75, 3, 28)") |
| Box piles and the tape | `interactable/chest` and `interactable/chestFree` |
| Letters | `forest/shrines/0` to `4` |
| Boss portal | the game's boss spawner, stood on the floor inside the hanging box above the main half pipe, with the level authoring where its boss actually appears (`bossSpawnPosition`) |

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

Hand-arranged items. Items moved in the editor are recorded in `scripts/thps_item_overrides.json` (item code to world `position` and euler `rotation`), and `collectibles()` applies them over the anchored transform, so regenerating the level reproduces them. The surface, overlap and node-distance tests skip these items, because the arrangement is deliberate. To record a new arrangement, save the level from the editor and run `uv run scripts/extract_thps_item_overrides.py <game>/UserData/Levels/thps.mblevel.json`; it takes the last move of each collectible placement and writes only the items that differ from the anchored transform, replacing the file. K, A, T, E, the tape and the two lane 100 chests at nodes 15 and 30 are currently overridden, so the table above shows their anchored starting points, not where they end up. The overrides are not checked against the mesh: at the last extraction A overlapped three collider triangles and the node 30 chest two, and T had a pitch of 0 rather than the upright 270. T's override stands on the main half pipe floor at (170.39, -4.91, 24.07), 0.02 above the mesh, and a test keeps it there; saved from the editor it had hovered 1.55 units up. E, the tape chest and the node 15 chest likewise had hovered 0.37 to 0.48 units and now rest on the surface; A and the node 30 chest lean into the floor by design and are left sunk by up to 0.8 units at their lowest corner. `lowest_clearance` measures the lowest footprint corner against the mesh, and a test keeps every hand-placed item from hovering.

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
- **Rail grinding needs the right approach.** The hidden `rail/0` objects do grind — the mesh rails and copings below were all checked in a run — but a rail does not catch on its own, and the harness injects no gameplay input, so speed, approach angle and jump timing still have to come from a hand on the keyboard.
- **The structure map itself is low confidence.** Box pile numbering, the start block's role and the exact positions are ambiguous in the source analysis; see its Unresolved list.

## Building the level

### Editable construction assembly

`levels/thps-editable.mblevel.json` is a separate reference layout assembled by
`scripts/build_thps_editable_level.py`. Run `task thps:editable-level` to regenerate
it, or `task thps:editable-install` to install it alongside the shipped level and
the already-built pack. Build a missing pack first with `task pack:thps`, then
relaunch with `relaunch(level="levels/thps-editable.mblevel.json")`.

The generator uses `pieces.json` instance positions, full rotations/scales and
canonical `catalogAsset` references, not a second implementation of mesh maths.
Repeated signs, boards, kicker parts, posts and props reuse a compact asset
library. Roof quads are merged into larger selectable sections, with shared
panel assets wherever their shape permits. It snapshots `attachments.json`
per-instance defaults into each owner placement: 17 supports and 41 grind paths.
The nine archival `suppressed-post` instances are intentionally absent. Attached
supports are not also placed at the root, and legacy rails are not emitted again.
Placement IDs reserve each owner's ordered children before the next root.

The consolidated library has 200 construction assets plus the legacy Warehouse.
The reference uses 32 roof sections instead of 1,541 individual quads, including
12 instances of the same stock flat panel. Its 24 loose planks use six artwork
variants; different kicker top artwork remains separate. The source-face
inventory remains complete without requiring an asset for each source instance.

Terrain bootstrap, generated-clutter removals, boss portal, radio and the 14
collectibles reuse the shipped generator's final transforms and overrides.
There is no `bundle:thps/Warehouse` placement. The shipped level and generator
remain the byte-preserved monolithic reference; the editable generator refuses
to overwrite that file. Regeneration resets the reference layout, so save custom
arrangements under another name rather than regenerating over them.

In the editor, the **Level** panel cycles through settings with `<` and `>`.
Enter marker coordinates as `[x,y,z]`, booleans as `true`/`false`, and `null` for
an optional setting's default; text fields take plain text and character lists
take a JSON array. **Clear** empties the input; **Apply** or Enter commits it;
**Cancel** or Escape discards the draft. Settings have their own **Undo/Redo**
buttons, separate from object history. Save includes both histories' current
state, and settings-only changes count as dirty.

The cyan player-start marker uses body height; the magenta boss destination uses
floor height. **Locate marker** flies the camera to the selected marker, and
**Marker to camera** moves it to the current camera position. Numeric input
also edits either marker. They are editor-only lines without colliders.
The boss destination remains independent of the portal and hanging room.
The portal, radio, collectibles and construction geometry use normal object
tools; Ctrl-click selects a hidden grind path instead of its visible owner.

Gameplay controls apply immediately and persist on save: kill floor (still
clamped above the catch floor), slope limit, slide-gated grinding and grass.
Music, title/descriptions and character restrictions are editable as well.
Map, stage, tier and seed changes are refused when existing edits target the
current generation; start a fresh level or regenerate the layout instead.
In-place Load similarly refuses a different generation. Pack dependencies are
derived at save time; schema/build metadata are compatibility data, not props.

The kit has its own revision (`packKitVersions`) in addition to the preserved
legacy pack version. See [pack versions](level-format.md#pack-versions).
Revision 2 replaces the original quad-per-prefab kit without compatibility
aliases; regenerate this reference after rebuilding the pack. The preserved
`thps.mblevel.json` and `forest_custom.mblevel.json` do not depend on those kit IDs.

### Shipped monolithic reference

`levels/thps.mblevel.json` is generated, not hand-edited: `scripts/build_thps_level.py` writes it (`uv run scripts/build_thps_level.py`) and `tests/test_build_thps_level.py` covers the generator. `ThpsLevelTests` in `tests/MegabonkLevels.Tests` replays the saved file through `EditStack` and `ReachabilityValidator` and checks that the kept tile is reachable from the generated spawn cell, that the authored kill floor sits below it, that the boss portal stands on the floor inside the hanging box, and that the authored `bossSpawnPosition` puts the boss on the pipe floor outside it. Regenerate and reload with `uv run scripts/build_thps_level.py` then `relaunch(level="levels/thps.mblevel.json")`.

What the file contains:

- One kept tile at the generated spawn cell (10, 7) (`GENERATED_SPAWN_CELL`), flat at level -1 (`INNER_LEVEL`), with an explicit `SetTileHeight` and `SetTileSlope` so nothing depends on the generated heights. It is there because the game places the player at the generated spawn before the edits apply, so that cell has to be floor while they run; the mesh hides it. Every other cell of the 15x15 grid is removed. The Warehouse block the mesh spans is 4 tiles east by 7 tiles north at cells x 8-11, z 4-10 (`INNER_X`, `INNER_Z`).
- `killFloorY` (`KILL_FLOOR_Y`, -35): authored rather than derived, because with a single hidden tile the derived floor would sit 40 units below it, deep enough for an actor to come to rest on the mesh's sub-floor skirt above it and stay unkillable. It is 15 units under the kept tile, so standing on that tile is safe, and above the mesh's lowest geometry (-48.6), so anything that ends up under the Warehouse dies. All 43 mesh faces below -20 are vertical (x 21-80, z 3.5-104: the west wall's skirt), so nothing is restable in that band.
- One `bundle:thps/Warehouse` placement at uniform scale 79.2 (4.4 units per metre times 18 metres per OBJ unit), centred on the arena and lifted 0.5 above y=0 (`WAREHOUSE_LIFT`). The footprint fits the arena (a test checks it). The level records `packs: {"thps": "<version>"}`, so the version check in asset-bundles.md applies; the pack has to be installed (`task pack:thps`) and the game relaunched before the level loads, or the placement shows a `Missing:` cube.
- `noGrass`: the game's grass manager raycasts onto the ground layer and otherwise grows through the Warehouse floor.
- `grindRequiresSlide`: with a rail on every lip, the game's own catch took the player into a grind the moment they rode over one, which is what made the lips impossible to skate (see "Grind gate" in [development.md](development.md)). A grind now starts only while the slide button is held, so an ollie off a lip keeps the player's momentum; see "Coping rails on the half pipes and wall quarter pipes".
- `playerStart` (`PLAYER_START`): the game places the player at the generated spawn and moving the spawn portal does not move it, so the mod re-applies the start position for 5 seconds after generation. `y` is the on-screen readout value, 1.925 above the feet. The spawn is (109, 38, -116), on the 26 degree slope of the start half pipe 4 units past the platform lip, so the player drops onto the pipe and slides forward; spawned nearer the lip, over its 72 degree face, the player caught the lip rail and stuck.
- Removal of every generator object except the spawn portal, the boss spawner and the particles, from the per-category counts the seed produces. The boss spawner is stood on the floor inside the hanging glass box above the main half pipe, world (170, 15.6, 27) (`BOSS_SPAWN_LOCAL`, `BOSS_SPAWN_Y`), hidden in plain sight the way the reference map has its secret room (see [thps-warehouse.md](thps-warehouse.md), "Glass corridor and secret room": the skater launches into it off the quarter pipe in front). It is scaled to 0.4 and turned 90 degrees so its arch faces across the floor, and its `BottomPiece` pillar mesh and the 43-unit-tall invisible `Collider` are hidden (`hiddenChildren` on the `object.move`); that collider otherwise reaches down into the pipe and blocks it, and a visible collider in the box would block a grind. In the mesh the box is a closed room: an interior floor top at 15.64 (its slab's underside at 15.31), a roof whose underside sits at 25.42, walls on all four sides between them, over a footprint of x 149.4-178.9, z 20.9-31.4 (`BOSS_PORTAL_FOOTPRINT`).
- `bossSpawnPosition`: the boss appears on the main half pipe's floor just outside the box's south wall, in the portal's own x column, world (170, -4.933, 20) (`BOSS_GROUND_LOCAL`). A spawner summons its boss at its own position and `EnemyMovementRb` chases with rigidbody physics on a Tiles map that has no navmesh, so a boss materialised inside a closed box can never get out and "Defeat the Boss" cannot complete; the mod moves it after the portal's `Interact()` (see `bossSpawnPosition` in [level-format.md](level-format.md)). The height comes from a raycast down onto the extracted mesh (`ws.drop`) starting at `BOSS_GROUND_DROP_FROM` (12.0), below the box's floor slab, so the box can never catch the ray — a drop started above the slab leaves the boss on the box rather than on the floor.
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
| Shorty's ledge, west wall, height 3.79 | (40.89, 3.79, 3.51) to (40.89, 3.79, 8.11), then (25.77, 3.79, 26.19), (25.77, 3.79, 48.87) and (21.17, 3.79, 58.73) | 4 segments | 4.6, 23.6, 22.7, 10.9 |
| Start half pipe platform, height 35.85 | (80.34, 35.85, -120.84) | (139.5, 35.85, -120.84) | 59.2 |

- **Measuring.** `lip_runs` in `scripts/warehouse_surface.py` finds the edges where two faces fall away from each other (a ridge) and where a ramp meets a flat deck, with a grade of at most 0.3, merged into straight runs. It returns every lip above, and `tests/test_build_thps_level.py` checks each `COPING_LIPS` entry against it when the extraction is present.
- **Start pipe.** The start half pipe's mesh is double-sided, so each edge carries four faces; the finders drop duplicate faces (same opposite vertex and normal up to sign) before looking for two. The platform lip runs the width of the pipe, wall to wall, and its rail covers it edge to edge: dropped 1.4 units from the west wall the player caught the grind and rode it to x 138.86, 0.6 short of the east wall. A harness teleport onto it puts the player in the grind pose with sparks on the coping but gives no speed, so the player holds still; a grind along it was not exercised. Other lip runs in the start area, such as (80.34, 26.95, -58.02) to (103.35, 26.95, -58.02) and the 48.01 runs at z -65.75, are not coped.
- **Ledge.** The Shorty's ledge is a flat deck over a vertical face, so `lip_runs` skips it; `ledge_runs` in `scripts/warehouse_surface.py` finds the top edges of decks over a face at least 80 degrees steep, and `LEDGE_LIPS` is checked against it. The player leaves the grind at (43, 2, 4) at the kicker end and (22, 2, 60) at the wall end. Both ends touch a wall. The matching ledge edges on the east side, from (162.57, 3.79, 60.14) to (170.75, 3.79, 51.69) and (168.76, 3.79, 75.94), are not coped.
- **Diagonals.** The west end of the main pipe is a hip: each lip bends down along a 21 unit diagonal to the floor corner, so `rail_along` pitches those rails and the grind chains onto them through `RailHandoffPatch`, the same long run and short bend as the mesh rail near (77, 2, 28).
- **Pocket tip.** The lip turns about 174 degrees round the pocket's rounded tip in four 2.5 unit mesh edges. Rails that short all sit within `RailHandoff.SearchRadius` of every joint, so the handoff bounced between them until all were on cooldown and dropped the player (the bail near (78, 3, 79)). The tip is two chords, (77.05, 8.56, 88.32) to (80.34, 8.56, 85.03) and on to (83.62, 8.56, 88.32), and `tests/test_build_thps_level.py` keeps every coping rail at least as long as the search radius.
- **Handoff direction.** At a sharp joint the game started the next rail at its end with its direction multiplier at +1, so the grind stopped at once. `RailHandoffPatch` now sets `railDirectionMultiplier` after `StartRail` to run toward the far end (`RailHandoff.DirectionAwayFromNearestEnd`), and the log line for each handoff prints the progress and direction. Checked in game across the tip from both sides.
- **Wall ends.** Each rail runs edge to edge along its lip, to the wall where a lip ends on one. A grind that reaches such an end keeps the rail's speed, about 19.5, and reaches the wall anyway, so `RailWallEndPatch` (`rail_wall_end_patch.cs`) ends the grind short of it: a postfix on `PlayerMovement.RailMovement` that on a custom level raycasts along the horizontal velocity and calls `StopRail` once a wall comes within `RailWallEnd.DetachDistance` (5 units). The hit has to be a wall, meaning near vertical (`WallNormalMaxY` 0.3, which keeps floors and the 45 degree pipe faces rideable) and facing the player (`FacingDotMin` 0.7, so a rail bar or a wall seen edge on does not end the grind), and the player has to be moving at least `MinSpeed` (2). A rail other than the one being ground, within `RailHandoff.SearchRadius` and off cooldown, suppresses the detach and leaves the chain to `RailHandoffPatch`, which is what keeps the joints and the pocket tip intact. The detach caps the horizontal speed at `MaxDismountSpeed` (6) and adds `DismountHop` (5) upward; without the hop the player slides along the coping and the game catches the same rail again several times. The game does catch it once more about half a second later at low speed and its own `StopRail` ends that at the rail's end, so the player comes to rest beside the wall rather than into it. The log line reads `RailWallEnd: ended the grind <n> short of a wall at (<x>, <y>, <z>), progress <p>, speed <s> kept <k>`. Checked in game against the east wall on the main pipe south lip: a 57 unit run up from x 122 let go 4.83 short at the full grind speed of 19.5, with the player alive at full health.
- **Not coped.** The two wooden kickers near (45, 3.3, 47) and (45, 3.3, 62), the taxi funbox plywood near (120 to 137, 2 to 5, 75 to 83), the three earlier mesh rails, and the vertical-faced tops at heights 45 to 51, which have no ramp face.
- **Checked in game.** Dropped onto the main pipe lips, the north tier, the south wall and the pocket, the player grinds with sparks on the coping, and from the north lip the grind carries onto the west diagonal. The harness injects no gameplay input, so a drop only ever grinds west, toward a coping rail's progress 0 end. An eastbound grind runs from a scratch copy of the level with the two main-pipe coping rails rotated 180 degrees (`.tools/evidence/thps-east-wall-scratch.mblevel.json`), which turns the same catch eastbound at the game's own grind speed. Ollies off the lips, and grinding from a run up a pipe, still need real keyboard input.
- **Slide-gated.** Because these rails sit on every lip, the level sets `grindRequiresSlide`, so a grind starts only while the slide button is held and riding over a coping keeps the player's momentum (`GrindGate` and `GrindGatePatch`, see "Grind gate" in [development.md](development.md)). Checked in game on the main pipe's north coping and the north wall tier with the harness holding the button in place of the keyboard. Released, the catch is refused and the player stands on the lip normally: `GrindGate: slide released, grind start blocked at (140.0, 7.9, 8.6) by the StartRail hook.` on the coping, `... blocked at (160.0, 11.1, -27.1) ...` on the tier (`.tools/evidence/grind-gate-live-blocked.png`). Held, the same drop starts a real moving grind: `GrindGate: slide held, grind started at (140.0, 7.9, 8.6) on the rail at (149.4, 5.4, 8.6).` on the coping, where the player travels to x 121, and `GrindGate: slide held, grind started at (160.0, 10.6, -27.1) on the rail at (159.2, 8.3, -27.1).` on the tier, where the run covers x 160 to 118.9 before the rail's end (`grind-gate-tier-held.png`). Chaining asks the same question, held: `RailHandoff: moved onto rail at distance 0.00, progress 0.000, direction 1.0.` onto the west diagonal, which then runs to `progress 1.000`. The button is a hold rather than a toggle, so releasing it at any point comes the player off the rail: `GrindGate: slide released, the grind ends at (112.2, 5.7, 6.6), progress 0.397.` mid-diagonal, with momentum carrying them the rest of the way along the lip while the catch keeps refusing them (`... blocked at (102.5, 3.1, 4.1) by the StartRail hook.`) until the button goes down again, when that same rail is caught at once (`GrindGate: slide held, grind started at (102.5, 3.1, 4.1) on the rail at (110.0, 3.0, 6.1).`). Checked on the keyboard as well: holding slide catches the coping and letting go drops the player off the lip. While held, `GrindAssist` also catches a rail within 2 units of the player's feet, so an approach that misses the bar still goes into a grind: dropped 1.6 units off that bar, `GrindAssist: caught the rail at (149.4, 5.4, 8.6) from 0.00 units at (150.0, 9.4, 10.2), progress 0.510.` That every blocked line names the `StartRail` hook answers what the dump could not: the game's `Rail.FixedUpdate` catch calls `StartRail` without consulting `CanStartGrind`. As a control, the same level with the key stripped (`.tools/evidence/thps-no-gate-scratch.mblevel.json`) still grinds on contact: dropped at x 176 with the button on the real device and nobody near the keyboard, the player rode the whole north coping and on to the floor at (88.6, 2.4, 0.5) with no `GrindGate` line at all (`.tools/evidence/grind-gate-no-key-control.png`).

### Slope limit on the half pipes

The player could not ollie off the main half pipe edges near (142, -3, 32). The cause is the movement limit, not the collision mesh: the pipe face passes 45 degrees about 3 units up its 8 unit rise, so above that the player is not grounded and cannot ride to the lip. The level file therefore sets `maxSlopeAngle` (`MAX_SLOPE_ANGLE` in `scripts/build_thps_level.py`, 88), which the mod applies to `PlayerMovement.maxSlopeAngle` for the run only (see `level-format.md`); Forest and every level without the key keep the game's 45. Vertical faces (90 degrees) stay unclimbable, so walls still block. The mod logs `LiveEdit: max slope angle 45 -> 88` when it applies. Open: how the raised limit feels on the other ramps and whether a lower value rides the pipes as well.

### Check against the reference frames

The frames in `tools/thps_warehouse_frames/` come from the 2020 remake, so the textures and lighting differ from the PS1 mesh by design. Compared with frames 4, 12 and 138 and the items map:

- Present: the walled room, the main half pipe and its hanging box, the banks, decks and ledges, the rail bars, the windows and the boss portal.
- Roof: the pack adds a flat dark roof (see "Warehouse roof" in asset-bundles.md), so a view from above the room shows the roof and not the interior; the items map and frame 12 are cut-away or interior views.
- Lighting: the level uses Forest's fog and lighting, which tints the room teal and has none of the remake's window light shafts. Surfaces read grey-green and dark.
- Not compared: a pitch-45 south-east overview matching the items map, because of the roof.
