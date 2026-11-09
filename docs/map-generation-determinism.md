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

A third mode, `LevelSeed`, is set programmatically by `ForceLevelSeed` when `LevelLoader` starts a run from a level file rather than by the hotkey; it does the same `debugSeed`/`useDebugSeed` forcing with the level's recorded seed. All of this forcing lives in the one prefix on `ProceduralTileGeneration.Generate` (the separate per-phase reseeds sit on the spawners), so none of it reaches the `ProceduralMesh` branch.

## Results

Tested on CrossOver/macOS (the only platform with a working, playable MelonLoader install), game build 1.0.69, with `SeedForcePatch.Mode = DebugSeed` active throughout (set once via F9, held across restarts).

### Forest (`MapForest`, `mapType=0` / `EMapType.Tiles`)

| run | mapSeed | debugSeed | tiles/flat/fill | nodes | hash |
| --- | --- | --- | --- | --- | --- |
| 1 | 1073930310 | 20261007 | 225/160/203 | 428 | `0F5D88E2C673F1BA929868626D21FB06A2ECF014298975352EF3EF28634665CB` |
| 2 | 1701581358 | 20261007 | 225/160/203 | 428 | `0F5D88E2C673F1BA929868626D21FB06A2ECF014298975352EF3EF28634665CB` |
| 3 | 111760902 | 20261007 | 225/160/203 | 428 | `0F5D88E2C673F1BA929868626D21FB06A2ECF014298975352EF3EF28634665CB` |

Identical hash across three separate full generations (restarting the run each time). `mapSeed` differed every time while `debugSeed` stayed at our forced value and the layout never changed.

**Conclusion: Forest/Tiles generation is fully deterministic given the same `debugSeed` with `useDebugSeed=true`, and `mapSeed` has no effect on the resulting layout** — the sequencer never passes it to the tile generator (decompiled, 0x4A26F0). `debugSeed` (not `mapSeed`) is the field that actually controls tile-based generation, confirmed by forcing it to a constant and observing reproducible output while `mapSeed` varied freely. `mapSeed` is not decorative: it is the seed for the procedural-mesh terrain and for the crypt, so it does decide a layout, just not a Tiles one.

### Desert (`MapDesert`, `mapType=1` / `EMapType.ProceduralMesh`)

| run | mapSeed | debugSeed | tiles/flat/fill | nodes | hash |
| --- | --- | --- | --- | --- | --- |
| 1 | 690394152 | 1952838951 | 400/292/417 | 817 | `692987B28DBC32CF22A58EED963FC8FD85F98C211DBEF66CE0A08370CBDB3546` |
| 2 | 648929461 | 1952838951 | 400/292/417 | 817 | `692987B28DBC32CF22A58EED963FC8FD85F98C211DBEF66CE0A08370CBDB3546` |

Identical hash across two full generations, so the reported Desert hash is stable. But note `debugSeed` here is **1952838951, not our forced 20261007**: the `DebugSeed` force (Harmony prefix on `ProceduralTileGeneration.Generate`) does not take effect for this map type, and the sequencer shows why (see "Procedural-mesh maps" below) — a `ProceduralMesh` map never calls `ProceduralTileGeneration.Generate`, so the prefix never runs, nothing on that path writes `debugSeed`, and the terrain comes from `MapGenerationController.mapSeed`, which did differ between the runs (`690394152`, `648929461`). Two caveats on what these rows prove. `runtime-map-structure.md` measures `proceduralTiles` null and `currentStage`/`currentMapParameters` null on a Desert run, so this hash is not describing the mesh terrain; and whether the 817 records are placed instances or whatever the `tiles`/`flatTiles`/`fillTiles` lists hold without a generation pass was never distinguished.

So: **the Desert rows show the reported hash repeating, not the terrain repeating.** `ProceduralMesh` terrain determinism is unmeasured, and the mod has no seed hook on that path — its only seed hook is the `ProceduralTileGeneration.Generate` prefix, which this branch never reaches.

## Fallback decision

Determinism holds for the `Tiles` map tested, and the `ProceduralMesh` path is a pure function of its seed by construction (see "Procedural-mesh maps" below), so **"seed + edits" stays the save format — a full-layout snapshot is not required.** However:

- For `Tiles` maps, the mod must force `useDebugSeed=true` and a chosen `debugSeed` value (via the same Harmony prefix approach used here) whenever it generates a map it intends to save/reproduce, and persist that `debugSeed` (not `MapGenerationController.mapSeed`, which is disconnected from the actual generation and will not reproduce anything).
- For `ProceduralMesh` maps, the seed-controlling value is now identified statically: the sequencer passes the per-run `mapSeed` straight into `MapGenerator.GenerateMap(MapData, StageData, int)` (decompiled, 0x4A26F0 → 0x509EA0), so a Harmony prefix on that third parameter is the control point. It has not been tried in the running game, so treat `ProceduralMesh` maps as "seed source identified, control unverified" and re-run this same hashing method when it is implemented.
- Only two (map, stage) combinations were tested, both on each map's default/first stage. If per-stage variation (e.g. a stage-specific `MapParameters` override) is worth checking later, re-run with a second stage of the same map using this same mod build.

## Object placement determinism

The hashing above covered only the tile grid (`ProceduralTileGeneration.tiles`/`flatTiles`/`fillTiles`). The ~850 props a Forest run also spawns — trees, rocks, bushes, chests, shrines, pots — are separate scene-root `<prefab>(Clone)` objects placed after the grid, and `debugSeed` does **not** control them. Forcing only `debugSeed` reproduces the floor but re-rolls every prop on each run (confirmed: identical tile hash, different `objectsHash`, with prop counts varying run-to-run, e.g. `rock_small_05` 24 vs 30).

Object placement draws from two independent RNGs, neither tied to `debugSeed`:

- **Positions**: `UnityEngine.Random.Range`. Reseedable with `UnityEngine.Random.InitState`.
- **Per-prefab counts**: `RandomMapObject.GetAmount()` rolls on `Utility.MyRandom.random`, a single static field typed `System.Random` (so the game, and the mod, can hand it a `ConsistentRandom`). Its static constructor only runs `new System.Random()` (decompiled: `MyRandom..cctor` RVA 0x3C4B30, `System.Random..ctor()` 0x14F8CD0), and that unseeded constructor takes its seed from the BCL's own time-and-GUID generator (0x14F8630), not from any game field, so counts are different every process run and uncontrollable through any map/stage/seed setting. Because the count drives how many position draws happen, drifting counts also shift positions even when `UnityEngine.Random` is reseeded. `MapGenerationController.mapSeed` has no effect here either.

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

Extra shrines spawn after relocation using mod-owned, level-seeded streams.
`CustomRunRandom` derives shrine planning, placement and boss selection seeds
with `SpawnSeed.PhaseSeed(level.Seed, phase)` for phases 101, 102 and 103.
`A_PreGeneration` resets all three streams and the shared boss used-name set,
including when native Restart bypasses the level loader. Seed 0 is valid.
These streams never reseed `UnityEngine.Random` or the game's `ConsistentRandom`.
The authored-spots plan fixes ranged counts, extra kinds and shuffled order
before physics placement; failed placement attempts cannot change that plan or
boss picks. Boss/miniboss calls share the selection stream and used-name set.
Replay requires identical settings, available prefabs and controlled boss-call
order; ordinary combat timing and loot remain random.

Compare `CustomRunRandom: reset`, `ExtraShrines: plan`, individual placement
lines and `BossPool:` replacements/fallbacks, not the baseline generation hashes.
Extras are added after the generation report captures its hashes. Seeded plans
do not establish physics-identical successful placements: collider state,
nudging, optional relocation and native prefab callbacks can still differ.
Repeated-seed runtime comparisons and the actual death-button path remain
separate verification requirements from the pure stream/reset tests.

On the Windows build under Proton, Forest seed `20261008` has also produced
different baseline `objectsHash` values across launches with relocation both
disabled and enabled, while the tile hash stayed identical. Those hashes are
logged before the relocation pass. Full prop determinism in that configuration
is therefore not yet confirmed; shared RNG consumers and placement timing need
further investigation. Compare runs with matching baseline hashes when isolating
the effect of the relocation flags, rather than attributing baseline drift to
the private randomization pass.

## How the original game uses random numbers, per map

This section maps each generator to the random source it draws from. Each claim carries its provenance: **decompiled** means the function was read in headless Ghidra against `GameAssembly.dll` (sha256 `4350a7ae…`, identical to the installed build; addresses are RVAs into that file), **dump** means a signature or field in the Il2Cpp dump (`.tools/il2cpp_dump/dump.cs`), and **measured** means a result recorded in this document or in `runtime-map-structure.md`.

### Map identifiers

The dump's `EMap` enum lists None 0, Forest 1, Desert 2, Hell 4 and Graveyard 8, but the loaded `MapData` assets report Forest 1, Desert 2, Graveyard 8, Dungeon 16 and Hell 64 (see `CatalogPrefabs.TryFindMap`), and the mod's `EMap` mirrors the assets. Trust the live `MapData.eMap` values over the dump's enum. `EMapType` has only `Tiles` and `ProceduralMesh`. The only dungeon-like generator found is the crypt (`RsgController`), a side dungeon reached from the Graveyard map.

### The generation sequence

`MapGenerationController.<GenerateMap>d__39.MoveNext` (RVA 0x4A26F0, decompiled) is the whole run in one coroutine. It fires `A_PreGeneration`, sets `isGenerating`, draws `mapSeed = UnityEngine.Random.Range(0, int.MaxValue)` into the static field, and then branches on `MapData.mapType` (offset 0x70): `Tiles` (0) runs `ProceduralTileGeneration.Generate(..., useDebugSeed=false)`, stores the maze exit as `tileSpawnPosition`/`tileSpawnDir`, runs `GenerateTileObjects.Generate`, runs `CryptGeneration(mapSeed, ...)` when `MapData.eMap` (0x58) is 8, and then runs the prop and interactable passes; `ProceduralMesh` (1) calls `MapGenerator.GenerateMap(mapData, stageData, mapSeed)` and skips everything the tile branch does. The prop and interactable passes are four `RandomObjectPlacer.RandomObjectSpawner` calls, then `SpawnInteractables.SetArea`, `SpawnRails` (0x49D840), `SpawnChests` (0x49CF60), `SpawnShrines` (0x49E180) and `SpawnOther` (0x49D4F0).

`mapSeed` has exactly one writer in the binary: that coroutine. Sweeping every function that references the `MapGenerationController` statics block for a write to the `mapSeed` slot returns a single hit, MoveNext itself; the only other reader is `InteractableCrypt.Teleport` (0x4C90E0), which hands the same value to `RsgController.Generate` when the player enters the crypt (decompiled). So `mapSeed` is a per-run roll that the tile grid never sees, and the crypt is the one generator that shares the terrain roll.

There is no global "run seed". Every generator either receives a seed argument or pulls from a process-wide stream, and the streams the game uses are: the Unity global stream (`UnityEngine.Random`, reseedable only with `Random.InitState`), `Utility.MyRandom.random` (one static `System.Random`, seeded once per process), and `RsgController.random` (a `ConsistentRandom` re-created per crypt generation). `ConsistentRandom` derives from `System.Random` and its `int` constructor is the ordinary subtractive generator seeded from that argument, so it is reproducible when seeded (decompiled, 0x4F88F0).

### Generators and their random sources

| Generator | Random source | Provenance |
| --- | --- | --- |
| Per-run map seed | `UnityEngine.Random.Range(0, int.MaxValue)` into the static `MapGenerationController.mapSeed` | decompiled (`<GenerateMap>d__39.MoveNext`, 0x4A26F0) |
| Tile maze (Forest, Graveyard) | `seed = useDebugSeed ? debugSeed : UnityEngine.Random.Range(0, int.MaxValue)`, written back to `debugSeed`; `Maze.Generate(size, size, seed)` runs on a private `new System.Random(seed)` | decompiled (0x5208A0, 0x423F60) |
| Tile heights | a second private `new System.Random(seed)` inside each variant, drawn as `Next(int,int)` and `NextDouble()`; the Unity stream is untouched | decompiled (`GenerateHeightHein` 0x422E10, `GenerateHeightMe` 0x4235E0) |
| Tile objects and the boss-spawner tile pick | two `MyRandom.random.Next(int,int)` draws plus one `Random.Range(float,float)`; `MapSpecificTiles` makes no draws at all | decompiled (`GenerateTileObjects.Generate` 0x495870, `MapSpecificTiles` 0x4962E0) |
| Props (`RandomObjectSpawner`) | counts from `MyRandom.random` through `RandomMapObject.GetAmount()`; box position, prefab index, rotation and scale from `UnityEngine.Random` | decompiled (0x49C2A0, 0x4810F0, 0x483470) |
| Chests, shrines, rails, other | chests and shrines roll on `MyRandom.random` (shrines also draw `Random.Range(float,float)`); rails draw only from the Unity stream; `SpawnOther` makes no draws of its own but calls `SpawnPositions.GetObjectSpawnPosition`, which does | decompiled (0x49CF60, 0x49E180, 0x49D840, 0x49D4F0) |
| Grass | three `Random.Range(float,float)` draws per chunk | decompiled (`GenerateGrassForChunk`, 0x3352E0) |
| Desert and Hell terrain | the per-run `mapSeed` → `MapGenerator.GenerateMap(MapData, StageData, int)` → `GeneratePerlinNoiseMap(seed)` → `Noise.GenerateNoiseMap`, which builds `new ConsistentRandom(seed)` and draws `Next(-100000, 100000)` per octave | decompiled (0x509EA0, 0x509B90, 0x509F80, 0x51CED0) |
| Crypt (side dungeon) | `mapSeed` → `CryptGeneration` → `RsgController.Generate(newSeed, ...)`: `customSeed` when `customSeed != 0 && CanUseCustomSeed()`, otherwise a fresh `Random.Range(0, int.MaxValue)`; the result is stored in `RsgController.seed` with `random = new ConsistentRandom(newSeed)` | decompiled (0x49A170, 0x50F6E0) |
| Stage enemy pool pick | `UnityEngine.Random.Range(0, count)` | decompiled (`StageSummoner.AddEnemyToPoolAndPickNewCard`, 0x485DB0) |
| Card draws and miniboss rolls | `MyRandom.random` (`Next(int,int)` and `NextDouble()`) | decompiled (`BaseSummoner.GetRandomCard` 0x46CDD0, `SummonerController.EventMiniboss` 0x487240) |
| Boss spawn position | `Random.insideUnitSphere` | decompiled (`SummonerController.SpawnStageBoss`, 0x487C20) |
| `MapGenerationController.mapSeed` on Tiles maps | no effect on tile layout or props: Forest was identical across three runs with different `mapSeed` | measured |

Streams are shared and sequential, so changing a count or adding a prop shifts every later draw. Inside `ProceduralTileGeneration.Generate` (decompiled, 0x5208A0) the order is: draw the seed, allocate the grid and the `tiles`/`flatTiles`/`fillTiles` lists from `MapParameters.size` (0x2c), `Maze.Generate(size, size, seed)`, write the seed back to `debugSeed`, `MazeHeightGenerator.GenerateHeight`, compute the world bounds and exit direction, `FillHoles` (0x520260), then one edge treatment selected by `currentStage` (0x88) → `StageData.mapEdgeFillType` (0x28): 0 `FillEdgesIsland` (0x51E4D0), 1 `FillEdgesWalls` (0x51EAE0), 2 `FillEdgesTrees` (0x51E8D0), 3 or anything else none. That numbering is the `MapEdgeFillType` enum in the dump. In the sequencer the order is `Generate`, `GenerateTileObjects.Generate`, `CryptGeneration` on Graveyard, four `RandomObjectSpawner` passes, then `SpawnRails`, `SpawnChests`, `SpawnShrines` and `SpawnOther` on the `interactablesSpawner` component (`MapGenerationController` field 0x88). `SpawnInteractables.SetArea` and `RandomObjectPlacer.GenerateInteractables` have no direct call sites in the binary — an xref sweep found only metadata references — so they are reached indirectly, and the mod's Harmony prefixes on them do fire (measured). This is why `seed_force_patch.cs` reseeds both of the game's generators at the start of each phase. A Forest run on Proton still drifted in `objectsHash` after forcing; the cause is unknown.

### Tiles maps (Forest, Graveyard)

`Maze.Generate` (decompiled, 0x423F60) is a randomized depth-first search on a private `new System.Random(seed)`: it picks a random start cell with `Next`, keeps a stack and a visited array, shuffles neighbour order, and carves walls as bit flags into a `NodeTree` rooted at the start. Both height variants (decompiled) build their own `new System.Random(seed)` and draw through the same `System.Random` vtable slots — `Next(int,int)` at 0x198 and `NextDouble()` at 0x1b8 — comparing the doubles against `MapParameters.volatility` (0x18) and branching on `MapParameters.biasStrategy` (0x3c), alongside `centerHeightTarget`, `slopeStrength`, `yOffset` and `flatMapBias`. Neither height generator touches the Unity stream, so heights depend only on the seed and `MapParameters`. Flat tile prefabs come from `StageTilePrefabs.flatTilePrefabs` and map-specific tiles such as the Graveyard `CoffinTile` from `mapSpecificTilesPrefabs`, placed by `GenerateTileObjects.MapSpecificTiles` (decompiled, 0x4962E0), which makes no random draws — it reads existing tile transforms and orients the extra pieces with `Quaternion.LookRotation`, so once the grid exists those tiles are fixed.

### Procedural-mesh maps (Desert, Hell)

The sequencer hands the per-run `mapSeed` to `MapGenerator.GenerateMap(MapData, StageData, int seed = 105)` (decompiled, 0x509EA0), which copies `StageData.proceduralTerrainData` (0xF8), `proceduralNoiseData` (0x100) and `proceduralMapScale` (0x108) into the component's own `terrainData`/`noiseData` fields and calls `GenerateMap(int seed)` (0x509B90). That runs `GeneratePerlinNoiseMap(seed)` (0x509F80) → `Noise.GenerateNoiseMap(mapWidth, mapHeight, seed, scale, octaves, persistance, lacunarity, blend, blendStrength, offset)` (0x51CED0), which constructs `new ConsistentRandom(seed)` and takes a `Next(-100000, 100000)` per-octave offset before each `Mathf.PerlinNoise`, then min/max-normalises the result; `FalloffGenerator.GenerateFalloffMap(size)` and `MeshGenerator.GenerateTerrainMesh(heightMap, heightMultiplier, heightCurve, lod)` follow, neither of which draws. So the terrain is a pure function of `mapSeed` plus the authored `TerrainData`/`NoiseData` assets, and the ScriptableObject numbers (scale, octaves, persistance, lacunarity, height curve) live in assets rather than the dump (dump). `MapGenerator` also has a private static `seed` field and an editor `drawMode`, which belong to the in-editor map preview path rather than the runtime call. Hell has no measurements here and is assumed to follow the same path, which is unverified.

### Props and interactables

`RandomMapObject` carries `amount` (0x10), `maxAmount` (0x14), `checkRadius`, `scaleMin` (0x1C), `scaleMax` (0x20), `maxSlopeAngle` (0x24), `upOffset` (0x28), `prefabs[]`, `randomRotationVector` and `alignWithNormal` (0x44). `GetAmount()` (decompiled, 0x4810F0) returns `amount` unchanged when `maxAmount` is 0 and otherwise draws `MyRandom.random.Next(amount, maxAmount + 1)`, so an entry with a fixed `amount` has a deterministic count. `RandomObjectPlacer.RandomObjectSpawner(RandomMapObject, float amountMultiplier = 1)` (decompiled, 0x49C2A0) computes `Mathf.RoundToInt(GetAmount() * amountMultiplier)`, adds `ItemBeacon.GetExtraShrines()` extras for shrine-kind entries, and then per instance: one float draw for a position inside the candidate box, `SpawnPositions.GetObjectSpawnPosition` (0x483470, 50 attempts, ground layer, `maxSlopeAngle`), `upOffset` scaled by a float draw along the hit normal, a prefab index from `Random.Range(0, prefabs.Length)`, and either `Quaternion.Euler` over the `scaleMin`/`scaleMax` ranges with three further float draws when `alignWithNormal` is false, or `Quaternion.LookRotation(normal)` when it is true; the instance's `localScale` is finally multiplied by a single float draw. `SpawnPositions` itself takes two float draws for the candidate point before raycasting. `SpawnInteractables` has `numChestsPerStage` 46, `numShrines` 14, `chestDensity`, `shrineDensity`, `chanceForFreeChest` and `numRails`; chest and shrine counts roll on `MyRandom.random`, and rails use only the Unity stream. Per-prefab values live in assets, not the dump.

### Crypt

`MapGenerationController.CryptGeneration(int seed, out Vector3 spawnPos, out Vector3 spawnDir)` (decompiled, 0x49A170) draws nothing itself: it forwards the seed to `RsgController.Generate(int newSeed, EDungeonType, out float traversalTime)` (0x50F6E0). That method replaces `newSeed` with `RsgController.customSeed` (statics 0x18) when `customSeed != 0` and `CanUseCustomSeed()` (0x50EC70) holds — which is `!ChallengesTracker.HasChallengeModifier(<name>)` (0x3FEC30), a single named challenge modifier whose string literal sits in the data section and was not read — and otherwise draws `UnityEngine.Random.Range(0, int.MaxValue)`. It then sets `isCurrentMapRandomSeed` (statics 0x28), stores the seed in `RsgController.seed` (statics 0x8) and rebuilds `RsgController.random` as `new ConsistentRandom(newSeed)`, so every room layout draw comes from that one seeded stream. The static constructor (0x50FDC0) defaults `seed` to 69420 and `customSeed` to 0, `SetCustomSeed` (0x50FD60) and the debug console command `SetSeedCrypt` (0x3D8F00) are the only writers, `HasCustomSeed` is `customSeed != 0` (0x50FEC0), and `GetSeed` (0x3D8A20) prints `RsgController.seed`. The room assembly itself (`RsgController.GetNextTransform`, `MirrorPiece`, `ReversePiece`, `FindMapLength`) consumes that `ConsistentRandom`; the piece sets are authored data.

### Enemies, minibosses and the boss

`StageTimeline` data decides what appears and when (`startEnemies`, `events`, `boss`, `minibosses`), and no seed field exists on it (dump). The runtime draws split across the two streams: `StageSummoner.AddEnemyToPoolAndPickNewCard` picks from the enemy pool with `UnityEngine.Random.Range(0, count)` (decompiled, 0x485DB0), while `BaseSummoner.GetRandomCard` (0x46CDD0) and `SummonerController.EventMiniboss` (0x487240) weight and select on `MyRandom.random`. `SummonerController.SpawnStageBoss` (0x487C20) offsets the boss position with `Random.insideUnitSphere`. `EnemyManager.SpawnBoss(EEnemy, int, EEnemyFlag, Vector3, float)` resolves the enemy data and calls the positional `EnemyManager.SpawnEnemy` overload at 0x41A3F0; it is not a coroutine wrapper (dump signature and decompiled, 0x41A200).

### What stays random in an authored from-scratch level

A from-scratch level skips the maze, heights, prop placers and stock `Spawn*` methods, so authored terrain and prop transforms are determined by the file. Its seed also controls the mod's extra-shrine planning/placement and boss-pool selection streams. Skipping `GenerateTileObjects.Generate` skips the boss spawner and its random tile pick, so the file's `bossSpawner` replaces it. These remain outside that custom seed contract:

- Enemy pool picks, which use the Unity global stream (`StageSummoner.AddEnemyToPoolAndPickNewCard`, decompiled).
- Card draws and miniboss rolls, which use `MyRandom.random`, seeded once per process (decompiled).
- The stage boss position offset, `Random.insideUnitSphere` in `SummonerController.SpawnStageBoss` (decompiled).
- The crypt layout: on a Graveyard map the room layout is re-rolled from the per-run `mapSeed` unless `RsgController.customSeed` is set, and `InteractableCrypt.Teleport` re-seeds `RsgController` from `mapSeed` when the player enters (decompiled).
- Grass chunk placement, which draws from the Unity stream as chunks stream in (decompiled, 0x3352E0).
- Successful extra-shrine placement, which still depends on live physics clearance despite seeded plans and placement draws.
- Interactable relocation, drawn from the mod's private random source.
- Chest loot and any other consumer of `UnityEngine.Random` during play.

### Unknowns

1. The residual Forest `objectsHash` drift on the Proton build. Every candidate left in the binary is a shared consumer of `UnityEngine.Random` or `MyRandom.random` running between the mod's reseed prefixes; isolating it needs a live measurement with the phases instrumented individually.
2. Whether the terrain on a `ProceduralMesh` map really reproduces for a fixed seed. The decompile says the heightmap is a pure function of `mapSeed` and the authored noise assets, but no run has hashed a mesh terrain — the Desert rows above hash tile lists, not terrain.
3. Whether `MapGenerator.GenerateMap(MapData, StageData, int)` can be seeded by a Harmony prefix in practice (the parameter is a value passed from the sequencer; untried).
4. The exact composition of `System.Random.GenerateSeed` (0x14F8630), which decides `MyRandom.random`'s unseeded value. It is BCL code that locks a shared `Random` and takes a value from it alongside a GUID-derived value; the precise mix was not followed, and it does not matter unless the mod starts seeding that field itself.
5. The `ChallengesTracker.HasChallengeModifier` name that `RsgController.CanUseCustomSeed` tests, and therefore when a crypt honours `customSeed` (the string literal was not read).
6. `SpawnInteractables.SetArea` and `RandomObjectPlacer.GenerateInteractables` have no direct call sites; whoever calls them determines whether their draws land between the mod's reseed prefixes.
7. Hell and Dungeon (`MapData.eMap` 64 and 16) have no measurements; which branch each takes at runtime is inferred from `mapType` only.
