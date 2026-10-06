---
id: TASK-004
title: Play a custom level at runtime
status: To Do
assignee: []
created_date: '2026-10-06 21:41'
labels:
  - level-editor
dependencies:
  - TASK-003
priority: high
type: feature
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Goal: given a `.mblevel.json` file (TASK-003's format), make Megabonk actually load and play that exact level, start to boss, with the edits visibly applied and enemies able to path onto edited tiles — without uploading any score/stats for the modded run. This is the first task where TASK-003's Unity-free core library gets wired into the real MelonLoader mod and the real game.

## Context

Read TASK-002's findings docs (hook surface, determinism, tile grid/navmesh/genId scheme) and TASK-003's `docs/level-format.md` before starting — this task is pure integration of those two: load a level file (TASK-003's reader), force the game to generate the specified map/stage/seed (`MapController.TestMap(RunConfig)` or `StartNewMap`, per TASK-002's confirmed findings), then apply TASK-003's edit ops to the real, running `LevelState`-equivalent (the actual spawned GameObjects) once generation completes (`A_GenerationComplete`).

Known constraints from earlier research (verify against TASK-002's actual findings, which supersede this list if they differ):

- `MapGenerationController` static fields `mapSeed`/`A_PreGeneration`/`A_GenerationComplete` are the hook points.
- Tile spacing/sizing must be read from `StageData.mapParameters` at runtime, never hardcoded (confirmed by TASK-002.03).
- `SteamLeaderboardsManagerNew` uploads kills to boards including a server-side `banned_players` list — modded/custom-level runs must never call `QueueLeaderboardUpload`/`UploadLeaderboardScore`, and likely also the Steam achievement/stats writes, to avoid players getting flagged.
- No existing save/load of map layout exists in the game; this mod is the first thing to add one.

This task produces the runtime half of the "seed + edits" model: TASK-003 proved the data model and logic in isolation; this task proves it works against the live, running game.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A level file can be loaded by the mod and used to start a run with the exact map, stage, tier, and seed it specifies, verified by observing the resulting map matches a previously-saved reference
- [ ] #2 Edits from the level file (at least one tile height/slope change and one object add/remove) are visibly applied to the live game world after generation completes
- [ ] #3 Enemies path correctly onto tiles affected by edits (not just the originally-generated layout), verified by observation in a real playthrough
- [ ] #4 While a custom/edited level is active, no leaderboard upload, achievement, or stats write occurs, verified by log inspection showing those calls are skipped
- [ ] #5 Loading a level file whose recorded gameBuildId does not match the running game's build produces a visible warning rather than silently proceeding or crashing
- [ ] #6 A full playthrough from spawn to boss portal is completed on an edited level without errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
