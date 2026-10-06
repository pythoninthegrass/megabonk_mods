---
id: TASK-004.01
title: Load a level file and start a forced-seed run
status: To Do
assignee: []
created_date: '2026-10-06 21:42'
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
- [ ] #1 A level file can be loaded and used to start a run with the exact map, stage, tier, and seed it specifies
- [ ] #2 The seed-forcing mechanism matches whatever TASK-002.02 confirmed actually controls generation, not an unverified assumption
- [ ] #3 Starting the run reuses MapController's confirmed entry point rather than reimplementing game logic
- [ ] #4 A gameBuildId mismatch between the level file and the running game produces a visible warning without crashing or silently proceeding
- [ ] #5 The same level file produces the same observable map when loaded twice, confirming the forced seed actually takes effect
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
