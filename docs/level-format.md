# Level file format

Documents the "seed + edits" level file schema and its migration mechanism. See [map-generation-determinism.md](map-generation-determinism.md) and [runtime-map-structure.md](runtime-map-structure.md) for why this model works and where its field values come from.

## Project layout

The Unity-free level-format core lives in `src/MegabonkLevels.Mod` alongside the Unity-free generation-report/hash files (`generation_report.cs`, `generation_hash.cs`, `placeholder_logic.cs`), compile-linked into `tests/MegabonkLevels.Tests` by relative path in that project's `.csproj`, rather than a separate `src/MegabonkLevels.Core` project.

Reasoning: the Unity-free boundary is enforced by what a file references, not by which project it physically sits in — these files simply don't reference `UnityEngine`/`Il2Cpp*` types, and the compile-link into the net10.0 xunit project (which has no access to those assemblies at all) is itself the proof that the boundary holds. A dedicated Core project would duplicate MSBuild plumbing (the `Directory.Build.props` Mods-folder deploy target, the MelonLoader/Il2Cpp `HintPath` references) for no additional isolation, since the Mod project's `csproj` already only references those assemblies for the files that need them.

One consequence of staying in the same project: the Mod project compiles against `net6.0` with `<Nullable>disable</Nullable>` (required because the Il2Cpp-generated assemblies ship a broken `NullableAttribute` constructor — see that csproj's comment). Level-format types must avoid `T?` reference-type annotations and avoid record **classes** (whose compiler-synthesized `Equals(T? other)` requires nullable-attribute metadata even under `disable`); `record struct` does not have this problem, since struct equality members take the type non-nullably. `LevelFile` is therefore a `readonly record struct`, not a `record class`; `LevelGrid`, `AuthoredCell` and `SpawnPoint` are record structs for the same reason, and the Mod project's C# 10 language level rules out collection expressions and primary constructors in level-format code.

## Schema

`LevelFile` (`src/MegabonkLevels.Mod/level_file.cs`), serialized with `System.Text.Json` using `JsonNamingPolicy.CamelCase` (`level_file_serialization.cs`):

| field | type | meaning |
| --- | --- | --- |
| `schemaVersion` | `int` | Current value: `LevelFile.CurrentSchemaVersion` (`4`). Files at versions 1 to 3 migrate on load and behave as before. |
| `gameBuildId` | `string` | Game build the level was authored against (e.g. `"1.0.69"`). Compared against the running game's build for staleness warnings during runtime playback; not interpreted here. |
| `map` | `EMap` | Mirrors the `eMap` values of the game's `MapData` assets (`None=0, Forest=1, Desert=2, Graveyard=8, Dungeon=16, Hell=64`), read from the running game. The Il2Cpp `EMap` enum in `.tools/il2cpp_dump/dump.cs` lists Hell as `4` and has no Dungeon, but the `MapHell` asset holds `64` and `MapDungeon` `16` — a value-level mirror, not a reference to the real Il2Cpp type, since this library must stay Unity/Il2Cpp-free. |
| `stageIndex` | `int` | Which stage within the map. |
| `tier` | `int` | Difficulty tier, 0-based (`0` is the game's "Tier 1"). A custom level always runs at tier 0: a higher value loads and is capped, because the Tier 2 portal leads to a vanilla stage (see "Custom tier cap" in [development.md](development.md#custom-tier-cap)). |
| `seed` | `int` | **The Tiles-map `debugSeed`** (see [map-generation-determinism.md](map-generation-determinism.md)) — the only field confirmed to control reproducible generation. **Never** `MapGenerationController.mapSeed`: that field varies freely per run and has no effect on layout. `ProceduralMesh` maps (Desert) don't yet have a confirmed-controllable seed field at all; storing a `seed` for those maps is "reproducible in practice so far" per that doc, not guaranteed. |
| `packs` | `IReadOnlyDictionary<string, string>` | Optional map from a referenced pack id to the manifest `version` recorded at save time, used by the pack-version compatibility check (see "Pack versions" below). A level with no `bundle:` edits has an empty map. |
| `baseline` | `string` | Optional. Absent or `"generated"` keeps the level an edit stack over the game's generated map. `"none"` makes it a from-scratch level (see "From-scratch levels" below). Any other value is rejected. Additive, so a version 3 file is a valid generated-baseline file. |
| `grid` | `LevelGrid` | From-scratch levels only; required there, rejected under a generated baseline. See "From-scratch levels". |
| `spawn` | `SpawnPoint` | From-scratch levels only; required there. Replaces `playerStart`. |
| `bossSpawner` | `SpawnPoint` | From-scratch levels only; required there. Replaces the generated boss spawner. May also carry `scale` and `hiddenChildren`, see "From-scratch levels". |
| `bossRedirect` | `bool` | Optional, default `false`, omitted when false. From-scratch levels only: turns the boss spawn redirect on, which a from-scratch level otherwise skips because its author places the spawner. Set it when the spawner stands somewhere a boss cannot leave, such as the Warehouse's closed glass box. See "Boss spawn redirect" in [development.md](development.md). Additive, so `schemaVersion` stays `4`. |
| `noGrass` | `bool` | Optional, default `false`. When `true` the mod disables the game's `GrassChunkManager` (`MapGenerationController.grassRenderer`) for the run. The manager raycasts onto the ground layer, so grass otherwise grows through a placed floor mesh such as the THPS Warehouse. Additive, so `schemaVersion` stays `2`. |
| `playerStart` | `float[3]` | Optional. World position `[x, y, z]` the player is moved to once generation has completed, with `y` the value the on-screen position readout shows (the body height, 1.925 above the feet). The game places the player at the generated spawn around generation and moving the spawn portal does not move it, so the mod re-applies the start for 5 seconds. Additive, so `schemaVersion` stays `2`. |
| `maxSlopeAngle` | `float` | Optional. Degrees. While the custom level runs the mod sets `PlayerMovement.maxSlopeAngle` to this value (the game's own is 45) and puts the game's value back for any later vanilla run. Without it movement is unchanged. A face steeper than the limit cannot be run up and does not count as ground, so the player cannot jump from it. |
| `killFloorY` | `float` | Optional. World height of the kill floor (see "Kill floor" in [runtime-map-structure.md](runtime-map-structure.md)). Without it the floor is derived from the lowest live tile level, 40 units below it (on a from-scratch level the live tiles are the authored grid, so that is its lowest cell); a level that removes almost all of its tiles has no meaningful lowest level to derive from, so it authors the height instead. The value is still raised to at least 8 units above the game's catch floor, so a body resting on that floor counts as fallen, and a level whose remaining tile is above the authored height is not lethal to stand on. Additive, so `schemaVersion` stays `3`. |
| `bossSpawnPosition` | `float[3]` | Optional. Retained in the schema and the editor marker, but the boss spawn redirect no longer reads it: the Boss Curse playthrough showed that moving every summoned boss to one authored point stacks the curse copies, so the redirect instead keeps each boss at the game's own spawn XZ — which already staggers copies apart — and drops it to the ground the level has beneath that point (see "Boss spawn redirect" in [development.md](development.md)). The field is currently ignored; existing level files keep loading unchanged. Additive, so `schemaVersion` stays `3`. |
| `music` | `string` | Optional. `bundle:<pack>/<clip>` names a bundled `AudioClip`, such as `bundle:thps/04_Superman`. `track:<filename without extension>`, such as `track:14 Strobe`, selects a case-insensitive filename discovered at startup in `<game>/UserData/CustomMusic/`. Spaces and dots are preserved; paths are not accepted. Runtime radio and automatic progression follow numeric filename components (`6`, `06.02`, `06.10`, `14`), then unnumbered names, and wrap; bundle playlists stay separate and sort by clip name. Missing, unreadable, invalid or unsupported audio warns and falls back to stock without failing level loading. Omitting music uses stock music without a warning. References are not part of the `packs` version check. See [music.md](music.md) for limits and platform support. Added in schema `3`. |
| `grindRequiresSlide` | `bool` | Optional, default `false`. When `true` the game's slide button is what grinding means, held rather than tapped: a rail touch starts a grind only while it is down, so riding over a coping rail or ollieing off a lip keeps the player's momentum instead of catching the nearest rail, and releasing it comes the player off the rail at once instead of leaving them riding to the next junction. Held through a joint, the grind carries onto the next rail; held near one, `GrindAssist` also catches a rail within 2 units of the player's feet, which the game's contact catch leaves behind. The game's own behaviour is kept everywhere else, so vanilla runs and levels without the key grind on contact. `GrindGate.AllowsGrind` (`grind_gate.cs`) decides, `GrindGatePatch` (`grind_gate_patch.cs`) applies it to `PlayerMovement.CanStartGrind`, `PlayerMovement.StartRail` and `PlayerMovement.RailMovement`, and the editor save writes it back. Additive, so `schemaVersion` stays `3`. |
| `fallDamageCharacter` | `string` | Optional. Name of the character whose fall damage a landing on this level is scored with: `calcium`, `tony` or `tonymczoom`, case-insensitive, the same names `allowedCharacters` takes. What differs between characters is `EStat.FallDamageReduction` — `PlayerHealth.OnPlayerLanded` scales its damage by the player's own total of it, while the `minFallDamageSpeed`/`maxFallDamageSpeed` thresholds sit on the one shared `PlayerHealth` component and so are every character's — so a character whose asset carries no such modifier is cut down by drops the other walks away from. With the field set, the mod puts the named character's own total into the player's stat dictionaries for the duration of that one landing call and puts the player's value back afterwards, which leaves the named character's own landings untouched. Absent, every character keeps its own stats, and so does any run the mod did not load. `FallDamagePolicy` (`fall_damage_policy.cs`) decides and computes the total from the character's `CharacterData.statModifiers`, `FallDamagePatch` (`fall_damage_patch.cs`) applies it, and the editor save writes it back. See "Fall damage" in [development.md](development.md) for the measured curve. Additive, so `schemaVersion` stays `3`. |
| `randomizeShadyGuy` | `bool` | Optional, default `false`. Relocate generated shady guy merchants to new safe ground positions each run. See "Interactable randomization" below. |
| `randomizeChests` | `bool` | Optional, default `false`. Relocate generated chests each run, independently of the other kinds. |
| `randomizeMoai` | `bool` | Optional, default `false`. Relocate generated stone-head Maoi shrines each run, independently of the other kinds. The game's class spells this `InteractableShrineMoai`; its prefab is `ShrineMaoi`. |
| `extraShrines` | `int` | Optional, default `0`. How many extra shrines to spawn beyond what the generator places, up to 32 (`ExtraShrines.MaxCount`). Each one is a random kind from the map's shrine pool, probed onto clear ground away from objects and hot paths. `0` or absent keeps stock behaviour. See "Extra shrines" below. |
| `extraShrineKinds` | `string[]` | Optional. Restricts the extra shrines to a subset of kinds: `challenge`, `magnet`, `cursed`, `greed`, `balance`, `moai`, `charge` or `shadyGuy` (case-insensitive). The editor's Level settings panel rejects unknown names; a level file loaded with unknown names warns and ignores them. Absent or empty allows every kind in the map's shrine pool. |
| `extraShrinesMax` | `int` | Optional. With it, each run draws the extra shrine count uniformly from `extraShrines` to this value instead of using `extraShrines` exactly. It must be at least `extraShrines` and at most 32. A maximum above `0` enables the pass even when `extraShrines` is `0`. See "Extra shrines" below. |
| `shrineSpots` | `float[][3]` | Optional. World positions `[x, y, z]` extra shrines may stand at. Present, placement skips the tile probe and instead takes these spots in a random order each run, which suits a level whose floor is a placed mesh and whose designer knows where a shrine belongs. A spot is an anchor: the height only needs to be within a few units of the floor, which is found under it, and when a shrine does not fit exactly there the nearest spot that fits within 8 units is used. Absent, the generated tiles are sampled. See "Extra shrines" below. |
| `guaranteedShrineKinds` | `string[]` | Optional. Shrine kinds (`challenge`, `magnet`, `cursed`, `greed`, `balance`, `moai`, `charge`, `shadyGuy`, case-insensitive) placed on the `shrineSpots` every run, one per name, ahead of the `extraShrines` random extras, and shuffled across the spots with them. A name repeated is a minimum of that many. A non-empty list enables the extra-shrines pass even when `extraShrines` is `0`. Only the authored-spots path reads it. See "Extra shrines" below. |
| `shrineKindRanges` | `object` | Optional. Maps a shrine kind name to `[min, max]`; each run draws a count for every named kind uniformly in its own range (each end between 0 and 32) and places that many of the kind on the `shrineSpots`, in addition to `guaranteedShrineKinds` and the `extraShrines` extras. For example `{"moai": [3, 5], "shadyGuy": [2, 3]}` places three to five stone-head Maoi shrines and two or three merchants. A non-empty object enables the extra-shrines pass. Only the authored-spots path reads it; on the tile probe path it is ignored with a warning. Each placed shrine needs its own spot, 12.5 units from the others, so list more spots than the largest total. See "Extra shrines" below. |
| `shrineGuarantees` | `object[]` | Optional. Each entry is `{"kind", "minX", "maxX", "minZ", "maxZ", "outside"}` in world coordinates (`outside` defaults to `false`): at least one placed shrine of that kind must stand inside the rectangle, or beyond it with `outside`. The first shrine of the kind is drawn only from spots that satisfy the entry, falling back to any spot with a warning when none is left, and each entry is checked against the shrines actually placed, logging `guarantee unmet` when it fails. Only the authored-spots path reads it. |
| `shrineKindSpacing` | `object` | Optional. Maps a shrine kind to a finite non-negative minimum horizontal distance from other shrines of that same kind placed by the authored-spots pass, for example `{"moai":120}`. Names are case-insensitive and duplicates differing only by case are rejected. The ordinary 12.5-unit gap still applies to all kinds. Candidate anchors and final nudged positions must pass; even tight-clearance fallback cannot relax spacing. When no eligible spot remains, logs `placement unmet` and skips that shrine. Missing rules preserve ordinary spacing. Applies only to `shrineSpots`, not stock shrines or the tile-probe path. |
| `fallDamageFreeHeight` | `float` | Optional, finite and non-negative. Landings whose net height loss between the last observed grounded support surface and the landing surface is at most this many world units (plus 0.25 contact tolerance) receive 100% fall-damage reduction for that landing only. Floor probes ignore the player's own colliders and reject distant support; body motion and jump apex height do not count against the allowance. Missing support/history leaves the landing normal; generation/player changes and the editor clear that history. Larger falls retain the character's normal fall-damage rules, or the `fallDamageCharacter` override when configured. Absent/null leaves existing behavior unchanged. This does not reduce lava or combat damage. |
| `groundZones` | `object[]` | Optional. Each entry is `{"material", "minX", "maxX", "minZ", "maxZ"}`: the ground tiles of the grid cells in that range (ends included) are drawn with the named game material instead of the Forest grass, so one level can show desert sand, hell rock or crypt floor under that biome's props. `material` is the name of a loaded Unity material, for example `m_1_TerrainDesert`, `m_TerrainHell` or `m_crypt_Floor`; a name the game does not have logs a `GroundSkin:` warning once and leaves the zone as it was. A later entry paints over an earlier one. Only the tile ground and slope surfaces change: cliff and fill pieces, collision and the level's `map` rules are untouched. Applied when a tile is built, including tiles the editor rebuilds. See `scripts/build_starter_level.py` for an example. |
| `bossPool` | `string[]` | Optional. `EEnemy` names (for example `Ent1`, `Pharaoh2`, `Bandit`, `Bush`) used to replace stage/final-boss `SpawnBoss` calls. Selection is level-seeded; both pools share used names, case-insensitively. Absent, empty or exhausted pools retain the game's original pick, which may repeat. Unknown names warn once and leave that call unchanged. Cross-map availability does not guarantee arena suitability. See "Mixed bosses and lava" below. |
| `minibossPool` | `string[]` | Optional. The same for miniboss spawns, which `SpawnBoss` receives with the `Boss` or `SummonerMiniboss` flag (for example `MinibossPig`, `MinibossGolemSand`, `Ghostham`, `CalciumDad`). |
| `lavaZones` | `object[]` | Optional. Each entry is `{"minX", "maxX", "minZ", "maxZ", "damage", "interval"}`: a player whose feet are within 1.5 units above the surface of that cell range, ends included, loses `damage` hit points (above 0, at most 1000) every `interval` seconds (0.1 to 60). The surface is the height of the zone's first cell. It is a damage volume only: pair it with a `groundZones` entry using the `Lava` material to give it a look. Damage stops in the editor and while the game is paused. A from-scratch level whose `spawn` or `playerStart` falls inside a lava zone is refused when it loads. |
| `chestLuckRange` | `float[2]` | Optional. `[min, max]`, a shift added to the luck the game rolls chest loot with (`ItemUtility.GetRandomChestItem`). One value is drawn uniformly per run, so every chest in a run shares it, and it is drawn again on each restart. Chests keep their positions. The game's rarity odds at luck 0 are about 77% common, 15% rare, 7% epic and 1.6% legendary; at -0.5 about 84% common, at 1 about 62% common and 5% legendary, and at 2 about 52% common and 8% legendary (measured by sampling `ItemUtility.GetRandomItem`). Only runs the mod loaded are shifted. Absent, chests use the game's own odds. |
| `title` | `string` | Optional. Replaces the stage name on the run-start banner (`MapTitle`) and the run-config panel (`RunConfigUi`) while the custom level runs. Without it the stock stage name shows. A level is listed on Map Selection only when it has a title, and that title is also the map name at the top right of the selection screen while the entry is selected (the native screen would show the borrowed base map's name). `LevelTitle` (`level_title.cs`) applies it. The tier line is untouched, so `tier: 0` still reads "Tier 1". Additive, so `schemaVersion` stays `3`. |
| `description` | `string` | Optional. Replaces the description typed out under the title on the run-start banner while the custom level runs. Without it the stock stage description shows. Additive, so `schemaVersion` stays `3`. |
| `mapDescription` | `string` | Optional. The description on the level's entry on the game's Map Selection screen. Without it the entry shows `description`. The run-start banner always uses `description`, so the two can differ as they do for the native maps. Additive, so `schemaVersion` stays `3`. |
| `allowedCharacters` | `string[]` | Optional. Names of the characters that may play the level: `calcium`, `tony` or `tonymczoom` (case-insensitive). Absent, empty, or with no recognised name means any character may play it. The Map Selection entry refuses Confirm for any other character, and a held load restricts the game's Character Selection screen to these characters. `CharacterPolicy` (`character_policy.cs`) applies it and the editor save writes it back. Additive, so `schemaVersion` stays `3`. |
| `edits` | `EditOp[]` | Ordered list of edit operations applied on top of the generated map. `EditOp(OpType, Target, Payload)` is a minimal shape (string opcode + string target id + a JSON-string payload) that round-trips and migrates correctly independent of any particular operation's payload shape — see "Edit operation types" below. |

## From-scratch levels

`baseline: "none"` marks a level whose tile grid is authored in the file instead of generated and then edited. `map`, `stageIndex` and `tier` still choose the kit (tile prefabs, stage data, enemies, music), and `seed` is optional because nothing is generated from it. `edits` carries object placements only.

```json
{
  "schemaVersion": 4,
  "baseline": "none",
  "map": 1,
  "stageIndex": 0,
  "tier": 0,
  "packs": {},
  "grid": {
    "width": 4,
    "depth": 3,
    "cells": [
      { "x": 0, "z": 0, "height": 0 },
      { "x": 1, "z": 1, "height": 0, "slope": "north" }
    ]
  },
  "spawn": { "position": [0.5, 2, 0.5], "rotation": [0, 90, 0] },
  "bossSpawner": { "position": [2.5, 3, 1.5], "rotation": [0, 180, 0] },
  "edits": []
}
```

| key | meaning |
| --- | --- |
| `grid.width`, `grid.depth` | Grid size in cells, both at least 1. The mod caps them at the kit's stock generator size when the level loads (Forest is 15 by 15). The file format does not know the kit, so the cap is a runtime check, not a validation error here. |
| `grid.cells` | Sparse list of `{x, z, height, slope}`. A cell missing from the list is empty. `slope` is `north`, `south`, `east` or `west` and is omitted when there is none. A cell must satisfy `0 <= x < width` and `0 <= z < depth` and no `(x, z)` may appear twice. |
| `spawn`, `bossSpawner` | `position` is world `[x, y, z]` and `rotation` is Euler degrees `[x, y, z]`. |
| `bossSpawner.scale` | Optional `[x, y, z]`, each positive and finite, applied to the spawner's local scale when it is instantiated. Omitted when absent. |
| `bossSpawner.hiddenChildren` | Optional list of child names whose renderers and colliders are switched off on the instantiated spawner. Omitted when absent. |

Validation (`LevelFileValidator`, `level_file_validation.cs`) runs in both `Deserialize` and `DeserializeWithMigration` and throws `ArgumentException` naming the problem:

- A from-scratch file requires `grid`, `spawn` and `bossSpawner`.
- A generated-baseline file (absent or `"generated"`) cannot carry a `grid`.
- A from-scratch file cannot contain a tile edit op (`tile.setHeight`, `tile.setSlope`, `tile.add`, `tile.remove`) or an object edit whose target starts with `gen:`, because the grid is the single source of truth and nothing is generated to target.
- Cells outside the grid or repeated are rejected.

`LevelGrid.ToLevelState()` (`level_grid.cs`) converts the grid to the `LevelState` that `ReachabilityValidator` and `LiveEditPlan` already consume. `grid`, `spawn` and `bossSpawner` are omitted from the written file when absent, so a generated-baseline file serializes as it did at version 3.

## Level thumbnail

A level's Map Selection entry shows a cover image when a sidecar file sits beside the level in `<game>/UserData/Levels/`: the level's base name (the file name without `.mblevel.json`) plus `.png`, `.jpg` or `.jpeg`, so `thps.mblevel.json` takes `thps.png`. The extension and the base name match case-insensitively. Nothing in the level file references it, and the image is not part of the schema or the `packs` version check.

`LevelThumbnailSidecar` (`level_thumbnail_sidecar.cs`, Unity-free and unit-tested) does the lookup and the checks, and `MapSelectionPatch.LoadThumbnail` decodes the result and puts it on the entry's `mapIcon`. The file must be nonempty and at most 8 MiB (`LevelThumbnailSidecar.MaxBytes`), and its header must report at most 4096 px per side (`MaxDimension`), read from the PNG `IHDR` or the JPEG start-of-frame before any decoding. Only the same folder is searched, and a linked (symlink) image is skipped. The decoded texture is freed with the entry when the selection screen is rebuilt.

## Level biome icon

The picture beside the map name on the right of Map Selection (`MapStatsInfoUi.mapIcon`) is the borrowed base map's biome image unless a second sidecar replaces it: the base name plus `.biome` and `.png`, `.jpg` or `.jpeg`, so `thps.mblevel.json` takes `thps.biome.png`. The stem `thps.biome` never equals the thumbnail stem `thps`, so the two lookups cannot pick each other's file. `LevelThumbnailSidecar.Find` takes the `.biome` suffix and applies the thumbnail's checks (nonempty, at most 8 MiB, at most 4096 px per side, no links, one image per level). A missing icon keeps the stock biome image; a rejected one logs a warning and does the same. The selected entry's `StatsConfigPostfix` applies the icon and the title after the native `SetConfig`, and selecting a native map restores the native values.

The generated `ImageConversion.LoadImage` wrapper cannot be used: it builds an `Il2CppSystem.Span<byte>` that throws `ObjectCollectedException`. `NativeImageLoader` (`native_image_loader.cs`) instead calls the engine icall `UnityEngine.ImageConversion::LoadImage_Injected` through `IL2CPP.ResolveICall`, passing a pinned buffer in a 16-byte span wrapper (pointer, then length) and the texture's native pointer read from `Object.m_CachedPtr` at offset `0x10`. Passing the IL2CPP object pointer instead of the native one crashes the game with an access violation, and because `InitButtons` runs when the main menu is built, that crash happens at startup.

A missing sidecar changes nothing: the entry keeps the flat purple placeholder with no warning. Two candidates for one level (`thps.png` and `thps.jpg`), an invalid level name, an empty, oversized or linked file, an unreadable header, oversized dimensions and a decode failure each log `MapSelection: ...; using the placeholder.` and leave the entry intact.

The image is stretched to the tile, which is about 3:2, so a 3:2 image around 1080x720 looks right and stays far under the size limit. The Warehouse ships `levels/thps.png`; bundle it by naming it next to the level, for example `task package:linux LEVELS="thps.mblevel.json thps.png" PACKS=thps`.

## Mixed bosses and lava

`bossPool` and `minibossPool` change which enemy a boss spawn summons, not when it spawns: the portal, timeline and Defeat the Boss quest retain their native timing. The prefix on `EnemyManager.SpawnBoss(EEnemy, ...)` classifies `StageBoss`/`FinalBoss` as boss-pool calls and `Boss`/`SummonerMiniboss` as miniboss-pool calls; other flags are untouched. Both pools share one level-seeded selection stream and one case-insensitive used-name set, reset at `A_PreGeneration`, including native Restart. Shrine draws cannot advance this stream. Identical settings and call order reproduce replacement picks, not the game's original picks, spawn positions or combat.

Each selected name is burned across both pools. Each curse-copy call is another draw, not a promise to clone the first replacement. Once a pool has no unused names, the original game pick stands and a `BossPool: <kind> pool exhausted` line is logged; fallback names are not added to the used set. A singleton pool therefore replaces only its first eligible call, and vanilla fallback can repeat an earlier enemy. Unknown selected names are also burned, warn once per process and leave that call unchanged. An absent/empty pool leaves calls unchanged without drawing. Repeat avoidance applies only to selected replacements, not every enemy spawned during the run.

The stage-0 Forest boss arrives as `Ent1` with `StageBoss`; timeline minibosses use `Boss`. Each replacement logs `BossPool: <kind> spawn of <enemy> (flags ...) replaced by <enemy>`. Candidate asset names include stage bosses `Ent1`–`Ent3`, `Pharaoh1`–`Pharaoh3`, `Bandit`, `Bush`; minibosses `MinibossPig`, `MinibossGolem`, `MinibossGolemSand`, `MinibossScorpion`, `Ghostham`, `CalciumDad`. `GhostKing` is a 500000 HP final boss; `GhostGrave1`–`GhostGrave4` are coffin enemies. Availability is not evidence of suitability for every arena: test movement and introductory difficulty separately.

Lava is the mod's own damage volume, not the game's `Lava` component: `LavaWatcher` reads the zones every frame, finds each zone's world rectangle from the live tiles, and calls the player's `DamagePlayerExternal` with the damage source `Lava` while a standing player is inside. The game's `Lava` material, applied through a `groundZones` entry, supplies the look. The player's damage cooldown and invulnerability still apply, so an invulnerable player takes nothing.

## Ground zones and grass

A `groundZones` rectangle repaints the ground tiles of its cells. The Forest grass manager would otherwise plant blades through the new ground, so the mod drops every grass blade whose cell is inside a ground zone as each chunk is generated (`GrassMask`, a postfix on `GrassChunkManager.GenerateGrassForChunk`). Cells outside every zone keep their grass, and `noGrass` still disables the manager entirely. The cell of a world point assumes a square grid centred on the origin with 40-unit cells, which is how from-scratch levels are built.

`LavaCrypt` additionally reuses a native Graveyard rectangular pool mesh, retaining its UV channels rather than painting the material onto the terrain mesh. The visual quad is fitted to the cell with a 0.02-unit lift; terrain collision and `lavaZones` damage are unchanged. No native damage behaviours are cloned. Generated surface meshes are released on the next generation. If no readable native rectangular template is available, a warning records the material-only fallback; a material name alone is not proof of the expected appearance.

## Interactable randomization

The three `randomize*` flags are additive schema-3 settings, editable as `true`
or `false` in the editor's Level settings panel. For example, this varies chests
while keeping merchants and Maoi shrines deterministic:

```json
{
  "randomizeShadyGuy": false,
  "randomizeChests": true,
  "randomizeMoai": false
}
```

The flags take effect on the next run, not immediately when edited. They survive
save/load and settings undo/redo. Omitted flags are false; disabling them restores
the seed's original placement on the next run.

Only surviving generator-spawned interactables are eligible. An explicit
`object.move` or `object.remove` targeting a generated object pins that object;
editor-placed objects and their attachments remain authored. Randomization never
adds objects or changes their counts. A kind absent from the generated map stays
absent. Runtime rolls do not become saved edit operations.

Placement runs after the deterministic objects have been indexed and saved edits
have been applied. It uses a private random source, leaving the tile seed and
both of the game's spawn RNGs alone. The pass waits one frame for native `Start`
callbacks (which add chest tilt), then finishes before the startup cover opens.
Candidates are flat surfaces on the edited
tile grid, connected to the player start by tile topology and clear physical
paths through a four-by-four sample grid within each tile. Ground raycasts, footprint support and object
clearance checks reject edges, obstructions and overlaps. Successful placements
keep the original ground-to-pivot offset and heading, aligning the prefab's
native up axis to world up (Y for merchants; Z for chests and Maoi). Each
object tries at most 256 candidate samples and stays at its original position,
with a warning, when no safe candidate is found. Terrain-only maps without a
tile grid retain their original placements with a warning.

## Extra shrines

`extraShrines` and `extraShrineKinds` are additive schema-3 settings, editable in
the editor's Level settings panel, where typing either one reports *Takes effect
next run*. For example, this adds four shrines of any kind:

```json
{
  "extraShrines": 4,
  "extraShrineKinds": []
}
```

and this adds three, drawn only from charge shrines:

```json
{
  "extraShrines": 3,
  "extraShrineKinds": ["charge"]
}
```

Each extra shrine is a random kind from the map's own shrine pool: the stage's
`MapData.shrines` entries plus the stage `RandomObjectPlacer`'s charge and greed
spawn lists. A kind with a live shrine already in the scene is cloned from it,
which preserves the authored pivot and upright rotation; otherwise the prefab is
instantiated with a native-up correction for the kind's authored up axis (Charge
Shrine and merchant models are Y-up; Greed, Magnet, Challenge, Cursed, Balance and
Moai models are Z-up). The merchant, kind `shadyGuy`, is the stage's shop NPC; it
is in the pool wherever the map's shrine list holds one, as Forest's does. Kinds outside `extraShrineKinds` are never chosen; an empty or absent list
means the full pool.

Placement runs after generation and any interactable relocation, before the
startup cover opens and the kill floor arms. Private level-seeded planning and
placement streams reset at `A_PreGeneration`; seed 0 is valid. On the authored
path, ranged counts, extra kinds and their order are planned before placement
and logged as `ExtraShrines: plan`. Placement failures cannot perturb that plan
or boss-pool picks. Tile/prop generation and ordinary combat/loot RNGs are not
reseeded by these custom streams. Identical plans do not guarantee identical
physical placements; compare each successful placement and failure separately.
Candidate points come from the same probe the
relocation pass uses (`placement_probe.cs`): flat ground samples connected to the
player start and clear of spawned objects, including shrines placed earlier in the
same pass. Each candidate is validated by trial instantiation and destroyed on
rejection. A point must also sit at least `ExtraShrines.ChargeZoneReach` (12.5
units) from every hot-path anchor — spawn portal, spawn platform, boss portal,
final boss portal, graveyard boss portal and the player start — from the straight
routes spawn→boss and boss→final, and from every other shrine, so no charge
sphere overlaps an object, another shrine, or the route a run takes. Each shrine
tries at most 256 candidates; when a shrine finds no valid point it is skipped
with a warning and the run keeps the shrines that did place. `ExtraShrines`
(`extra_shrines.cs`) decides, `ExtraShrinesPatch` (`extra_shrines_patch.cs`)
applies, and the editor save writes both fields back. `0` or absent spawns
nothing and the level is stock. Placements log under `ExtraShrines:` with each
shrine's position, nearest-shrine and nearest-route distance.

A level with `shrineSpots` takes the authored path instead of the tile probe, which is what a level built on a placed floor mesh needs: the tile probe only sees the generated tiles, and on the Warehouse that is one hidden tile under the floor, so it finds nothing. Each run draws the shrine count from `extraShrines` to `extraShrinesMax` and then places that many one at a time. The next spot is drawn with odds proportional to the square of its distance from the nearest shrine already placed (the first is uniform), so layouts are usually spread out but two can still end up close, as in the native levels where zones sometimes overlap; a spot within 12.5 units (`ExtraShrines.MinSpotGap`) of a placed shrine is never used. For the chosen spot the mod looks for the floor under it (from 3 units above its height to 8 below, against every collider, taking the highest surface whose normal is at least 0.8 up). The shrine is tried there and then at rings of eight directions every 2 units out to 8, and the first position where a trial instance overlaps no collider is kept. A rejected trial is deactivated at once, since `Destroy` only takes effect at the end of the frame. If nothing fits within the rings, the shrine is placed on the nearest floor with no clearance check and a `tight` warning is logged, since the spot is authored and a corner at the top of a quarter pipe can leave a flat strip narrower than the clearance box. Hot-path checks are skipped, because the spots are authored. The shrines placed are the `guaranteedShrineKinds` plus a count of `extraShrines` to `extraShrinesMax` random kinds from `extraShrineKinds`, put in a random order, and each takes the next spot drawn. A kind that fails to fit a spot moves on to another spot, so the guaranteed kinds are placed whenever there are enough spots, and the log reports `planned` against `spawned`. Each Charge Shrine placed this way is golden with a 10% chance (`ExtraShrines.GoldenChance`), drawn again every run and logged as `golden Charge`. The game rolls golden itself only once per shrine in `Awake`, with a `goldChance` of 0.008, so the mod sets `ChargeShrine.isGolden` and the gold material after instantiating; a golden shrine offers legendary rewards where a regular one offers common ones. A spot where nothing fits is skipped with a warning naming the collider in the way, and the run keeps the shrines that did place, so list more spots than the largest count, allowing for spots that exclude each other.

## Migration mechanism

`SchemaMigrator.Migrate` (`level_file_migration.cs`) takes a parsed `JsonObject`, a target version, and a `IReadOnlyDictionary<int, MigrationStep>` keyed by *from*-version. It loops: look up the step registered for the document's current `schemaVersion`, apply it (the step returns a new `JsonObject` with its own, incremented `schemaVersion`), repeat until the target version is reached. Reaching a version with no registered step throws.

`LevelFileSerializer.DeserializeWithMigration` (`level_file_serialization.cs`) calls this with `LevelFile.CurrentSchemaVersion` and a `ProductionSteps` dictionary. The real steps are `1 -> 2`, which carries an existing `packs` object over (or writes an empty one) while bumping `schemaVersion` to 2, and `2 -> 3`, which only bumps `schemaVersion` because `music` is optional and absent from older files, and `3 -> 4`, which only bumps `schemaVersion` because `baseline`, `grid`, `spawn` and `bossSpawner` are optional and a file without them is a generated-baseline level. `SchemaMigrator` reuses the same loop and public API for any future version: adding one `[from] = step` entry to `ProductionSteps` is the whole change.

`SchemaMigrator_AppliesRegisteredStepUntilTargetVersionReached` in `tests/MegabonkLevels.Tests/level_file_tests.cs` still exercises the mechanism with a synthetic, test-local step (renaming a field and bumping to a made-up version `2`), and `SchemaMigrator_MissingStepForOlderVersion_Throws` covers the "no step registered" failure path. The real migrations are covered by `DeserializeWithMigration_V1WithoutPacks_MigratesToEmptyPacks`, `DeserializeWithMigration_V2WithPacks_PreservesPacks` and `DeserializeWithMigration_V2WithoutMusic_MigratesToCurrentVersion` and `Migration_FromVersionThree_BumpsVersionAndLeavesGeneratedBaseline`.

## Round-trip

`LevelFileSerializer.Serialize`/`Deserialize` round-trip a `LevelFile` through `System.Text.Json`; `level_file_tests.cs`'s `RoundTrip_SerializeThenDeserialize_ProducesEqualLevel` covers this. `LevelFile` overrides `Equals`/`GetHashCode` to compare `Edits` by sequence (the default record-struct equality would otherwise compare the `IReadOnlyList<EditOp>` reference, which differs after a deserialize produces a new list instance). `Packs` is compared as a dictionary by key/value pairs, not by reference, for the same reason.

## Pack versions

The level records the manifest `version` of each pack it references, so a run can warn when a pack changed since the level was saved. The recorded values come from the installed manifests at save time, not from the catalogIds, so the map is `"<packId>": "<manifest version>"`. The compatibility check (`GamePackVersionCheck.MismatchWarning`, mirroring `GameBuildIdCheck`) compares each recorded version to the installed manifest version by exact string match: a mismatch logs a warning and the run still starts, and an absent recorded version or absent installed manifest produces no warning. It runs in both load paths (`LevelLoaderPatch.Start` and `EditorTileTools.LoadSelected`). The editor save fills the map from the manifests of the packs the level references (`LiveEditPatch.BuildPacks`), reading each referenced pack's manifest version (`PackPrefabs.ManifestVersion`).

Construction kits can declare a separate `kitVersion` and `kitAssetPrefixes` in
the manifest without changing a legacy version pinned by preserved levels.
For THPS these are revision `"2"` and prefixes `"piece-"`, `"added-"`; only assets
actually listed in the manifest qualify. Kit-using levels record the optional
`packKitVersions` dictionary, for example `{"thps":"1"}`. Save inspects root and
attachment catalog IDs, records installed revisions and retains loaded
requirements when the pack is unavailable. Both load paths warn on a different
or missing installed kit revision, without preventing loading. Older manifests
have no kit revision and cannot silently satisfy a kit-using file. Legacy levels
omit the field and retain their compatibility behavior. The field is additive;
schema remains 3. Bump kit revision when kit geometry, transforms or attachment
defaults change; do not refresh the preservation baseline to advertise additions.

## Edit operation types

`src/MegabonkLevels.Mod/edit_operations.cs` defines seven typed edit operations that replace `EditOp`'s placeholder payload shape, each a Unity-free `readonly record struct` with a validating constructor plus a `ToEditOp()`/static `FromEditOp(EditOp)` pair that (de)serializes the op's fields to/from `EditOp.Payload` (a `System.Text.Json` camelCase JSON string) and, for object ops that reference an existing object, `EditOp.Target`:

| op type | `EditOp.OpType` | fields | `EditOp.Target` |
| --- | --- | --- | --- |
| `SetTileHeight` | `tile.setHeight` | `X, Z, Height` | unused (`""`) |
| `SetTileSlope` | `tile.setSlope` | `X, Z, Direction` (`SlopeDirection`: `None, North, South, East, West`) | unused (`""`) |
| `AddTile` | `tile.add` | `X, Z, Height` | unused (`""`) |
| `RemoveTile` | `tile.remove` | `X, Z` | unused (`""`) |
| `PlaceObject` | `object.place` | `CatalogId, Position, Rotation, Scale` (`Vector3Data`), optional `Hidden`, `Attachments`, `PlacementId` (see below) | unused (`""`) |
| `MoveObject` | `object.move` | `Target` (`ObjectTarget`), `NewTransform` (`TransformData`), optional `HiddenChildren` (names of descendants whose renderers and colliders are disabled when the move applies, left out of the payload when empty) | `Target.Serialize()` |
| `RemoveObject` | `object.remove` | `Target` (`ObjectTarget`) | `Target.Serialize()` |

Tile ops identify the tile by grid coordinates carried in the payload, so they have no need of `EditOp.Target`; object ops that mutate an *existing* object carry their target there instead, so an op can be filtered/routed by `EditOp.Target` alone without deserializing the payload.

In a generated-baseline file, tile ops apply on top of the generated grid, not an empty one. (A from-scratch file has no tile ops: its grid is authored directly, see "From-scratch levels".) At generation the mod snapshots every live tile's height and slope into a baseline `LevelState`, and `LiveEditPlan.Build(edits, baseline)` replays the edits on a copy of it. `SetTileHeight` therefore keeps a cell's generated slope, and `SetTileSlope` keeps its generated height. Generation is deterministic for a seed, so the same file produces the same baseline, and a level loads exactly as it looked when it was edited. `AddTile` always places a flat tile. An `EditStack` built on an empty `LevelState` still falls back to height 0 and no slope for a cell it has no record of.

### `ObjectTarget`: genId vs. placement id

`MoveObject`/`RemoveObject` reference an existing object through `ObjectTarget`, which distinguishes two kinds:

- **`GenId`** — an opaque string identifying a generator-spawned object, using a `{category}:{sequentialIndex}` scheme; treated here as an opaque non-blank string.
- **`PlacementId`** — a non-negative `int` identifying an editor placement, scoped to the edit list. Without an explicit `placementId`, replay assigns the next incremental ID. An explicit ID must be unused and at least the next ID. The editor saves it so undo followed by new placement cannot renumber later edit targets on reload. Attachments consume the immediately following IDs in list order.

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

`Bundle` is reserved for custom AssetBundle packs (see "Manifests and pack versions" in [asset-bundles.md](asset-bundles.md)). The grammar accepts `bundle:` ids now, and a pack's assets are validated against its manifest before any bundle is loaded.

**Game-asset segment shapes**, cross-checked against the confirmed runtime catalog organization (`DataManager.Instance.maps[] : MapData` → `stages[] : StageData` → `randomMapObjects[] : RandomMapObject` → `.prefabs[] : GameObject[]`; `StageData.stageTilePrefabs : StageTilePrefabs` with `flatTilePrefabs[]`/`mapSpecificTilesPrefabs[]`; `MapData.shrines[]` and `MapData.randomObjectsOverride[]`, both map-scoped not stage-scoped; `SpawnInteractables`'s singular `chest`/`chestFree` fields and `rails[]`; `RandomObjectPlacer`'s singular `chargeShrineSpawns`/`greedShrineSpawns` `RandomMapObject` channels) rather than invented independently:

| shape | example | source |
| --- | --- | --- |
| `{map}/stage{N}/randomMapObjects/{objectIndex}/{prefabIndex}` | `forest/stage0/randomMapObjects/2/0` | `StageData.randomMapObjects[2].prefabs[0]` |
| `{map}/stage{N}/stageTilePrefabs/flat/{index}` | `desert/stage1/stageTilePrefabs/flat/3` | `StageData.stageTilePrefabs.flatTilePrefabs[3]` |
| `{map}/stage{N}/stageTilePrefabs/specific/{index}` | `graveyard/stage2/stageTilePrefabs/specific/1` | `StageData.stageTilePrefabs.mapSpecificTilesPrefabs[1]` |
| `{map}/shrines/{index}` | `forest/shrines/5` | `MapData.shrines[5]` |
| `{map}/randomObjectsOverride/{groupIndex}/{prefabIndex}` | `graveyard/randomObjectsOverride/0/0` | `MapData.randomObjectsOverride[0].prefabs[0]`, the map-wide counterpart to the per-stage `randomObjects` list, map-scoped like `shrines` and grouped under the palette's Overrides tab |
| `interactable/chargeShrine/{index}` | `interactable/chargeShrine/0` | `RandomObjectPlacer.chargeShrineSpawns.prefabs[index]`; scene-wide, so listed once for the loaded map |
| `interactable/greedShrine/{index}` | `interactable/greedShrine/0` | `RandomObjectPlacer.greedShrineSpawns.prefabs[index]`; scene-wide, so listed once for the loaded map |
| `interactable/chest`, `interactable/chestFree` | — | `SpawnInteractables.chest` / `.chestFree` (singular fields) |
| `interactable/boombox` | — | `EffectManager.boomboxQuest`, the game's only `InteractableBoombox` prefab; in a level with `music` it is the radio (see [music.md](music.md)). No schema change: it is an ordinary `PlaceObject` id |
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
- `PlaceObject` reserves its owner and attachment IDs once per `Apply`, using the explicit `placementId` when present, and reuses those IDs across undo/redo. IDs are never reused by later placements, including after undo.

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

A hardcoded hotkey (F6, `MegabonkLevelsMod.Tick`) loads `megabonklevels-test-level.mblevel.json` beside the plugin DLL in `BepInEx/plugins/MegabonkLevels/`. F10 collides with the game's built-in debug console. Copy `levels/example-forest.mblevel.json` there under the hotkey's expected name to test Forest, stage 0, tier 0, seed 20261007, with no edits. Arbitrary paths are available through the harness rather than this hotkey.

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

The editor's object tools (see "Object tools" in [development.md](development.md)) emit these same ops: Place sends `PlaceObject` with the palette entry's `catalogId`, and Select sends `MoveObject` and `RemoveObject` targeting `gen:<genId>` for a generator-spawned object or `placement:<id>` for one the editor placed. A `MoveObject` always carries the full new transform, so a rotate repeats the current position and scale.

Editor undo/redo and save use this same op stream, not a second state model. The editor session stores the ordered list of forward ops (seeded from the loaded level's edit list, if any), and each new op is paired with planned inverse ops based on the pre-op `LevelState`: tile undo restores the previous height+slope pair, and object undo restores the previous transform (or deactivates/removes as appropriate). Undo and redo apply these planned ops through the same live pipeline (`LiveEditPlanner` + applier), so visuals, fill and collision updates stay identical to normal edits.

For object removals, live `RemoveObject` deactivates the object instead of destroying it, and `MoveObject` reactivates before applying the transform. This keeps target identity stable across remove/undo/redo for both generator and editor-placed objects.

Editor save writes the current forward-op list to `<game>/UserData/Levels/<name>.mblevel.json` through `LevelFileSerializer`, using current runtime metadata (`MapController.currentMap/currentStage`, `MapController.runConfig.mapTierIndex`, `ProceduralTileGeneration.debugSeed`) for the non-edit fields.

Known limits: `AddTile` outside the `size x size` grid logs a warning and does nothing. A replacement flat tile reuses the previous tile's direction, or faces +Z in an empty cell. After the tile edits the mod regenerates the wall and fill pieces on every edge between an edited tile and an occupied neighbour, and rebuilds the baked ground collision; see "Walls after edits" and "Ground collision after edits" in [runtime-map-structure.md](runtime-map-structure.md). Edges against a removed cell are left as they were, so a removed tile leaves an open hole with the old walls around it standing or floating; the kill floor ends a fall into it. On a `ProceduralMesh` map (Desert) only the object ops replay, because they are keyed by world `Position`, which needs no grid: `PlaceObject` stores the terrain height at the cursor as `Y`, and the `tile.*` ops are skipped with a warning. The saved `seed` is `0` there (no confirmed-controllable seed), so a saved Y assumes the same terrain regenerates. `catalogId` resolution works only for `Tiles` maps (the edit list is skipped, with a warning, when `proceduralTiles` is null), and `bundle:` ids are rejected.

### Suppressing Steam leaderboard, achievement, and stats writes

A custom or edited level's scores and progress must never reach Steam: the game keeps a server-side `banned_players` leaderboard, and a modded run didn't come from legitimate procedural generation. `src/MegabonkLevels.Mod/custom_level_state.cs` (`CustomLevelState`, Unity-free and unit-tested) tracks whether the *currently active* run was started through `LevelLoaderPatch` rather than the game's own menu: `LoadAndStart` calls `MarkPendingStart()` immediately before `MapController.StartNewMap`, and a Harmony prefix on that same method (`custom_level_state_patch.cs`, `CustomLevelStatePatch`) — the single entry point both the normal menu flow and the mod funnel through, per the `SceneTransitionProbe` finding above — calls `OnRunStarting()`, which resolves whatever is pending into `IsActive` and clears the pending flag. This is a one-flag, consume-on-start state machine: a normal run always re-resolves to `IsActive = false`, even immediately after a custom-level run, so there is one source of truth instead of separate "did we mod this" bookkeeping at each call site. It logs `CustomLevelState: run starting, IsActive=<bool>` on every run start, modded or not.

`src/MegabonkLevels.Mod/steam_write_guard_patch.cs` (`SteamWriteGuard`) Harmony-prefixes the four confirmed write paths and returns `false` (cancelling the original call) whenever `RunExclusion.Reason()` is non-null (a custom level is active, or the run is a mod character, see [characters](characters.md#keeping-mod-character-runs-off-steam)), logging `SteamWriteGuard: suppressed <call> (<reason>)` each time, where the reason for a custom level is `custom-level run active` — otherwise it returns `true` and the original call runs exactly as before. Targets, confirmed against `.tools/il2cpp_dump/dump.cs` (all RVAs unique, so safe to patch per the RVA-sharing note above):

| class.method | namespace | why this one |
| --- | --- | --- |
| `SteamLeaderboardsManagerNew.QueueLeaderboardUpload` | *(global)* | queues a score for a leaderboard, including the `kills`/`kills_weekly` boards that feed `banned_players` |
| `SteamLeaderboardsManagerNew.UploadLeaderboardScore` | *(global)* | the queue's own upload call; guarded independently in case anything calls it directly |
| `SteamAchievementsManager.TryUnlockAchievement` | `Assets.Scripts.Steam` | the only public write entry point — the unlock check and the upload queueing both happen inside it |
| `SteamStatsManager.OnStatUpdated` (private) | `Assets.Scripts.Steam` | the bridge subscribed to `MyStats.A_StatUpdated` that caches a local stat change for Steam upload; blocking it here leaves the game's own local progression (`MyStats`/`RunStats`) untouched and only suppresses the Steam-bound copy |

Live-verified on the CrossOver reference platform: loading the test level file logs `CustomLevelState: run starting, IsActive=True` immediately after `LevelLoader: starting ...`, and an idle, invulnerable run (`scripts/run.py invulnerable`) suppressed over 200 `SteamStatsManager.OnStatUpdated` calls in under a minute with no errors or exceptions. The leaderboard and achievement prefixes were not exercised live in this pass — those fire on rarer events (run completion, specific achievement thresholds) that a full playthrough is better placed to hit — but are structurally identical guards confirmed to compile against the real game assembly.

## Checking live edits

Use `levels/example-forest.mblevel.json` as a generated-baseline starting point.
In the editor, raise and slope tiles, remove a tile, add it back, place a chest,
and remove an indexed generated object. Save a separate level and relaunch into
it to verify replay. Check `BepInEx/LogOutput.log` for `LiveEdit: applied`,
`FillRegeneration`, `CollisionRebuild` and `KillFloor: armed` without edit warnings.

Play across the edited terrain and check that enemies can traverse raised and
sloped tiles. Leave a hole to exercise the kill floor, and verify the placed and
removed objects after saving and loading. Old task-specific regression files are
not distributed; the schema above describes each operation.

## Hidden placements

A `PlaceObject` with `hidden: true` spawns normally but the mod disables every `Renderer` under it, so its colliders and components stay live and it draws nothing. The THPS level uses this to lay the game's straight `interactable/rail/0` along the Warehouse mesh's own rail bar, so the bar keeps its original look while the game rail supplies the grind.

### Attached placements

An optional `attachments` array in `object.place` contains named child placements:

```json
{
  "name": "coping",
  "catalogId": "interactable/rail/0",
  "localTransform": {
    "position": {"x": 0, "y": 0.1, "z": 0.2},
    "rotation": {"x": 0, "y": 90, "z": 0},
    "scale": {"x": 0.01, "y": 0.01, "z": 0.01}
  },
  "hidden": true
}
```

Names must be nonblank and unique within the owner; catalog IDs and positive
scales use normal placement validation. Attachments are one level deep, not
recursive assemblies. Their local transforms include the owner's scale; the
child's prefab root scale is replaced, not multiplied again. The owner gets the
placement's first ID, and each ordered child gets its own following ID. They
remain normal move/remove targets. Removing an owner hides its descendants;
restoring it preserves each child's independent removed state. Replaying a saved
placement uses its serialized attachment list, never the pack's current defaults.

`MoveObject` retains the existing editor convention: world position and rotation,
**local** scale. For a child, replay converts position/rotation back to the owner's
frame and preserves the local scale, so moving a post does not detach it. Owner
transforms propagate through Unity parenting, including nonuniform scale. Empty
attachments and absent explicit IDs are omitted, preserving old payload bytes.
These optional fields keep schema version 3, but files using them require a mod
that understands attached placements.
