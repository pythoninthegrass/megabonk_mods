---
id: TASK-005.05
title: 'Undo/redo UI, validate overlay, save/load UI'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-06 21:43'
updated_date: '2026-10-11 05:33'
labels:
  - level-editor
dependencies:
  - TASK-005.03
  - TASK-005.04
parent_task_id: TASK-005
priority: high
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-005 first for full context.

Implement three UI pieces that complete the editing loop:

1. **Undo/redo**: buttons and keybinds (e.g. Ctrl+Z/Ctrl+Y) calling TASK-003.03's `EditStack.Undo()`/`Redo()`, with the result re-applied live (reuse TASK-004.02's apply logic for the inverse operations too — confirm the live-application layer can apply an "undo" the same way it applies a forward edit, or extend it if needed).
2. **Validate overlay**: a button that runs TASK-003.04's reachability validator against the current live level state and visually highlights (e.g. a colored overlay or outline) any tiles it reports as unreachable from spawn, and separately indicates whether the boss portal is currently reachable.
3. **Save/load UI**: a save dialog (filename input, writes a `.mblevel.json` via TASK-003.01's serializer, capturing the current `EditStack`'s full edit history) and a load dialog (lists existing level files from `UserData/Levels/`, loads one via TASK-004.01's loader).

These three are grouped into one subtask since they're each relatively small, UI-focused wrappers around machinery TASK-003/TASK-004 already built.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Undo/redo buttons and keybinds correctly revert/reapply the most recent edit, visible live in the 3D view
- [x] #2 A validate action highlights every tile the reachability validator reports as unreachable from spawn, and separately reports boss-portal reachability
- [x] #3 A save dialog writes the current edit history to a named .mblevel.json file in UserData/Levels/ via TASK-003.01's serializer
- [x] #4 A load dialog lists existing level files in UserData/Levels/ and loads a selected one via TASK-004.01's loader
<!-- AC:END -->



## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approved plan (2026-10-10, Lance):
1) Add an editor session model that owns an EditStack seeded from the generated baseline plus currently loaded file edits, and exposes Apply/Undo/Redo, CanUndo/CanRedo, and current edit history for save.
2) Extend live edit application so undo/redo replays through the same live path as forward edits (same applier, fill regeneration, collision rebuild) rather than mutating scene state ad hoc.
3) Add validate UI action in editor mode that runs ReachabilityValidator on the current live state, renders an unreachable-tile overlay, and separately reports boss-portal reachability.
4) Boss portal targeting decision: Option 1 approved. Detect portal dynamically at runtime from live objects (PlayerSpawnPortal/portal-prefab-based match), then map its world position to a grid cell for IsReachable checks.
5) Add save/load UI in editor mode:
   - Save: filename input, writes .mblevel.json into <game>/UserData/Levels, serializing map/stage/tier/seed and the full current edit history.
   - Load: list existing .mblevel.json files from the same folder and load the selected one via LevelLoaderPatch.LoadAndStart.
6) Keep existing toolbar/tools behavior intact and integrate new controls cleanly.
7) TDD first for testable logic (session/undo-redo coordination, save filename normalization/path rules, level listing/sorting, portal-targeting helper behavior), then runtime/UI glue, then task check and docs updates (development.md and level-format.md as needed).

User-directed load regression fix (2026-10-10):
1. Remove the Load-adjacent previous/next chevron controls.
2. Add palette-style mouse-wheel selection while the pointer is over the saved-level list, with pure selection-index behavior covered by a failing unit test.
3. Change Load to call `LevelLoaderPatch.LoadAndStart` for the selected file, preserving its map/stage/tier/forced seed/pending edit pipeline so the selected save regenerates and applies immediately.
4. Build the mod, run focused and full tests, then use the development harness to verify the saved chest position and restored tree after a UI load.

User-directed harness reliability fix (2026-10-10): add an explicit `steam-ready` harness command that probes the in-game Steamworks client without starting a level; make `run.py relaunch` poll it before `load-level`, report readiness milestones, and cover the new payload/flow with script tests.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-11: Fixed non-deterministic level load/relaunch (objects re-rolling every generation despite forced debugSeed). Root cause found via Binary Ninja on GameAssembly.dll: object placement draws from two RNGs neither tied to debugSeed. Positions use UnityEngine.Random.Range. Per-prefab counts use RandomMapObject.GetAmount() rolling on Utility.MyRandom.random, a static ConsistentRandom whose static ctor seeds once from QueryPerformanceCounter (wall clock). Drifting counts cascade into shifted positions even when UnityEngine.Random is reseeded, and mapSeed has no effect. Fix (seed_force_patch.cs): SeedForcePatch.ReseedPhase reseeds both RNGs from the forced seed before each spawn sub-phase via Harmony prefixes on GenerateTileObjects.Generate, SpawnInteractables.SpawnChests/SpawnShrines, and RandomObjectPlacer.GenerateInteractables, using SpawnSeed.PhaseSeed (new pure helper in spawn_seed.cs; SeedForceMode enum moved there) for a phase-distinct derived seed. Added objectsHash to the generation report (generation_report.cs/generation_patch.cs/generation_hash.cs reuse) to verify. Live verification: two relaunches of levels/example-forest.mblevel.json now produce byte-identical objectsHash and identical per-category object hashes/counts, while mapSeed still varies freely. Tests: new spawn_seed_tests.cs (ForcedSeed/PhaseSeed), updated generation_report_tests.cs; full task check passes (537 xUnit, 44 script tests, markdownlint, ruff). Docs: docs/map-generation-determinism.md gains an "Object placement determinism" section. Also added binary_ninja MCP server to opencode.jsonc and .mcp.json.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
