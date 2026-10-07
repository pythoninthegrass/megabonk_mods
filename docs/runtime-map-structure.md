# Runtime map structure (TASK-002.03)

Required reading for TASK-003 (level format) and TASK-004 (runtime editing/playback). Answers, with concrete type/field names confirmed against the running game (CrossOver/macOS, game build 1.0.69), where the tile grid lives, what drives its spacing, whether a navmesh is baked, and how to index generator-spawned objects.

All runtime values below come from extending the mod (`src/MegabonkLevels.Mod/grid_shape_patch.cs`, `navmesh_patch.cs`) that TASK-002.02 already had hooked into `MapGenerationController.A_GenerationComplete`, then observing `MelonLoader/Latest.log` across a Forest run, a Desert run, and a Graveyard run (which also triggers the crypt/boss dungeon). See [map-generation-determinism.md](map-generation-determinism.md) for the companion seed-determinism findings.

## 1. Where the tile grid lives (AC#1)

`ProceduralTileGeneration.proceduralTiles` is `Il2Cpp.ProceduralTile[][]` — a **dense, fully-populated jagged array**, not sparse, for `Tiles`-type maps (`EMapType.Tiles`, `mapType=0`):

| map | `MapParameters.size` | `proceduralTiles.Length` | row length | occupied cells | `tiles.Count` |
| --- | --- | --- | --- | --- | --- |
| Forest | 15 | 15 | 15 (uniform) | 225 | 225 |
| Graveyard | 19 | 19 | 19 (uniform) | 361 | 361 |

Every row has the same length (`size`), and every cell in every row is non-null (`occupiedCells == size * size == tiles.Count`) — it's a complete `size x size` grid, no holes. `ProceduralTileGeneration.tiles` (the `List<GameObject>` TASK-002.02 already hashes) is exactly the flattened, deduplicated contents of this grid for the tiles that exist post-generation.

`flatTiles` and `fillTiles` are **separate lists, not subsets of `proceduralTiles`** — they hold additional GameObjects (flat-ground variants and wall/edge fill pieces from `FillHoles()`/`FillEdges()`/`FillWallSlopeToFlat()`) that get attached around/between the base grid tiles. Their counts (Forest: 179 flat / 226 fill; Graveyard: 231 flat / 387 fill) don't equal `tiles.Count` and shouldn't be assumed to.

**`ProceduralMesh` maps (Desert, `mapType=1`) don't use this grid at all.** On a Desert run, `ProceduralTileGeneration.proceduralTiles` is `null` and `currentStage`/`currentMapParameters` are both `null` — `ProceduralTileGeneration.Generate()` is simply never called for this map type. Desert's terrain comes from `MapGenerationController.proceduralMapMeshGenerator` (type `MapGenerator`), which builds a heightmap-based mesh via `GenerateMap(MapData, StageData, int seed = 105)` and exposes `heightMap`/`worldScale`/`mapChunkSize` instead of a tile grid. TASK-002.02 already noted its seed isn't controlled by the `debugSeed` force that works for Tiles maps — this `seed` parameter on `MapGenerator.GenerateMap` is the likely real control point, unconfirmed/untried.

**Gotcha for TASK-004:** any edit-application code that assumes "the map is a `proceduralTiles` grid" must branch on `EMapType` first. Only `Tiles` maps (Forest, Graveyard, and presumably other `Tiles`-type stages) have this grid; `ProceduralMesh` maps need a different editing model entirely (this task does not attempt to define one).

### Accessing fields that look private

`ProceduralTileGeneration.currentStage` and `.currentMapParameters` are declared `private` in the Il2CppDumper output, which looked like it would require reflection. It doesn't: **Il2CppInterop generates these as public C# properties** backed by native field-offset reads (see the real `MelonLoader/Il2CppAssemblies/Assembly-CSharp.dll`, not the `.tools/il2cpp_dump/DummyDll` declarations-only dump). Read them directly — `tileGen.currentMapParameters`, `tileGen.currentStage.mapParameters` — no `BindingFlags.NonPublic` needed. (A first attempt at this task used reflection against the DummyDll's private-field declaration and silently got `null` every time; that was the bug, not an actual access restriction.)

## 2. Tile spacing source (AC#2)

`StageData.mapParameters` (type `Il2CppAssets.Scripts.MapGeneration.ProceduralTiles.MapParameters`) is confirmed as the authoritative spacing source for `Tiles` maps, cross-checked against measured transform distances on two stages:

| map | `tileWidth` | `scale` | `scaledTileWidth` (= tileWidth × scale) | measured world distance between adjacent grid cells |
| --- | --- | --- | --- | --- |
| Forest | 2 | 20 | 40 | **40.0000** |
| Graveyard | 2 | 20 | 40 | **40.0000** |

Measurement method: walk `proceduralTiles[x][y]` vs `proceduralTiles[x+1][y]` for the first pair of adjacent non-null cells, take `|Δworld.x|`. Exact match, both stages, within float precision. **`scaledTileWidth` is the real-world planar grid step — use it, not `tileWidth` or `scale` alone, and never hardcode a spacing constant.**

`scaledTileHeight` (= `tileHeight × scale` = 1 × 20 = 20) was *not* independently cross-measured — based on `MazeHeightGenerator.GenerateHeight` existing specifically to vary tile elevation, `tileHeight`/`scaledTileHeight` almost certainly control the **vertical (Y) step per height level** in the terraced terrain, not a second planar axis. The grid is square in the X/Z plane (both axes step by `scaledTileWidth`); don't assume `scaledTileHeight` is a Z-axis spacing value without checking a map with visible multi-level terracing.

## 3. NavMeshSurface (AC#3)

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

## 4. Proposed `genId` scheme (AC#4)

TASK-002.02 confirmed Tiles-map generation is fully deterministic given a fixed `debugSeed`. Combined with this task's confirmation that `tiles`/`flatTiles`/`fillTiles` and the spawner lists are built in a fixed, repeatable order every run, each generated object can be assigned a stable id of the form:

```text
{category}:{sequentialIndexWithinCategory}
```

Per-run, build this by iterating each source **in the exact order the game populates it** (not after any sorting — TASK-002.02's hash sort is only for determinism comparison, not identity) and assigning a zero-based counter per category:

| category | source | example id |
| --- | --- | --- |
| `tile` | `ProceduralTileGeneration.tiles` (or `proceduralTiles[x][y]` grid-walk order, equivalent) | `tile:0042` |
| `flatTile` | `ProceduralTileGeneration.flatTiles` | `flatTile:0017` |
| `fillTile` | `ProceduralTileGeneration.fillTiles` | `fillTile:0203` |
| `randomObject:{spawnerName}` | `RandomObjectPlacer.randomObjects[i]` spawns, keyed by the `RandomMapObject`'s prefab/spawner name so different object types (trees, rocks, etc.) don't share a counter | `randomObject:Tree:0003` |
| `tileObject` | `GenerateTileObjects.Generate()` (boss spawners, map-specific prop placement) | `tileObject:0001` |
| `chest` | `SpawnInteractables.SpawnChests()` (46/stage) | `chest:0012` |
| `shrine` | `SpawnInteractables.SpawnShrines()` (14/stage) | `shrine:0003` |
| `rail` | `SpawnInteractables.SpawnRails()` | `rail:0001` |

Since generation order is deterministic for a given (`stage`, `debugSeed`), the same `genId` refers to the same conceptual spawn ("the 3rd tree this run generated") across repeat generations with that seed — exactly what TASK-004's edit-application layer needs. This is a proposal, not yet implemented; `RandomMapObject`'s exact prefab-name field should be confirmed when TASK-004 builds the indexer, since this task only confirmed the type shape, not its field names, via static analysis.

**Caveat:** this scheme is only confirmed viable for `Tiles`-type maps (Forest, Graveyard), where determinism was tested. `ProceduralMesh` maps (Desert) don't have a confirmed-controllable seed yet (see §1), so a `genId` scheme for Desert's object placement is unverified and out of scope here.
