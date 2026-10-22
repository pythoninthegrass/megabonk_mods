---
id: TASK-010.07
title: MCP input and gameplay tools with an end-to-end check on macOS
status: To Do
assignee: []
created_date: '2026-10-22 03:43'
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
- [ ] #1 MCP tools key, mouse, type_text, teleport and dismiss_levelup exist, write the documented harness payloads, and return the result dict or raise a tool error carrying the result file's error text
- [ ] #2 teleport validates that exactly one of position or cell is given, and mouse move validates that x and y are present, before anything is sent
- [ ] #3 Tool docstrings state the screenshot-pixel top-left coordinate convention, point at the valid key names, and describe frame timing
- [ ] #4 Each tool has a test in tests/test_mcp_server.py written first, covering payload, result, rejection and argument validation
- [ ] #5 An end-to-end run through the MCP tools only (relaunch, screenshot, click, key or text input, teleport, state, screenshot, quit) succeeds on macOS and the commands and observations are recorded in the task notes
- [ ] #6 docs/development.md lists all MCP tools and contains an end-to-end walkthrough, and AGENTS.md lists the MCP tools as the preferred way to verify in the running game
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
