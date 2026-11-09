---
id: TASK-059
title: Run the megabonk MCP server from any directory with one install command
status: Done
assignee: []
created_date: '2026-11-09T17:53:00Z'
updated_date: '2026-11-09T19:42:00Z'
labels: []
dependencies: []
references:
  - >-
    https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/get-started/real-host.md
  - >-
    https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/run/index.md
  - 'https://docs.astral.sh/uv/concepts/tools/'
  - 'https://github.com/pythoninthegrass/osascript-mcp'
  - 'https://github.com/pythoninthegrass/osascript-mcp/blob/main/pyproject.toml'
  - >-
    https://github.com/pythoninthegrass/osascript-mcp/blob/main/src/osascript_mcp/server.py
documentation:
  - docs/development.md
  - site/src/content/mcp-config.md
modified_files:
  - pyproject.toml
  - uv.lock
  - taskfile.yml
  - .env.example
  - src/megabonk_harness/
  - scripts/run.py
  - scripts/game_paths.py
  - scripts/launch_game.py
  - scripts/mcp_server.py
  - scripts/perf_sweep.py
  - scripts/repair_bepinex.py
  - scripts/install_melonloader.py
  - scripts/il2cpp_dump.py
  - tests/
  - .mcp.json
  - opencode.jsonc
  - AGENTS.md
  - README.md
  - docs/development.md
  - docs/gamepadui.md
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

Reference implementation: the sibling `osascript-mcp` MCP server already ships the packaging shape to copy. It is an installable `src/osascript_mcp/` package (`__main__.py` plus a `main()` entry point, absolute intra-package imports) declared with `[build-system] requires = ["hatchling"]`, `[tool.hatch.build.targets.wheel] packages = ["src/osascript_mcp"]`, and a `[project.scripts] osascript-mcp = "osascript_mcp.server:main"` console command, and its README registers it as `uv tool install git+…` / `uvx --from git+… osascript-mcp` with `uv run --directory <repo> osascript-mcp` kept only for development. Copy that packaging and registration shape, not the SDK call surface: it pins `mcp>=1.7.1` and builds on `mcp.server.lowlevel.Server` + `stdio_server`, while this server targets `mcp>=2.3,<3`. It is also a self-contained tool with no repository to point at, so nothing there answers checkout discovery — the `.env`, evidence, `levels/` and `task` anchoring in criteria 2-4 has no precedent to copy.

Decision (2026-11-09): package the harness and register the installed command. Rather than patching the loose-script entry to be working-directory-independent, refactor the harness out of standalone working-tree scripts into an importable package that `uv tool install` can build a real command from, then document that command as the only registration. A checkout remains mandatory, so the documented flow is: clone the repository once, install the command once, and let the installed command discover that checkout at runtime.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A machine with only uv installed can run the megabonk MCP server with one documented `uvx` registration entry against the repository, with no per-machine path in the entry, and start it regardless of the client's working directory; verified by an initialize + tools/list handshake returning the full tool set from an unrelated directory
- [x] #2 When started as an installed copy, the server resolves the game directory and `.env`, the default screenshot/evidence directory, and level files from the user's checkout rather than the tool cache; verified by the `paths` tool output and a screenshot landing in the checkout's evidence directory
- [x] #3 Harness actions that shell out to `task` (relaunch) still work when the server process was started outside the checkout
- [x] #4 Started where no checkout can be found, the server fails with an error naming the missing checkout instead of silently reading `.env` or writing evidence into an install cache
- [x] #5 The installed command's dependency requirements live in exactly one authoritative place — the package metadata — with the script's duplicated PEP 723 pin list gone or clearly non-authoritative; record in implementation notes which one was kept and why
- [x] #6 Checkout/repo-root discovery is covered by Python tests, including the installed-copy case, and `task scripts:test` passes
- [x] #7 The MCP server section of docs/development.md and site/src/content/mcp-config.md show the same megabonk-only registration entry, agree with each other, and markdownlint passes on the changed files
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
Package the harness as `src/megabonk_harness/` built with uv_build (`[tool.uv.build-backend] module-name = "megabonk_harness"`), with console scripts `megabonk-mcp` and `megabonk-harness`.

1. Tests first: tests/test_checkout.py covers checkout discovery, including the cache-installed case.
2. Move game_paths, menu_input, launch_game, run and mcp_server into the package with absolute imports; replace `Path(__file__)` repo anchors with checkout discovery or `-m` invocations; run `task` with cwd set to the checkout.
3. Leave scripts/{run,game_paths,launch_game,mcp_server}.py as shims; move other scripts and tests to package imports; drop PEP 723 headers from scripts that now import the package.
4. Register the server with `uvx --from git+<repo> megabonk-mcp` and pass MEGABONK_REPO through, in .mcp.json, opencode.jsonc, docs/development.md and site/src/content/mcp-config.md.
5. Document uv and mise requirements in README.md and docs/development.md; document the new and previously missing variables in .env.example.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reference implementation: osascript-mcp (packaging shape only; its SDK surface and self-containedness were deliberately not copied, so checkout discovery is original work).

Layout: src/megabonk_harness/{checkout,game_paths,launch_game,menu_input,run,mcp_server}.py; scripts/{run,game_paths,launch_game,mcp_server}.py are shims. Checkout discovery order: MEGABONK_REPO, the working directory's ancestors, then the tree the module was loaded from (marker: taskfile.yml + src/megabonk_harness). Under uvx the code runs from uv's cache, so the third step never applies and the checkout comes from MEGABONK_REPO or the client's cwd.

Dependency authority (AC5): pyproject.toml. The PEP 723 headers were removed from the moved modules and from install_melonloader.py and il2cpp_dump.py, which now run in the project environment. pyproject was kept because the package build reads it and it already carries exclude-newer. A uvx install ignores the checkout's uv.lock and exclude-newer, so dependencies resolve fresh from the declared ranges.

Build backend: uv_build>=0.11.32,<0.12 (the pinned uv is 0.11.32); module-name is set because the project name would otherwise default to megabonk_mods.

Registration: uvx --from git+https://github.com/pythoninthegrass/megabonk_mods megabonk-mcp with env.MEGABONK_REPO (`${MEGABONK_REPO:-}` in .mcp.json, `{env:MEGABONK_REPO}` in opencode.jsonc). MEGABONK_REPO is process-environment only because it is needed to find .env. A built commit is cached; run `uv cache clean megabonk-mods` after a pull. Remote boxes need `uv sync` so scripts/run.py's shim can import the package (noted in docs/gamepadui.md).

Verification: task check passes. From an unrelated cwd, an editable install, a non-editable install (fails naming MEGABONK_REPO when unset, works when set) and a git+file uvx run all returned 45 tools. A live relaunch plus screenshot through the installed command landed in the checkout's .tools/evidence. After a session restart the pushed uvx registration served `paths`, `relaunch` and `screenshot` end to end. A capture taken immediately after relaunch shows the Loading overlay; a later one shows the editor.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-11-09T19:11:00Z

---

Reference implementation set to the sibling `osascript-mcp` MCP server (packaging shape only — see notes). The route is now decided as a `uv tool install`-able package rather than a patched loose-script entry, so the Modified files list is provisional: expect a new importable package directory and `scripts/*.py` reduced to shims or removed. Update that list once the package name and layout are chosen.

---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Packaged the dev harness as `src/megabonk_harness/` (built with uv_build; commands `megabonk-mcp` and `megabonk-harness`) and registered the MCP server with `uvx --from git+<repo> megabonk-mcp`, so one entry with no per-machine path works from any client directory. The `scripts/*.py` entry points remain as shims, so Taskfiles and docs keep working.\n\nA new checkout discovery step (MEGABONK_REPO, then the working directory's ancestors, then the source tree) anchors `.env`, the evidence folder, levels and `task` runs to the user's clone, and fails with an error naming the missing checkout when none is found. pyproject.toml is the only dependency declaration. README.md, docs/development.md, the site MCP page and .env.example were updated, including uv/mise requirements and the previously undocumented MEGABONK_* variables.\n\nVerification: `task check` passes (1308 Python tests, 2780 .NET tests, lint). A handshake from an unrelated directory returned 45 tools for editable, non-editable and git+file uvx runs; the no-checkout case exits naming MEGABONK_REPO. After a session restart, the pushed uvx registration served `paths`, `relaunch` and `screenshot` against the live game, with the screenshot saved in the checkout's .tools/evidence.\n\nRisks and follow-ups: uvx caches the built commit and ignores the checkout's uv.lock and exclude-newer, so run `uv cache clean megabonk-mods` after pulling harness changes and expect dependencies to resolve fresh. Remote boxes need `uv sync` so the `scripts/run.py` shim can import the package. A client that cannot expand `${MEGABONK_REPO:-}` needs the variable set a different way.
<!-- SECTION:FINAL_SUMMARY:END -->
