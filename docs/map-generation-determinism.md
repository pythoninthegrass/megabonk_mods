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
