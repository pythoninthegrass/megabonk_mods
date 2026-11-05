---
id: TASK-038.01
title: >-
  Attribute Wine stubs to their CrossOver bottle on macOS and report what the
  quit reaper spared
status: To Do
assignee: []
created_date: '2026-11-05 21:10'
updated_date: '2026-11-05 21:10'
labels:
  - tooling
  - process-hygiene
  - macos
dependencies: []
references:
  - scripts/run.py
  - tests/test_run.py
documentation:
  - docs/development.md
parent_task_id: TASK-038
priority: medium
ordinal: 169000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
On macOS under CrossOver, `run.py quit` cannot tell which bottle a Wine stub process belongs to, so any live Windows process in any bottle makes the reaper leave every stub alone. Observed on the macOS CrossOver host: with the game not running, `quit` printed "leaving Wine leftovers alone while other Windows processes run" and listed nine pids. Eight were the Steam client inside Megabonk's bottle; the ninth was an unrelated game running for weeks in a different bottle. That one process held back the reap of roughly 30 stubs (services, winedevice, plugplay, svchost, rpcss, explorer, lsass, conhost) from several boot generations until it was killed by hand. After it was killed, `quit` stopped 28 leftover processes and force-killed 4 more.

Why attribution fails today: the reaper attributes a process to a prefix from its environment (WINEPREFIX, Proton's STEAM_COMPAT_DATA_PATH) or a drive_c/pfx path in argv. On macOS the process table comes from `ps`, which carries no environment, and CrossOver's stubs have no bottle path in argv, so every stub is "unattributed" and falls back to the blanket rule: reap only when no Windows process is live at all.

What macOS does expose, confirmed with `lsof -p <pid>` on the affected host: stubs hold open files under `~/Library/Application Support/CrossOver/Bottles/<bottle name>/drive_c/...`, so the bottle name is readable per process; and each bottle has its own wineserver socket directory under `/private/tmp/.wine-<uid>/server-<id>/`, shared by every process of that bottle. A process with no bottle path of its own (for example the `winewrapper.exe` of the unrelated game) shares its server directory with processes that do have one, so it can be attributed through that directory.

Second problem: the "leaving Wine leftovers alone" message is a bare pid list. Working out what held the reap back required running `ps` on each pid by hand. The message should name what it spared and why.

Not in scope: stopping the Steam client that lives inside the bottle (`--stop-steam` only handles the native client and the Flatpak today); that is separate work.

Tests come first, against an injected process-table provider, following the existing pattern in tests/test_run.py.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 On macOS, a stub whose open files are under Megabonk's bottle is attributed to that bottle, and a stub under another bottle is attributed to that other bottle
- [ ] #2 A process with no bottle path of its own is attributed to the bottle of any process that shares its wineserver socket directory
- [ ] #3 With a live Windows process attributed to a foreign bottle, quit still reaps the stubs attributed to Megabonk's bottle and never signals the foreign bottle's processes
- [ ] #4 A stub that cannot be attributed (lsof unreadable or no bottle signal) keeps the current conservative behaviour: reaped only when no Windows process is live
- [ ] #5 Reading open files execs only flags valid on macOS, is confined to the single macOS process-table function behind the injected provider, and the Linux path still execs no external command
- [ ] #6 The 'leaving Wine leftovers alone' message names each spared process with its executable, its bottle (or 'unknown') and the reason it was spared, instead of a bare pid list
- [ ] #7 Unit tests for attribution, the foreign-bottle spare, the unattributable fallback and the message are written first and pass; the existing reap tests are updated rather than duplicated where pinned semantics change
- [ ] #8 docs/development.md documents the macOS attribution signals, the fallback, and the new message; task check passes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
