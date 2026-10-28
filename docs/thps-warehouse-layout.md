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

The skater is 1.8 m and the player is 3.85 units, so true scale is about 2.1 units per THPS metre. At that scale a tile is about 19 m wide and one height level is about 9 m, which is far coarser than the warehouse: its 2-3 m ramps are 4-6 units, a quarter of one level. Tiles can therefore only supply the floor, the enclosure and one coarse raised block. Every ramp, deck, ledge and kicker has to be a placed object.

### Chosen scale

4.4 units per THPS metre, about 2.1 times true player scale, so the playable footprint fills a whole number of tiles.

- The map outline measures about 35 m north by 22 m east (from the pixel-to-metre conversion in thps-warehouse.md, low confidence), which is about 155 x 97 units.
- A block of 4 tiles north by 3 tiles east (160 x 120 units) holds it.
- A 2-3 m ramp becomes 9-13 units, about 2.5-3.5 player heights, and one height level (20 units) is about 4.5 m. The raised north-east block fits one level.

### Grid orientation

- Map north is grid +Z and map east is grid +X, the same as `SlopeDirection` (`North` is +Z, `East` is +X). Block-local coordinates below are units from the block's south-west corner, `x` east and `z` north.
- Which 4x3 block of the 15x15 grid is used is not chosen yet: it should need the fewest terrain edits on seed `20261007`, which needs a height dump of the generated grid. The block is surrounded by a ring of cells raised two levels so the generated cliff pieces act as walls; the rest of the grid is removed (`RemoveTile`) and the kill floor ends a fall.

### Player-reachable heights

Measured in the running game (build 1.0.69, CrossOver):

- A plain jump from the floor peaks at about 7.8 units above it (the capsule centre reaches about 9.7 with a resting centre height of 1.925). The jump is stat-driven (`GetJumpForce`), so a run with different items can differ. Decks, ledges and platforms are kept at 6 or lower so a jump clears them; `PLAYER_JUMP_APEX` in the generator is the limit its tests use.
- `PlayerMovement.maxSlopeAngle` is 45. A ramp face steeper than that cannot be run up: on a test pipe reaching 56 degrees the player stalled between a body height of 8 and 10. Every ramp is therefore capped near 40 degrees, which makes a pipe at least 1.5 times as deep as it is high.
- Anything taller than a jump is reached by running up a ramp or by launching off one, the same way the skater uses quarter pipes. The corridor floor at 13 units is a ramp rise plus a jump away from the half pipe.
- The game has a `JumpPad`, `Ladder`, wall climbing and rail grinding (`railSpeed`, `canJumpOffRailTime`), so higher spots can also be reached through those.

## Structure to catalog mapping

Catalog IDs follow level-format.md. A thumbnail-only identification is marked "thumb"; none of the IDs below has been placed in a level yet.

| Structure (map code) | Reuse or new | Catalog ID or reason |
| --- | --- | --- |
| Floor of the arena | reuse | tile ops on the 4x3 block; flat variants `forest/stage0/stageTilePrefabs/flat/0` to `flat/8` for appearance |
| Enclosure (west, north and the cut-away sides) | reuse | ring of cells raised two levels (`SetTileHeight`); the game builds the cliff walls |
| Raised north-east block M14 and the two sloped lanes | reuse | `SetTileHeight` +1 for the block, `SetTileSlope` North or East for the lane cells; one level is about 4.5 m |
| Dark pit M13 | reuse | `RemoveTile` on one cell, left as a hole with the kill floor under it |
| Big rail M15, high rail, ledge rails | reuse | `interactable/rail/1` (about 50 units long at scale 1, with a bend) for the big rail; `interactable/rail/0` (a straight bar about 28 units long at scale 1) for the ledge and high rails; `rail/2` to `5` are curved variants not yet placed |
| Box piles and cardboard heaps | new | the Forest palette has no crate or cardboard prop; the box pile collectibles are chests (below) and the cardboard heaps are decorative only |
| West bank M1, north bank M6, middle pipe M7, channel pipe M8, back pipe M9, notch pipe M10 | new | the palette has no ramp or curved transition prop; a slope tile is 40 units wide and rises 20, too coarse |
| Platform M2, deck M9, ledge M11 | new | no low solid block prop; rocks and logs are the wrong shape and their colliders are unchecked |
| Half pipe M4 | new | two opposed transitions with a flat between; built from the same quarter pipe asset if it can be mirrored |
| Taxi funbox M3 | new | no vehicle; a mound with a car shape |
| Plywood kickers M12 | new | small wedge; the smallest slope tile is still 20 units high |
| Hanging corridor M5 and the tape room | new | a box on a frame with a walkable floor; the breakable glass is not reproduced |
| Roll-up doors, windows, pilasters, trusses, graffiti, cones and barricades | new, decorative | no equivalent props; only done if the layout needs the visual |

The ramps, ledges and decks above are the new-asset work, built as the `thps` pack described in [asset-bundles.md](asset-bundles.md): five prefabs (`QuarterPipe`, `Kicker`, `Block`, `Taxi`, `Corridor`) scaled per placement.

### Placed structures

Block-local centre of the footprint in units (x east, z north), base height, and the scaled width, rise and depth. A ramp climbs toward yaw 0 north, 90 east, 180 south, 270 west. These are the `STRUCTURES` table in `scripts/build_thps_level.py`.

| Code | Asset | Centre (x, z) | Base y | Yaw | Width x rise x depth | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | `QuarterPipe` | (9, 12) | 0 | 270 | 24 x 12 x 18 | west bank; the high rail sits on its lip |
| M2 | `Block` | (7, 33) | 0 | 0 | 14 x 5.5 x 14 | west platform; the ledge rail sits on it |
| M3 | `Taxi` | (34, 25) | 0 | 90 | 8 x 5 x 20 | long axis east to west |
| M4a, M4b | `QuarterPipe` | (33, 35.5), (33, 54.5) | 0 | 180, 0 | 30 x 6 x 9 | the half pipe: two opposed pipes with a 10 unit flat between |
| M5 | `Corridor` | (10, 66) | 13 | 0 | 18 x 13 x 28 | hangs 13 units up, open at both ends |
| M6, M7, M8 | `QuarterPipe` | (34, 71), (58, 74), (77, 72.5) | 0 | 0 | 20 x 12 x 18, 12 x 8 x 12, 18 x 10 x 15 | the channel pipes, on flat ground south of the lanes |
| M9 | `Block` | (101, 103) | 0 | 0 | 38 x 6 x 24 | east deck |
| M9b | `QuarterPipe` | (111, 103) | 6 | 90 | 24 x 12 x 18 | back pipe standing on the deck |
| M10 | `QuarterPipe` | (67, 4.5) | 0 | 180 | 20 x 6 x 9 | south notch pipe |
| M10b | `Block` | (60, 15) | 0 | 0 | 22 x 4 x 10 | ledge in front of M10 |
| M11 | `Block` | (99, 67) | 0 | 0 | 18 x 4 x 12 | south-east ledge |
| M12a, M12b | `Kicker` | (87, 46), (87, 32) | 0 | 180, 0 | 12 x 4.4 x 6.3, 12 x 2.6 x 3.7 | the kicker pair, lips facing each other with 7.6 units between |

## Collectible mapping (confirmed)

Confirmed as written: box piles are chests, letters are shrines, the tape and the three 100 pickups are free chests. The 4.4 units per THPS metre scale is confirmed too.

Collectibles stay as normal Megabonk items. The Forest palette has `interactable/chest`, `interactable/chestFree` and five shrines `forest/shrines/0` to `4`, which is exactly one shrine per letter.

| THPS item | Megabonk item | Block-local (x east, z north) and y, units | Stands on | Source position (thps-warehouse.md) |
| --- | --- | --- | --- | --- |
| Box pile R1 | `interactable/chest` | (8, 34), 5.5 | M2 west platform | M2 |
| Box pile R2 | `interactable/chest` | (61, 16), 4 | M10b south notch ledge | M10 |
| Box pile R3 | `interactable/chest` | (98, 67), 4 | M11 south-east ledge | M11 |
| Box pile R4 | `interactable/chest` | (86, 100), 6 | M9 east deck | M9 |
| Box pile R5 | `interactable/chest` | (20, 88), 4 | the west lane, near its low end | uncertain, see below |
| Letter S | `forest/shrines/0` | (84, 40), 0 | ground between the kickers | M12 |
| Letter K | `forest/shrines/1` | (33, 2), 0 | ground, south-west corner | K |
| Letter A | `forest/shrines/2` | (34, 26), 5 | M3 taxi | M3 |
| Letter T | `forest/shrines/3` | (27, 60.5), 0 | ground between M4b and M6 | M4 |
| Letter E | `forest/shrines/4` | (86, 108), 6 | M9 east deck, north corner | M8, M9 |
| Secret tape | `interactable/chestFree` | (11, 67), 13 | M5 corridor floor | M5 |
| 100 pickup, north | `interactable/chestFree` | (31, 99), 9.5 | the west lane | north lane |
| 100 pickup, east | `interactable/chestFree` | (56, 99), 9.5 | the east lane | east lane |
| 100 pickup, south | `interactable/chestFree` | (82, 13), 0 | ground | M10 |

These are the `COLLECTIBLES` table in `scripts/build_thps_level.py`. Positions are the map's floating-icon positions mapped through the low-confidence pixel-to-metre conversion, nudged where the compressed structure layout (see "Building the level") moved the feature they belonged to:

- The chest, shrine and merchant prefabs are authored lying down (the prefab asset's euler X is 270), so a placement at rotation 0 renders them on their side. Items are placed at X 270, and the three lane items at 270 minus the 26.6 degree lane slope so they sit square to the ground.
- Every item stands on its surface rather than floating about one player height above it. A shrine or chest hovering in the air has nothing to rest on, so the letters are reached by jumping onto the structure, not by an air trick.
- R4 and the E shrine move onto the deck (the spec's E position at x 75 falls off the deck's west edge) and are split along it so they do not overlap.
- Letter T moves from (27, 64), which is inside the M6 pipe, to the 3 unit gap between M4b and M6.
- Box pile R5 stands on the west lane's low end at ground level instead of "under the north-east block"; the lane cell slopes one level over its 40 units, so an item on it uses `ground_height` (a slope of 20 units per 40, checked in game: the player settled at the predicted height).
- `forest/shrines/3` is the `ShadyGuy` prefab, the merchant NPC, not a shrine, and `forest/shrines/0` to `2` and `4` are the Challenge, Magnet, Maoi and Cursed shrines. The mapping stays one catalog entry per letter.

## Open questions and risks

- **Tape reach is unverified.** The corridor floor is at 13, above the 7.8 jump apex, and the harness can teleport the player but not move or jump it. The route is the lip of M6 (12 high, at x 24-44) with a running jump across the 5 unit gap to the corridor's east side (x 19), or the half pipe lip. Nobody has played it; if it fails the tape is the only collectible that needs a new ramp.
- **Interaction is only partly verified.** The collectibles spawn through the same catalog path as generated chests, and a player standing at the R5 chest shows the chest's 30 gold price label. Opening one needs the `Interact` key and gold, which the harness cannot send.
- **Shrine effects on the letters.** The mapping is confirmed, but shrines change a run when used, so whether the effect suits a letter is worth a look once they are placed.
- **Block choice.** The 4x3 block has to be chosen from a height dump of seed `20261007` to keep terrain edits small.
- **Generated clutter.** The seed spawns trees, rocks and shrines inside the block, which have to be removed with `RemoveObject` (`gen:` ids) or the block placed where there are few.
- **Rail grinding is unconfirmed.** `rail/0` and `rail/1` place and render at a scaled size, but nobody has grinded them in a run.
- **Climbing the new ramps is only partly verified.** A teleported player lands on every ramp and does not fall through, and rests on shallow slopes, but a run up each pipe and kicker at speed was only tried by hand on one test pipe.
- **The structure map itself is low confidence.** Box pile numbering, the start block's role and the exact positions are ambiguous in the source analysis; see its Unresolved list.

## Building the level

`levels/thps.mblevel.json` is generated, not hand-edited: `scripts/build_thps_level.py` writes it (`uv run scripts/build_thps_level.py`) and `tests/test_build_thps_level.py` covers the generator. `ThpsLevelTests` in `tests/MegabonkLevels.Tests` replays the saved file through `EditStack` and `ReachabilityValidator` and checks that every arena tile is reachable from the generated spawn cell. Regenerate and reload with `uv run scripts/build_thps_level.py` then `relaunch(level="levels/thps.mblevel.json")`.

What the file contains:

- A 3 tile by 4 tile arena at cells x 8-10, z 4-7, flat at height 0, wrapped by a one-cell ring at height 2 (cells x 7-11, z 3-8). Every other cell of the 15x15 grid is removed. Each kept cell gets an explicit `SetTileHeight` and `SetTileSlope`, so nothing depends on the generated heights.
- The raised north-east block (two cells at height 1) and the two slope cells that climb to it.
- Removal of every generator object except the spawn portal, the boss spawner and the particles, from the per-category counts the seed produces. The boss spawner is moved to world (170, 15.6, 27), scaled to 0.4 and turned 90 degrees so its arch faces down the corridor, so it fills the hanging glass box above the main half pipe, and its `BottomPiece` pillar mesh and the 43-unit-tall invisible `Collider` are hidden (`hiddenChildren` on the `object.move`); that collider otherwise reaches down into the pipe and blocks it. The box's size is estimated from screenshots, so the position and scale are tuned by eye.
- The three rails from the structure table. The ledge rail sits on the M2 platform top and the high rail on the M1 lip (`LEDGE_RAIL_HEIGHT`, `HIGH_RAIL_HEIGHT`).
- The sixteen placed structures in the table above, as `bundle:thps/<asset>` placements. The level records `packs: {"thps": "1.0.0"}`, so the version check in asset-bundles.md applies. The pack has to be installed (`task pack:thps`) and the game relaunched before the level loads with the structures; without it each placement shows a `Missing:` cube.

Deviations from the spec above, and findings:

- **Block position.** The player is placed at the generator's spawn (world (120, 2, -3), cell (10, 7)) before edits apply, and moving the spawn portal with `MoveObject` does not move the player. The arena therefore sits over cell (10, 7) at ground level, in the north-east corner next to the raised block, instead of anywhere in the grid.
- **Layout compressed.** The structures are placed from the map's pixel positions mapped through the same conversion as the collectible table, then moved by hand so no two overlap, nothing sits within 10 units of the player spawn, and every footprint stays in the arena (all checked by tests). The half pipe is shorter and lower than the video (6 high with a 10 unit flat), the channel pipes M6 to M8 stand on the flat strip south of the lanes instead of on the sloped lane cells (a flat-based pipe on a slope would half-bury itself), and the back pipe M9b stands on the deck.
- **Pipes stop at 40 degrees.** The real pipes go vertical; these end at about 40 degrees because the player cannot run up a face past 45. The curve is a fixed profile in `ThpsPack.cs`.
- **Decoration and glass skipped.** Doors, windows, pilasters, trusses, graffiti, cones, barricades, the plywood kickers by the big rail and the corridor's breakable glass are not built. Structures are flat-coloured: plywood, light plywood, concrete grey and taxi yellow, with no textures.
- **Dark pit omitted.** The removed cell would fall under the south 100 pickup and the S shrine at the 4.4 units per metre scale, and the structure is unidentified, so the pit is not built.
- **Flat-tile prefabs are whole tiles.** `forest/stage0/stageTilePrefabs/flat/7` placed a flat slab with a ruined stone tower and blocks, not a crate. The palette thumbnail was misleading. Do not use the flat-tile entries as props.
- **Rails.** `rail/0` and `rail/1` place with a `PlaceObject` and honour rotation and uniform scale. The big rail is `rail/1` at scale 0.75 and yaw 90, the ledge rail `rail/0` at scale 0.4 and the high rail `rail/0` at scale 0.5, 12 units up. The high rail floats until the west bank asset exists.
- **Editor camera.** In editor mode the editor owns the camera, so the harness `camera` command has no effect there. For screenshots call `editor(on=false)`, `freeze()` and then `camera(...)`.
- **Validate.** The editor's Validate button produces no visible result in the toolbar or the log on this level, so reachability is checked by `ThpsLevelTests` instead.
- **Save names.** The editor save writes to `UserData/Levels/<name>.mblevel.json`; use a new name so no existing custom level is overwritten.

### Check against the reference frames

Built overview (a high three-quarter shot of the arena) against frame 12, the intro flyover:

- Present: a closed, walled floor, the raised block with its two lanes at the north-east end, a rail in the middle, and the boss spawner ring in place of the start block.
- Missing: every ramp, deck, ledge, kicker, the half pipe, the taxi, the glass corridor and the doors, windows, trusses and graffiti, all of which need new assets.
- Different: the walls are 40 units of grass-and-dirt cliff under a bright sky, not stained concrete under a steel ceiling; the lighting and fog are Forest's; and the arena reads small and bare because the 4.4 units per metre scale puts a 2-3 m ramp at 9-13 units against walls of 40.
- Rails: the bent `rail/1` resembles the big rail's bend in frame 24, but it is a bare bar on short posts, with no platform, trench or barricades.
- Spawn: the player starts in the arena just east of the raised block on the same northern row, near where the start arrow is on the map, and the boss portal stands next to the spawn.

A run on the level starts and, over the first 30 seconds with the harness's invulnerability on, the player stays at spawn at ground level with enemies spawning around the arena and no kill floor event logged. A run without invulnerability was not played. One enemy was seen standing on top of a ring wall.
