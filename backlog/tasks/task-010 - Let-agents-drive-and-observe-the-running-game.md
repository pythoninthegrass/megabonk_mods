---
id: TASK-010
title: Let agents drive and observe the running game
status: Done
assignee: []
created_date: '2026-10-22 03:42'
updated_date: '2026-10-23T01:51:00Z'
labels:
  - dev-harness
  - tooling
dependencies: []
priority: medium
ordinal: 53000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Goal: an agent (or script) on macOS can drive Megabonk with the mod loaded and read back structured results, without OS-level input and without grepping MelonLoader/Latest.log. Today the dev harness (scripts/run.py drops JSON files into <game dir>/harness/commands/, src/MegabonkLevels.Mod/dev_harness.cs polls them every 0.5 s of unscaled time and moves each to done/ or rejected/) can only report accepted or rejected. It also cannot press keys, click, type, move the player or dismiss the level-up dialog (docs/development.md, "Not covered").

Why: outstanding tasks TASK-005.07, 005.09, 005.04.01, 004.11, 005.06 and TASK-004 AC#3/#6 each need checks in the running game that involve keys, mouse, text entry or the player. OS-level injection is rejected: the osascript MCP sends keys only, needs the window frontmost and Accessibility permission, and has no mouse clicks. The editor reads input itself through 34 raw UnityEngine.Input calls in 5 files (editor_mode.cs, editor_tile_tools.cs, editor_object_tools.cs, editor_palette.cs, megabonk_levels_mod.cs), so input is injected inside the mod through one seam. Gameplay owned by Rewired (player movement, level-up dialog) gets targeted commands instead of generic input.

Structure (7 subtasks): 010.01 results and state; 010.02 input seam; 010.03 key/mouse/type commands; 010.04 research on teleport and level-up; 010.05 teleport and dismiss-levelup commands; 010.06 MCP server over the existing harness; 010.07 MCP input and gameplay tools plus end-to-end check. 010.01, 010.02 and 010.04 have no dependencies and can run in parallel.

Read first: docs/development.md (harness sections), AGENTS.md ("Verifying changes in the running game", "Reloading a rebuilt mod"), scripts/run.py, src/MegabonkLevels.Mod/dev_harness.cs, harness_command.cs.

Rules every subtask follows (restated in each): write a failing test first (TDD); no section-banner or multi-paragraph comments, at most a 1-2 line comment only where naming does not make intent clear; docs describe content, not task IDs; `task check` passes; conventional commit with no attribution; verify in the game with `task mod:build` then `uv run scripts/run.py relaunch`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every harness command returns a structured JSON result (or a structured error) that run.py can read
- [x] #2 The editor accepts injected key, mouse and text input without the game window having focus
- [x] #3 A player teleport and a level-up dismissal command exist
- [x] #4 An MCP server exposes the harness, with screenshots returned inline as image content
- [x] #5 An end-to-end check through the MCP server succeeds on macOS and is documented in docs/development.md
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
An agent can now drive Megabonk with the mod loaded and read structured results, without OS-level input or log grepping. All seven subtasks are done. Harness commands write result files (ok/error plus a result object) and a state command reports level, editor, player, tool and selection (010.01). The editor reads input through an injectable seam (010.02), fed by key, mouse and type commands that work with the game window unfocused (010.03). Player teleport (position or cell) and level-up dismissal were researched (010.04) and added as commands (010.05). The megabonk MCP server exposes the harness with screenshots returned inline (010.06) plus key, mouse, type_text, teleport and dismiss_levelup tools (010.07). An end-to-end run through the MCP tools only succeeded on macOS (relaunch, palette click, place, select, rotate, text entry, teleport, state, screenshot, quit), and dismiss_levelup was confirmed in the real game for a valid pick, no dialog open and an out-of-range choice. The walkthrough is in docs/development.md ("MCP server", "End-to-end check") and AGENTS.md lists the MCP tools first. Open items: the palette search text path (needs the palette search feature to land) is untested end to end, and the teleport-after-relaunch non-application noted in docs/development.md did not recur but is unexplained.
<!-- SECTION:FINAL_SUMMARY:END -->
