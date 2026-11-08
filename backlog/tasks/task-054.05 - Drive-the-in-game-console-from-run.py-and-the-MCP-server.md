---
id: TASK-054.05
title: Drive the in-game console from run.py and the MCP server
status: Done
assignee: []
created_date: '2026-11-08T07:54:00Z'
updated_date: '2026-11-08T20:36:00Z'
labels: []
dependencies:
  - TASK-054.01
  - TASK-054.02
references:
  - scripts/run.py
  - scripts/mcp_server.py
  - src/MegabonkLevels.Mod/harness_command.cs
  - src/MegabonkLevels.Mod/dev_harness.cs
  - tests/test_mcp_server.py
documentation:
  - docs/development.md
parent_task_id: TASK-054
priority: medium
type: enhancement
ordinal: 196000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Agents verify game changes through the dev harness (`scripts/run.py` and the `megabonk` MCP server), not through OS-level keyboard input. Typing into the console with the harness `type` and `key` commands works, but it is slow, depends on the overlay being open, and gives back only a screenshot. A harness command that takes a raw console line and returns the console's reply lines makes the command language (TASK-054.02) testable end to end on any fleet box, including headless SSH sessions. The reply is exactly what the overlay would print. Lines run this way also appear in the console's scrollback and history, so a later screenshot shows them.

The line goes through the same registry, gating and dispatch as typed input, so `MEGABONK_DEV` gating applies here too.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A harness command accepts a console line and returns its reply lines and an ok flag; parse tests cover a missing or empty line
- [x] #2 run.py gains a console subcommand taking the line as one argument, printing the reply
- [x] #3 The MCP server gains a console tool returning the reply; tests/test_mcp_server.py covers the payload
- [x] #4 Gated verbs sent this way reply 'requires MEGABONK_DEV' when MEGABONK_DEV is not true
- [x] #5 Lines run through the harness appear in the overlay's scrollback and history
- [x] #6 docs/development.md lists the run.py and MCP console commands alongside the other harness commands
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
1. Add failing C# parser/console execution tests and Python CLI/MCP payload/reply tests.
2. Add a console harness command carrying a raw line; share the overlay submission path for registry binding, MEGABONK_DEV gating, execution, scrollback and history. Return reply lines plus a console-level ok flag without changing transport-envelope behavior.
3. Expose run.py console (one quoted argument, prints reply lines and exits nonzero on console refusal) and an MCP console tool using the shared payload builder.
4. Document both entry points, run focused suites and task check, and verify the rebuilt mod through the running game where available. Commit only task-related changes with a conventional subject.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Tests-first evidence: Python console tests failed for the absent CLI builder/subcommand and unknown MCP tool; C# tests failed compilation for the absent Console kind, Line property and Execute method before implementation. Focused tests then passed (294 C#; 12 Python including existing console-log tests).

task check passed: mod build, Go formatting/vet/tests, 2780 C# tests, 1158 Python tests, markdownlint and ruff. Live CLI and a fresh in-memory MCP client drove the rebuilt game successfully. Commands submitted before first opening the overlay appeared in numbered history and rendered scrollback; screenshot retained at .tools/evidence/console-harness-05405.png. Unknown verbs returned result.ok=false with reply lines and no MCP transport error. Non-dev launch verification is next.

Non-dev live verification passed after launching with MEGABONK_DEV=false: run.py console 'tp 1 2 3' printed requires MEGABONK_DEV and exited 1; a fresh MCP console('player.kill') returned result.ok=false and the same refusal with no tool transport error. Restored the normal dev/editor launch afterward. Implementation committed as 76fa569 (feat(harness): run console lines through CLI and MCP).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added console harness requests carrying a raw line and returning console-level ok plus printed lines. CLI and MCP share the payload builder and overlay submission path, preserving registry gating, history, scrollback and first-open persistence without key injection. Documented the request/reply contract and CLI exit behavior. Tests written first; task check passed (2780 C#, 1158 Python, Go checks and lint). Verified live CLI/MCP replies, overlay history/scrollback, and non-dev gating. Restart an existing MCP server to expose the console tool.
<!-- SECTION:FINAL_SUMMARY:END -->
