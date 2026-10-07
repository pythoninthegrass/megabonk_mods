# Level file format (TASK-003)

Documents the "seed + edits" level file schema and its migration mechanism. See [map-generation-determinism.md](map-generation-determinism.md) and [runtime-map-structure.md](runtime-map-structure.md) for why this model works and where its field values come from.

## Project layout decision (TASK-003.01, AC#1)

The Unity-free level-format core lives in `src/MegabonkLevels.Mod` alongside the existing TASK-002 files (`generation_report.cs`, `generation_hash.cs`, `placeholder_logic.cs`), compile-linked into `tests/MegabonkLevels.Tests` by relative path in that project's `.csproj` — the same pattern those files already established, not a new `src/MegabonkLevels.Core` project.

Reasoning: the Unity-free boundary is enforced by what a file references, not by which project it physically sits in — these files simply don't reference `UnityEngine`/`Il2Cpp*` types, and the compile-link into the net10.0 xunit project (which has no access to those assemblies at all) is itself the proof that the boundary holds. A dedicated Core project would duplicate MSBuild plumbing (the `Directory.Build.props` Mods-folder deploy target, the MelonLoader/Il2Cpp `HintPath` references) for no additional isolation, since the Mod project's `csproj` already only references those assemblies for the files that need them.

One consequence of staying in the same project: the Mod project compiles against `net6.0` with `<Nullable>disable</Nullable>` (required because the Il2Cpp-generated assemblies ship a broken `NullableAttribute` constructor — see that csproj's comment). Level-format types must avoid `T?` reference-type annotations and avoid record **classes** (whose compiler-synthesized `Equals(T? other)` requires nullable-attribute metadata even under `disable`); `record struct` does not have this problem, since struct equality members take the type non-nullably. `LevelFile` is therefore a `readonly record struct`, not a `record class`.

## Schema (AC#2)

`LevelFile` (`src/MegabonkLevels.Mod/level_file.cs`), serialized with `System.Text.Json` using `JsonNamingPolicy.CamelCase` (`level_file_serialization.cs`):

| field | type | meaning |
| --- | --- | --- |
| `schemaVersion` | `int` | Current value: `LevelFile.CurrentSchemaVersion` (`1`). |
| `gameBuildId` | `string` | Game build the level was authored against (e.g. `"1.0.69"`). Compared against the running game's build by TASK-004 for staleness warnings; not interpreted here. |
| `map` | `EMap` | Mirrors the game's `EMap` flags enum by value (`None=0, Forest=1, Desert=2, Hell=4, Graveyard=8`, confirmed against `.tools/il2cpp_dump/dump.cs`) — a value-level mirror, not a reference to the real Il2Cpp type, since this library must stay Unity/Il2Cpp-free. |
| `stageIndex` | `int` | Which stage within the map. |
| `tier` | `int` | Difficulty tier. |
| `seed` | `int` | **The Tiles-map `debugSeed`** (see [map-generation-determinism.md](map-generation-determinism.md)) — the only field confirmed to control reproducible generation. **Never** `MapGenerationController.mapSeed`: that field varies freely per run and has no effect on layout. `ProceduralMesh` maps (Desert) don't yet have a confirmed-controllable seed field at all; storing a `seed` for those maps is "reproducible in practice so far" per that doc, not guaranteed. |
| `edits` | `EditOp[]` | Ordered list of edit operations applied on top of the generated map. TASK-003.02 defines the real typed operation set; `EditOp(OpType, Target, Payload)` here is a minimal placeholder shape (string opcode + string target id + a JSON-string payload) that already round-trips and migrates correctly, so TASK-003.02 can replace the payload's shape without touching the root schema or migration mechanism. |

## Migration mechanism (AC#3)

`SchemaMigrator.Migrate` (`level_file_migration.cs`) takes a parsed `JsonObject`, a target version, and a `IReadOnlyDictionary<int, MigrationStep>` keyed by *from*-version. It loops: look up the step registered for the document's current `schemaVersion`, apply it (the step returns a new `JsonObject` with its own, incremented `schemaVersion`), repeat until the target version is reached. Reaching a version with no registered step throws.

`LevelFileSerializer.DeserializeWithMigration` (`level_file_serialization.cs`) calls this with `LevelFile.CurrentSchemaVersion` and a `ProductionSteps` dictionary that is **empty today** — schema version 1 is the only version that has ever shipped, so there is nothing to migrate from yet. Adding a real version 2 later means adding one `[1] = step` entry to `ProductionSteps`; the loop and the public API do not change.

Since there is no real version 2 to migrate from/to yet, the mechanism itself is exercised directly in `tests/MegabonkLevels.Tests/level_file_tests.cs` (`SchemaMigrator_AppliesRegisteredStepUntilTargetVersionReached`) with a synthetic, test-local step (renaming a field and bumping to a made-up version `2`) — this proves the loop/registry mechanism works without implying a real version 2 schema exists. `SchemaMigrator_MissingStepForOlderVersion_Throws` covers the "no step registered" failure path.

## Round-trip (AC#4)

`LevelFileSerializer.Serialize`/`Deserialize` round-trip a `LevelFile` through `System.Text.Json`; `level_file_tests.cs`'s `RoundTrip_SerializeThenDeserialize_ProducesEqualLevel` covers this. `LevelFile` overrides `Equals`/`GetHashCode` to compare `Edits` by sequence (the default record-struct equality would otherwise compare the `IReadOnlyList<EditOp>` reference, which differs after a deserialize produces a new list instance).
