# Runtime map structure

Required reading for level format and runtime editing/playback work. Answers, with concrete type/field names confirmed against the running game (CrossOver/macOS, game build 1.0.69), where the tile grid lives, what drives its spacing, whether a navmesh is baked, and how to index generator-spawned objects.

All runtime values below come from extending the mod (`src/MegabonkLevels.Mod/grid_shape_patch.cs`, `navmesh_patch.cs`), hooked into `MapGenerationController.A_GenerationComplete`, then observing `MelonLoader/Latest.log` across a Forest run, a Desert run, and a Graveyard run (which also triggers the crypt/boss dungeon). See [map-generation-determinism.md](map-generation-determinism.md) for the companion seed-determinism findings.

## 1. Where the tile grid lives

`ProceduralTileGeneration.proceduralTiles` is `Il2Cpp.ProceduralTile[][]` — a **dense, fully-populated jagged array**, not sparse, for `Tiles`-type maps (`EMapType.Tiles`, `mapType=0`):

| map | `MapParameters.size` | `proceduralTiles.Length` | row length | occupied cells | `tiles.Count` |
| --- | --- | --- | --- | --- | --- |
| Forest | 15 | 15 | 15 (uniform) | 225 | 225 |
| Graveyard | 19 | 19 | 19 (uniform) | 361 | 361 |

Every row has the same length (`size`), and every cell in every row is non-null (`occupiedCells == size * size == tiles.Count`) — it's a complete `size x size` grid, no holes. `ProceduralTileGeneration.tiles` (the `List<GameObject>` already hashed for the determinism check) is exactly the flattened, deduplicated contents of this grid for the tiles that exist post-generation.

`flatTiles` and `fillTiles` are **separate lists, not subsets of `proceduralTiles`** — they hold additional GameObjects (flat-ground variants and wall/edge fill pieces from `FillHoles()`/`FillEdges()`/`FillWallSlopeToFlat()`) that get attached around/between the base grid tiles. Their counts (Forest: 179 flat / 226 fill; Graveyard: 231 flat / 387 fill) don't equal `tiles.Count` and shouldn't be assumed to.

**`ProceduralMesh` maps (Desert, `mapType=1`) don't use this grid at all.** On a Desert run, `ProceduralTileGeneration.proceduralTiles` is `null` and `currentStage`/`currentMapParameters` are both `null` — `ProceduralTileGeneration.Generate()` is simply never called for this map type. Desert's terrain comes from `MapGenerationController.proceduralMapMeshGenerator` (type `MapGenerator`), which builds a heightmap-based mesh via `GenerateMap(MapData, StageData, int seed = 105)` and exposes `heightMap`/`worldScale`/`mapChunkSize` instead of a tile grid. Its seed isn't controlled by the `debugSeed` force that works for Tiles maps — this `seed` parameter on `MapGenerator.GenerateMap` is the likely real control point, unconfirmed/untried.

**Gotcha for editing code:** any edit-application code that assumes "the map is a `proceduralTiles` grid" must branch on `EMapType` first. Only `Tiles` maps (Forest, Graveyard, and presumably other `Tiles`-type stages) have this grid; `ProceduralMesh` maps are edited as objects only: the editor raycasts `MapGenerator.mesh`'s `MeshCollider` and places objects at the hit point in world space (see "Object tools" in development.md).

### Accessing fields that look private

`ProceduralTileGeneration.currentStage` and `.currentMapParameters` are declared `private` in the Il2CppDumper output, which looked like it would require reflection. It doesn't: **Il2CppInterop generates these as public C# properties** backed by native field-offset reads (see the real `MelonLoader/Il2CppAssemblies/Assembly-CSharp.dll`, not the `.tools/il2cpp_dump/DummyDll` declarations-only dump). Read them directly — `tileGen.currentMapParameters`, `tileGen.currentStage.mapParameters` — no `BindingFlags.NonPublic` needed. (A first attempt at this task used reflection against the DummyDll's private-field declaration and silently got `null` every time; that was the bug, not an actual access restriction.)

## 2. Tile spacing source

`StageData.mapParameters` (type `Il2CppAssets.Scripts.MapGeneration.ProceduralTiles.MapParameters`) is confirmed as the authoritative spacing source for `Tiles` maps, cross-checked against measured transform distances on two stages:

| map | `tileWidth` | `scale` | `scaledTileWidth` (= tileWidth × scale) | measured world distance between adjacent grid cells |
| --- | --- | --- | --- | --- |
| Forest | 2 | 20 | 40 | **40.0000** |
| Graveyard | 2 | 20 | 40 | **40.0000** |

Measurement method: walk `proceduralTiles[x][y]` vs `proceduralTiles[x+1][y]` for the first pair of adjacent non-null cells, take `|Δworld.x|`. Exact match, both stages, within float precision. **`scaledTileWidth` is the real-world planar grid step — use it, not `tileWidth` or `scale` alone, and never hardcode a spacing constant.**

`scaledTileHeight` (= `tileHeight × scale` = 1 × 20 = 20) was *not* independently cross-measured — based on `MazeHeightGenerator.GenerateHeight` existing specifically to vary tile elevation, `tileHeight`/`scaledTileHeight` almost certainly control the **vertical (Y) step per height level** in the terraced terrain, not a second planar axis. The grid is square in the X/Z plane (both axes step by `scaledTileWidth`); don't assume `scaledTileHeight` is a Z-axis spacing value without checking a map with visible multi-level terracing.

## 3. NavMeshSurface

**Confirmed at runtime: a navmesh is baked, but only for the crypt/graveyard boss dungeon — never for the open Tiles/ProceduralMesh maps.**

Static analysis first: across the entire decompiled `Assembly-CSharp`, exactly one type references `Unity.AI.Navigation.NavMeshSurface` — `RsgController.navmeshSurface`. `RsgController` ("Rsg" = room/piece-based dungeon generator) is the crypt/boss-dungeon generator (`roomBoss: GraveyardBossRoom`, `rsgEnd: InteractableCryptLeave`), wired into `MapGenerationController` via `cryptParent`/`cryptExitOutside`/`rsgController`/`CryptGeneration(int seed, ...)` — **it is not a third `EMapType`** (`EMapType` only has `Tiles` and `ProceduralMesh`); the crypt is a side-dungeon generated alongside/within a normal map. `EnemyMovementRb` (the main enemy movement component) has no `NavMeshAgent`-shaped fields at all — it's direct `Rigidbody`-based chase (`desiredVelocity`/`desiredRotation` toward the player) — confirming the open maps never needed a navmesh.

Runtime confirmation (Harmony postfix on `Unity.AI.Navigation.NavMeshSurface.BuildNavMesh`, `navmesh_patch.cs`):

```text
[MegabonkLevels] NavMesh: BuildNavMesh() called on 'RSG_Controller'
[MegabonkLevels] A_GenerationComplete: map=MapGraveyard mapType=0 ...
```

`BuildNavMesh()` fired once, on the `RSG_Controller` GameObject, ~0.5s before the enclosing `MapGraveyard` map's own `A_GenerationComplete`. No `BuildNavMesh()` call was logged during either the Forest or Desert runs — the hook was live and working (same build) for all three, so its silence on Forest/Desert is a real negative result, not a gap in instrumentation.

**Rebuild trigger for a future mod:** call `rsgController.navmeshSurface.BuildNavMesh()` directly. That's the literal method the game calls, now proven reachable and safe to invoke.

**Gotcha — do not Harmony-patch `RsgController.Generate`:** an attempt to add a Harmony prefix/postfix on `RsgController.Generate(int, EDungeonType, out float)` to log crypt generation caused a `NullReferenceException` inside the IL2CppInterop native→managed trampoline on every crypt entry, hanging the game at a black screen, reproduced twice. The crash fired *before* the prefix's own log line, with a try/catch-wrapped postfix, ruling out the patch body itself — it's the Harmony detour/trampoline on that specific signature (the `out float` parameter combined with the `EDungeonType` enum is the likely culprit, unconfirmed). Removing that one patch (keeping only the `NavMeshSurface.BuildNavMesh` hook) fixed it; the crypt loads normally. **Don't Harmony-patch this method** — call into `RsgController` instance members directly instead if a future task needs to trigger regeneration.

## Slope tiles and editing the grid

Slope tiles are the `ProceduralTileGeneration.slopeTile` prefab (`TileSlope`), flat tiles the `flatTile` prefab (`TileGround`); both are public fields. On a slope `ProceduralTile.isFlat` is false and `dir` points uphill, with the tile's yaw following it: `dir` (0,0,1) is euler Y 0, (1,0,0) is 90, (0,0,-1) is 180, (-1,0,0) is 270. `posY` is the lower edge's level and the uphill neighbour is at `posY + 1`. `ProceduralTileGeneration.InstantiateTile(Vector2Int pos, int height, GameObject prefab, Vector3 dir, Vector3 parentDir)` is public and places a tile at `origin + pos * scaledTileWidth` in X/Z and `height * scaledTileHeight` in Y (Forest cell (9,7) lands at (80, h*20, 0)); the mod's applier assigns the returned tile's `ProceduralTile` to `proceduralTiles[x][z]` and updates `tiles` itself rather than relying on `InstantiateTile` to do it.

Generated tiles may be statically batched. Moving their transforms does **not** move their rendered surfaces: a raised tile can retain render bounds at its old height even though rebuilt collision moves correctly, leaving actors apparently floating on missing ground. The live applier checks `Renderer.isPartOfStaticBatch` and replaces batched tiles with fresh flat/slope prefab instances instead of moving them. Unbatched tiles with unchanged slope can still move directly; slope changes always replace the tile. Old instances are deactivated before destruction so neither rendering nor collision retains the stale surface.

## Navigation after edits

Open `Tiles` and `ProceduralMesh` maps bake no navmesh, and `EnemyMovementRb` chases the player with `Rigidbody` velocity, so editing the grid needs no navigation rebuild: enemy movement is physics on whatever collider is there. The ground collider is baked once and is rebuilt after edits (see below), so a tile removed with `RemoveTile` is a real hole, and the kill floor ends a fall into it. Whether enemies get stuck on edited terrain in a real run is unconfirmed: it needs a playthrough with enemies, which the harness cannot drive. The only `NavMeshSurface.BuildNavMesh()` call is the Graveyard crypt (`RsgController`), a separate dungeon that tile edits do not touch. If enemies ever need to avoid holes or edited terrain actively, that would be new behaviour, not a rebuild step.

## Ground collision after edits

All ground collision is one baked mesh, `ProceduralTileGeneration.collider` (a GameObject named `CombinedCollisionMesh`, 413 vertices on Forest seed 20261007), built at generation time by the public static `MeshColliderCombiner.CombineMeshes(List<GameObject>)`. The game then strips the per-piece `MeshCollider` from every live tile, wall and fill piece, so they have none left to read. Edits alone therefore left the old collision in place: a removed tile kept an invisible floor, and a raised or added tile had only a small collider of its own, so a ray straight down over the removed Forest cell (13,7) still hit `CombinedCollisionMesh` at y=0.

`CollisionRebuild.Replace` rebuilds it after tile edits. For each live piece in `tiles`, `flatTiles` and `fillTiles` it matches the prefab by name (`flatTile`, `slopeTile`, `wallFlat`, `wallLeftUp`, `wallLeftDown`, `wallLeftCross`), attaches that prefab's collider mesh as a temporary `MeshCollider`, runs the game's combiner, destroys the temporary colliders, and swaps the result into `collider`. Running the same rebuild on an unedited level reproduces the original mesh exactly (413 vertices, identical bounds), which is how the piece set was validated. Pieces deactivated by an edit must be skipped because `Destroy` only takes effect at the end of the frame, so `RemoveTile` and tile replacement deactivate the object and drop it from `tiles` and `flatTiles` as well as destroying it. After the rebuild, straight-down rays on the scratch level hit the slope at y=10 (the midpoint of a level 0 to 1 ramp), the added tile at y=20, and nothing but the world floor over the removed cell. The editor's tile tools apply one edit per click through the same path, so each click regenerates the fill around that cell and rebuilds the whole collision mesh. On Forest (about 600 pieces) a click shows no visible delay. The tools also raycast against this mesh to find the targeted tile, since the tiles themselves have no colliders.

## Walls after edits

Whole-grid `FillHoles`/`FillEdges` would duplicate pieces everywhere, so the mod uses the per-edge private `ProceduralTileGeneration.FillHole(Vector2Int from, Vector2Int to)` through reflection. Calling it from a vanilla slope cell to each of its four neighbours recreates exactly the four wall pieces generation had built there (`TileWall` below, `TileWallSlopeLeftDown` on the slope sides, same positions, rotations and scales).

`FillRegeneration.Regenerate` runs after tile edits and before the collision rebuild, for both level-file edits and editor clicks (including undo/redo). `FillEdgePlan.EdgesAround` selects occupied–occupied edges for `FillHole` in both directions; `EdgesAroundRemovals` selects occupied–empty edges for `FillEdge` on the occupied side, directed toward the hole. This also rebuilds walls when an occupied tile beside an existing hole changes. The cleanup set includes empty–empty edges between adjacent removals and exterior edges of removed border cells; unchanged exterior cliffs of occupied cells are left alone.

For each affected edge the mod destroys fill pieces whose position lies on the edge line (within 0.5 units, and within half a tile along it). Midpoints come from `TilePositionToWorldPosition(Vector2Int.zero)` and grid spacing, not nullable tile transforms. Pieces are removed from `fillTiles` and deactivated before destruction, so deferred Unity destruction cannot include them in the collision rebuild. New pieces are appended to `fillTiles`; the genId index is built before the edits, so the ids of existing objects do not move.

### Confirmed `FillEdge` parameters

Native code read with REA's Ghidra provider confirms `FillEdge` (RVA `0x51DCC0`), `FillEdgesIsland` (`0x51E4D0`), and `FillEdgesWalls` (`0x51EAE0`) use the following contract:

| Parameter | Meaning |
| --- | --- |
| `pos1` | Occupied grid cell owning the edge. The method reads its tile and `GetEdge` result; neither may be null. |
| `desiredHeightOffset` | Signed vertical extent in tile-height levels, not an absolute target height. For a flat edge, positive values stack upward from `tile.posY + edge.offsetHeight`; negative values stack downward from one level below that height. Zero creates no flat wall. |
| `isFacingOut` | If false, negate `dir` before edge lookup and construction. If true, use `dir` unchanged. Negative extents additionally reverse the piece direction while retaining the selected edge. |
| `dir` | Cardinal grid direction of the selected edge after the conditional negation; resolved with `tile.GetEdge(dir)`. |
| `useEdgeTextures` | Forwarded to `InstantiateFillTile` for the wall pieces; false uses normal textures. |

Sloped edges use `wallLeftUp` or `wallLeftDown` according to the extent's sign and a flip flag according to slope handedness, with flat pieces extending the wall. Even a zero extent can emit a slope cap; it is not a universal no-op. `FillHole` computes its signed height difference from both tiles' `posY + edge.offsetHeight`, but cannot accept a missing tile.

For holes the mod mirrors `FillEdgesIsland`: `desiredHeightOffset = minimumLivePosY - 1 - occupiedTile.posY`, `isFacingOut = true`, `dir = emptyCell - occupiedCell`, `useEdgeTextures = false`. This guarantees downward walls even for same-height neighbours. The removed tile's former height is not needed. The game's enclosed-map border builder, `FillEdgesWalls`, instead uses `maximumPosY + 2 - tile.posY`, false, an inward direction, and edge textures to build upward-extending perimeter walls.

Verified on Forest seed 20261007: removing the edited East slope at (9,7) through the editor removes eight stale pieces and builds four hole-facing edges. Flat removal at (11,6), undo, and redo also rebuild correctly; straight-down probes against the rebuilt combined mesh miss the hole. `levels/removed-tile-regression.mblevel.json` exercises load-time removal at (9,7), (13,7), and adjacent border cells (0,0)/(0,1). Screenshots show continuous side walls up to the occupied edges, with sky visible only down the open shaft, not through missing side faces; downward collision probes miss all four removed cells. Generated props are not terrain pieces and can still overhang a hole.

## Kill floor

The game has its own catch floor: a `WorldCollider` (`WorldColliderTrigger`) at y=-80 whose mesh bounds read as a 1x1x1 box, so its height is taken from its transform. A body that falls through a removed tile rests there. In a level loaded by the mod, `KillFloorWatcher` checks every quarter second and kills anything below the kill floor, as in Super Mario Bros: the player through `MyPlayer.Instance.inventory.playerHealth.KillPlayer()`, and enemies through `Enemy.Kill("KillFloor")` over `EnemyManager.Instance.enemies` plus the manager's private `stageBosses` list.

`KillFloor.FloorY` puts the floor 40 units below the lowest live tile level, raised to at least 8 units above the catch floor so a body resting on it still counts as fallen. A level can author the height instead through its `killFloorY` field (`KillFloor.FloorYExplicit`, which applies the same catch-floor clamp), which is what a level needs when it has removed nearly every tile: with one hidden tile left, the derived height sits 40 units below it, deep enough for a body to come to rest on placed geometry above it and stay unkillable. `Arm` logs which it used: `KillFloor: armed at y=-35 (authored, catch floor y=-80)` or `... (derived from tiles, catch floor y=-80)`. The watcher arms after generation when a level file started the run, and disarms on any other generation. Verified in the game with a level that removes every tile but one: the log shows `KillFloor: armed at y=-40` and `player fell to y=-48.49, killing`, and the run ends on the death screen. Enemy kills are observed in a playthrough of a level with a removed tile: 67 distinct enemies were killed in about three minutes. A killed enemy stays in `EnemyManager.enemies` for a while, so `KillTracker` (pure logic) skips an actor for 2 seconds after a kill and then retries it with a higher attempt number, which the log marks as `still present`. Without it the same enemy was killed on every check, about seven times on average. The stage boss (Forest, Lil Bark) is in `stageBosses` and also in `enemies`, under the same `Enemy1(Clone)` name as every other enemy, so only its id identifies it. The earlier watcher compared the transform pivot with the floor, and a tall actor never crossed it: Lil Bark's pivot rested at about y=-66.5 on the catch floor (y=-80), about 5 above the floor at -72, and he climbed back out of the hole alive; a golem showed the same. The watcher therefore compares `KillFloor.LowestPoint`: the lower of the pivot and the bottom of `Enemy.collider` (a `CapsuleCollider`, enabled only). This killed the Forest stage boss in a playthrough: the boss's pivot was at y=-63.4 and its lowest point at y=-76.3 when it was killed, once, with no retry. An optional heartbeat line every 5 seconds (`KillFloor: watch ...`, off by default; see "Kill-floor heartbeat" in [development.md](development.md)) reports the enemy and stage boss counts, the lowest point each group reached, and the boss ids, so a boss that never reaches the floor can be told apart from one that is not scanned.

## 4. `genId` scheme

The Tiles terrain snapshot repeats with a fixed `debugSeed`; this does not guarantee every generated object's transform or identity repeats (see [map-generation-determinism.md](map-generation-determinism.md) and the measured repeat behaviour below). The live index built at `A_GenerationComplete` had the same categories and counts on repeat loads of Forest seed 20261007: 225 tiles, 160 flat, 203 fill, 39 tile objects, 1474 indexed in total. Each generated object gets an order-based id within that generation; equal counts alone do not prove that an id refers to the same object and transform across generations:

```text
{category}:{sequentialIndexWithinCategory, 4 digits, zero-based}
```

Sources are walked in the order the game populated them, never sorted. Where each category lives in the live scene (`GeneratedMap`):

| category | source | example id |
| --- | --- | --- |
| `tile` | `ProceduralTileGeneration.tiles` | `tile:0042` |
| `flatTile` | `ProceduralTileGeneration.flatTiles` | `flatTile:0017` |
| `fillTile` | `ProceduralTileGeneration.fillTiles` | `fillTile:0203` |
| `tileObject` | children of `GenerateTileObjects.tileObjectsParent` (`TileObjectsParent`), in sibling order | `tileObject:0001` |
| `object:{prefabName}` | scene-root GameObjects named `<prefab>(Clone)` that come after the `TileObjectsParent` root, grouped by name in root order | `object:Tree0:0003`, `object:Chest:0000` |
| `scenery:{name}` | scene-root GameObjects after the `TileObjectsParent` root whose name does not end in `(Clone)`, grouped by name in root order; tile prefab decoration such as ruined towers, crates, cubes, pillars and dead trees (`Castle`, `Crate (2)`, `Ruins (1)`, `Tree`). `FogOfWarSphere` is the one such root left out of the index (`SceneRootCategory`) | `scenery:Castle:0003`, `scenery:Crate (2):0000` |

The `object:` category covers everything `RandomObjectPlacer` and `SpawnInteractables` spawn: trees, bushes, rocks, logs, pots, chests, shrines, the boss spawner and the player spawn portal. `RandomObjectPlacer` and `SpawnInteractables` have no children and expose no result list; their output is parented to the scene root, so the root order is the only record of spawn order. The prefab name is the cloned GameObject's name (no `RandomMapObject` name field exists). The index is a snapshot taken at `A_GenerationComplete`; objects the game creates later (enemies, projectiles, pickups) are not in it.

A tile's world position is `origin + (x, z) * scaledTileWidth` with Y at `posY * scaledTileHeight` (Forest: grid cell (0,0) at world (-280, -280), `posY=1` at Y=20). `PlayerSpawnPortal` in the Forest test seed sits at (120, 0, 0), i.e. grid cell (10, 7).

**Caveat:** only confirmed for `Tiles`-type maps (Forest, Graveyard). `ProceduralMesh` maps (Desert) have no confirmed-controllable seed yet (see §1), so the scheme is unverified there.

## Minimap components

The HUD minimap is a camera rendered to a texture and shown in a circular mask. Confirmed against the IL2CPP dump and by dumping the live hierarchy in a mod-loaded Forest level.

UI side, under `GameUI/GameUI/HUD/Minimap` (a `RawImage` with the `MinimapUi` component, 175x175 canvas units, anchored to the top-right corner):

- `MapRenderer` (`RawImage` with a `Mask`, circle sprite `256Circle`) holds `RenderTexture` (`RawImage` showing the 256x256 render texture `MinimapTexture`) and `Jammer` (`RawImage`, `MinimapJammed`, `MinimapUi.jammer`).
- `Border` (`RawImage`, `MinimapBorder`) holds four `TextMeshProUGUI` direction letters `N`, `S`, `E` and `W`, exposed as `MinimapUi.directionLetters`. `MinimapUi` rotates them as the camera yaw changes (`OnRotationUpdated`), and its scale follows the `minimap_size` setting.

World side:

- `MinimapCamera` (namespace `Assets.Scripts.Camera`) exists twice. The one on `Player/MinimapCamera` drives the HUD minimap: orthographic, size 110, rendering into the 256x256 `MinimapTexture`, culling mask 16384 (layer 14). Its `minimapCamera` follows the player at a fixed height (about y=1000) and looks straight down, so the player is always at the centre. The one on `MapCamera` is orthographic size 300 into a 1024x1024 texture at (0, 1000, 0), so it covers the whole 600x600 map; it is presumably the full-map view.
- `MinimapMesh` (`meshRenderer`, `meshFilter`; `Set(Mesh, Color fogColor)`) is the map drawn for those cameras, centred on the origin with bounds of 600x600 in x and z.
- The player marker is `MinimapCamera.playerIcon`, the object `Player/MinimapIcon`, which moves with the player and is drawn by the minimap camera like any other layer-14 object (`MinimapPlayerIcon`, `MinimapIcon`).
- Enemy markers are icon objects made by `AddEnemyMinimapIcon(Enemy, Material, float)` from `enemyIconPrefab` and tracked in `enemyIconDictionary` (`Dictionary<Enemy, GameObject>`), updated by `UpdateEnemyMinimapIcons`. Boss and portal arrows are `Assets.Scripts.Camera.MinimapArrow` objects (`target`, `Set(Transform, Color)`) tracked in `arrowDict`. Pickups, chests and shrines carry their own `minimapIcon` object.

## Minimap coordinate mapping

The HUD minimap camera is orthographic with size 110, so the view spans 220 world units across the 256-pixel render texture (about 1.16 pixels per unit), and the circular mask crops it to the same diameter. Its position tracks the player's x and z exactly (a player at (120, 1.92, 3) had the camera at (120, 1000.93, 3)), so the player icon is always at the centre of the minimap. The camera looks straight down and is rotated about the vertical axis; in the default dynamic orientation (`MinimapCamera.staticOrientation` false) the yaw presumably follows the game camera (observed: 180, with `S` at the top) and the `N`/`S`/`E`/`W` letters turn with it, and a static orientation presumably uses `staticRotation`.

For a world point `p` and the player at `q`, the offset from the minimap centre is `((p.x - q.x), (p.z - q.z))` rotated by the camera yaw and scaled by `128 / 110` render-texture pixels per world unit. The mapping is therefore recoverable in both directions, but the minimap is a local view: it never shows where on the map the player is, only what is within 110 units. A position or grid cell readout cannot be read off the minimap itself and has to come from the player's transform.

The second `MinimapCamera` on `MapCamera` (orthographic size 300, 1024x1024, at (0, 1000, 0) with rotation (90, 0, 0)) is not player-centred: one world unit is 1024 / 600 pixels and world (0, 0) is the centre of the texture. Where that texture is displayed in the HUD was not located.

## Minimap label verdict

A text label for the player's world position and grid cell on the minimap is viable. The minimap root (`MinimapUi`, found with `FindObjectOfType`) is an ordinary canvas `RawImage` whose siblings and children are `TextMeshProUGUI` labels, so a mod can instantiate one of the existing direction letters (`MinimapUi.directionLetters[0]`, which brings the game's font asset and material) as a child of the minimap root, anchor it below the circle and set its text from the player's transform. The label must not be parented to a direction letter or to `Border`'s letters, because `MinimapUi` rotates those with the camera. The position comes from the player transform, not from the minimap (see the coordinate mapping above).

Cost: about 50 to 70 lines (find the minimap, clone and place the label once per level, update the text a few times a second), plus the `UnityEngine.UI`, `UnityEngine.UIModule` and `Unity.TextMeshPro` assembly references. The world-to-cell conversion and the text formatting are pure logic and can be unit tested.

Risk of breaking on a game update: low to moderate. It depends on `MinimapUi` and its public `directionLetters` field, which would have to be renamed or removed to break it, and on the HUD staying a canvas with TextMeshPro labels. A failure should be contained by a null check that logs once and draws nothing. The `GameUI/GameUI/HUD/Minimap` path was only used to confirm the hierarchy and should not be relied on. This verdict is from reading the hierarchy; whether the cloned label renders legibly at the minimap's size is confirmed when it is built.

## Replacing generation for from-scratch levels

Findings from Ghidra on `GameAssembly.dll` (game build 1.0.69): `MapGenerationController.<GenerateMap>d__39.MoveNext` (RVA 0x4A26F0), `ProceduralTileGeneration.Generate` (0x5208A0), `GetWorldSize` (0x521320), `GetWorldCenter` (0x5210B0), `ClearTiles` (0x51DBA0) and `GenerateTileObjects.Generate` (0x495870). Field offsets come from `dump.cs`. A throwaway patch confirmed the result in the running game (see "Dynamic proof").

### What `Generate` sets

Besides `proceduralTiles` (0xB8) it sets `currentStage` (0x88) and `currentMapParameters` (0x90) from its arguments, and allocates the `tiles` (0x68) and `flatTiles` (0x70) lists. It calls `ClearTiles` first, which destroys every object in `tiles`. It writes the seed into `debugSeed` (0x20), runs the generator, then `FillHoles`, then one of `FillEdgesIsland`, `FillEdgesWalls` or `FillEdgesTrees` chosen by `StageData.mapEdgeFillType` (0x28); `None` (3) runs none of them. It destroys and rebuilds `collider` (0x80) from the combined tile and fill meshes, creates a new `tilesParent` (0xB0), re-parents every tile and fill tile under it and static-batches it. It returns the start tile's world position (x/z of the start cell scaled by `scaledTileWidth`, y 0) and writes the start tile's direction to the `out firstTileDirection`.

`GenerateMap` stores the returned position and direction into the static `tileSpawnPosition` (backing field 0x14) and `tileSpawnDir` (0x20), keeps both locally for the spawn portal, and reads `collider`'s mesh as the world mesh handed to the minimap builder. If `collider` is null `GenerateMap` throws, so a replacement must leave a `collider` object with a mesh.

### Skipping the object phases

`GenerateMap` calls `GenerateTileObjects.Generate(RandomTileObjects, flatTiles, stageData)` and later `interactablesSpawner` `SetArea`, `SpawnRails` (0x49D840), `SpawnChests` (0x49CF60), `SpawnShrines` (0x49E180) and `SpawnOther` (0x49D4F0), in that order, and `randomObjectPlacer`'s private `RandomObjectSpawner` (0x49C2A0) for each `StageData.randomMapObjects` entry, the shrine entries and the `MapData` overrides. None of the return values are read, so a prefix that returns false on each is a localized patch and `GenerateMap` still runs on to `A_GenerationComplete`. `RandomObjectPlacer.GenerateInteractables` (0x49C020) is not called from `GenerateMap`. `GenerateTileObjects.Generate` is the one phase with side effects `GenerateMap` depends on: it creates the boss spawner (below), so skipping it means the mod must place the boss spawner itself.

### Spawn portal, platform, boss spawner and boss portal

For `EMapType.Tiles` the spawn portal (`spawnPortal`, 0x58) is instantiated in the first `MoveNext` state, right after `Generate` returns, at the returned spawn position with the rotation `LookRotation(-spawnDirection)`. `spawnPlatform` (0x68), `bossPortal` (0x60), `bossPortalFinal` (0x70) are instantiated only in the `EMapType.ProceduralMesh` branch (a raycast down from above the world, up to 50 attempts); a Tiles map never uses those three fields. The boss spawner is instantiated by `GenerateTileObjects.Generate` from `bossSpawner` (0x28), or `bossSpawnerFinal` (0x30) on the final stage, on a random flat tile popped from the `flatTiles` copy, with that tile's position and rotation.

The boss portal on a Tiles map is part of the boss spawner prefab, not a separate placement: `GenerateMap` has no code that positions it. A from-scratch level therefore authors one position, the boss spawner's, and the portal follows it. This agrees with the Warehouse's boss portal being fixed inside its glass box until the spawn redirect moves the boss itself.

### What sizes the catch floor, minimap, edges and grass

World size comes from map parameters and tile heights, not from the grid array: `GetWorldSize` returns `(size * scaledTileWidth, maxY - minY, size * scaledTileWidth)`, where `size` and `scaledTileWidth` are read from `currentMapParameters` and `maxY`/`minY` are the tile `transform.position.y` extremes across the `tiles` list. `GetWorldCenter` returns `(0, minY + (maxY - minY) / 2, 0)` from the same heights. An empty `tiles` list does not throw but gives a nonsensical height range.

- Catch floor (`colliderBox`, 0x50): scaled to `worldSize * 1.55` on every axis with `worldSize.y + 200` as the height input, centred `20 + worldSize.y / 2` below `worldCenter`.
- Minimap: the static bounds are set from `worldCenter` and `worldSize` (minimum `center - size / 2`, maximum `center + size / 2`), and `minimapMesh` is built from the `collider` mesh.
- Map edges: `MapEdges.Set` (0x499B80) runs only when `mapEdgeFillType` is `None`, with `worldCenter` and `worldSize`.
- Grass: `grassRenderer` is given the stage grass material and `grassPerChunk` only; its placement is not derived from these values in `GenerateMap`, so how it samples the world is unconfirmed.

A from-scratch level with a small grid must therefore hand `Generate` a cloned `MapParameters` whose `size` matches the authored grid, or the catch floor and minimap stay sized for the stock map.

### Dynamic proof

A throwaway patch replaced `Generate` with a prefix that builds a 5x5 flat grid from a cloned `MapParameters` (`size` 5), reuses `CollisionRebuild` for the collider and returns the centre tile as the spawn position. Further prefixes skipped `GenerateTileObjects.Generate` (placing only the `bossSpawner` prefab on a corner tile), `SpawnChests`, `SpawnShrines`, `SpawnRails`, `SpawnOther` and `RandomObjectSpawner`. Loaded through `relaunch` with the Forest example level, `Latest.log` showed:

- `CollisionRebuild: combined 75 pieces`, then `A_GenerationComplete: ... tiles=25 flatTiles=50 fillTiles=0 ... objects=0`, so `GenerateMap` ran to the end with no generated props.
- `GridShape: proceduralTiles.Length=5 rowLengths=[5] occupiedCells=25` and `MapParameters size=5 ... scaledTileWidth=40`.
- `KillFloor: armed at y=-12 (derived from tiles, catch floor y=-20)`.
- The harness state put the player at cell [2,2], the returned spawn cell, and `query_objects` found one `PlayerSpawnPortal`, the cloned `BossSpawner`, and the same count of `InteractablePortal` (`PortalBlue`) objects as `InteractableBossSpawner` objects (3 each: the clone and the two spawner prefabs), consistent with the boss portal being part of the spawner prefab.

`flatTiles=50` against `tiles=25` shows `ProceduralTileGeneration.InstantiateTile` already appends to `flatTiles`; the patch added each tile a second time. Not checked: grass placement, and the minimap content (the minimap rendered but was not inspected). The view shows a teal tint and tall translucent walls around the grid that were not investigated.

### Verdict

Go. Replacing generation needs only localized patches: one prefix on `Generate` that builds the authored grid, the `collider`, the cloned `MapParameters` and the returned spawn position and direction, plus a one-line skipping prefix on each object phase. The mod must place the boss spawner itself because it skips `GenerateTileObjects.Generate`. If a later change needs more than that, the fallback is to generate the stock map and clear it in one step.

### Shipped load path

Authored grids build their cliff faces before baking collision. The from-scratch
builder passes every occupied cell to `FillRegeneration` with `includeExterior`
enabled: shared edges use the native `FillHole` calls, while
`FillEdgePlan.ExposedEdges` includes sparse holes and the outer grid boundary.
Exposed faces extend downward to one level below the lowest authored tile.
Tile, flat and fill pieces are parented together and included in the collision
bake. The normal edit path leaves unchanged outer cliffs alone. Omitting this
initial fill pass leaves raised tiles and ramp sides visibly open to the sky.

The "go" verdict is implemented in `from_scratch_generation_patch.cs`; [development.md](development.md#from-scratch-level-load-path) describes the load path and its log lines. Earlier verification, before the initial fill pass was added, reported `tiles=49 flatTiles=48 fillTiles=0 objects=0` for `levels/from-scratch-fixture.mblevel.json`'s 49 authored cells. `InstantiateTile` appends to both tile lists itself and the patch must not. That run had `MapParameters size=7`, one `TileSlope(Clone)` and 48 `TileGround(Clone)` objects, no `(Clone)` chests, and the player at the authored spawn after both loading and a death-screen restart. A summoned boss walked across the grid. With initial fill enabled, Bramblecrown Hill's 225 cells log `420 edge(s), 60 hole edge(s)` and create 383 fill pieces on the tested game build. The teal tint, translucent map boundary and grass placement remain native behaviours rather than authored scenery.

## Stage parameter interpretation

Measured Forest stage assets use the same generator strategies but different grid metrics and prop sets: stages 1, 2 and 3 have size/scale pairs 15/20, 15/22 and 16/24. They are not merely re-skins at identical dimensions. Stage 1 has two bush groups instead of one, with `Bush1` aligned to the surface normal, and ten fewer logs than stages 2 and 3.

The measured Desert asset's fixed `NoiseData.seed` (257) is a field value, not proof that runtime noise offsets use it instead of the generator's seed argument. See [Procedural-mesh maps](map-generation-determinism.md#procedural-mesh-maps-desert-hell) for the decompiled seed path. Repeated snapshots alone do not establish which seed controls the terrain.

## 12. Tier 2 stage identity and per-stage generation parameters (measured)

Everything in this section was read from the running game (offline Wine prefix, game build 1.0.69) with `query-objects --depth`, the read-only asset query described in [development.md](development.md#querying-live-objects). `depth` makes the query walk nested `UnityEngine.Object` references and collections instead of printing their `ToString()`, so one call returns a whole `MapData` with its `stages`, `MapParameters`, `NoiseData` and `TerrainData` inlined. The JSON dumps this section summarizes are the gitignored `.tools/evidence/task053_*.json` files (`task053_mapdata_d3.json`, `task053_stagedata_d2.json`, `task053_challengedata.json`, `task053_mapparameters.json`, `task053_noisedata.json`, `task053_terraindata.json`, `task053_ptg_forest_stage2.json`).

### Which stage index is the vanilla Tier 2 stage

Stage index 1. Two independent asset sources agree, and both are read live rather than inferred from the level format:

| `MapData.stages` index | Forest | Desert | `StageData.challenges` rows | `ChallengeData.tier` of those rows |
| --- | --- | --- | --- | --- |
| 0 | `StageForest1` | `StageDesert1` | 13 `a_forest1_*` / 9 `a_desert1_*` | 0 |
| 1 | `StageForest2` | `StageDesert2` | 6 `a_forest2_*` / 5 `a_desert2_*` | 1 |
| 2 | `StageForest3` | `StageDesert3` | 6 `a_forest3_*` / 5 `a_desert3_*` | 2 |

`StageData` has no tier field of its own, so the tier lives only on `ChallengeData`: the 55 loaded challenge rows carry `map` (Forest 1, Desert 2, Warehouse 8), `name`, `requiresNumChallengesCompleted` and `tier`, and their counts per `(map, tier)` are exactly the `challenges` arrays above (Forest 13/6/6, Desert 9/5/5), with the `a_<map><index>_<challenge>` name prefix carrying the stage number as `tier + 1`. So the stage the game presents as Tier 2 is `MapData.stages[1]` — `StageForest2` for Forest and `StageDesert2` for Desert — and a level that wants to author or replay vanilla Tier 2 sets `stageIndex: 1`, not 2. The Warehouse group (`map: 8`, 11 rows named `a_forest1_hard 1` and similar) is challenge metadata for the Warehouse rather than a third stage band.

### Forest stage parameters (measured)

`MapData` `MapForest`: `eMap` 1, `mapType` 0 (`Tiles`), `stageDuration` 600, `numChestsMultiplier`, `numShrinesMultiplier` and `numShrinesPotsAndOtherMultiplier` all 1. Nothing differs between the stages except `mapParameters`, the prefab sets behind `randomMapObjects` and `challenges`:

| Field | `StageForest1` | `StageForest2` | `StageForest3` |
| --- | --- | --- | --- |
| `mapParameters` | `ParamForest1` | `ParamForest2` | `ParamForest3` |
| `MapParameters.size` | 15 | 15 | 16 |
| `MapParameters.scale` | 20 | 22 | 24 |
| `tileWidth` / `tileHeight` | 2 / 1 | 2 / 1 | 2 / 1 |
| `scaledTileWidth` / `scaledTileHeight` | 40 / 20 | 44 / 22 | 48 / 24 |
| `volatility` | 0.8 | 0.8 | 0.8 |
| `centerHeightTarget`, `slopeStrength`, `yOffset`, `flatMapBias` | 0 | 0 | 0 |
| `biasStrategy` / `heightGenerationStrategy` | 0 / 1 | 0 / 1 | 0 / 1 |
| `proceduralNoiseData` / `proceduralTerrainData` | null / null | null / null | null / null |
| `proceduralMapScale` | 1 | 1 | 1 |
| `mapEdgeFillType` | 3 | 3 | 3 |
| `randomMapObjects` groups | 6 | 5 | 5 |
| `stageTilePrefabs` | 9 flat prefabs, `populateTilesRatio` 0.25 | same | same |
| `challenges` | 13 `a_forest1_*` | 6 `a_forest2_*` | 6 `a_forest3_*` |

The tile grid therefore grows only in `size` and `scale`: stage 3 is a 16×16 grid of `48 × 24` scaled tiles while stages 1 and 2 are 15×15 grids of `40 × 20` and `44 × 22`. Everything else that differs per stage is the prop set, and no group ever changes its `checkRadius` or `upOffset`. What changes is the prefab list, the count, and the scale range (`scaleMin`–`scaleMax` in parentheses):

| Group | `StageForest1` | `StageForest2` | `StageForest3` |
| --- | --- | --- | --- |
| Trees | 300 `Tree0` (0.75–2.5) | 300 `Tree0Forest2`, `Tree1Forest2`, `Tree2` (1–4) | 300 `DeadTree0`, `DeadTree1`, `DeadTree2` (1–5) |
| Logs | 40 `Log0` (0.75–1.5) | 50 `Log0` (0.75–3) | 50 `Log0Dead` (0.75–3) |
| Bushes | 100 `Bush0` (0.75–1.25) plus 100 `Bush1` (1–2, `alignWithNormal`) | 300 `Bush` (0.75–3.5, `alignWithNormal`) | 300 `BushRed` (0.75–3.5, `alignWithNormal`) |
| Rocks | 150 `rock_medium_01`–`03`, `rock_small_01`/`02`/`05` (1–7) | same six prefabs, same range | the same six as `*Dark` variants (1–8) |
| Boulders | 8 `Boulder` (0.75–2, `upOffset` 4, `alignWithNormal`) | same | same |

### Desert stage parameters (measured)

`MapData` `MapDesert`: `eMap` 2, `mapType` 1 (`Terrain`), `stageDuration` 600, all three object multipliers 1. Desert stages carry no `MapParameters`; their assets instead reference noise and terrain settings. The measured differences include `proceduralMapScale`, the stage-3 noise asset and prop settings:

| Field | `StageDesert1` | `StageDesert2` | `StageDesert3` |
| --- | --- | --- | --- |
| `mapParameters` | null | null | null |
| `proceduralNoiseData` | `NoiseDesert1` | `NoiseDesert1` | `NoiseDesert3` |
| `NoiseData.noiseScale` | 100 | 100 | 40 |
| `octaves` / `lacunarity` | 2 / 3 | 2 / 3 | 2 / 3 |
| `persistance` (the game's spelling) | 0.4 | 0.4 | 0.5 |
| `blend` / `blendStrength` / `seed` | 0.02 / 0 / 257 | 0.02 / 0 / 257 | 0.02 / 0 / 257 |
| `proceduralTerrainData` | `TerrainDesert` | `TerrainDesert` | `TerrainDesert` |
| `TerrainData.uniformScale` / `useFalloff` / `heightMultiplier` | 1 / false / 11 | 1 / false / 11 | 1 / false / 11 |
| `proceduralMapScale` | 1 | **1.1** | **1.2** |
| `mapEdgeFillType` | 3 | 3 | 3 |
| `randomMapObjects` groups | 7 | 7 | 7 |
| `stageTilePrefabs` | 0 flat prefabs, `populateTilesRatio` 0.33 | same | same |
| `challenges` | 9 `a_desert1_*` | 5 `a_desert2_*` | 5 `a_desert3_*` |

The seven Desert prop groups are, in the asset's own order: 8 landmarks (`Ladnmark1`, `Ladnmark2`, `Landmark3`, `Landmark4` — the first two are misspelled in the game's own prefabs), 15 houses (`TilePrefabHouse`, `TilePrefabHouse2`), 60 `Rock_*_Small` rocks, 120 cacti, 60 logs (`Log0 1`, `Log2`, the space included), 15 desert trees and 300 `DesertBush`. Only three groups move between stages: stage 2 widens the landmark scale from 1.3–3 to 2–5, and stage 3 takes the landmark count to 14 with scale 2–6, the rock count to 100 with `scaleMax` 8, and the tree count to 50.

### How far the stage override actually reaches

`run.py load <level> --stage N` (or the MCP `load(stage=N)`) requests the stage index for that load, and the log confirms the request — `LevelLoader: starting map=Forest stage=2 tier=0 seed=424242`. What the running generator does with that number is a different matter. Requests for Forest stage 0, 1 and 2 at a fixed seed produced the same tile snapshot (`tiles=225 flatTiles=165 fillTiles=190`, `nodes=415`, `hash=A2B9C891…`, `objects=847`), and the live `ProceduralTileGeneration` dump taken after a stage-2 request (`task053_ptg_forest_stage2.json`) reported `currentStage=StageForest1` with `currentMapParameters=ParamForest1` (`size` 15) — not the requested `StageForest3`. `RunConfig.mapTierIndex`, which `CustomTierCap` pins to 0 on this harness (`src/MegabonkLevels.Mod/custom_tier_cap.cs`), is a candidate explanation, not established causality. Neither the effective challenge band nor successful Tier 2 generation follows from the request log. Effective-stage selection remains unresolved; the repeat measurements below must not be presented as verified Tier 2 layouts.

### Repeat behaviour of the generated layout

The Forest tile snapshot repeated under the seed pin; its object hash did not always repeat. On Forest, `debugSeed` is the level seed under the pin and the game's own roll appears there on an unseeded load. Desert does not run that tile-generator hook, so its logged `debugSeed` is not an unseeded-terrain control. `hash`/`objectsHash` are SHA-256 hashes over the tile-list and `(Clone)` root snapshots taken at `A_GenerationComplete` (`src/MegabonkLevels.Mod/generation_patch.cs`), shown as prefixes below. The tile-list hash does not capture Desert mesh terrain. The snapshot column gives counts (`tiles / flatTiles / fillTiles`), not width, height and depth; stage indices are requests, not verified effective stages.

| Map | Stage | Seed | Loads | Tile snapshot | Nodes | Tile hash | Objects | Objects hash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Forest | 0 | 424242 | 1 (Mac) | 225 / 165 / 190 | 415 | `A2B9C891…` | 847 | `C0376874…` |
| Forest | 1 | 424242 | 8 (Mac) | 225 / 165 / 190 | 415 | `A2B9C891…` | 847 | `C0376874…` ×4, `92A74E52…` ×4 |
| Forest | 2 | 424242 | 3 (Mac) | 225 / 165 / 190 | 415 | `A2B9C891…` | 847 | `C0376874…`, `92A74E52…` ×2 |
| Forest | 1 | game-rolled | 2 (Mac) | 225 / 170 / 227 and 225 / 165 / 198 | 452, 423 | `79FD5A54…`, `92594BE1…` | 848, 847 | differs every load |
| Desert | 0, 1, 2 | 424242 and game-rolled | 6 (Mac: 4 seeded, 2 game-rolled) | 400 / 292 / 417 | 817 | `692987B2…` | 0 | `E3B0C442…` |

The per-run rows behind that table are the Mac `task053_*_gen.txt` and `task053_*_log.txt` files under `.tools/evidence`. The table counts each labelled Mac run once, not each log copy. Linux files with inconsistent requested-map labels or incomplete generation records are excluded rather than counted as independent runs. The larger batch's files are no longer available; these totals cover only surviving records, not the planned matrix.

Three findings come out of that table.

The recorded seeded Mac Forest tile snapshots match (`A2B9C891…`, 415 records, 225 / 165 / 190). This establishes repeatability for the captured runs, not all stages or platforms. The two Mac unseeded Forest loads (`run.py load <level> --no-seed`, MCP `load(unseeded=true)`) instead produced 225 / 170 / 227 with 452 records and 225 / 165 / 198 with 423. Their game-rolled `debugSeed` values were `63019176` and `1314710470`, rather than the pinned `424242`; their tile and object hashes differed. The tile count itself stayed 225.

The recorded Mac Forest object hashes are **bimodal**: the 12 seeded records contain two values, `C0376874…` on 6 and `92A74E52…` on 6, with `objects=847` throughout. Matching counts do not reveal which transforms or identities differ. A second random stream, capture timing, or another cause has not been established. The next measurement should compare full object snapshots, including repeated captures within a single generation, rather than infer a cause from hash prefixes alone.

This resembles the residual Forest `objectsHash` drift left open in [map-generation-determinism.md](map-generation-determinism.md): identical tile hash, differing object hash, with the mod's per-phase reseeding active. The Mac offline Wine prefix also produced it, splitting its 8 same-stage seeded repeats 4 and 4. Two observed hashes in a finite sample do not establish a binary RNG decision, identify a consumer, or bound future outcomes. The cause remains unresolved; equal object counts do not establish stable object identity or transforms.

Desert says nothing about object determinism, because the snapshot is empty: `objects=0` and `objectsHash=E3B0C442…` (SHA-256 of empty input). The patch collects scene-root `(Clone)` objects occurring after the `TileObjectsParent` root, not children under that parent. No objects were captured by that selection in these Desert runs. The tile-list snapshot also repeated (`400 / 292 / 417`, 817 records, `692987B2…`), but it does not describe the generated mesh. Neither stable terrain nor absent props follows from these snapshots. Desert object placement, its capture coverage and the effective runtime terrain seed remain unresolved.
