---
id: TASK-010.06
title: MCP server over the dev harness
status: To Do
assignee: []
created_date: '2026-10-22 03:43'
updated_date: '2026-10-22 06:09'
labels:
  - dev-harness
  - tooling
dependencies:
  - TASK-010.01
references:
  - scripts/run.py
  - tests/test_run.py
  - tests/conftest.py
  - pytest.ini
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
Read parent TASK-010 first. TASK-010.01 is done (result files, `state` command, `read_result` and `send_for_result` in scripts/run.py). Can run in parallel with TASK-010.03 and TASK-010.05; those add more harness commands that TASK-010.07 exposes as MCP tools, so keep the tool-registration pattern here easy to extend.

Goal: an MCP server `megabonk` so an agent can call typed tools instead of shell commands, and get screenshots back inline as image content. This task covers the commands that exist now: relaunch, load, quit, screenshot, state, editor, freeze/resume, invulnerable/vulnerable, camera, plus a log reader. Input and gameplay tools come in TASK-010.07.

Where tests live (decided): the repo's Python tests are pytest tests in tests/ (not scripts/). tests/conftest.py already isolates every test from MEGABONK_* settings and the repo .env, and pins the anyio backend to asyncio. `task scripts:test` already supplies pytest, python-decouple and mcp (pinned with exclude-newer in taskfile.yml). Do NOT edit taskfile.yml, pytest.ini or tests/conftest.py. Async tests use `@pytest.mark.anyio` and need no other plugin. New test file: tests/test_mcp_server.py (plain pytest functions; `pythonpath = scripts` in pytest.ini lets it `import mcp_server` and `import run`).

MCP SDK facts (verified against mcp 2.3.0, do not re-derive):
- `from mcp.server import MCPServer`; `mcp = MCPServer("megabonk")`; tools are `@mcp.tool()`; stdio is `mcp.run()` under `if __name__ == "__main__":`.
- `from mcp.server.mcpserver import Image, Context`. A tool annotated `-> Image` returns `Image(data=<png bytes>, format="png")` or `Image(path=...)`; the client sees a content block with type `image` and mime type `image/png`. `await ctx.report_progress(progress, total, message=...)` takes absolute values.
- Errors: a plain exception inside a tool becomes the generic text "Error executing tool <name>" and the real message is lost. Raise `from mcp.server.mcpserver.exceptions import ToolError` with the message instead; the client then gets is_error true and text "Error executing tool <name>: <your message>".
- Tests: `from mcp.client import Client`; `async with Client(server) as client: result = await client.call_tool("name", {...})` talks to the MCPServer in memory. Check `result.is_error` and `result.content[0]` (`.type`, `.mime_type`, `.text`).

Design (decided):
1. New script `scripts/mcp_server.py`, executable PEP 723 like run.py: `requires-python = ">=3.13,<3.14"`, `dependencies = ["mcp>=2.3,<3", "python-decouple>=3.8"]`, and the same `[tool.uv] exclude-newer` pin as run.py. Shebang `#!/usr/bin/env -S uv run --script`.
2. Import run.py with `sys.path.insert(0, str(Path(__file__).resolve().parent))` then `import run`. Reuse what exists: `run.resolve_game_dir`, `run.load_lookup`, `run.write_command`, `run.wait_for_outcome`, `run.read_result`, `run.build_command`, `run.to_game_path`, `run.quit_game`, `run.launch_game`, `run.wait_for_log_line`, `run.wait_for_steamworks_ready`, `run.latest_log_path` (imported from game_paths). Do not copy their logic.
3. stdout is the protocol channel, so nothing may print to it. `run.send_for_result`, `run.send`, `run.quit_game` and `run.main` print. Split `send_for_result` into a non-printing `request_result(harness, payload, timeout) -> tuple[str, dict | None]` returning the outcome (`done`, `rejected` or `timeout`) and the parsed result file, and make `send_for_result` call it and keep its current printing and return value exactly. Tests first. MCP tools call `request_result` and raise ToolError (message = the result file's `error` when present, else `<command> <outcome>`) unless the outcome is `done` and the result is not `ok:false`. `quit_game` prints too: add a non-printing variant the same way, or implement the tool's quit with `request_result` plus `run.wait_for_exit`; keep `quit_game`'s CLI output unchanged.
4. Extract `relaunch` from the `case "relaunch":` branch of `main` (scripts/run.py) into `def relaunch(harness: Path, game_dir: Path, level: Path, timeout: float, task: str, on_step: Callable[[str], None], on_error: Callable[[str], None]) -> bool`. It must do exactly what the branch does now, in the same order: quit_game; launch_game(task); wait for `DevHarness: enabled`; wait_for_steamworks_ready; up to 5 load-level attempts each followed by waiting for `KillFloor: armed`; then invulnerable; then editor on. It returns True only if every step succeeded. The CLI branch becomes `ok = relaunch(..., on_step=print, on_error=lambda m: print(m, file=sys.stderr))` and `main` still returns 0 when ok and 1 otherwise; every message string stays identical, so CLI behaviour and exit codes do not change. The MCP tool passes callbacks that forward steps to `ctx.report_progress` and collect errors, and raises ToolError with the collected message when relaunch returns False. Tests first: monkeypatch `run.quit_game`, `run.launch_game`, `run.wait_for_log_line`, `run.wait_for_steamworks_ready` and `run.send` and assert (a) the call order and True on success, (b) False and the exact error text when the harness never becomes ready, (c) False when Steamworks never becomes ready, (d) a load that does not arm the kill floor is retried and gives up after 5 attempts with False.
5. Blocking waits (`wait_for_outcome`, `wait_for_exit`, `relaunch`) must not block the event loop: call them with `await anyio.to_thread.run_sync(...)`.
6. Tools and return values: `relaunch(level?: str)` -> the final `state` result dict; `load(level: str)` -> result dict; `quit()` -> bool; `screenshot()` -> `Image` (write the PNG to a per-call temp path in the OS temp directory, wait with `run.wait_for_png`, return `Image(path=...)`); `state()` -> dict; `editor(on: bool)`, `freeze()`, `resume()`, `invulnerable(on: bool)`, `camera(position?, rotation?, clear: bool = False)` -> result dict; `log_tail(pattern?: str, since_launch: bool = True, max_lines: int = 50)` -> list of lines from `run.latest_log_path(game_dir)`. Build payloads with `run.build_command` and the existing payload helpers (`build_editor_command`, `camera_payload`-style logic); do not invent new wire formats.
7. Register in `.mcp.json`: server `megabonk`, command `uv`, args `["run", "--script", "scripts/mcp_server.py"]`. Do not remove other entries.
8. Tests (tests/test_mcp_server.py) use `Client(server)` against a temp harness directory (point the server at it through MEGABONK_GAME_DIR, set with monkeypatch) and a fake-mod thread that watches `commands/`, writes `results/<name>` and moves the file to `done/` or `rejected/`. Cover: a successful tool call, a rejected command (is_error true and the text contains the result file's error), a timeout, `screenshot` returning an `image` content block with mime type `image/png` and a valid PNG header (the fake mod writes a tiny valid PNG), and that nothing was written to stdout (capsys).

Verification you can run unattended: `task scripts:test`, `task lint`, and starting `uv run --script scripts/mcp_server.py` by hand once to confirm it starts and prints nothing to stdout until it receives a message. Do not start the game and do not run `task game:*`.

Steps (TDD): tests first for each helper and tool, then implement; keep the CLI behaviour identical (the existing tests in tests/test_run.py must keep passing unchanged); document in docs/development.md ("MCP server": what it is, the tool list, how to register it, the no-stdout rule) and add one line to AGENTS.md under "Verifying changes in the running game".

Left for a human, not this task's agent: confirming against the real game that `/mcp` shows `megabonk` connected and that `relaunch`, `state` and `screenshot` work through it, with the image viewed. Write that into the task notes as an open item; do not claim it is verified.

Do not: print to stdout from the server, duplicate run.py logic, add input or gameplay tools (TASK-010.07), add dependencies beyond mcp and python-decouple, or edit taskfile.yml, pytest.ini or tests/conftest.py.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 scripts/mcp_server.py is a PEP 723 script using MCPServer over stdio with the documented tools: relaunch, load, quit, screenshot, state, editor, freeze, resume, invulnerable, camera and log_tail
- [ ] #2 screenshot returns an inline image/png content block, and relaunch reports progress through the MCP context
- [ ] #3 Tools reuse run.py functions: send_for_result is split into a non-printing request_result with tests written first and unchanged CLI output, and relaunch is extracted from the CLI dispatch with tests for its order, its failure cases and its 5-attempt limit, with unchanged CLI messages and exit codes
- [ ] #4 Nothing is written to stdout by the server, and blocking waits run off the event loop
- [ ] #5 A rejected command or a timeout surfaces as a ToolError whose text contains the result file's error, not the generic 'Error executing tool' text alone
- [ ] #6 tests/test_mcp_server.py uses the in-memory Client against a temp harness with a fake mod and covers success, rejection, timeout, screenshot and stdout silence, and runs under task scripts:test without changes to taskfile.yml, pytest.ini or tests/conftest.py
- [ ] #7 The server is registered as megabonk in .mcp.json without removing other entries
- [ ] #8 docs/development.md has an MCP server section and AGENTS.md points to it
- [ ] #9 The task notes list the check against the real game (megabonk connected under /mcp, relaunch, state and screenshot viewed) as an open item for a human, not as verified
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Definition of Done item 'task check passes' cannot be run unattended because task check builds the mod and the csproj deploys into the live game's Mods folder. This task changes only Python, so satisfy it with task scripts:test and task lint.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
