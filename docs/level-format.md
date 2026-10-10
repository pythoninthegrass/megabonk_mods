# Level file format

Documents the "seed + edits" level file schema and its migration mechanism. See [map-generation-determinism.md](map-generation-determinism.md) and [runtime-map-structure.md](runtime-map-structure.md) for why this model works and where its field values come from.

## Project layout

The Unity-free level-format core lives in `src/MegabonkLevels.Mod` alongside the Unity-free generation-report/hash files (`generation_report.cs`, `generation_hash.cs`, `placeholder_logic.cs`), compile-linked into `tests/MegabonkLevels.Tests` by relative path in that project's `.csproj`, rather than a separate `src/MegabonkLevels.Core` project.

Reasoning: the Unity-free boundary is enforced by what a file references, not by which project it physically sits in — these files simply don't reference `UnityEngine`/`Il2Cpp*` types, and the compile-link into the net10.0 xunit project (which has no access to those assemblies at all) is itself the proof that the boundary holds. A dedicated Core project would duplicate MSBuild plumbing (the `Directory.Build.props` Mods-folder deploy target, the MelonLoader/Il2Cpp `HintPath` references) for no additional isolation, since the Mod project's `csproj` already only references those assemblies for the files that need them.

One consequence of staying in the same project: the Mod project compiles against `net6.0` with `<Nullable>disable</Nullable>` (required because the Il2Cpp-generated assemblies ship a broken `NullableAttribute` constructor — see that csproj's comment). Level-format types must avoid `T?` reference-type annotations and avoid record **classes** (whose compiler-synthesized `Equals(T? other)` requires nullable-attribute metadata even under `disable`); `record struct` does not have this problem, since struct equality members take the type non-nullably. `LevelFile` is therefore a `readonly record struct`, not a `record class`.

## Schema

`LevelFile` (`src/MegabonkLevels.Mod/level_file.cs`), serialized with `System.Text.Json` using `JsonNamingPolicy.CamelCase` (`level_file_serialization.cs`):

| field | type | meaning |
| --- | --- | --- |
| `schemaVersion` | `int` | Current value: `LevelFile.CurrentSchemaVersion` (`1`). |
| `gameBuildId` | `string` | Game build the level was authored against (e.g. `"1.0.69"`). Compared against the running game's build for staleness warnings during runtime playback; not interpreted here. |
| `map` | `EMap` | Mirrors the game's `EMap` flags enum by value (`None=0, Forest=1, Desert=2, Hell=4, Graveyard=8`, confirmed against `.tools/il2cpp_dump/dump.cs`) — a value-level mirror, not a reference to the real Il2Cpp type, since this library must stay Unity/Il2Cpp-free. |
| `stageIndex` | `int` | Which stage within the map. |
| `tier` | `int` | Difficulty tier. |
| `seed` | `int` | **The Tiles-map `debugSeed`** (see [map-generation-determinism.md](map-generation-determinism.md)) — the only field confirmed to control reproducible generation. **Never** `MapGenerationController.mapSeed`: that field varies freely per run and has no effect on layout. `ProceduralMesh` maps (Desert) don't yet have a confirmed-controllable seed field at all; storing a `seed` for those maps is "reproducible in practice so far" per that doc, not guaranteed. |
| `edits` | `EditOp[]` | Ordered list of edit operations applied on top of the generated map. `EditOp(OpType, Target, Payload)` is a minimal shape (string opcode + string target id + a JSON-string payload) that round-trips and migrates correctly independent of any particular operation's payload shape — see "Edit operation types" below. |

## Migration mechanism

`SchemaMigrator.Migrate` (`level_file_migration.cs`) takes a parsed `JsonObject`, a target version, and a `IReadOnlyDictionary<int, MigrationStep>` keyed by *from*-version. It loops: look up the step registered for the document's current `schemaVersion`, apply it (the step returns a new `JsonObject` with its own, incremented `schemaVersion`), repeat until the target version is reached. Reaching a version with no registered step throws.

`LevelFileSerializer.DeserializeWithMigration` (`level_file_serialization.cs`) calls this with `LevelFile.CurrentSchemaVersion` and a `ProductionSteps` dictionary that is **empty today** — schema version 1 is the only version that has ever shipped, so there is nothing to migrate from yet. Adding a real version 2 later means adding one `[1] = step` entry to `ProductionSteps`; the loop and the public API do not change.

Since there is no real version 2 to migrate from/to yet, the mechanism itself is exercised directly in `tests/MegabonkLevels.Tests/level_file_tests.cs` (`SchemaMigrator_AppliesRegisteredStepUntilTargetVersionReached`) with a synthetic, test-local step (renaming a field and bumping to a made-up version `2`) — this proves the loop/registry mechanism works without implying a real version 2 schema exists. `SchemaMigrator_MissingStepForOlderVersion_Throws` covers the "no step registered" failure path.

## Round-trip

`LevelFileSerializer.Serialize`/`Deserialize` round-trip a `LevelFile` through `System.Text.Json`; `level_file_tests.cs`'s `RoundTrip_SerializeThenDeserialize_ProducesEqualLevel` covers this. `LevelFile` overrides `Equals`/`GetHashCode` to compare `Edits` by sequence (the default record-struct equality would otherwise compare the `IReadOnlyList<EditOp>` reference, which differs after a deserialize produces a new list instance).

## Edit operation types

`src/MegabonkLevels.Mod/edit_operations.cs` defines seven typed edit operations that replace `EditOp`'s placeholder payload shape, each a Unity-free `readonly record struct` with a validating constructor plus a `ToEditOp()`/static `FromEditOp(EditOp)` pair that (de)serializes the op's fields to/from `EditOp.Payload` (a `System.Text.Json` camelCase JSON string) and, for object ops that reference an existing object, `EditOp.Target`:

| op type | `EditOp.OpType` | fields | `EditOp.Target` |
| --- | --- | --- | --- |
| `SetTileHeight` | `tile.setHeight` | `X, Z, Height` | unused (`""`) |
| `SetTileSlope` | `tile.setSlope` | `X, Z, Direction` (`SlopeDirection`: `None, North, South, East, West`) | unused (`""`) |
| `AddTile` | `tile.add` | `X, Z, Height` | unused (`""`) |
| `RemoveTile` | `tile.remove` | `X, Z` | unused (`""`) |
| `PlaceObject` | `object.place` | `CatalogId, Position, Rotation, Scale` (`Vector3Data`) | unused (`""`) |
| `MoveObject` | `object.move` | `Target` (`ObjectTarget`), `NewTransform` (`TransformData`) | `Target.Serialize()` |
| `RemoveObject` | `object.remove` | `Target` (`ObjectTarget`) | `Target.Serialize()` |

Tile ops identify the tile by grid coordinates carried in the payload, so they have no need of `EditOp.Target`; object ops that mutate an *existing* object carry their target there instead, so an op can be filtered/routed by `EditOp.Target` alone without deserializing the payload.

Tile ops apply on top of the generated grid, not an empty one. At generation the mod snapshots every live tile's height and slope into a baseline `LevelState`, and `LiveEditPlan.Build(edits, baseline)` replays the edits on a copy of it. `SetTileHeight` therefore keeps a cell's generated slope, and `SetTileSlope` keeps its generated height. Generation is deterministic for a seed, so the same file produces the same baseline, and a level loads exactly as it looked when it was edited. `AddTile` always places a flat tile. An `EditStack` built on an empty `LevelState` still falls back to height 0 and no slope for a cell it has no record of.

### `ObjectTarget`: genId vs. placement id

`MoveObject`/`RemoveObject` reference an existing object through `ObjectTarget`, which distinguishes two kinds:

- **`GenId`** — an opaque string identifying a generator-spawned object, using a `{category}:{sequentialIndex}` scheme; treated here as an opaque non-blank string.
- **`PlacementId`** — a non-negative `int` identifying an object the editor itself placed via a `PlaceObject` op, scoped to the edit list (assigned incrementally by `EditStack` as `PlaceObject` ops are appended). `PlaceObject` itself carries no target — its identity is assigned by whatever appends it to the edits list, not by this op.

`ObjectTarget.Serialize()`/`Parse()` encode these onto `EditOp.Target` as `gen:<genId>` or `placement:<id>`.

### Validation convention

Every op type's constructor throws on invalid input — `ArgumentException` for logical/format errors (e.g. a malformed `catalogId`, a non-positive scale component, an undefined `SlopeDirection`), or its `ArgumentOutOfRangeException` subclass for out-of-range numeric input (negative tile coordinates, a negative placement id). Catching `ArgumentException` covers both. There is no `Result`/error-code type: construction failure here always means the caller passed data that can never be valid, not a recoverable runtime condition. `PlaceObject.CatalogId` stays a plain `string` in the schema (no JSON shape change) but its constructor now validates it with `CatalogId.Parse` (below) instead of a non-blank-only placeholder.

### `catalogId` format

`src/MegabonkLevels.Mod/catalog_id.cs` defines `CatalogId`, a purely syntactic parser/validator for the strings `PlaceObject` uses to reference a placeable prefab. It does not know which map/stage/category names are real — that catalog-building concern belongs to `PaletteCatalogBuilder`, which populates the editor's object palette (see "Catalog palette" in `development.md`) — it only enforces the grammar below.

Two namespaces, distinguished by a `bundle:` prefix:

| namespace | form | example |
| --- | --- | --- |
| `GameAsset` (default) | `segment/segment{/segment...}` (>= 2 segments, no prefix) | `interactable/chest` |
| `Bundle` | `bundle:segment/segment{/segment...}` (>= 2 segments after the prefix) | `bundle:mypack/props/rock` |

Rules, checked in this order by `CatalogId.TryParse`/`Parse`:

1. The raw string must not be null/empty/whitespace-only.
2. If it starts with `bundle:`, the namespace is `Bundle` and the rest is parsed as segments. Otherwise, if it contains a `:` anywhere, it's rejected as an unknown namespace prefix — `:` is reserved exclusively for the `bundle:` prefix, so a game-asset id must never contain one.
3. The (post-prefix) body is split on `/`. Every segment must be non-empty (catches a leading/trailing/doubled `/`) and match `^[A-Za-z0-9_-]+$` (letters, digits, `_`, `-` only).
4. At least 2 segments are required in both namespaces.

`Bundle` is reserved for future custom AssetBundle packs — nothing produces these ids yet, but the grammar accepts them now so a future pack-loading feature doesn't need to revisit this validator.

**Game-asset segment shapes**, cross-checked against the confirmed runtime catalog organization (`DataManager.Instance.maps[] : MapData` → `stages[] : StageData` → `randomMapObjects[] : RandomMapObject` → `.prefabs[] : GameObject[]`; `StageData.stageTilePrefabs : StageTilePrefabs` with `flatTilePrefabs[]`/`mapSpecificTilesPrefabs[]`; `MapData.shrines[]`, map-scoped not stage-scoped; `SpawnInteractables`'s singular `chest`/`chestFree` fields and `rails[]`) rather than invented independently:

| shape | example | source |
| --- | --- | --- |
| `{map}/stage{N}/randomMapObjects/{objectIndex}/{prefabIndex}` | `forest/stage0/randomMapObjects/2/0` | `StageData.randomMapObjects[2].prefabs[0]` |
| `{map}/stage{N}/stageTilePrefabs/flat/{index}` | `desert/stage1/stageTilePrefabs/flat/3` | `StageData.stageTilePrefabs.flatTilePrefabs[3]` |
| `{map}/stage{N}/stageTilePrefabs/specific/{index}` | `graveyard/stage2/stageTilePrefabs/specific/1` | `StageData.stageTilePrefabs.mapSpecificTilesPrefabs[1]` |
| `{map}/shrines/{index}` | `forest/shrines/5` | `MapData.shrines[5]` |
| `interactable/chest`, `interactable/chestFree` | — | `SpawnInteractables.chest` / `.chestFree` (singular fields) |
| `interactable/rail/{index}` | `interactable/rail/2` | `SpawnInteractables.rails[2]` |

**Prefabs have no name field.** `RandomMapObject.prefabs`, `StageTilePrefabs`'s arrays, `MapData.shrines`, and `SpawnInteractables.rails` are all plain `GameObject[]` with nothing resembling a human-readable name — only an array index. The final segment of a game-asset id is therefore typically numeric, not a descriptive name; the palette shows each prefab's GameObject name next to its id, but the id itself stays index-based.

`tests/MegabonkLevels.Tests/catalog_id_tests.cs` covers valid ids in both namespaces (including every shape above) and a table-driven set of malformed inputs (empty/whitespace, unknown namespace prefix, empty segment from a leading/trailing/doubled `/`, invalid characters, too few segments), each asserted against its specific failure reason.

### JSON round-trip inside `LevelFile.Edits`

`tests/MegabonkLevels.Tests/edit_operations_tests.cs` covers valid/invalid construction and `ToEditOp`/`FromEditOp` round-trips for every op type individually, plus `EditOperationsInLevelFileTests.AllSevenOpTypes_RoundTripInsideLevelFileEditsArray`, which builds a `LevelFile` whose `Edits` contains one of each op type, round-trips the whole file through `LevelFileSerializer`, and recovers every original op from the deserialized `EditOp`s — proving the typed ops are compatible with the schema and migration mechanism without any change to `LevelFile` or `SchemaMigrator`.

## `LevelState` and `EditStack`

`src/MegabonkLevels.Mod/level_state.cs` adds `LevelState`: a Unity-free, mutable in-memory model of a tile grid (`Dictionary<(int X, int Z), TileState>`, `TileState(Height, Slope)`) plus an object-override table (`Dictionary<ObjectTarget, ObjectState>`, `ObjectState(Removed, CatalogId, Transform)`). It is the "current materialized level" that `EditOp`s accumulate into; `LevelFile.Edits` is the serialized log that produces it by replay.

`src/MegabonkLevels.Mod/edit_stack.cs` adds `EditStack(LevelState)`, which applies `EditOp`s to that state with undo/redo:

- `Apply(op)` parses the op to its typed form, mutates `LevelState`, pushes an undo/redo pair onto the undo stack, and clears the redo stack.
- `Undo()`/`Redo()` pop from their respective stacks and push onto the other; both return `false` (no-op, not an exception) when their stack is empty.

**Inverse design.** Every op's undo/redo pair is built by capturing whatever `LevelState` record (if any) the op is about to overwrite, *before* mutating:

- If no record existed at that key, undo deletes the key entirely (back to "no edit has ever touched this", not a synthesized default) — this is what makes undoing a `MoveObject`/`RemoveObject` applied to a generator (`GenId`) object well-defined even though `LevelState` never knew that object's generator-assigned transform.
- If a record existed, undo restores it verbatim, including fields the forward op didn't touch (e.g. undoing `SetTileHeight` restores the prior height *and* keeps whatever slope was already there; undoing `MoveObject` on a placed object restores its prior transform without losing its `CatalogId`).
- `PlaceObject` carries no target of its own (see above) — `EditStack` allocates one `LevelState.AllocatePlacementId()` per `Apply`, once, and reuses that same id across its own undo/redo; the id is never reused by a later `PlaceObject` even if this one is undone, since `LevelState`'s counter only increments.

`tests/MegabonkLevels.Tests/edit_stack_tests.cs` covers: single-apply state for every op type, undo/redo restoring exact prior records (including the "no prior record" deletion case for both tiles and objects), undo on an empty stack being a no-op, apply-after-undo clearing the redo stack, and a multi-step apply/undo/undo/redo/redo sequence.

## `ReachabilityValidator`

`src/MegabonkLevels.Mod/reachability_validator.cs` adds `ReachabilityValidator.Validate(LevelState, (int X, int Z) start)`, a BFS over `LevelState.Tiles`. Two 4-adjacent tiles are connected when the heights of the edges that face each other are equal. It returns a `ReachabilityResult` exposing the full `Reachable` set, the `Unreachable` tiles (every grid tile minus `Reachable`), and `IsReachable(tile)` for a specific target (e.g. a boss portal). `Validate` throws `ArgumentException` if `start` isn't itself a tile in the grid.

### Slope semantics

A tile's `Height` is the game's `ProceduralTile.posY`, and a slope is a separate tile prefab (`TileSlope`) at that height, not a flag on a flat tile. `SlopeDirection` names the **uphill** side of the slope and equals the game's `ProceduralTile.dir`: `North` is +Z (yaw 0), `East` +X (90), `South` -Z (180), `West` -X (270). A slope at height `h` spans `h` along its downhill edge to `h + 1` along its uphill edge, and its two side edges connect to nothing. Observed on 40 Forest slope tiles: the neighbour on the uphill side is always at `h + 1`, and the downhill neighbour is a flat tile at `h` or a slope whose own uphill edge is at `h`. A flat tile has the same height on all four edges, so a two-level climb is a chain of two slopes.

`tests/MegabonkLevels.Tests/reachability_validator_tests.cs` covers: a flat grid (full reachability), a single slope-assisted one-step climb (both tiles mutually reachable), a cliff with no slope (two regions internally connected but mutually unreachable — the deliberate "unreachable tiles" case), a cliff fixed by chaining two slopes, a slope entered from its side, a flat tile at the wrong height for a slope's edge, two slopes meeting at their uphill edges, spawn-to-boss-portal reachability both when true and false, and `Validate` throwing when the start tile doesn't exist.

## Runtime playback: loading a level file into a running game

`src/MegabonkLevels.Mod/level_loader_patch.cs` (`LevelLoaderPatch.LoadAndStart`) reads a `.mblevel.json` file with this schema's own `LevelFileSerializer.DeserializeWithMigration` (no separate reader — reusing the exact same reader this doc already describes) and starts a real run matching it:

1. Resolve the `MapData` whose `eMap` matches the file's `map` via `Resources.FindObjectsOfTypeAll<MapData>()` (ScriptableObject assets aren't reachable through a normal scene search), then index into `mapData.stages[stageIndex]` for the `StageData`.
2. Force the seed through `SeedForcePatch.ForceLevelSeed(level.Seed)` — a `LevelSeed` mode added to the existing F9 test-harness patch (`seed_force_patch.cs`), so there is exactly one Harmony prefix on `ProceduralTileGeneration.Generate` forcing `debugSeed`/`useDebugSeed` rather than two competing ones. This is the field confirmed to actually control Tiles-map generation; `MapGenerationController.mapSeed` is never touched.
3. Build a `RunConfig { mapData, stageData, mapTierIndex = level.Tier }` and start the run with `MapController.StartNewMap(runConfig)`.

`MapController.StartNewMap(RunConfig)` is confirmed live to be the right entry point: a `SceneTransitionProbe` Harmony postfix on it fired when a normal, manual map-select-and-confirm playthrough started a Forest run, immediately followed by `A_GenerationComplete`. The original hypothesis, `MapController.TestMap(RunConfig)`, does *not* start a run — calling it only sets `MapController.currentMap`/`currentStage`/`runConfig`; `MapController.IsMainMenu()` stays `true` before and after the call, and no generation follows. `TestMap` is exposed for a different purpose than reusing the normal in-run flow and must not be used here.

A hardcoded hotkey (F6, `MegabonkLevelsMod.OnUpdate`) loads a fixed file name (`megabonklevels-test-level.mblevel.json`) from MelonLoader's `Mods` directory (`MelonEnvironment.ModsDirectory`) — a manually-placed test file is sufficient; loading an arbitrary user-chosen path is not implemented. F10 was tried first and rejected: it collides with the game's own built-in debug console, which also toggles on F10 independently of mod code. `levels/example-forest.mblevel.json` in this repo is that test file's content (Forest, stage 0, tier 0, `debugSeed=20261007` — confirmed reproducible across three separate Forest generations — no edits); copy it into the game's `Mods` folder under the hotkey's expected name to use it.

**Reproducibility check (no new code needed):** `GenerationPatch` already logs a SHA-256 hash of every spawned tile/object's transform on every `A_GenerationComplete`, regardless of what triggered generation. Pressing F6 from the main menu, waiting for generation to finish, and repeating a couple more times and diffing the `hash=` values in `Latest.log` is the verification that the forced seed actually reproduces the same map — confirmed live across three separate loads, all producing the identical hash despite each run's irrelevant random `mapSeed` differing.

**Harmony patch safety note:** before adding a Harmony patch target, check that its RVA in `.tools/il2cpp_dump/dump.cs` is unique (`grep -c "RVA: 0x<addr> "`). `MapMenu.StartMap`'s RVA was shared by 1,453 other methods — a linker-folded trivial/empty-body address — and patching it crashed the game immediately by intercepting every one of those unrelated call sites. Also never patch a core Unity engine method (e.g. `UnityEngine.SceneManagement.SceneManager.LoadScene`) rather than game code; those are native icalls IL2CPP interop can't safely hook the way it hooks the game's own compiled methods.

### `gameBuildId` staleness check

`src/MegabonkLevels.Mod/game_build_id_check.cs` (`GameBuildIdCheck.MismatchWarning`, Unity-free and unit-tested) compares the level file's `gameBuildId` against the running game's actual build id and returns a human-readable warning string (or `null` if they match or the file has no recorded id). `src/MegabonkLevels.Mod/game_build_id_patch.cs` supplies the actual value via `Il2CppSteamworks.SteamApps.GetAppBuildId()` — the game links Steamworks.NET and SteamAPI is already initialized by the game itself before any mod code runs, so this needs no initialization of its own. A mismatch logs a warning and the run still starts; it never blocks or crashes, since a stale build id means the saved layout *may* not reproduce exactly, not that it definitely won't.

### Applying edits to the live game

After `LevelLoaderPatch` forces the seed it hands `level.Edits` to `LiveEditPatch.SetPendingEdits`; the next `A_GenerationComplete` consumes them (and clears them, so a later vanilla run is never edited). `src/MegabonkLevels.Mod/live_edit_plan.cs` (`LiveEditPlan.Build`, Unity-free and unit-tested) replays the edits through a fresh `EditStack`/`LevelState` and flattens them into ordered `LiveAction`s, so op semantics (resulting tile state, monotonic placement ids) live in one place. `src/MegabonkLevels.Mod/live_edit_patch.cs` runs those actions against the live objects:

| action | live effect |
| --- | --- |
| `SetTile` | `TilePlacement.Decide` compares the live tile (flat or slope, slope direction read from `ProceduralTile.dir`) with the target `TileState`. Same kind: sets `posY` and moves the transform to `height * MapParameters.scaledTileHeight` on Y. Different kind, or an empty cell: instantiates `ProceduralTileGeneration.slopeTile` or `flatTile` through the game's own `InstantiateTile(cell, height, prefab, dir, parentDir)` (which positions the tile from `MapParameters.scaledTileWidth`), destroys the old tile, and updates `proceduralTiles[x][z]` and `tiles`; the grid cell is `proceduralTiles[x][z]` |
| `RemoveTile` | destroys the tile GameObject, drops it from `tiles` and `flatTiles`, and nulls its grid cell |
| `SpawnObject` | resolves `catalogId` through `src/MegabonkLevels.Mod/catalog_route.cs` into the game's own prefab arrays and instantiates it at the given transform; registered as `placement:N` |
| `MoveObject` / `RemoveObject` | resolves `gen:<genId>` against the live index or `placement:N` against objects spawned by this edit list |

Known limits: `AddTile` outside the `size x size` grid logs a warning and does nothing. A replacement flat tile reuses the previous tile's direction, or faces +Z in an empty cell. After the tile edits the mod regenerates the wall and fill pieces on every edge between an edited tile and an occupied neighbour, and rebuilds the baked ground collision; see "Walls after edits" and "Ground collision after edits" in [runtime-map-structure.md](runtime-map-structure.md). Edges against a removed cell are left as they were, so a removed tile leaves an open hole with the old walls around it standing or floating; the kill floor ends a fall into it. `catalogId` resolution works only for `Tiles` maps (the edit list is skipped, with a warning, when `proceduralTiles` is null), and `bundle:` ids are rejected.

### Suppressing Steam leaderboard, achievement, and stats writes

A custom or edited level's scores and progress must never reach Steam: the game keeps a server-side `banned_players` leaderboard, and a modded run didn't come from legitimate procedural generation. `src/MegabonkLevels.Mod/custom_level_state.cs` (`CustomLevelState`, Unity-free and unit-tested) tracks whether the *currently active* run was started through `LevelLoaderPatch` rather than the game's own menu: `LoadAndStart` calls `MarkPendingStart()` immediately before `MapController.StartNewMap`, and a Harmony prefix on that same method (`custom_level_state_patch.cs`, `CustomLevelStatePatch`) — the single entry point both the normal menu flow and the mod funnel through, per the `SceneTransitionProbe` finding above — calls `OnRunStarting()`, which resolves whatever is pending into `IsActive` and clears the pending flag. This is a one-flag, consume-on-start state machine: a normal run always re-resolves to `IsActive = false`, even immediately after a custom-level run, so there is one source of truth instead of separate "did we mod this" bookkeeping at each call site. It logs `CustomLevelState: run starting, IsActive=<bool>` on every run start, modded or not.

`src/MegabonkLevels.Mod/steam_write_guard_patch.cs` (`SteamWriteGuard`) Harmony-prefixes the four confirmed write paths and returns `false` (cancelling the original call) whenever `CustomLevelState.IsActive`, logging `SteamWriteGuard: suppressed <call> (custom-level run active)` each time — otherwise it returns `true` and the original call runs exactly as before. Targets, confirmed against `.tools/il2cpp_dump/dump.cs` (all RVAs unique, so safe to patch per the RVA-sharing note above):

| class.method | namespace | why this one |
| --- | --- | --- |
| `SteamLeaderboardsManagerNew.QueueLeaderboardUpload` | *(global)* | queues a score for a leaderboard, including the `kills`/`kills_weekly` boards that feed `banned_players` |
| `SteamLeaderboardsManagerNew.UploadLeaderboardScore` | *(global)* | the queue's own upload call; guarded independently in case anything calls it directly |
| `SteamAchievementsManager.TryUnlockAchievement` | `Assets.Scripts.Steam` | the only public write entry point — the unlock check and the upload queueing both happen inside it |
| `SteamStatsManager.OnStatUpdated` (private) | `Assets.Scripts.Steam` | the bridge subscribed to `MyStats.A_StatUpdated` that caches a local stat change for Steam upload; blocking it here leaves the game's own local progression (`MyStats`/`RunStats`) untouched and only suppresses the Steam-bound copy |

Live-verified on the CrossOver reference platform: loading the test level file logs `CustomLevelState: run starting, IsActive=True` immediately after `LevelLoader: starting ...`, and an idle, invulnerable run (`scripts/run.py invulnerable`) suppressed over 200 `SteamStatsManager.OnStatUpdated` calls in under a minute with no errors or exceptions. The leaderboard and achievement prefixes were not exercised live in this pass — those fire on rarer events (run completion, specific achievement thresholds) that a full playthrough is better placed to hit — but are structurally identical guards confirmed to compile against the real game assembly.

## Regression check: the full-playthrough test level

`levels/task-004-05-regression.mblevel.json` is a hand-written Forest level (seed `20261007`, a debugSeed confirmed reproducible) that exercises all six edit op types in one file, as an integration acceptance check for the whole live-editing pipeline. Re-run it after a game update, or after a future editor UI starts producing real edit lists, to confirm the live-application pipeline still works end to end.

| cell / target | op(s) | effect |
| --- | --- | --- |
| (10,5) | `SetTileHeight` -> 1, then `SetTileSlope` -> None | the generated West slope at level 0 raised one level and flattened (`TileGround` replaces `TileSlope`) |
| (9,7) | `SetTileHeight` -> 0, then `SetTileSlope` -> East | the generated North slope at level -1 raised to level 0 and turned East, yaw 90 |
| (11,7) | `RemoveTile` then `AddTile` -> height 1 | the only way to exercise `AddTile` on a truly empty cell (the live grid is dense, so a cell must be vacated first); ends as a raised flat tile |
| (13,7) | `RemoveTile` | left removed — a real hole with the kill floor armed under it |
| world (80, 0, 80) | `PlaceObject` `interactable/chest` | a chest placed independent of any tile edit |
| `gen:object:Tree0:0010` | `RemoveObject` | deletes one generator-spawned tree |

Tile ops replay on the generated grid (see "Edit operation types"), so the explicit `SetTileSlope` -> None and `SetTileHeight` -> 0 pin both cells to the shape the playthrough below was verified on.

(11,7)/(9,7)/(13,7) reuse coordinates already playtested clean as a scratch level (enemies crossed the raised and sloped tiles without sticking, and were killed by the kill floor after falling into the hole).

**Observed during a full playthrough:** the removed cell (13,7) sits on a path the Forest stage boss happens to roam, and in one run the boss wandered into the hole and was killed by the kill floor. The boss portal still activated normally and the run continued — the early death did not block anything. This is useful confirmation that the kill floor handles a boss-tier actor correctly (see "Kill floor" above). Separately, tier 1 has no win/finish screen by the game's own design, so "a complete run" on this level means reaching and activating the boss portal, not beating the game.

### Re-running the automated part

```sh
uv run scripts/run.py enable   # once; relaunch the game after
uv run scripts/run.py load levels/task-004-05-regression.mblevel.json
```

Then check `MelonLoader/Latest.log` for:

- `LiveEdit: applied 9 edit(s)` with no `WARNING` lines about the edits themselves, immediately followed by `FillRegeneration`, `CollisionRebuild` and `KillFloor: armed` with no errors.
- No `error`/`exception` lines for the rest of the session.
- `SteamWriteGuard: suppressed ...` lines appearing (and no unsuppressed `QueueLeaderboardUpload`/`UploadLeaderboardScore`/`TryUnlockAchievement` lines) once `run.py invulnerable` lets the run continue — `CustomLevelState: run starting, IsActive=True` confirms the guard is armed for this run.

`run.py freeze` plus `run.py camera X Y Z --rot 90 0 0` pointed at each cell's own logged world position (printed by the `LiveEdit:` lines above) gives a screenshot of that specific edit; a low altitude (50-60 units) and an angled rotation (e.g. `35 335 0`) shows the raised/removed tiles' cliff walls, since a straight-down shot alone doesn't show elevation.

### Human playthrough

The harness cannot press keys or move the player (see "Not covered" above), so the actual spawn-to-boss-portal run needs a person at the controls: load the level, play normally, and confirm enemies path across the raised, sloped and added tiles and into the removed cell without getting stuck, the chest and the missing tree are visibly correct, and the run completes with no crash. Turning on `run.py cells on` and `run.py heartbeat on` beforehand logs enemy cell transitions and kill-floor activity during the run for a written record.

### Verification status

Verified on the CrossOver reference platform: automated checks (load, edit application, screenshots of each edit, idle-invulnerable survival with enemies approaching the edited cells) and a full human playthrough from spawn to the boss portal both passed. All six edit op types applied cleanly and were visually confirmed; enemies, including the stage boss, crossed and interacted with the edited terrain without getting stuck; the boss portal activated normally; and the run produced zero errors or exceptions and zero unsuppressed leaderboard/achievement/stats calls across the whole session (thousands of stats writes suppressed).
