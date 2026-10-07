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

### `ObjectTarget`: genId vs. placement id

`MoveObject`/`RemoveObject` reference an existing object through `ObjectTarget`, which distinguishes two kinds:

- **`GenId`** — an opaque string identifying a generator-spawned object, using a `{category}:{sequentialIndex}` scheme; treated here as an opaque non-blank string.
- **`PlacementId`** — a non-negative `int` identifying an object the editor itself placed via a `PlaceObject` op, scoped to the edit list (assigned incrementally by `EditStack` as `PlaceObject` ops are appended). `PlaceObject` itself carries no target — its identity is assigned by whatever appends it to the edits list, not by this op.

`ObjectTarget.Serialize()`/`Parse()` encode these onto `EditOp.Target` as `gen:<genId>` or `placement:<id>`.

### Validation convention

Every op type's constructor throws on invalid input — `ArgumentException` for logical/format errors (e.g. a malformed `catalogId`, a non-positive scale component, an undefined `SlopeDirection`), or its `ArgumentOutOfRangeException` subclass for out-of-range numeric input (negative tile coordinates, a negative placement id). Catching `ArgumentException` covers both. There is no `Result`/error-code type: construction failure here always means the caller passed data that can never be valid, not a recoverable runtime condition. `PlaceObject.CatalogId` stays a plain `string` in the schema (no JSON shape change) but its constructor now validates it with `CatalogId.Parse` (below) instead of a non-blank-only placeholder.

### `catalogId` format

`src/MegabonkLevels.Mod/catalog_id.cs` defines `CatalogId`, a purely syntactic parser/validator for the strings `PlaceObject` uses to reference a placeable prefab. It does not know which map/stage/category names are real — that catalog-building concern belongs to whatever populates the editor's object palette (TASK-004/TASK-005) — it only enforces the grammar below.

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

`Bundle` is reserved for TASK-007's custom AssetBundle packs — nothing produces these ids yet, but the grammar accepts them now so TASK-007 doesn't need to revisit this validator.

**Game-asset segment shapes**, cross-checked against TASK-002's confirmed catalog organization (`DataManager.Instance.maps[] : MapData` → `stages[] : StageData` → `randomMapObjects[] : RandomMapObject` → `.prefabs[] : GameObject[]`; `StageData.stageTilePrefabs : StageTilePrefabs` with `flatTilePrefabs[]`/`mapSpecificTilesPrefabs[]`; `MapData.shrines[]`, map-scoped not stage-scoped; `SpawnInteractables`'s singular `chest`/`chestFree` fields and `rails[]`) rather than invented independently:

| shape | example | source |
| --- | --- | --- |
| `{map}/stage{N}/randomMapObjects/{objectIndex}/{prefabIndex}` | `forest/stage0/randomMapObjects/2/0` | `StageData.randomMapObjects[2].prefabs[0]` |
| `{map}/stage{N}/stageTilePrefabs/flat/{index}` | `desert/stage1/stageTilePrefabs/flat/3` | `StageData.stageTilePrefabs.flatTilePrefabs[3]` |
| `{map}/stage{N}/stageTilePrefabs/specific/{index}` | `graveyard/stage2/stageTilePrefabs/specific/1` | `StageData.stageTilePrefabs.mapSpecificTilesPrefabs[1]` |
| `{map}/shrines/{index}` | `forest/shrines/5` | `MapData.shrines[5]` |
| `interactable/chest`, `interactable/chestFree` | — | `SpawnInteractables.chest` / `.chestFree` (singular fields) |
| `interactable/rail/{index}` | `interactable/rail/2` | `SpawnInteractables.rails[2]` |

**Prefabs have no name field.** `RandomMapObject.prefabs`, `StageTilePrefabs`'s arrays, `MapData.shrines`, and `SpawnInteractables.rails` are all plain `GameObject[]` with nothing resembling a human-readable name — only an array index. The final segment of a game-asset id is therefore typically numeric, not a descriptive name; a `Tree_03`-style segment would have to come from a future name lookup this task doesn't build, not from the game's own data.

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

`src/MegabonkLevels.Mod/reachability_validator.cs` adds `ReachabilityValidator.Validate(LevelState, (int X, int Z) start)`, a BFS over `LevelState.Tiles` implementing the "chain/slope rule": two 4-adjacent tiles are connected if they're at the same height, or if they differ by exactly one and a slope bridges the step. It returns a `ReachabilityResult` exposing the full `Reachable` set, the `Unreachable` tiles (every grid tile minus `Reachable`), and `IsReachable(tile)` for a specific target (e.g. a boss portal). `Validate` throws `ArgumentException` if `start` isn't itself a tile in the grid.

**Slope ownership/direction assumption (pending confirmation).** The tile grid's shape and spacing are confirmed, but which tile "owns" a slope at a height step, and which way `SlopeDirection` points relative to travel direction, are not. This implementation assumes the *higher* of the two tiles carries the slope, and that `SlopeDirection` names the downhill direction (the direction you'd walk off the ramp toward the lower tile), independent of which direction you're currently traveling — this is what makes a slope-bridged step mutually reachable in both directions. A `TODO` comment on `ReachabilityValidator` flags this for revisiting once real runtime slope data is available.

`tests/MegabonkLevels.Tests/reachability_validator_tests.cs` covers: a flat grid (full reachability), a single slope-assisted one-step climb (both tiles mutually reachable), a cliff with no slope (two regions internally connected but mutually unreachable — the deliberate "unreachable tiles" case), a cliff fixed by chaining two slopes, spawn-to-boss-portal reachability both when true and false, and `Validate` throwing when the start tile doesn't exist.
