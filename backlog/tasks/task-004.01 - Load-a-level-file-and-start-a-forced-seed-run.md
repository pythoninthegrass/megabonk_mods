---
id: TASK-004.01
title: Load a level file and start a forced-seed run
status: Done
assignee: []
created_date: '2026-10-06 21:42'
updated_date: '2026-10-07 22:59'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-004
priority: high
type: feature
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-004 first for full context.

Wire TASK-003's level file reader into the MelonLoader mod: given a path to a `.mblevel.json` file, read it (reusing TASK-003's schema/deserialization code directly, not reimplementing), and start a Megabonk run using its `map`, `stageIndex`, `tier`, and `seed` fields — forcing the seed via whichever field(s) TASK-002.02 confirmed actually control generation (`MapGenerationController.mapSeed` and/or `ProceduralTileGeneration.debugSeed`), and starting the run via `MapController.TestMap(RunConfig)` or `StartNewMap(RunConfig)` per TASK-002's confirmed findings — not the hypothesis in the parent task description if TASK-002 found something different.

Also implement the `gameBuildId` check: compare the level file's recorded build ID against the running game's actual build ID (confirm where this is obtainable — e.g. Steam's reported build ID, or a game-internal version string) and surface a clear warning (not a crash, not a silent ignore) if they differ, since level layouts may shift across game updates.

For this subtask, a hardcoded/manually-placed test level file (no edits, or trivial edits) is sufficient — proving file-to-running-map works is the goal; edit application is TASK-004.02's job.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A level file can be loaded and used to start a run with the exact map, stage, tier, and seed it specifies
- [x] #2 The seed-forcing mechanism matches whatever TASK-002.02 confirmed actually controls generation, not an unverified assumption
- [x] #3 Starting the run reuses MapController's confirmed entry point rather than reimplementing game logic
- [x] #4 A gameBuildId mismatch between the level file and the running game produces a visible warning without crashing or silently proceeding
- [x] #5 The same level file produces the same observable map when loaded twice, confirming the forced seed actually takes effect
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
1. GameBuildIdCheck (Unity-free, test-first): pure MismatchWarning(recorded, actual) comparison.
2. GameBuildIdPatch: thin Il2Cpp wrapper exposing Il2CppSteamworks.SteamApps.GetAppBuildId() as the actual build id.
3. Extend SeedForcePatch (TASK-002.02's confirmed debugSeed hook) with a LevelSeed mode so a level file's exact seed forces generation through the same, single Harmony prefix already proven to control Tiles-map generation.
4. LevelLoaderPatch.LoadAndStart: read a .mblevel.json via TASK-003's LevelFileSerializer, resolve MapData via Resources.FindObjectsOfTypeAll<MapData>() + stageIndex, force the seed, build a RunConfig, start via MapController.StartNewMap(RunConfig) — switched from the original TestMap(RunConfig) hypothesis after live testing showed TestMap only stages state without leaving the main menu.
5. Hotkey (F6, not F10 — F10 collides with the game's own built-in debug console) in MegabonkLevelsMod loads a hardcoded Mods-folder file; sample level file committed at levels/example-forest.mblevel.json (Forest, stage 0, tier 0, debugSeed=20261007 — the exact seed TASK-002.02 proved reproducible).
6. Reuse TASK-002.02's existing GenerationPatch hash logging for AC #5 (load three times, diff hash= lines) instead of adding new verification code.
7. docs/level-format.md documents all of the above.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Code complete and live-verified end-to-end on the CrossOver install (TASK-002's reference platform).

**TestMap(RunConfig) does not start a run — switched to StartNewMap(RunConfig).** The original hypothesis (and TASK-002's unverified assumption) was `MapController.TestMap(RunConfig)`. Live testing (a `SceneTransitionProbe` Harmony postfix, temporary investigation code, see `src/MegabonkLevels.Mod/scene_transition_probe.cs`) proved `TestMap` only sets `MapController.currentMap`/`currentStage`/`runConfig` — `IsMainMenu()` stays `true` before and after, and no generation follows. The same probe confirmed a normal manual map-select-and-confirm playthrough calls `MapController.StartNewMap(RunConfig)`, immediately followed by `A_GenerationComplete`. `LevelLoaderPatch` now calls `StartNewMap`, confirmed live.

**F10 collided with the game's own built-in debug console** (an in-game dev console, unrelated to the mod, also bound to F10) — moved the load hotkey to F6.

**Harmony patch safety: check RVA uniqueness before patching.** Patching `MapMenu.StartMap` crashed the game instantly on load. Its RVA (`0x3321E0`) is shared by 1,453 other methods in `.tools/il2cpp_dump/dump.cs` — a linker-folded trivial/empty-body address — so the patch hijacked every one of those unrelated call sites too. Also avoid patching core Unity engine methods (e.g. `SceneManager.LoadScene`) rather than game code; IL2CPP interop can't safely hook native icalls the way it hooks the game's own compiled methods. Documented in `docs/level-format.md` and as a comment on `scene_transition_probe.cs` for future Harmony patches in this mod.

**Live verification (AC #1, #2, #5):** pressing F6 from the main menu three separate times all produced `debugSeed=20261007` (the level file's seed) and the identical hash `0F5D88E2C673F1BA929868626D21FB06A2ECF014298975352EF3EF28634665CB`, despite each run's irrelevant random `mapSeed` differing. Confirms the forced seed reproduces the exact same map, and that `StartNewMap(RunConfig)` is the correct, confirmed entry point.

task check green (96/96 tests), deployed DLL hash-verified against rebuild before every live test per [[feedback_verify_deployed_mod_dll]].
<!-- SECTION:NOTES:END -->
