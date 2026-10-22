---
id: TASK-010.01
title: Harness command results and a state command
status: Done
assignee:
  - claude
created_date: '2026-10-22 03:42'
updated_date: '2026-10-22T05:54:00Z'
labels:
  - dev-harness
  - tooling
dependencies: []
references:
  - scripts/run.py
  - scripts/test_run.py
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/harness_command.cs
  - tests/MegabonkLevels.Tests/harness_command_tests.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
documentation:
  - docs/development.md
  - AGENTS.md
modified_files:
  - docs/development.md
  - scripts/run.py
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/editor_object_tools.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
  - src/MegabonkLevels.Mod/harness_command.cs
  - src/MegabonkLevels.Mod/harness_result.cs
  - src/MegabonkLevels.Mod/kill_floor_watcher.cs
  - src/MegabonkLevels.Mod/player_invulnerability.cs
  - src/MegabonkLevels.Mod/position_label.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - tests/MegabonkLevels.Tests/harness_command_tests.cs
  - tests/MegabonkLevels.Tests/harness_result_tests.cs
  - tests/test_run.py
parent_task_id: TASK-010
priority: medium
ordinal: 54000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. No dependencies; can run in parallel with TASK-010.02 and TASK-010.04.

Problem: the harness tells the caller only whether a command was accepted (file lands in harness/done/ or harness/rejected/). Data comes back through side channels (a PNG, lines in MelonLoader/Latest.log). Agents need a structured result per command and a way to ask for the game's current state.

Design (decided, do not change; other subtasks build on it):
1. In `DevHarness.Process` (dev_harness.cs), before moving the command file to done/ or rejected/, write `<game dir>/harness/results/<command file name>` atomically (write `<name>.tmp`, then rename). Create `results/` in `Install` next to the other folders. The command file still moves exactly as today, so run.py stays backward compatible.
2. Result body, UTF-8 JSON, one object: success `{"command":"<wire name>","ok":true,"result":<object or null>}`; failure `{"command":"<wire name>","ok":false,"error":"<message>"}`. A parse failure writes the failure form with command `null`.
3. `Execute` returns the result object (or null) for each command. Existing commands return null except where noted by other subtasks.
4. New command `state`, wire `{"command":"state"}`, add `State` to `HarnessCommandKind` and to `HarnessCommand.TryParse`. Its result object has these fields; a field the mod cannot source is `null` (record the reason in docs/development.md): `levelLoaded` (bool), `killFloorArmed` (bool), `editor` (bool), `frozen` (bool), `invulnerable` (bool), `player` (`{"position":[x,y,z],"cell":[x,y]}` or null), `editorTool` (string or null), `selected` (string, genId or placement id, or null), `paletteEntries` (int or null), `screen` (`[width,height]`).
5. Keep the pure part Unity-free: a `HarnessResult` record plus a serializer in a new file `src/MegabonkLevels.Mod/harness_result.cs` and a `GameStateSnapshot` record, both linked into the test project with a `<Compile Include="../../src/MegabonkLevels.Mod/harness_result.cs" Link="harness_result.cs" />` entry in the test csproj (follow the existing entries). Unity-reading code that fills the snapshot stays in dev_harness.cs.
6. scripts/run.py: add `read_result(harness: Path, name: str) -> dict | None` (None when the file is absent or not valid JSON), and a `state` subcommand that sends the command, then prints the result JSON on stdout. `send` also reports `ok:false` results as a failure exit code 1 with the error text. Update the module docstring usage list.

Steps (TDD): 1) failing xUnit tests for the result serializer (success with object, success with null, failure, special characters in the error) and for `TryParse` of `{"command":"state"}`; 2) failing Python tests in scripts/test_run.py for `read_result` (present, absent, invalid JSON) and the `state` subcommand against a temp harness dir with a fake result file; 3) implement; 4) `task check`; 5) in the game: `task mod:build`, `uv run scripts/run.py relaunch`, `uv run scripts/run.py state`, confirm `editor: true` and a non-null `player`; 6) update docs/development.md (result files, the `state` fields table, the null-field reasons) and the "Not covered" list.

Do not: change the done/rejected semantics, add a socket or HTTP listener, or put result data into log lines.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every harness command writes harness/results/<name> before its command file moves to done/ or rejected/, atomically, in the documented success and failure shapes
- [x] #2 A state command returns levelLoaded, killFloorArmed, editor, frozen, invulnerable, player, editorTool, selected, paletteEntries and screen, with null for any field that cannot be sourced
- [x] #3 run.py has read_result and a state subcommand that prints the result JSON, and a result with ok:false makes the subcommand exit 1
- [x] #4 Result serialization and state command parsing have xUnit tests written first; read_result and the state subcommand have Python self-tests written first
- [x] #5 Confirmed in the running game: state after relaunch reports editor true and a non-null player
- [x] #6 docs/development.md documents the results folder, the result shapes and the state fields, and the Not covered list is updated
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
Work in worktree ../megabonk_mods.TASK-010.01 on branch TASK-010.01 (main checkout is occupied by TASK-010.02). Note tests live in tests/test_run.py, not scripts/test_run.py.

1. xUnit tests first (tests/MegabonkLevels.Tests): harness_result_tests.cs (success with object, success with null, failure, special characters in error, null command on parse failure, GameStateSnapshot JSON with nulls and with values) and TryParse of {"command":"state"} in harness_command_tests.cs. Link harness_result.cs into the test csproj. Confirm red.
2. Python tests first (tests/test_run.py): read_result present/absent/invalid JSON, state subcommand against a temp harness dir with a fake result file, send reporting ok:false as exit 1. Confirm red.
3. Implement: harness_result.cs (HarnessResult, GameStateSnapshot, serializer); HarnessCommandKind.State + TryParse; DevHarness.Process writes harness/results/<name> atomically before moving the command file, Execute returns JsonObject?; state snapshot reader in dev_harness.cs (needs small public accessors: KillFloorWatcher.Armed, PlayerInvulnerability.Active, EditorTileTools.CurrentTool, EditorObjectTools selection, PositionLabel cell lookup); run.py read_result, state subcommand, send checks result.
4. task check; task mod:build; uv run scripts/run.py relaunch then state; confirm editor true and non-null player.
5. docs/development.md: results folder, shapes, state field table, null-field reasons, Not covered list. Conventional commit, no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added HarnessCommand.Name (wire name recorded by TryParse) so result files carry the wire name; not in the original design, needed because the command file name does not contain it. The mod's .NET 6 System.Text.Json has no JsonNode.DeepClone, so HarnessResult.ToJson re-parses the result text instead. In-game check on the Wine setup: relaunch then state returned editor true, player position [120,1.925,-3], cell [10,7], paletteEntries 75; a malformed command file produced a result with command null; a rejected steam-ready produced an ok:false result. Python tests are in tests/test_run.py (scripts/test_run.py named in the task does not exist). Work done in worktree ../megabonk_mods.TASK-010.01, branch TASK-010.01, commit 833a39f.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Every harness command now writes harness/results/<command file name> atomically before its file moves to done/ or rejected/ (ok:true with result object or null; ok:false with error; command null on parse failure). New state command returns levelLoaded, killFloorArmed, editor, frozen, invulnerable, player (position and grid cell), editorTool, selected, paletteEntries and screen, with null where not sourceable (reasons in docs/development.md). run.py gains read_result and a state subcommand, and any command whose result has ok:false exits 1 with the error on stderr; a missing result file does not fail a command. Pure serializer and snapshot live in harness_result.cs, linked into the test project. Verification: task check passes (551 xUnit, 101 pytest); in the running game, state after relaunch reported editor true and a non-null player. Risk: the rebuilt DLL was deployed into the shared game Mods folder, so TASK-010.02 runs in the same game directory will load it. Follow-up for other subtasks: Execute now returns JsonObject, so new commands return their data from their switch case.
<!-- SECTION:FINAL_SUMMARY:END -->
