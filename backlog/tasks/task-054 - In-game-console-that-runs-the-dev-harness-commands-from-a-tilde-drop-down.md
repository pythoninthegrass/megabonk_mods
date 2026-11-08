---
id: TASK-054
title: In-game console that runs the dev harness commands from a tilde drop-down
status: To Do
assignee: []
created_date: '2026-11-08T07:53:00Z'
updated_date: '2026-11-08T07:55:00Z'
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
- [ ] #1 Pressing the backquote/tilde key in a run, in the editor, or on menus opens and closes a translucent dark grey console anchored to the bottom of the screen
- [ ] #2 Every in-game run.py/MCP command has a snake_case dot-notation console verb, and the listed Fallout-style aliases work
- [ ] #3 Cheat/debug verbs refuse with 'requires MEGABONK_DEV' when MEGABONK_DEV is not true; harmless verbs still run
- [ ] #4 The run is paused while the console is open and its previous pause state is restored on close
- [ ] #5 Music transport verbs control level/radio playback
- [ ] #6 docs/development.md documents the console (verbs, aliases, gating, keys) and README.md has a short player-facing note
- [ ] #7 All subtasks are Done
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
