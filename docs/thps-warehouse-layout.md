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

The player's jump force is computed from stats (`GetJumpForce`) and is not measured, so no reachable height is established. Working assumptions, to be confirmed by measurement before building:

- A plain jump clears about one player height (3.85 units), which is about 0.9 m at the chosen scale. Decks, ledges and low ramps are kept at or under this.
- Anything taller is reached by running up a slope, the same way the skater uses quarter pipes.
- The game has a `JumpPad`, `Ladder`, wall climbing and rail grinding (`railSpeed`, `canJumpOffRailTime`), so higher spots (the corridor, the high rail) can be reached through those if a ramp is not enough.

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

The ramps, ledges and decks above are the new-asset work. They need a collider the player can run on, which the asset pack route supports as a prefab (see asset-bundles.md), and they are not touched by the shader remap beyond a toon material.

## Collectible mapping (confirmed)

Confirmed as written: box piles are chests, letters are shrines, the tape and the three 100 pickups are free chests. The 4.4 units per THPS metre scale is confirmed too.

Collectibles stay as normal Megabonk items. The Forest palette has `interactable/chest`, `interactable/chestFree` and five shrines `forest/shrines/0` to `4`, which is exactly one shrine per letter.

| THPS item | Megabonk item | Block-local position (x east, z north, units) | Source position (thps-warehouse.md) |
| --- | --- | --- | --- |
| Box pile R1 | `interactable/chest` | (8, 34) on the west platform | M2 |
| Box pile R2 | `interactable/chest` | (61, 16) on the south notch ledge | M10 |
| Box pile R3 | `interactable/chest` | (98, 67) on the south-east ledge | M11 |
| Box pile R4 | `interactable/chest` | (83, 103) on the east deck | M9 |
| Box pile R5 | `interactable/chest` | (18, 140) under the north-east block | uncertain, see below |
| Letter S | `forest/shrines/0` | (84, 40) between the kickers | M12 |
| Letter K | `forest/shrines/1` | (33, 2) south-west corner | K |
| Letter A | `forest/shrines/2` | (34, 26) above the taxi | M3 |
| Letter T | `forest/shrines/3` | (27, 64) above the half pipe | M4 |
| Letter E | `forest/shrines/4` | (75, 103) east deck corner | M8, M9 |
| Secret tape | `interactable/chestFree` | (11, 67) in the corridor | M5 |
| 100 pickup, north | `interactable/chestFree` | (31, 99) | north lane |
| 100 pickup, east | `interactable/chestFree` | (56, 99) | east lane |
| 100 pickup, south | `interactable/chestFree` | (82, 13) | M10 |

Positions are the map's floating-icon positions mapped through the low-confidence pixel-to-metre conversion, at ground level. Heights follow the guide: letters and the tape are meant to be reached in the air, so their Y is the structure height plus about one player height (about 4 units) once the structures exist.

## Open questions and risks

- **Shrine effects on the letters.** The mapping is confirmed, but shrines change a run when used, so whether the effect suits a letter is worth a look once they are placed.
- **Jump height is unmeasured.** Every height rule above is an assumption. It needs a measurement of the player's jump on this build.
- **Block choice.** The 4x3 block has to be chosen from a height dump of seed `20261007` to keep terrain edits small.
- **Generated clutter.** The seed spawns trees, rocks and shrines inside the block, which have to be removed with `RemoveObject` (`gen:` ids) or the block placed where there are few.
- **Rail grinding is unconfirmed.** `rail/0` and `rail/1` place and render at a scaled size, but nobody has grinded them in a run.
- **New assets are the bulk of the work.** Eleven structures need a custom prefab; the asset pack route is proven for a cube and a four-part model only, and scripts cannot ship in a bundle.
- **The structure map itself is low confidence.** Box pile numbering, the start block's role and the exact positions are ambiguous in the source analysis; see its Unresolved list.

## Building the level

`levels/thps.mblevel.json` is generated, not hand-edited: `scripts/build_thps_level.py` writes it (`uv run scripts/build_thps_level.py`) and `tests/test_build_thps_level.py` covers the generator. `ThpsLevelTests` in `tests/MegabonkLevels.Tests` replays the saved file through `EditStack` and `ReachabilityValidator` and checks that every arena tile is reachable from the generated spawn cell. Regenerate and reload with `uv run scripts/build_thps_level.py` then `relaunch(level="levels/thps.mblevel.json")`.

What the file contains:

- A 3 tile by 4 tile arena at cells x 8-10, z 4-7, flat at height 0, wrapped by a one-cell ring at height 2 (cells x 7-11, z 3-8). Every other cell of the 15x15 grid is removed. Each kept cell gets an explicit `SetTileHeight` and `SetTileSlope`, so nothing depends on the generated heights.
- The raised north-east block (two cells at height 1) and the two slope cells that climb to it.
- Removal of every generator object except the spawn portal, the boss spawner and the particles, from the per-category counts the seed produces. The boss spawner is moved into the arena.
- The three rails from the structure table.

Deviations from the spec above, and findings:

- **Block position.** The player is placed at the generator's spawn (world (120, 2, -3), cell (10, 7)) before edits apply, and moving the spawn portal with `MoveObject` does not move the player. The arena therefore sits over cell (10, 7) at ground level, in the north-east corner next to the raised block, instead of anywhere in the grid.
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
