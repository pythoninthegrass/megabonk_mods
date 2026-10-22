---
id: TASK-010.01
title: Harness command results and a state command
status: To Do
assignee: []
created_date: '2026-10-22 03:42'
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
- [ ] #1 Every harness command writes harness/results/<name> before its command file moves to done/ or rejected/, atomically, in the documented success and failure shapes
- [ ] #2 A state command returns levelLoaded, killFloorArmed, editor, frozen, invulnerable, player, editorTool, selected, paletteEntries and screen, with null for any field that cannot be sourced
- [ ] #3 run.py has read_result and a state subcommand that prints the result JSON, and a result with ok:false makes the subcommand exit 1
- [ ] #4 Result serialization and state command parsing have xUnit tests written first; read_result and the state subcommand have Python self-tests written first
- [ ] #5 Confirmed in the running game: state after relaunch reports editor true and a non-null player
- [ ] #6 docs/development.md documents the results folder, the result shapes and the state fields, and the Not covered list is updated
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
