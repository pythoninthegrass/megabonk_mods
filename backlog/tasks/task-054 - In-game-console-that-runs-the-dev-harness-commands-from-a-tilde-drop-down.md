---
id: TASK-054
title: In-game console that runs the dev harness commands from a tilde drop-down
status: Done
assignee: []
created_date: '2026-11-08T07:53:00Z'
updated_date: '2026-11-08T20:42:00Z'
labels: []
dependencies: []
references:
  - scripts/run.py
  - scripts/mcp_server.py
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/harness_command.cs
  - >-
    https://www.pcgamer.com/fallout-4-cheats-and-console-commands-can-turn-you-into-a-superhero/
documentation:
  - docs/development.md
priority: medium
type: feature
ordinal: 191000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Today every game-side command can only be sent from outside the game: `scripts/run.py` and the `megabonk` MCP server write JSON into the file-queue dev harness (`<game>/harness/commands`). That needs a shell, the `harness/enabled` marker and a second machine or terminal. The maintainer wants a Fallout 4-style console inside the game: pressing the backquote/tilde key slides a dark grey, translucent panel up from the bottom of the screen, and typed commands run there.

Decisions already made by the maintainer (binding for all subtasks):
- **Naming:** verbs are snake_case, with dot notation for namespaces, the way Fallout writes `player.additem`. Examples: `player.teleport 10 5 3`, `enemies.kill all`, `music.track 12`. Short Fallout-style aliases sit alongside: `tgm` (toggle god mode / invulnerable), `tfc` (toggle editor free camera), `killall`, `coc` (load a level by title), `tm` (toggle HUD), `qqq` (quit), `tp`, `cls`.
- **Scope:** parity with every in-game command that `run.py` / MCP expose. Host-only commands are excluded: relaunch, cycle, teardown, enable/disable, menu, paths, log_tail/log_wait, key/mouse/type, steam-ready, character-screen, load-bundle, music-probe, apply-pending-edits. The console also gets music transport (play/pause/next/prev/play track N/list/now playing).
- **Gating:** harmless verbs (help, clear, history, state, music.*, ui.hud, ui.coordinates, level.list) work for everyone. Cheat and debug verbs need `MEGABONK_DEV=true` and otherwise reply `requires MEGABONK_DEV` without running.
- **Pause:** opening the console pauses the run and closing it restores the previous pause state, as Fallout 4 does. The cursor is freed while the console is open. The mod has no way to block Rewired gameplay input today, so pausing is what stops typed keys from moving the player.
- **Single source of truth:** console verbs go through the existing harness parser and dispatcher rather than reimplementing handlers, so harness and console behaviour cannot drift apart.
- **Coexistence:** the game has its own dev `DebugConsole` on F10. The mod's F6–F9 hotkeys must keep working, and the tilde console must not open while the game's DebugConsole is active.

Subtask map and order:
- TASK-054.01 (in-process harness entry point) and TASK-054.02 (command language) are independent and can run in parallel.
- TASK-054.03 (overlay UI), TASK-054.04 (music transport) and TASK-054.05 (run.py/MCP `console` command) each depend on .01 and .02. They are independent of each other.
- DRAFT-001 (XP/gold/silver/heal), DRAFT-002 (true god mode and noclip) and DRAFT-003 (bookmarks, teleport to camera, boss spawn, `bat` scripts) are proposed new verbs. They are not approved; they stay Drafts until the maintainer promotes them.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Pressing the backquote/tilde key in a run, in the editor, or on menus opens and closes a translucent dark grey console anchored to the bottom of the screen
- [x] #2 Every in-game run.py/MCP command has a snake_case dot-notation console verb, and the listed Fallout-style aliases work
- [x] #3 Cheat/debug verbs refuse with 'requires MEGABONK_DEV' when MEGABONK_DEV is not true; harmless verbs still run
- [x] #4 The run is paused while the console is open and its previous pause state is restored on close
- [x] #5 Music transport verbs control level/radio playback
- [x] #6 docs/development.md documents the console (verbs, aliases, gating, keys) and README.md has a short player-facing note
- [x] #7 All subtasks are Done
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
1. Audit all eleven completed subtasks, their acceptance evidence and conventional commits against the parent criteria.
2. Add the missing player-facing README console note and reconcile stale commit checkboxes in the command-language and music subtasks using git history.
3. Validate documentation and rely on the immediately preceding successful full task check and live console checks for unchanged implementation. Record evidence, close the parent, and commit the closeout.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Closeout audit: all eleven subtasks (.01-.11) are Done with their acceptance criteria checked. Overlay/pause/cursor/menu and F10 evidence is recorded in .03 and rendering evidence in .06; command/alias/gating coverage is in .02; live pack/runtime/stock music transport verification is in .04; CLI/MCP replies, first-open history/scrollback and non-dev refusal verification is in .05. Enhancements and regression checks are recorded in .07-.11.

The immediately preceding task check on the final implementation passed: build, Go formatting/vet/tests, 2780 C# tests, 1158 Python tests, markdownlint and ruff. Closeout changes only add the missing README player-facing console note and reconcile stale commit checkboxes (.02 commit 1d6cd44; .04 commit 1380494). Markdownlint passed again for README.md and all console task records. Existing conventional implementation commits satisfy the commit requirement; no runtime code changed during closeout.

Known verification limits retained from subtasks: music playback was verified through source state/logs rather than by ear; gamepad interaction was not exercised. These are not unmet acceptance criteria. Unapproved draft verbs remain outside this task.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed the in-game tilde console and all eleven subtasks: shared in-process harness dispatch, command registry and aliases, dev gating, translucent bottom overlay with pause/cursor restoration, music transport, CLI/MCP console entry points, persistent history and fuzzy search, clear chord, scroll indicator, argument completion and literal path rendering. Parent closeout added the missing README player-facing note and reconciled stale subtask commit checkboxes. Acceptance evidence is recorded in the completed subtasks, including live-game checks; final implementation task check passed (2780 C#, 1158 Python, installer checks and lint). No remaining approved scope.
<!-- SECTION:FINAL_SUMMARY:END -->
