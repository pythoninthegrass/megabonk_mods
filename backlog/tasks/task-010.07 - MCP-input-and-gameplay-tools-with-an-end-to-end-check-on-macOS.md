---
id: TASK-010.07
title: MCP input and gameplay tools with an end-to-end check on macOS
status: Done
assignee:
  - claude
created_date: '2026-10-22 03:43'
updated_date: '2026-10-23T01:47:00Z'
labels:
  - dev-harness
  - tooling
dependencies:
  - TASK-010.03
  - TASK-010.05
  - TASK-010.06
references:
  - scripts/mcp_server.py
  - tests/test_mcp_server.py
  - scripts/run.py
  - .mcp.json
documentation:
  - docs/development.md
  - AGENTS.md
parent_task_id: TASK-010
priority: medium
ordinal: 60000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. Depends on TASK-010.03 (harness `key`, `mouse`, `type` commands), TASK-010.05 (harness `teleport`, `dismiss-levelup` commands) and TASK-010.06 (the `megabonk` MCP server and its tool-registration pattern, `request_result` helper, ToolError handling and fake-mod test harness). Do not start until all three are merged. If TASK-010.05 shipped only one of its two commands, add only the matching tool and say so in the docs.

Goal: expose the new harness commands as MCP tools and prove the whole chain, agent to MCP to harness to mod to game and back, on macOS.

Tools to add to scripts/mcp_server.py, following the pattern TASK-010.06 set (async, off the event loop, no stdout, rejected command raises a tool error with the result file's error text):
- `key(key: str, modifiers: list[str] = [], action: Literal["tap","down","up"] = "tap")`
- `mouse(action: Literal["move","click","down","up","clear"], x?: float, y?: float, button: int = 0)`; coordinates are screenshot pixels, top-left origin, the same convention the harness uses
- `type_text(text: str)`
- `teleport(position?: list[float], cell?: list[int])`; exactly one of the two, validated in the tool before sending
- `dismiss_levelup(choice: int = 0)`
Each returns the result dict from the result file. Tool docstrings state the coordinate convention, the valid key names (point at docs/development.md) and the frame timing, because the docstring is what a less capable agent reads.

Steps (TDD): 1) failing tests in tests/test_mcp_server.py for each tool against the fake mod: exact payload written to commands/, result returned, a rejection surfaced as a tool error, argument validation (teleport with both or neither of position/cell, mouse move without x/y); 2) implement; 3) `task check`; 4) end-to-end check in the real game, recorded in the task notes with the commands used and what was seen: through the MCP tools only, `relaunch` (editor mode on), `screenshot` and view the palette, `mouse` click a palette entry, `type_text` into the palette search if TASK-005.07 has landed (otherwise use `key` taps for tool hotkeys and report which), `key` tap R on a selected object, `teleport` to a distant cell, `state` to confirm position and editor state, `screenshot` to see it, then `quit`. Do not use run.py or shell for anything in this check except reading the log if a step fails; 5) docs/development.md: add the new tools to the MCP server section, and write a short "End-to-end check" walkthrough that a future agent can follow; update AGENTS.md's "Verifying changes in the running game" so the MCP tools are the first-listed way and `cycle`/`relaunch` in run.py the fallback.

If any step of the end-to-end check fails, find out which layer (MCP, harness file, mod, game) and report it with the evidence; do not paper over it by switching to OS-level input.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 MCP tools key, mouse, type_text, teleport and dismiss_levelup exist, write the documented harness payloads, and return the result dict or raise a tool error carrying the result file's error text
- [x] #2 teleport validates that exactly one of position or cell is given, and mouse move validates that x and y are present, before anything is sent
- [x] #3 Tool docstrings state the screenshot-pixel top-left coordinate convention, point at the valid key names, and describe frame timing
- [x] #4 Each tool has a test in tests/test_mcp_server.py written first, covering payload, result, rejection and argument validation
- [x] #5 An end-to-end run through the MCP tools only (relaunch, screenshot, click, key or text input, teleport, state, screenshot, quit) succeeds on macOS and the commands and observations are recorded in the task notes
- [x] #6 docs/development.md lists all MCP tools and contains an end-to-end walkthrough, and AGENTS.md lists the MCP tools as the preferred way to verify in the running game
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
1. Tests first in tests/test_mcp_server.py: parametrized payload/result, rejection and argument-validation cases for key, mouse, type_text, teleport, dismiss_levelup (done, 26 failing before implementation).
2. Add the five tools to scripts/mcp_server.py using run.build_*_command and _request; validate teleport (exactly one of position/cell, lengths) and mouse (x/y both or neither, move needs both) and key (modifiers only with tap) before sending.
3. task check.
4. Docs: extend the MCP server section and add an End-to-end check walkthrough in docs/development.md; make the MCP tools the first-listed way in AGENTS.md.
5. End-to-end run through the MCP tools only after the megabonk MCP server is reconnected (the running server predates the new tools); record commands and observations in the task notes.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
End-to-end run on macOS (Wine runtime), MCP tools only, after reconnecting the megabonk server:
- relaunch -> state: editor true, frozen true, invulnerable true, player [120,1.925,-3] cell [10,7], paletteEntries 75, screen [1512,982].
- screenshot: palette on the left, Select tool active.
- mouse click (40,343) on the Boulder row -> palette title 'selected: Boulder'.
- key Alpha5 -> state editorTool Place. mouse click (760,540) -> log 'LiveEdit: spawned ... (prefab Boulder) as placement:0', 1 edit, boulder visible. key Alpha6 -> Select.
- mouse click (758,535) -> state selected 'placement:0'. key R -> log 'EditorObjectTools: rotate placement:0 clockwise -> object.move', edits 2.
- mouse click level-name field (690,77), type_text 'e2e' -> field shows 'e2e'. TASK-005.07 (palette search) has not landed, so text went into the level-name field and tool hotkeys were sent as key taps.
- teleport cell [30,30] -> tool error 'cell (30,30) is outside the 15x15 grid' (mod rejection surfaced as ToolError). teleport cell [2,12] -> {position [-200,-8.075,200], cell [2,12]}. state -> player position [-200,-8.075,200] cell [2,12], editor true. screenshot: HUD label 'me: pos(-200, -8, 200)'; the editor free-fly camera does not follow the player, so the view is unchanged.
- quit -> true.
No failures in any layer. dismiss_levelup was covered by the fake-mod tests only; no level-up dialog was open in the run.

dismiss_levelup in the real game (macOS): relaunch, editor(on=false), invulnerable on, user played to a level-up. state showed frozen true; screenshot showed 3 offers (Wireless Dagger, Aura, Space Noodle). dismiss_levelup(choice=1) -> {dialogWasOpen:true, chosen:'Aura'}. state afterwards: frozen false, editor false; screenshot showed the dialog closed and an Aura icon in the weapon slots with the aura ring around the player. dismiss_levelup(choice=0) with no dialog open -> {dialogWasOpen:false, chosen:null}, no error. An out-of-range choice was not run.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added MCP tools key, mouse, type_text, teleport and dismiss_levelup to scripts/mcp_server.py, with argument validation before anything is sent (teleport exactly one of position/cell, mouse move needs x and y, key modifiers only with tap). Tests were written first in tests/test_mcp_server.py (payload, result, rejection, validation); task check passes. docs/development.md lists the tools and has an End-to-end check walkthrough; AGENTS.md lists the MCP tools first. A full end-to-end run through the MCP tools on macOS succeeded (details in the notes). dismiss_levelup was verified by tests only.
<!-- SECTION:FINAL_SUMMARY:END -->
