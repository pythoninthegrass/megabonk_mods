---
id: TASK-038.01
title: >-
  Attribute Wine stubs to their CrossOver bottle on macOS and report what the
  quit reaper spared
status: Done
assignee: []
created_date: '2026-11-05 21:10'
updated_date: '2026-11-05 23:15'
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
- [x] #1 On macOS, a stub whose open files are under Megabonk's bottle is attributed to that bottle, and a stub under another bottle is attributed to that other bottle
- [x] #2 A process with no bottle path of its own is attributed to the bottle of any process that shares its wineserver socket directory
- [x] #3 With a live Windows process attributed to a foreign bottle, quit still reaps the stubs attributed to Megabonk's bottle and never signals the foreign bottle's processes
- [x] #4 A stub that cannot be attributed (lsof unreadable or no bottle signal) keeps the current conservative behaviour: reaped only when no Windows process is live
- [x] #5 Reading open files execs only flags valid on macOS, is confined to the single macOS process-table function behind the injected provider, and the Linux path still execs no external command
- [x] #6 The 'leaving Wine leftovers alone' message names each spared process with its executable, its bottle (or 'unknown') and the reason it was spared, instead of a bare pid list
- [x] #7 Unit tests for attribution, the foreign-bottle spare, the unattributable fallback and the message are written first and pass; the existing reap tests are updated rather than duplicated where pinned semantics change
- [x] #8 docs/development.md documents the macOS attribution signals, the fallback, and the new message; task check passes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. ProcessInfo gains optional open_paths (default None).
2. read_process_table_ps (the single macOS table function) runs one `lsof -n -P -F pn` for Wine-looking pids, tolerating failure; Linux /proc path execs nothing.
3. wine_prefix_root also attributes via open paths under CrossOver/Bottles/<name>/drive_c; find_wine_leftovers lets a process with no bottle inherit the bottle of any process sharing its /private/tmp/.wine-<uid>/server-<id>/ directory.
4. Foreign-bottle processes never block our stubs and are never signalled; unattributable stubs keep the no-Windows-process-live rule.
5. WineLeftovers carries spared detail (pid, exe, bottle or unknown, reason); the quit message lists each.
6. Tests first in tests/test_run.py (attribution, server-dir inheritance, foreign spare, unattributable fallback, message, lsof argv, Linux no exec); update existing reap tests in place; confirm failing before implementing.
7. Update docs/development.md reap paragraph.
8. task check, one conventional commit, no attribution trailers.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The quit reaper now attributes Wine processes to their bottle on macOS and says what it spared.

- ProcessInfo gains open_paths. read_process_table_ps, the single macOS table function, runs one `lsof -n -P -F pn -p <pids>` for Windows-looking processes and tolerates a missing or refusing lsof. The Linux /proc path execs nothing.
- wine_prefix_root also reads drive_c/pfx roots from open files. A process with no signal of its own inherits the bottle that every attributed process sharing its /private/tmp/.wine-<uid>/server-<id>/ directory agrees on; a directory holding two bottles leaves it unattributed.
- A live foreign-bottle process no longer holds back our stubs and is never signalled. Unattributable stubs keep the reap-only-when-no-Windows-process-is-live rule.
- The "leaving Wine leftovers alone" message lists each spared process: pid, executable, bottle or unknown, and reason.
- Tests were written first and confirmed failing. The existing ps-flags test was updated in place because the ps table now adds an lsof call when a Windows process is present. docs/development.md documents the signals, fallback and message.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
