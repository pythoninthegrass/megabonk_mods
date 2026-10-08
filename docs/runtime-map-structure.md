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

**Gotcha for editing code:** any edit-application code that assumes "the map is a `proceduralTiles` grid" must branch on `EMapType` first. Only `Tiles` maps (Forest, Graveyard, and presumably other `Tiles`-type stages) have this grid; `ProceduralMesh` maps need a different editing model entirely (not yet defined).

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

## Navigation after edits

Open `Tiles` and `ProceduralMesh` maps bake no navmesh, and `EnemyMovementRb` chases the player with `Rigidbody` velocity, so editing the grid needs no navigation rebuild: enemy movement is physics on whatever collider is there. The ground collider is baked once and is rebuilt after edits (see below), so a tile removed with `RemoveTile` is a real hole, and the kill floor ends a fall into it. Whether enemies get stuck on edited terrain in a real run is unconfirmed: it needs a playthrough with enemies, which the harness cannot drive. The only `NavMeshSurface.BuildNavMesh()` call is the Graveyard crypt (`RsgController`), a separate dungeon that tile edits do not touch. If enemies ever need to avoid holes or edited terrain actively, that would be new behaviour, not a rebuild step.

## Ground collision after edits

All ground collision is one baked mesh, `ProceduralTileGeneration.collider` (a GameObject named `CombinedCollisionMesh`, 413 vertices on Forest seed 20261007), built at generation time by the public static `MeshColliderCombiner.CombineMeshes(List<GameObject>)`. The game then strips the per-piece `MeshCollider` from every live tile, wall and fill piece, so they have none left to read. Edits alone therefore left the old collision in place: a removed tile kept an invisible floor, and a raised or added tile had only a small collider of its own, so a ray straight down over the removed Forest cell (13,7) still hit `CombinedCollisionMesh` at y=0.

`CollisionRebuild.Replace` rebuilds it after tile edits. For each live piece in `tiles`, `flatTiles` and `fillTiles` it matches the prefab by name (`flatTile`, `slopeTile`, `wallFlat`, `wallLeftUp`, `wallLeftDown`, `wallLeftCross`), attaches that prefab's collider mesh as a temporary `MeshCollider`, runs the game's combiner, destroys the temporary colliders, and swaps the result into `collider`. Running the same rebuild on an unedited level reproduces the original mesh exactly (413 vertices, identical bounds), which is how the piece set was validated. Pieces deactivated by an edit must be skipped because `Destroy` only takes effect at the end of the frame, so `RemoveTile` and tile replacement deactivate the object and drop it from `tiles` and `flatTiles` as well as destroying it. After the rebuild, straight-down rays on the scratch level hit the slope at y=10 (the midpoint of a level 0 to 1 ramp), the added tile at y=20, and nothing but the world floor over the removed cell.

## Walls after edits

Whole-grid `FillHoles`/`FillEdges` would duplicate pieces everywhere, so the mod uses the per-edge private `ProceduralTileGeneration.FillHole(Vector2Int from, Vector2Int to)` through reflection. Calling it from a vanilla slope cell to each of its four neighbours recreates exactly the four wall pieces generation had built there (`TileWall` below, `TileWallSlopeLeftDown` on the slope sides, same positions, rotations and scales).

`FillRegeneration.Regenerate` runs after the tile edits and before the collision rebuild. `FillEdgePlan` lists the edges between each edited, still occupied tile and each occupied neighbour. For each edge the mod destroys the fill pieces whose position lies on the edge line (within 0.5 units, and within half a tile along it), then calls `FillHole` in both directions. New pieces are appended to `fillTiles`; the genId index is built before the edits, so the ids of existing objects do not move. Edges against a removed cell or the grid border are not touched. On the scratch level the sky that showed through the replaced slope at (9,7) is gone and the slope has side walls.

## Kill floor

The game has its own catch floor: a `WorldCollider` (`WorldColliderTrigger`) at y=-80 whose mesh bounds read as a 1x1x1 box, so its height is taken from its transform. A body that falls through a removed tile rests there. In a level loaded by the mod, `KillFloorWatcher` checks every quarter second and kills anything below the kill floor, as in Super Mario Bros: the player through `MyPlayer.Instance.inventory.playerHealth.KillPlayer()`, and enemies through `Enemy.Kill("KillFloor")` over `EnemyManager.Instance.enemies` plus the manager's private `stageBosses` list.

`KillFloor.FloorY` puts the floor 40 units below the lowest live tile level, raised to at least 8 units above the catch floor so a body resting on it still counts as fallen. The watcher arms after generation when a level file started the run, and disarms on any other generation. Verified in the game with a level that removes every tile but one: the log shows `KillFloor: armed at y=-40` and `player fell to y=-48.49, killing`, and the run ends on the death screen. Enemy kills are observed in a playthrough of a level with a removed tile: 67 distinct enemies were killed in about three minutes. A killed enemy stays in `EnemyManager.enemies` for a while, so `KillTracker` (pure logic) skips an actor for 2 seconds after a kill and then retries it with a higher attempt number, which the log marks as `still present`. Without it the same enemy was killed on every check, about seven times on average. The stage boss (Forest, Lil Bark) is in `stageBosses` and also in `enemies`, under the same `Enemy1(Clone)` name as every other enemy, so only its id identifies it. The earlier watcher compared the transform pivot with the floor, and a tall actor never crossed it: Lil Bark's pivot rested at about y=-66.5 on the catch floor (y=-80), about 5 above the floor at -72, and he climbed back out of the hole alive; a golem showed the same. The watcher therefore compares `KillFloor.LowestPoint`: the lower of the pivot and the bottom of `Enemy.collider` (a `CapsuleCollider`, enabled only). This killed the Forest stage boss in a playthrough: the boss's pivot was at y=-63.4 and its lowest point at y=-76.3 when it was killed, once, with no retry. An optional heartbeat line every 5 seconds (`KillFloor: watch ...`, off by default; see "Kill-floor heartbeat" in [development.md](development.md)) reports the enemy and stage boss counts, the lowest point each group reached, and the boss ids, so a boss that never reaches the floor can be told apart from one that is not scanned.

## 4. `genId` scheme

Tiles-map generation is fully deterministic given a fixed `debugSeed` (see [map-generation-determinism.md](map-generation-determinism.md)), and the live index built at `A_GenerationComplete` has the same categories and counts on repeat loads of the same level (Forest, seed 20261007: 225 tiles, 160 flat, 203 fill, 39 tile objects, 1474 indexed in total). Each generated object gets a stable id:

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

The `object:` category covers everything `RandomObjectPlacer` and `SpawnInteractables` spawn: trees, bushes, rocks, logs, pots, chests, shrines, the boss spawner and the player spawn portal. `RandomObjectPlacer` and `SpawnInteractables` have no children and expose no result list; their output is parented to the scene root, so the root order is the only record of spawn order. The prefab name is the cloned GameObject's name (no `RandomMapObject` name field exists). The index is a snapshot taken at `A_GenerationComplete`; objects the game creates later (enemies, projectiles, pickups) are not in it.

A tile's world position is `origin + (x, z) * scaledTileWidth` with Y at `posY * scaledTileHeight` (Forest: grid cell (0,0) at world (-280, -280), `posY=1` at Y=20). `PlayerSpawnPortal` in the Forest test seed sits at (120, 0, 0), i.e. grid cell (10, 7).

**Caveat:** only confirmed for `Tiles`-type maps (Forest, Graveyard). `ProceduralMesh` maps (Desert) have no confirmed-controllable seed yet (see §1), so the scheme is unverified there.
