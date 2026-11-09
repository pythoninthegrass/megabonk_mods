---
id: TASK-014
title: Quiet the Steamworks-not-initialized trace during relaunch
status: Done
assignee:
  - '@claude'
created_date: '2026-10-23T17:43:00Z'
updated_date: '2026-11-09 05:26'
labels:
  - editor
dependencies: []
references:
  - src/MegabonkLevels.Mod/editor_mode.cs
priority: low
ordinal: 65000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`task game:editor` (`run.py relaunch`) prints and logs an IL2CPP stack trace (`System.InvalidOperationException: Steamworks is not initialized.`) while it polls the harness `steam-ready` command before the game's Steamworks client is up. It was first reported as a trace on closing the editor, but no editor close path reproduces it (harness off, F8, level reload with an object selected). The trace comes from the expected startup poll. The harness reported the not-ready state by throwing, so MelonLoader logged an ERROR and a trace on every poll. `SteamReady` should return not-ready as data and keep real faults visible.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The source and exception type of the trace are identified and recorded in the task notes
- [x] #2 The not-initialized fault is returned as a not-ready result by the harness; any other fault still propagates and is logged
- [x] #3 run.py steam-ready exits 1 on not ready and relaunch keeps polling until ready, with no stack trace in the console or Latest.log
- [x] #4 The probe logic is covered by tests outside the game, and the behavior is documented in docs/*.md
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reproduce the editor close paths (none produce a trace); identify the relaunch steam-ready poll as the source.
2. Tests first: C# `SteamReadiness` (steam_readiness_tests.cs) and `run.py steam-ready` exit codes (test_run.py).
3. Add `steam_readiness.cs`, use it in the `SteamReady` harness case, add `send_steam_ready` to run.py.
4. Document in docs/development.md ("Steamworks readiness").
5. Verify with `task check` and a fresh `task game:editor`.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Repro attempts on CrossOver (fresh relaunch, Tree0 selected each time), no IL2CPP trace in Latest.log: (a) harness `editor off`, (b) F8 key, (c) `load` of a level while the editor is open (run restart; EditorMode exits via Tick, then re-enters). Only trace in the log is the expected startup SteamReady one. Untested: player death, quit to menu, game quit while editor open.

Likely source of the reported trace: `task game:editor` (`run.py relaunch`) polls the harness `steam-ready` command until Steamworks initialises. While it is not ready, `dev_harness.cs` (SteamReady case) throws `System.InvalidOperationException: Steamworks is not initialized.` from `SteamApps.GetAppBuildId`. MelonLoader logs it as an ERROR with an IL2CPP stack trace and `run.py` echoes it (`steam-ready: rejected` plus the block). It prints before `load-level` and `editor`, so it is unrelated to closing the editor. Exception type: InvalidOperationException; path: startup readiness poll. Pending the maintainer's confirmation that this is the trace he saw.

Fix: `SteamReadiness.Probe` (steam_readiness.cs) catches only exceptions whose message contains `Steamworks is not initialized` (the Il2Cpp interop surfaces it with that text in Message, so the type cannot be matched) and returns `{ready:false}`; `{ready:true,buildId}` otherwise. run.py `send_steam_ready` treats `ready:false` as not ready; a null result counts as ready for older mods.

Verification: `task check` passed (668 C# tests, 165 pytest, lint clean). Fresh `task game:editor` printed `steam-ready: done` twice with no trace; Latest.log has one `Steamworks ready (build 21750826)` line and no `IL2CPP STACK TRACE`. The MCP server holds the old run.py in memory until restarted, so an MCP `relaunch` right after the change loaded the level early (LoadLevel hit the same fault and the retry succeeded).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The harness `steam-ready` command now returns `{ready:false}` while Steamworks starts instead of throwing, so relaunch polls no longer log an IL2CPP stack trace. `SteamReadiness.Probe` catches only the not-initialized message; other faults still propagate. `run.py steam-ready` exits 1 on not ready and `relaunch` keeps polling. The trace was never an editor-close fault: harness off, F8 and level reload with a selection all logged none. Verified with `task check` (668 C# tests, 165 pytest) and a fresh `task game:editor` with no trace in the console or Latest.log. Player death, quit to menu and game quit with the editor open were not tested. Restart the MCP server to pick up the new run.py.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
