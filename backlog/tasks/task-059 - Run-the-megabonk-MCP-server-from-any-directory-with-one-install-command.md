---
id: TASK-059
title: Run the megabonk MCP server from any directory with one install command
status: To Do
assignee: []
created_date: '2026-11-09T17:53:00Z'
labels: []
dependencies: []
references:
  - >-
    https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/get-started/real-host.md
  - >-
    https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/index.md
  - 'https://docs.astral.sh/uv/concepts/tools/'
documentation:
  - docs/development.md
  - site/src/content/mcp-config.md
modified_files:
  - pyproject.toml
  - uv.lock
  - scripts/mcp_server.py
  - scripts/run.py
  - scripts/game_paths.py
  - tests/test_mcp_server.py
  - docs/development.md
  - site/src/content/mcp-config.md
priority: medium
type: enhancement
ordinal: 210000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The registered command is `uv run --script scripts/mcp_server.py`, which only works when the MCP client happens to start its process at the repository root. Started from anywhere else it cannot find the script, and even a working-directory override leaves the server reading `.env`, `levels/` and `Taskfile.yml` from wherever it was launched. The goal is a single command an agent host can paste that works no matter where the client was started.

Investigated on 2026-11-09 (uv 0.11.32) whether this generalizes to `uvx` plus the repository. Findings a future implementer cannot recover from the code:

- `uvx` works as a launcher against an existing checkout. Both `uvx --directory <repo> --from <repo> python scripts/mcp_server.py` and `uvx --directory <repo> --with <pins> mcp run scripts/mcp_server.py` complete initialize + tools/list (45 tools) and a `paths` call from an unrelated working directory. The second duplicates the script header's pins and loses its `exclude-newer` guard.
- The clean `uvx --from <repo> <command>` form does not work: the project declares no build system and no console script, so the built wheel installs none of the script modules ("does not provide any executables").
- Making it installable is not only a metadata change. The scripts are working-tree scripts: `scripts/run.py` imports its siblings implicitly, which only resolves while the script directory is on `sys.path`, and the repo-relative anchors (`.env`, the default screenshot/evidence directory, the example forest level) plus the `task` subprocess resolve against the launch directory or the tool cache once installed. A scratch install demonstrated anchors pointing into the uv cache with the `.env` and evidence paths missing.
- A checkout is mandatory either way: the server reads `levels/`, `.tools/evidence`, `.env` and `Taskfile.yml` from it, so a git-URL install cannot replace a clone, and a git-based install caches its commit until refreshed.

So the work is either to package the Python harness so a real command can be installed while still discovering the user's checkout at runtime, or to settle on a working-directory-independent launch entry — and to say which in the docs. Decide which one, then make it true.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A machine with only uv installed can start the megabonk MCP server with one documented command that succeeds regardless of the client's working directory; verified by an initialize + tools/list handshake returning the full tool set from an unrelated directory
- [ ] #2 When started as an installed copy, the server resolves the game directory and `.env`, the default screenshot/evidence directory, and level files from the user's checkout rather than the tool cache; verified by the `paths` tool output and a screenshot landing in the checkout's evidence directory
- [ ] #3 Harness actions that shell out to `task` (relaunch) still work when the server process was started outside the checkout
- [ ] #4 Started where no checkout can be found, the server fails with an error naming the missing checkout instead of silently reading `.env` or writing evidence into an install cache
- [ ] #5 The server's dependency requirements live in exactly one authoritative place; record in implementation notes which one was kept and why
- [ ] #6 Checkout/repo-root discovery is covered by Python tests, including the installed-copy case, and `task scripts:test` passes
- [ ] #7 The MCP server section of docs/development.md and site/src/content/mcp-config.md show the same megabonk-only registration entry, agree with each other, and markdownlint passes on the changed files
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
