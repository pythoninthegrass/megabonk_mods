---
id: TASK-054.01
title: 'Run harness commands in-process, independent of the file queue and its marker'
status: To Do
assignee: []
created_date: '2026-11-08T07:53:00Z'
labels: []
dependencies: []
references:
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/harness_command.cs
  - src/MegabonkLevels.Mod/harness_result.cs
  - src/MegabonkLevels.Mod/megabonk_levels_mod.cs
documentation:
  - docs/development.md
parent_task_id: TASK-054
priority: medium
type: enhancement
ordinal: 192000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The in-game console (TASK-054) has to run the same commands as the file-queue dev harness without writing files. Two things stand in the way today:
- `DevHarness`'s dispatch switch is private and reachable only through the file poller.
- The harness logger and the rest of its setup are initialised only when the `<game>/harness/enabled` marker exists at startup. The console is available to every player (harmless verbs ungated), so it will run on installs without that marker, and handlers that log would then fail with a null logger.

This subtask exposes one in-process entry point that takes a parsed `HarnessCommand` and returns the same result envelope (`{command, ok, result|error}`) that the file queue writes. It also makes everything the handlers need available whether or not the marker exists. The marker keeps controlling only whether the file queue is polled.

This subtask provides the API that the console registry (TASK-054.02), the console UI (TASK-054.03) and the `console` harness command (TASK-054.05) call.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A public/internal entry point runs a parsed HarnessCommand on the main thread and returns the same ok/result/error envelope the file queue writes; a handler exception becomes ok=false with the message, not a crash
- [ ] #2 The file-queue path uses that same entry point, so queue behaviour and result files are unchanged (existing harness tests and run.py round trips still pass)
- [ ] #3 Handlers that log work when the harness/enabled marker is absent; without the marker the queue folders are still not created or polled
- [ ] #4 Tests cover the envelope for success, failure and handler exception where the logic is Unity-free
- [ ] #5 docs/development.md's harness section notes the in-process entry point and that the marker gates only the file queue
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
