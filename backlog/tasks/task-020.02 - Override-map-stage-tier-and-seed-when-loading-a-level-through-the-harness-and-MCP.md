---
id: TASK-020.02
title: >-
  Override map, stage, tier and seed when loading a level through the harness
  and MCP
status: Done
assignee:
  - claude
created_date: '2026-10-27T20:07:00Z'
updated_date: '2026-10-27T21:18:00Z'
labels:
  - mcp
  - dev-harness
dependencies: []
parent_task_id: TASK-020
priority: low
type: enhancement
ordinal: 82000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Testing a different map meant copying a level file, patching its map with jq, running it, then deleting it; this happened three times in one session. Optional overrides on the load and relaunch calls would make a one-off probe a single call with no file left behind.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `run.py load`, `run.py relaunch` and the MCP `load` and `relaunch` tools accept optional map, stage, tier and seed overrides that replace those fields of the level file for that load only
- [x] #2 The level file on disk is not modified, and no temporary level file is left behind
- [x] #3 Without overrides the behaviour is unchanged
- [x] #4 An override value that is not an integer, or a stage outside the map's stage range, is rejected with the reason
- [x] #5 Argument parsing and override merging have offline unit tests
- [x] #6 Documented in docs/development.md
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
Approach: overrides ride on the `load-level` wire command and are merged in the mod after the level file is read, so nothing is written to disk (AC #2) and a temp file cannot be left behind or raced.

1. C# (tests first, tests/MegabonkLevels.Tests): `load-level` accepts optional integer fields `map`, `stageIndex`, `tier`, `seed`; a non-integer value fails the parse naming the field (AC #4). Add a pure `LevelOverrides.Apply(LevelFile)` that replaces only the supplied fields (AC #1, #3).
2. C#: thread the overrides from `HarnessCommand` through `dev_harness.cs` into `LevelLoaderPatch.LoadAndStart`; the existing stageIndex range check in `StartOnce` rejects an out-of-range stage with the reason; confirm the failure is visible to `run.py relaunch`.
3. Python (tests first, tests/test_run.py, tests/test_mcp_server.py): `--map/--stage/--tier/--seed` int options on `run.py load` and `relaunch`; `build_command`-style helper that adds only supplied overrides; `relaunch()` forwards them; MCP `load` and `relaunch` tools take the same optional ints.
4. Document the wire fields, CLI flags and MCP parameters in docs/development.md (AC #6).
5. `task check`, then live verification via relaunch with a map override.

Risk: the stage range depends on MapData, known only in the game, so that rejection surfaces through the game log / harness result rather than offline; offline tests cover parsing and merging only.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Live check on the CrossOver setup: `relaunch --map 2` logged `LevelLoader: starting map=Desert` with the level file's sha unchanged; `relaunch --stage 99` logged `LevelLoader: load failed: stageIndex 99 out of range for Forest (3 stages)` and exited 1 with `relaunch: the level failed to load`; a plain `relaunch` loaded Forest and entered the editor as before.

The out-of-range stage message previously lacked the `load failed` prefix that `relaunch` waits for, so a bad stage would have hung until timeout; the prefix was added to the log line.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`load-level` accepts optional integer `map`, `stageIndex`, `tier` and `seed`; the mod merges them in memory (`LoadOverrides.Apply`) after reading the level file, so no file is modified or created. `run.py load`/`relaunch` take `--map/--stage/--tier/--seed`; the MCP `load` and `relaunch` tools take `map/stage/tier/seed`. Non-integers (and unknown map values) are rejected at parse time naming the field; an out-of-range stage is rejected by the loader with `LevelLoader: load failed: ...`, which `relaunch` reports. Offline tests: C# `load_overrides_tests.cs` (1004 pass), Python `test_run.py`/`test_mcp_server.py` (266 pass); `task check` passes. Documented in docs/development.md. Verified through the restarted MCP server: `relaunch` with `seed=12345` logged `starting map=Forest ... seed=12345`, and `load` with `stage=99` logged the `load failed` rejection.
<!-- SECTION:FINAL_SUMMARY:END -->
