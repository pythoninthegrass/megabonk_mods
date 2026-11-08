---
id: TASK-053
title: Record the generated Forest and Desert Tier 2 stage parameters and layouts
status: In Progress
assignee: []
created_date: '2026-11-07T23:07:00Z'
updated_date: '2026-11-08T01:35:00Z'
labels:
  - research
  - generation
dependencies: []
documentation:
  - docs/map-generation-determinism.md
  - docs/runtime-map-structure.md
  - docs/development.md
priority: medium
type: spike
ordinal: 190000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
To audit how levels are generated, the Tier 2 stages of Forest and Desert need to be measured, not just the first stage. Custom levels are capped to Tier 1 and the stock menu driver only works on Linux, so a completed Tier 2 playthrough is not a practical way to get this, and the per-generation log line holds only counts and hashes. The harness can already generate a map and stage directly, so the stage's data and its generated output can be captured and compared without playing a run.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 It is established and written down which stage index of Forest and of Desert is the vanilla Tier 2 stage (for example Deep Forest), with the evidence.
- [x] #2 For Forest and for Desert at that stage, the stage's generation parameters (grid size, height strategy and its inputs, edge fill, prop and interactable counts or multipliers, and for the procedural-mesh map its terrain and noise settings) are recorded in a document with the values read from the running game.
- [ ] #3 Each of the two stages is generated at least twice with the same forced seed and at least twice without, and the generation log lines (seed, counts, layout hash, object hash) are recorded to show what repeats and what varies.
- [x] #4 The findings are added to docs/map-generation-determinism.md or docs/runtime-map-structure.md, and any harness or script change needed to capture them is covered by tests.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Plan

Measurement box: the Mac's plain-Wine install through the megabonk MCP harness (owns the running game). The level-test leg runs on the Linux player box over SSH with the same harness (venv python), as a cross-machine check of the generated hashes.

1. Read-only harness extension for nested asset values (tests first).
   - `tests/MegabonkLevels.Tests/asset_dump_tests.cs`: pure-logic tests for a new `AssetDump` walker (primitives, enums as ints, null, arrays with a cap and a truncation marker, depth cut naming nested objects, Unity-object-like nodes by `name`, member read failure recorded as an error string, reference cycle guard).
   - `src/MegabonkLevels.Mod/asset_dump.cs`: reflection walker, System.Reflection + System.Text.Json only, no UnityEngine types, so the tests project compiles it.
   - Extend `query-objects` with an optional integer `depth` (default 0 keeps today's ToString-for-objects behaviour) instead of adding a new command: `ObjectQuery.Read` gains a depth parameter and delegates value conversion to `AssetDump`; parse test in `harness_command_tests.cs`, pass-through tests in `tests/test_run.py` and `tests/test_mcp_server.py`.
   - `scripts/run.py` builder + MCP `query_objects(depth=...)`; document `depth` in the "Querying live objects" section of docs/development.md.
2. Stage-index finding: dump each `MapData` (Forest, Desert) with `stages` expanded, recording per-index asset name, `localizedName.cachedValue`, `mapEdgeFillType`, and per-stage identity, then read `MapController.currentStage`/`GetStageIndex()` equivalents from the loaded assets to say which index is the vanilla Tier 2 stage. Evidence: stage array order plus names, corroborated by generating that index and matching it to the Tier 2 stage the stock portal loads.
3. Parameter capture from the running game for Forest and Desert at that index: `MapParameters` (size, scale, tileWidth/Height, scaled values, volatility, centerHeightTarget, slopeStrength, yOffset, flatMapBias, biasStrategy, heightGenerationStrategy), `mapEdgeFillType`, `grassPerChunk`, prop entries (`randomMapObjects`: amount/maxAmount/checkRadius/scale range/maxSlopeAngle/upOffset/prefab count), `MapData` multipliers (numShrines/Chests/ShrinesPotsAndOther), and for Desert `proceduralTerrainData` + `proceduralNoiseData` + `proceduralMapScale`.
4. Generation runs with `levels/example-forest.mblevel.json` (generated baseline, edits empty), overriding map/stage/tier/seed: Forest stage N and Desert stage N, x2 with the same forced `--seed` and x2 with the seed varying, relaunching between runs. Capture each `A_GenerationComplete` line (seed, tiles/flat/fill, nodes, hash, objects, objectsHash) plus a screenshot per stage.
5. Save raw logs, screenshots and the raw dumps under `.tools/evidence/` (gitignored); write the stage-index finding, the parameter tables and the repeat-versus-vary table as a new section of docs/runtime-map-structure.md, with at most one cross-reference line elsewhere.
6. Validate: `~/.local/bin/mise exec -- task check` (includes markdownlint and the C#/Python suites); commit as atomic conventional commits with no attribution; leave the game unfrozen, spawns on, no camera override.

Risks: the Desert seed is not controllable by the level-seed force (only `ProceduralTileGeneration.Generate` is patched), so the Desert forced-seed comparison may show the tile/mesh side varying - record what actually happens rather than assuming; the Wine game is shared with nothing else right now but a rebuild needs a relaunch to load.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Harness surface (tests written first): `AssetDump` (`src/MegabonkLevels.Mod/asset_dump.cs`) walks public fields and properties using System.Reflection and System.Text.Json only, no UnityEngine types, so `tests/MegabonkLevels.Tests/asset_dump_tests.cs` drives it with fakes (`asset_dump_unity_fakes.cs`). `query-objects` gained an optional integer `depth` (default 0 keeps the ToString behaviour) and `ObjectQuery.Read` delegates value conversion to the walker. Rails: MaxDepth 6, DefaultMaxItems 64, DefaultMaxNodes 20000, MaxLevel 24, `$cycle` for a node already on the path, `$truncated` at a rail, `$fieldsOnly` for a non-ScriptableObject UnityEngine.Object, `$error: <Type>: <message>` for a throwing getter. `scripts/run.py` and the MCP mirror the ceiling as `MAX_QUERY_DEPTH = 6`.

Unseeded load: `LoadOverrides.Unseeded` set from `"seed": null` calls `SeedForcePatch.ReleaseLevelSeed()` (mode Off), surfaced as `run.py --no-seed` and MCP `unseeded=` on `load` and `relaunch`. Verified live as `SeedForcePatch mode -> Off (seed left to the game)` plus a game-rolled `debugSeed` in the generation line.

Stage-index finding: index 1 is the vanilla Tier 2 stage for both maps. `StageData` carries no tier field, so the proof is `ChallengeData.tier` (0, 1, 2 for the `a_forest1/2/3_*` and `a_desert1/2/3_*` rows) read together with the `StageData.challenges` arrays, whose per-tier counts match exactly (Forest 13/6/6, Desert 9/5/5).

Published as a new section 12 of `docs/runtime-map-structure.md`: the stage-index table, the Forest and Desert per-stage parameter tables read with `query-objects --depth 3`, how far the stage override reaches, the repeat-versus-vary table and three findings. Harness `depth` and the unseeded load are documented in `docs/development.md`.

Open questions left in the doc rather than assumed: the tile generator ignores the stage override (`ProceduralTileGeneration.currentStage` stayed `StageForest1` after a stage-2 load), with `RunConfig.mapTierIndex` clamped by `CustomTierCap` the unconfirmed candidate; Forest `objectsHash` is bimodal, two values over 14 seeded runs with `objects=847` constant; Desert snapshots are empty (`objects=0`, `E3B0C442…` is SHA-256 of empty input) so no Desert object-determinism claim is made.

Evidence lives under gitignored `.tools/evidence`: raw asset dumps, per-run `_gen.txt`/`_log.txt` pairs, and `summarize_runs.py` and `extract_params.py` which reprint the published tables. The 12-run-per-cell matrix files were lost from disk partway through; the published counts come from the surviving `_gen.txt`/`_log.txt` rows and the run transcripts, and are labelled as such.

Reviewed HEAD 280f45b before staging. Preserved its standalone Stage parameter interpretation section verbatim and left the shared genId, fill/cliff, removal-wall, SpawnBoss and TASK-048.01 edits unstaged. Removed unsupported binary-RNG causality and Desert terrain-repeatability claims from the pending research section. Stage-selection causality, Forest object-hash divergence, Desert object placement and terrain seed remain unresolved.

AC3 remains unchecked: requests for stage index 1 do not establish effective Tier 2 generation. The live Forest dump after a stage-2 request instead reported StageForest1/ParamForest1. Captured requested-stage repeats must not be called verified Tier 2 layouts. Do not close this task on the existing evidence.

Validation before this final review: task check exited 0, including 2129 C# tests and 1105 Python tests; docs markdown lint passed. The user corrections themselves added no runtime validation. The latest documentation qualifications need final lint; no additional runtime measurements are claimed. Earlier notes mentioning 16 seeded Forest runs are superseded by the current 14-record table; cross-file Linux evidence provenance still warrants care.

Final review evidence correction: the published repeat table now excludes Linux files with inconsistent requested-map labels or incomplete generation records. It counts 12 surviving seeded Mac Forest records (6 hashes C0376874…, 6 hashes 92A74E52…), 2 unseeded Mac Forest records, and 6 Mac Desert records. Earlier 14/16-record and cross-machine claims are superseded. The stage-selection cause, object-hash cause, Desert capture coverage and terrain seed remain unresolved.

After review of 280f45b and the subsequent shared-edit commit 549b542, task check was rerun successfully: 2129 C# tests, 1105 Python tests, markdownlint and Ruff passed. No new runtime validation was performed. Only TASK-053 changes staged; no commit made. AC3 and the commit DoD remain unchecked, and the task remains In Progress.
<!-- SECTION:NOTES:END -->
