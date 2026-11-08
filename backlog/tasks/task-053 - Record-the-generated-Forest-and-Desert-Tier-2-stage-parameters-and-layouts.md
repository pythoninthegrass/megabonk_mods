---
id: TASK-053
title: Record the generated Forest and Desert Tier 2 stage parameters and layouts
status: Done
assignee: []
created_date: '2026-11-07T23:07:00Z'
updated_date: '2026-11-08T04:32:00Z'
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
- [x] #3 Each of the two stages is generated at least twice with the same forced seed and at least twice without, and the generation log lines (seed, counts, layout hash, object hash) are recorded to show what repeats and what varies.
- [x] #4 The findings are added to docs/map-generation-determinism.md or docs/runtime-map-structure.md, and any harness or script change needed to capture them is covered by tests.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Establish native initial-stage selection and keep the existing tier cap unchanged.
2. Add tests-first, default-off dev-only one-shot stage selection and a narrow read-only static MapController depth query; forward the switch through the macOS GUI launcher.
3. Deploy and relaunch between every measurement. Verify Forest PTG stage/parameters and Desert MapController stage plus MapGenerator terrain/noise before accepting hashes. Immediately append each run and its full launch log to .tools/evidence/tier2-effective-runs.jsonl.
4. Record two forced-seed requests and two unseeded runs per effective stage, keeping Desert hook/capture limitations explicit. Exclude unverified probes and the default-off control.
5. Publish section 12 and development instructions; verify exact log lines against the journal, markdownlint and full task check; commit implementation and findings separately with conventional subjects and no attribution.
6. Leave a normal default-off Forest run unfrozen, spawns on, editor off and camera cleared; finalize only after all criteria and DoD are verified.

Approved continuation: add a separate default-off dev terrain-seed measurement path (never broaden SeedForcePatch or change CustomTierCap), pin the three-argument MapGenerator call, observe the Noise seed and hash its mesh-input grid. Preserve the original 11 journal records byte-identically; rerun Desert control, two identical pins, another seed, two unseeded launches and one Forest inertness check, with a fresh offline Mac relaunch each time. Publish exact evidence and buffer-read limitations, run lint/full checks, commit atomically and restore normal gameplay before finalization.
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

Resumed with a clean worktree at 081ff9c. AC3 requires fresh effective-stage verification before any measurement hash is accepted; the earlier request-only rows remain excluded from Tier 2 evidence. The MCP server currently advertises older query/relaunch signatures without depth or unseeded; inspect the maintained CLI fallback rather than silently drop either control. Honcho recall failed with a server session-not-found error; proceeding without memory.

REA namespace is unavailable in this tool catalog. Used read-only objdump of the installed GameAssembly.dll instead: StartNewMap writes -1 to MapController statics +0x8 at VA 0x180422485 and calls LoadNextStage at 0x1804224A0. LoadNextStage increments statics +0x8 at 0x180421FA4, reads currentMap +0x50 (stages), indexes by that value, and writes currentStage at 0x18042205A. Tier-cap causality is not supported; initial-stage reset is established directly.

Tests-first gate implemented: eight pure C# cases failed to compile before InitialStageOverride existed, then passed; the GUI launcher whitelist dropped the new switch on the first attempted load, which was captured as unverified in .tools/evidence/tier2-effective-runs.jsonl. Added a failing GUI handoff test, then explicitly forwarded only the new switch; all 17 GUI tests pass. No tier-cap changes. The first three accepted Forest runs each report StageForest2/ParamForest2 in depth-2 dumps; both forced runs have 225/165/190 tiles, 415 nodes, hash 0BDEF92F…, objects=957 but differing object hashes CCCC82DA… and AF779C3A…. First unseeded run has debugSeed=1591920135, 225/171/410, 635 nodes, hash 634C6141…, objects=958. Every completed launch and dump is appended/fsynced to the journal before the next relaunch.

Forest matrix complete: four verified effective StageForest2/ParamForest2 launches (two forced, two unseeded), all durably recorded. Desert first probe durably captured with null tile-generator currentStage/currentMapParameters, MGC test defaults MapForest/StageForest1, and live MapGenerator TerrainDesert/NoiseDesert1. Do not mistake serialized testStageData for effective stage. Need static MapController query for direct identity proof.

Eight required runs now durably saved in .tools/evidence/tier2-effective-runs.jsonl: four Forest and four Desert, two forced-424242 and two unseeded per map, each after a fresh relaunch. Forest depth-2 PTG dumps verify StageForest2/ParamForest2 (scale22); Desert depth-2 MapController dumps verify index1/currentStage StageDesert2/proceduralMapScale1.1, and MapGenerator dumps match TerrainDesert (heightMultiplier11, uniformScale1, useFallofffalse) and NoiseDesert1 (scale100, octaves2, lacunarity3, persistance0.4, seed257). Desert PTG currentStage/currentMapParameters are null; MGC testStageData remains the serialized Forest default and is not evidence of its generated stage. Native coroutine MoveNext RVA0x4A26F0 reads MapController statics+0x18 into captured stageData+0x30 at VA0x1804A39C0 and passes it to MapGenerator.GenerateMap at VA0x1804A3BE0. Saved disassembly in .tools/evidence/tier2-generation-native.txt. Static MapController query added narrowly to harness with three tests written first (red then green); 21 focused C# cases pass. Desert mapSeeds1288405723/1439882283 (forced requests) and80866481/480924260 (unseeded); debugSeed1952838951 is unused and constant, tile snapshot400/292/417 nodes817 hash692987B2…, objects0 empty hash. No terrain/object determinism claim.

Validation complete: markdownlint -c .markdownlint.jsonc docs passed; full mise task check exited successfully with 2140 C# tests and 1106 Python tests, repository markdownlint and Ruff. Exact eight accepted generation lines in docs/runtime-map-structure.md match the append-only journal; all four unseeded logs explicitly show mode -> Off. Three excluded records (GUI switch-loss attempt, Desert probe, default-off control) remain in the same journal. Final deployed-build default-off control requests stage1/tier1 but verifies index0 StageForest1/ParamForest1 and the original A2B9C891… tile hash, demonstrating normal behaviour remains unchanged. No environment-file changes or tier-cap changes were made.

Implementation committed as 0cfa58a (feat(dev): add opt-in initial stage measurements), with no attribution. AC3 remains unchecked under its literal controlled-seed requirement: all eight runs have verified Tier 2 stage assets, and the two forced requests/two unseeded loads per map are recorded, but Desert does not reach the seed-force hook and its actual mapSeed differs between its two forced requests. The documentation explicitly reports that limitation rather than claiming a pinned Desert seed. Finishing that strict requirement needs an approved Desert terrain seed-control path and another verified matrix; this completion pass does not silently broaden the seed hook or reinterpret requests as successful pins. All DoD items are now met; task stays In Progress because AC3 is not genuinely met.

Final game cleanup verified by state: default-off Forest control run left running, editor=false, frozen=false, spawnsOff=false, invulnerable=false; explicit camera clear sent. Fresh docs-only final wording passed markdownlint again. No new task created for Desert seed control.

Terrain seed follows MapGenerationController.mapSeed into MapGenerator.GenerateMap and pure Noise.GenerateNoiseMap. A ref-argument prefix corrupted the native call; guarded re-invocation with a value argument works. The mesh builder input provides 58081 float cells via buffer@multi; wrapper field reads are unreadable and no cell-by-cell validation occurred. Initial seven-run results showed equal repeated-pin hashes, another hash at another seed and different unseeded hashes; these are archived separately pending fresh stats-bearing measurements. Stats compilation fixed (nullable value extraction), deployed DLL hash verified; 2175 C# tests and 37 capture self-checks pass. Original 11 journal records retain SHA-256 f15fcd55649627c1f90bbddd54c198a855984b0bdb884a8bc7fb0d04f5c45226. Fresh seven-run matrix is in progress; completion remains unclaimed.

Fresh stats-bearing matrix complete: seven new launches, all verified, with original 11 records still byte-identical (SHA-256 f15fcd55649627c1f90bbddd54c198a855984b0bdb884a8bc7fb0d04f5c45226). Desert StageDesert2/index1/proceduralMapScale1.1 verified in every controller dump; RunConfig.mapTierIndex remains 0. Pins 424242 at game rolls 1696564175 and 1387787013 both reach Noise as 424242 and produce CF4ED58EB73F18CE2D1832595B65577CB1E745B2CDD488E195F65FA7FB0555F6. Pin 1234567 gives 7B398C89…; unseeded rolls/noise seeds 1766705161 and 1355200338 give 8C8520D7… and D14E53CF…. All five grids are 58081 cells, buffer@multi, range 0–1; means 0.5011/0.5011/0.4732/0.5109/0.5262. No independent cell reads succeeded. Hashes compare four-decimal normalized mesh input, not final vertex/index buffers or bitwise float identity. Desert debugSeed remains 1952838951, tile hash 692987B2…, objects=0 and empty hash; no object determinism claim. Switch-off Desert control emits no measurement lines. Forest inertness verifies StageForest2/ParamForest2 and original tile hash, never enters terrain generator, and adds object hash 3E9FD818… to the original two outcomes.

All 26 published evidence lines round-trip exactly to the journal. Final validation: task check passes with 2175 C# tests and 1107 Python tests, Ruff and repository Markdown lint; separate markdownlint -c .markdownlint.jsonc docs passes after final wording. Capture self-test passes 37 checks. Rebuilt/deployed DLL byte-verified. Implementation commit e386be9; findings commit 0c02b85. Final default-off Forest relaunch completed, camera-clear sent; state verifies editor=false, frozen=false, invulnerable=false, spawnsOff=false. No seed-force broadening, tier-cap edits or environment-file changes.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a separate default-off development terrain-seed pin and mesh-input measurement path. Replaced request-only Desert seed evidence with two verified identical pins and two unseeded generations, plus different-seed/control checks; preserved the original Forest matrix and all 11 legacy journal records. Documented exact seed/noise/grid evidence, stage-asset versus progression limits, buffer-read uncertainty, unresolved Forest object drift and missing Desert prop/final-mesh coverage. Full tests and lint pass; implementation and findings committed separately. Game restored to default-off, unfrozen gameplay with spawns on and editor/camera overrides cleared.
<!-- SECTION:FINAL_SUMMARY:END -->
