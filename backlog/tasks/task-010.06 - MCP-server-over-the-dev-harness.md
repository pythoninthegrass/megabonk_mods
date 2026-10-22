---
id: TASK-010.06
title: MCP server over the dev harness
status: To Do
assignee: []
created_date: '2026-10-22 03:43'
labels:
  - dev-harness
  - tooling
dependencies:
  - TASK-010.01
references:
  - scripts/run.py
  - scripts/test_run.py
  - scripts/launch_game.py
  - .mcp.json
  - taskfile.yml
documentation:
  - docs/development.md
  - AGENTS.md
  - 'https://github.com/modelcontextprotocol/python-sdk'
parent_task_id: TASK-010
priority: medium
ordinal: 59000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. Depends on TASK-010.01 (result files and `read_result` and the `state` command in run.py). Do not start until it is merged. Can run in parallel with TASK-010.03 and TASK-010.05; those add more harness commands that TASK-010.07 exposes as MCP tools, so keep the tool-registration pattern here easy to extend.

Goal: an MCP server `megabonk` so an agent can call typed tools instead of shell commands, and get screenshots back inline as image content. This task covers the commands that exist after TASK-010.01: relaunch, load, quit, screenshot, state, editor, freeze/resume, invulnerable/vulnerable, camera, plus a log reader. Input and gameplay tools come in TASK-010.07.

Design (decided):
1. New script `scripts/mcp_server.py`, executable PEP 723 like run.py: `requires-python = ">=3.13,<3.14"`, dependencies `mcp>=2.3,<3` and `python-decouple>=3.8`, and the same `[tool.uv] exclude-newer` pin as run.py. Header shebang `#!/usr/bin/env -S uv run --script`.
2. SDK v2 API (verified against the python-sdk docs; re-check with Context7 library `/modelcontextprotocol/python-sdk` before writing): `from mcp.server import MCPServer` (the v1 `FastMCP` path is the old name), `mcp = MCPServer("megabonk")`, tools with `@mcp.tool()`, async tools may take a `Context` and call `await ctx.report_progress(progress, total, message)` (absolute values), screenshots are returned by annotating the return type as `Image` and returning `Image(path=...)` from `mcp.server`'s helper (check the exact import in the docs), run with `mcp.run()` under `if __name__ == "__main__":` (stdio).
3. Import run.py the way scripts/test_run.py does: `sys.path.insert(0, str(Path(__file__).resolve().parent))` then `import run`. Reuse `run.resolve_game_dir`, `write_command`, `wait_for_outcome`, `read_result`, `send_screenshot`, `quit_game`, `wait_for_log_line`, `to_game_path`. Do not copy their logic.
4. stdout is the protocol channel: nothing may print to stdout. run.py's `send` and `main` print, so do not call them from tools; add small non-printing helpers in run.py (for example `run_command(harness, payload, timeout) -> dict` returning the parsed result and raising on rejected/timeout) with tests, and have `send` use it, keeping CLI output unchanged.
5. Extract `relaunch` from run.py's CLI dispatch (around lines 413-459) into `def relaunch(level: str | None, on_step: Callable[[str], None], ...) -> None` that raises on failure; the CLI passes a printing callback, the MCP tool passes one that calls `ctx.report_progress`. Write tests for the extraction first. Existing relaunch behaviour and exit codes must not change.
6. Blocking waits (the polling in `wait_for_outcome`, `quit_game`, relaunch) must not block the event loop: call them with `anyio.to_thread.run_sync`.
7. Tools and their return values: `relaunch(level?: str)` -> final `state` dict; `load(level: str)` -> result dict; `quit()` -> bool; `screenshot()` -> `Image` (write the PNG under a per-call temp path in the OS temp dir, not in the repo); `state()` -> dict; `editor(on: bool)`, `freeze()`, `resume()`, `invulnerable(on: bool)`, `camera(position?, rotation?, clear: bool = False)` -> result dict; `log_tail(pattern?: str, since_launch: bool = True, max_lines: int = 50)` -> list of lines (read MelonLoader/Latest.log via `game_paths.latest_log_path` or run.py's equivalent). A command that is rejected or times out raises a tool error with the result file's `error` text.
8. Register in `.mcp.json`: server `megabonk`, command `uv`, args `["run", "--script", "scripts/mcp_server.py"]`. Do not remove other entries.
9. Self-test `scripts/test_mcp_server.py` (PEP 723 header like scripts/test_run.py; scripts:test in taskfile.yml picks up every `scripts/test_*.py` automatically): use `from mcp.client import Client` with the `MCPServer` instance directly (in-memory transport, `async with Client(server) as client: await client.call_tool(name, args)`) against a temp harness directory (point the server at it with the same env override run.py uses for the game dir) and a fake-mod thread that watches `commands/`, writes `results/<name>` and moves the file to `done/`. Cover: a successful tool call, a rejected command (tool error carries the message), a timeout, and `screenshot` returning image content of type `image/png` with a valid PNG header (the fake mod writes a tiny valid PNG).

Steps (TDD): tests first for each helper and tool, then implement; `task check`; start the server by hand once (`uv run --script scripts/mcp_server.py`) to confirm it starts and stays silent on stdout until it receives a message; in the game: `/mcp` shows `megabonk` connected, then call `relaunch`, `state`, `screenshot` through it and view the image; document in docs/development.md ("MCP server": what it is, the tool list, how to register it, the no-stdout rule) and add one line to AGENTS.md under "Verifying changes in the running game".

Do not: print to stdout, duplicate run.py logic, add input or gameplay tools (TASK-010.07), or add dependencies beyond mcp and python-decouple.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 scripts/mcp_server.py is a PEP 723 script using MCPServer over stdio with the documented tools: relaunch, load, quit, screenshot, state, editor, freeze, resume, invulnerable, camera and log_tail
- [ ] #2 screenshot returns an inline image/png content block, and relaunch reports progress through the MCP context
- [ ] #3 Tools reuse run.py functions: relaunch is extracted from the CLI dispatch with tests written first and unchanged CLI behaviour, and a non-printing run_command helper replaces printing inside tool paths
- [ ] #4 Nothing is written to stdout by the server, and blocking waits run off the event loop
- [ ] #5 A rejected command or a timeout surfaces as a tool error containing the result file's error text
- [ ] #6 scripts/test_mcp_server.py uses the in-memory Client against a temp harness with a fake mod and covers success, rejection, timeout and screenshot, and runs under task scripts:test
- [ ] #7 The server is registered as megabonk in .mcp.json without removing other entries, and confirmed connected and working against the real game
- [ ] #8 docs/development.md has an MCP server section and AGENTS.md points to it
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
