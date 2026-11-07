# Map generation determinism

This records the seed-determinism findings behind the "seed + edits" level save format. The core question: does `MapGenerationController`'s generation reproduce an identical layout given the same map, stage, and seed? If not, the save format has to store a full layout snapshot instead.

## Method

The mod (`src/MegabonkLevels.Mod/`) hooks `MapGenerationController.A_GenerationComplete` and, on every fire, builds a `GenerationSnapshot`:

- Collects every distinct `GameObject` (deduplicated by `GetInstanceID()`) across `ProceduralTileGeneration.tiles`, `.flatTiles`, and `.fillTiles`.
- For each, records its **world** position, rotation, and scale (`generation_patch.cs:ToRecord`) — world transforms, not local, because these lists don't all share one stable parent.
- Sorts the records by a quantized grid key (round to the nearest 0.01 unit) so hierarchy/list iteration order never affects the result, then formats each as `name|x,y,z|qx,qy,qz,qw|sx,sy,sz` and SHA-256-hashes the concatenated, newline-joined text (`generation_hash.cs:GenerationHash.Compute`).
- Logs `map=<name> mapType=<EMapType int> mapSeed=<MapGenerationController.mapSeed> debugSeed=<ProceduralTileGeneration.debugSeed> tiles=<n> flatTiles=<n> fillTiles=<n> nodes=<records.Count> hash=<sha256 hex> objects=<n> objectsHash=<sha256 hex>` to `MelonLoader/Latest.log` (`generation_report.cs`). `hash` covers the tile grid; `objectsHash` covers every spawned prop's world transform (see "Object placement determinism" below).

An initial attempt instead walked the Transform hierarchy under `ProceduralTileGeneration.newRoot` — that root was empty (`nodes=0`, hash of empty input) by the time `A_GenerationComplete` fires, so it was abandoned for the GameObject-list approach above, which is what's documented and shipped.

**Forcing a seed** (`seed_force_patch.cs`): an F9 hotkey (`MegabonkLevelsMod.OnUpdate`) cycles `SeedForcePatch.Mode` through `Off → DebugSeed → MapSeedOnly → Off`. A Harmony prefix on `ProceduralTileGeneration.Generate` applies the active mode immediately before the call:

- `DebugSeed`: sets `__instance.debugSeed = 20261007` and forces the `useDebugSeed` parameter to `true`.
- `MapSeedOnly`: sets the static `MapGenerationController.mapSeed = 20261007` and leaves `useDebugSeed`/`debugSeed` untouched.

## Results

Tested on CrossOver/macOS (the only platform with a working, playable MelonLoader install), game build 1.0.69, with `SeedForcePatch.Mode = DebugSeed` active throughout (set once via F9, held across restarts).

### Forest (`MapForest`, `mapType=0` / `EMapType.Tiles`)

| run | mapSeed | debugSeed | tiles/flat/fill | nodes | hash |
| --- | --- | --- | --- | --- | --- |
| 1 | 1073930310 | 20261007 | 225/160/203 | 428 | `0F5D88E2C673F1BA929868626D21FB06A2ECF014298975352EF3EF28634665CB` |
| 2 | 1701581358 | 20261007 | 225/160/203 | 428 | `0F5D88E2C673F1BA929868626D21FB06A2ECF014298975352EF3EF28634665CB` |
| 3 | 111760902 | 20261007 | 225/160/203 | 428 | `0F5D88E2C673F1BA929868626D21FB06A2ECF014298975352EF3EF28634665CB` |

Identical hash across three separate full generations (restarting the run each time). `mapSeed` differed every time while `debugSeed` stayed at our forced value and the layout never changed.

**Conclusion: Forest/Tiles generation is fully deterministic given the same `debugSeed` with `useDebugSeed=true`, and `mapSeed` has no effect on the resulting layout** — it's a separately, independently randomized value exposed for some other purpose (display/save bookkeeping), not the generation seed. `debugSeed` (not `mapSeed`) is the field that actually controls tile-based generation, confirmed by forcing it to a constant and observing reproducible output while `mapSeed` varied freely.

### Desert (`MapDesert`, `mapType=1` / `EMapType.ProceduralMesh`)

| run | mapSeed | debugSeed | tiles/flat/fill | nodes | hash |
| --- | --- | --- | --- | --- | --- |
| 1 | 690394152 | 1952838951 | 400/292/417 | 817 | `692987B28DBC32CF22A58EED963FC8FD85F98C211DBEF66CE0A08370CBDB3546` |
| 2 | 648929461 | 1952838951 | 400/292/417 | 817 | `692987B28DBC32CF22A58EED963FC8FD85F98C211DBEF66CE0A08370CBDB3546` |

Identical hash across two full generations — Desert is also reproducible. But note `debugSeed` here is **1952838951, not our forced 20261007**: the `DebugSeed` force (Harmony prefix on `ProceduralTileGeneration.Generate`) did not take effect for this map type, yet the result was still reproducible both times with the same (uncontrolled) value. This means one of two things, not yet distinguished:

1. `ProceduralMesh` maps route generation through a different call path that doesn't honor the `useDebugSeed`/`debugSeed` parameters our patch targets (the `MapGenerationController.proceduralMapMeshGenerator`/`MapGenerator` field is a plausible candidate for the actual noise/mesh generator, separate from `ProceduralTileGeneration`), or
2. the value `1952838951` is an authored/baked default on this stage's data rather than something rolled at runtime, which would make it stable across runs incidentally rather than because our seed-forcing worked.

Either way: **Desert/ProceduralMesh is empirically deterministic across the two runs tested, but the mod cannot yet control or vary its seed on demand** the way it can for Forest/Tiles. This is an open follow-up, not a blocker for the "seed + edits" decision below, since determinism itself held.

## Fallback decision

Determinism holds for both map types tested (one `Tiles`, one `ProceduralMesh`), so **"seed + edits" stays the save format — a full-layout snapshot is not required.** However:

- For `Tiles` maps, the mod must force `useDebugSeed=true` and a chosen `debugSeed` value (via the same Harmony prefix approach used here) whenever it generates a map it intends to save/reproduce, and persist that `debugSeed` (not `MapGenerationController.mapSeed`, which is disconnected from the actual generation and will not reproduce anything).
- For `ProceduralMesh` maps, the actual seed-controlling field/mechanism is still unidentified — a short follow-up spike needs to find the real seed source, likely on `MapGenerationController.proceduralMapMeshGenerator` (type `MapGenerator`), before the mod can guarantee a chosen, reproducible seed for these maps. Until then, treat `ProceduralMesh` maps as "reproducible in practice so far, but not yet controllable," and re-run this same hashing method against whatever field is tried next.
- Only two (map, stage) combinations were tested, both on each map's default/first stage. If per-stage variation (e.g. a stage-specific `MapParameters` override) is worth checking later, re-run with a second stage of the same map using this same mod build.

## Object placement determinism

The hashing above covered only the tile grid (`ProceduralTileGeneration.tiles`/`flatTiles`/`fillTiles`). The ~850 props a Forest run also spawns — trees, rocks, bushes, chests, shrines, pots — are separate scene-root `<prefab>(Clone)` objects placed after the grid, and `debugSeed` does **not** control them. Forcing only `debugSeed` reproduces the floor but re-rolls every prop on each run (confirmed: identical tile hash, different `objectsHash`, with prop counts varying run-to-run, e.g. `rock_small_05` 24 vs 30).

Object placement draws from two independent RNGs, neither tied to `debugSeed`:

- **Positions**: `UnityEngine.Random.Range`. Reseedable with `UnityEngine.Random.InitState`.
- **Per-prefab counts**: `RandomMapObject.GetAmount()` rolls on `Utility.MyRandom.random`, a single static `ConsistentRandom` (the game's `System.Random` subclass). Its static constructor seeds it **once from `QueryPerformanceCounter`** (wall-clock ticks), so counts are different every process run and uncontrollable through any map/stage/seed field. Because the count drives how many position draws happen, drifting counts also shift positions even when `UnityEngine.Random` is reseeded. `MapGenerationController.mapSeed` has no effect here either.

To reproduce props, the mod reseeds **both** RNGs from the forced seed before each spawn sub-phase (`seed_force_patch.cs`): `UnityEngine.Random.InitState(phaseSeed)` and `Utility.MyRandom.random = new ConsistentRandom(phaseSeed)`, hooked as Harmony prefixes on `GenerateTileObjects.Generate`, `SpawnInteractables.SpawnChests`/`SpawnShrines`, and `RandomObjectPlacer.GenerateInteractables`. Each phase gets a distinct derived seed (`SpawnSeed.PhaseSeed`) so a phase reproduces independently of unrelated `UnityEngine.Random` consumers running between phases. With this in place the full `objectsHash` (every spawned prop's world transform) is identical across runs while `mapSeed` still varies freely. The generation report logs `objectsHash` alongside the tile `hash` for this check.

### Opt-in interactable variety

Level files can opt into per-run relocation with `randomizeShadyGuy`,
`randomizeChests` and `randomizeMoai`. All default to false. They do not change
phase seeds or spawn counts: generation and genId assignment remain exactly as
before. After saved edits are applied, only eligible generated objects of the
enabled kinds are relocated using a private RNG. Explicitly moved or placed
objects remain pinned, and unrelated objects retain their deterministic
transforms. See [the level format](level-format.md#interactable-randomization)
for settings and candidate-validation rules.

The generation report's hashes are captured before this post-edit relocation,
so they continue to describe the deterministic baseline, not the randomized
playable positions. Compare the `InteractableRandomization` placement log or
live transforms to verify variety. With all flags absent or false the
relocation pass returns without consuming randomness or touching transforms.

Extra shrines (`extraShrines`, `extraShrineKinds`) spawn after the relocation
pass from a private RNG seeded from a fresh `Guid` per run, so they consume
neither `UnityEngine.Random` nor the game's `ConsistentRandom`. The baseline —
tiles, props, genIds and the reported hashes — reproduces identically across
runs of a seed whether or not the field is set; the extra shrines themselves
deliberately vary between runs of the same seed. They are added after the
generation report captures its hashes, so the extras never appear in them.
Compare the `ExtraShrines:` placement log or live scene objects to verify them.

On the Windows build under Proton, Forest seed `20261008` has also produced
different baseline `objectsHash` values across launches with relocation both
disabled and enabled, while the tile hash stayed identical. Those hashes are
logged before the relocation pass. Full prop determinism in that configuration
is therefore not yet confirmed; shared RNG consumers and placement timing need
further investigation. Compare runs with matching baseline hashes when isolating
the effect of the relocation flags, rather than attributing baseline drift to
the private randomization pass.

## How the original game uses random numbers, per map

This section maps each generator to the random source it draws from. Each claim carries its provenance: **decompiled** means a function read in Ghidra, **dump** means a signature or field in the Il2Cpp dump (`.tools/il2cpp_dump/dump.cs`), and **measured** means a result recorded in this document or in `runtime-map-structure.md`. Only `ProceduralTileGeneration.Generate`, `Maze.Generate` and the `MazeHeightGenerator.GenerateHeight` dispatcher were decompiled; everything else below is dump signatures or measurements.

### Map identifiers

The dump's `EMap` enum lists None 0, Forest 1, Desert 2, Hell 4 and Graveyard 8, but the loaded `MapData` assets report Forest 1, Desert 2, Graveyard 8, Dungeon 16 and Hell 64 (see `CatalogPrefabs.TryFindMap`), and the mod's `EMap` mirrors the assets. Trust the live `MapData.eMap` values over the dump's enum. `EMapType` has only `Tiles` and `ProceduralMesh`. The only dungeon-like generator found is the crypt (`RsgController`), a side dungeon reached from the Graveyard map.

### Generators and their random sources

| Generator | Random source | Provenance |
| --- | --- | --- |
| Tile maze layout and tile heights (Forest, Graveyard) | `seed = useDebugSeed ? debugSeed : UnityEngine.Random.Range(0, int.MaxValue)`, written back to `debugSeed`; the same value feeds `Maze.Generate(size, size, seed)` and `MazeHeightGenerator.GenerateHeight(..., seed, mapParams)` | decompiled (`ProceduralTileGeneration.Generate`, RVA 0x5208A0) |
| Maze algorithm | A private `System.Random(seed)`, separate from every other stream | decompiled (`Maze.Generate`, RVA 0x423F60) |
| Tile props, shrines, chests, rails (`GenerateTileObjects`, `RandomObjectPlacer`, `SpawnInteractables`) | Positions draw from `UnityEngine.Random`, the global stream. Per-entry counts draw from `Utility.MyRandom.random`, one static `ConsistentRandom` seeded once per process from the performance counter. Neither is tied to `debugSeed` | measured; field in dump |
| `MapGenerationController.mapSeed` | No effect on tile layout or props: Forest was identical across three runs with different `mapSeed` | measured |
| Desert and Hell terrain | `MapGenerator.GenerateMap(MapData, StageData, int seed = 105)` and a private static `MapGenerator.seed`; who supplies the argument is not confirmed | dump |
| Crypt (side dungeon) | `RsgController.Generate(int newSeed, EDungeonType, out float)` with a private static `ConsistentRandom`, `SetCustomSeed`, `HasCustomSeed` and `CanUseCustomSeed`; `MapGenerationController.CryptGeneration(int seed, ...)` | dump |
| Enemy waves, minibosses, boss | `StageTimeline` is authored data (`startEnemies`, `events`, `boss`, `minibosses`); `SummonerController` holds a `minibossPool`. No seed field was found | dump |

Streams are shared and sequential, so changing a count or adding a prop shifts every later draw. The documented order is tile `Generate`, `GenerateTileObjects.Generate` (the boss spawner on a random flat tile, then the map-specific tiles), then `SetArea`, `SpawnRails`, `SpawnChests`, `SpawnShrines`, `SpawnOther`, and finally one `RandomObjectSpawner` pass per `StageData.randomMapObjects` entry, shrine entry and `MapData.randomObjectsOverride`. This is why `seed_force_patch.cs` reseeds both of the game's generators at the start of each phase. A Forest run on Proton still drifted in `objectsHash` after forcing; the cause is unknown.

### Tiles maps (Forest, Graveyard)

`ProceduralTileGeneration.GenerateTileGrid` allocates a `size` by `size` grid from `MapParameters.size`. `Maze.Generate` is a randomized depth-first search: it picks a random start cell with `Random(seed).Next`, keeps a stack and a visited array, shuffles the neighbour directions with `Maze.Shuffle<T>(list, Random)`, and carves walls as bit flags (top 1, right 2, bottom 4, left 8) into a `NodeTree` rooted at the start (decompiled). `GenerateHeight` then dispatches on `MapParameters.heightGenerationStrategy`: 0 calls `GenerateHeightHein` and 1 calls `GenerateHeightMe`, driven by `volatility`, `centerHeightTarget`, `slopeStrength`, `yOffset`, `flatMapBias`, a Gaussian or linear `biasStrategy`, and the tile width, height and scale (decompiled dispatcher; the two height functions were not read). Before collision is combined, `FillHoles` runs and `StageData.mapEdgeFillType` selects one edge treatment: 0 `FillEdgesIsland`, 1 `FillEdgesTrees`, 2 `FillEdgesWalls`, or none (decompiled). Flat tile prefabs come from `StageTilePrefabs.flatTilePrefabs` and specific tiles such as the Graveyard `CoffinTile` from `mapSpecificTilesPrefabs`, placed by `GenerateTileObjects.MapSpecificTiles` (dump; its random source was not read).

### Procedural-mesh maps (Desert, Hell)

`MapGenerator` builds a heightmap with `Noise.GenerateNoiseMap(w, h, seed, scale, octaves, persistance, lacunarity, blend, blendStrength, offset)` and `GeneratePerlinNoiseMap(NoiseData, seed, useFalloffMap)`, then `MeshGenerator.GenerateTerrainMesh(heightMap, heightMultiplier, heightCurve, lod)`. `StageData` supplies `proceduralTerrainData`, `proceduralNoiseData` and `proceduralMapScale`; the numeric values live in ScriptableObject assets, not the dump (dump). Desert reproduced across runs while `debugSeed` stayed unchanged, because `ProceduralTileGeneration.Generate` is never called for it, so the `debugSeed` force does not apply (measured). Hell has no measurements here and presumably follows the same path.

### Props and interactables

`RandomMapObject` carries `amount`, `maxAmount`, `checkRadius`, `scaleMin`, `scaleMax`, `maxSlopeAngle`, `upOffset`, `prefabs[]`, `randomRotationVector` and `alignWithNormal`; `GetAmount()` draws from `MyRandom.random`. `RandomObjectSpawner` loops per entry with `amountMultiplier` and the `MapData` multipliers (`numShrinesMultiplier`, `numChestsMultiplier`, `numShrinesPotsAndOtherMultiplier`). `SpawnInteractables` has `numChestsPerStage` 46, `numShrines` 14, `chestDensity`, `shrineDensity`, `chanceForFreeChest` and `numRails`. The raycast, clearance and rotation code was not decompiled, and per-prefab values live in assets (dump).

### What stays random in an authored from-scratch level

A from-scratch level skips the maze, the heights, the prop placers and the `Spawn*` methods, so terrain and prop layout are fully determined by the level file, and `seed` is bookkeeping. Skipping `GenerateTileObjects.Generate` also skips the boss spawner and its random tile pick, so the level file's `bossSpawner` replaces it. These still vary every run and are not tied to level data:

- Enemy waves and minibosses, from the stage timeline and summoners; which random source they use is unconfirmed.
- The boss spawn redirect, a random walkable spot at least 35 units from the spawner.
- Extra shrines, placed by the mod's own `System.Random` seeded from a fresh `Guid` each run, including the counts rolled from `shrineKindRanges`.
- Interactable relocation, drawn from the mod's private random source.
- Chest loot and any other consumer of `UnityEngine.Random` during play.

### Unknowns

1. Who passes the Desert and Hell seed to `MapGenerator.GenerateMap`, and the noise parameters.
2. How `GenerateHeightHein` and `GenerateHeightMe` consume randomness.
3. Which random source the enemy, miniboss and boss draws use.
4. The `RandomObjectSpawner` raycast, rotation and `alignWithNormal` details.
5. The `RsgController.Generate` algorithm and the `HasCustomSeed` rules.
6. Where `mapSeed` is written and read; it may only matter to the crypt.
7. The cause of the residual Forest drift on Proton.
