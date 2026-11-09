---
id: TASK-059
title: Run the megabonk MCP server from any directory with one install command
status: In Progress
assignee: []
created_date: '2026-11-09T17:53:00Z'
updated_date: '2026-11-09T19:36:00Z'
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
- [x] #1 A machine with only uv installed can install the megabonk MCP server with one documented `uv tool install` command against the cloned repository, and start it with one command that succeeds regardless of the client's working directory; verified by an initialize + tools/list handshake returning the full tool set from an unrelated directory
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
Decisions (approved 2026-11-09): package `src/megabonk_harness/`; console scripts `megabonk-mcp` (server) and `megabonk-harness` (run.py CLI); move game_paths, menu_input, launch_game, run and mcp_server into the package, leave scripts/*.py as thin shims so Taskfiles, docs and `uv run scripts/run.py` keep working.

1. Tests first: new tests/test_checkout.py for discovery (env override MEGABONK_REPO, then cwd walk-up, then repo containing the source tree for editable/dev copies; error naming the missing checkout otherwise), including an installed-copy case (module located outside any checkout).
2. Add pyproject build-system (hatchling), `[tool.hatch.build.targets.wheel] packages`, `[project.scripts]`, pytest `pythonpath = ["scripts", "src"]`.
3. `git mv` the five modules into the package with absolute imports; replace `Path(__file__)` repo anchors (ENV_FILE, evidence_dir, TEST_FOREST_LEVEL, self-relaunch argv of run.py and launch_game.py) with checkout discovery or `-m` invocations; run `task` with cwd=checkout.
4. scripts/{run,game_paths,launch_game,menu_input,mcp_server}.py become shims; update sibling scripts and tests to package imports.
5. Remove the PEP 723 pin list from the server entry so pyproject.toml is the single authority (the shim carries no deps; `uv run scripts/run.py` shim stays working via the project environment).
6. Update docs/development.md, site/src/content/mcp-config.md and AGENTS.md to `uv tool install` registration; verify handshake + paths + screenshot from an unrelated cwd.

Build backend changed from hatchling to uv_build (`requires = ["uv_build>=0.11.32,<0.12"]`, `[tool.uv.build-backend] module-name = "megabonk_harness"` because the project name megabonk-mods would otherwise default to module megabonk_mods; src layout is the uv_build default). Verified with uv build --wheel, a fresh editable tool install (45 tools from an unrelated cwd) and task check.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reference implementation: `osascript-mcp` (github.com/pythoninthegrass/osascript-mcp), the macOS desktop-automation MCP server. Worth lifting from it:

- Layout: `src/osascript_mcp/{__init__,__main__,server,executor}.py`, absolute imports between modules, single `main()` that both `__main__.py` and the console script call.
- Packaging: `[build-system] requires = ["hatchling"]` / `build-backend = "hatchling.build"`, `[tool.hatch.build.targets.wheel] packages = ["src/osascript_mcp"]`, `[project.scripts] osascript-mcp = "osascript_mcp.server:main"`.
- Registration copy in its README: `claude mcp add osascript -- uvx --from git+https://github.com/pythoninthegrass/osascript-mcp osascript-mcp`, plus `"command": "uv", "args": ["run", "--directory", "/path/to/osascript-mcp", "osascript-mcp"]` for source development. That `--directory` form is the development fallback this task replaces for registration.
- It shares dependency shape with this harness (`python-decouple`, a pinned `toon-format`), so the dependency-set move from script header to package metadata has a working example.

Deliberately not copied: its SDK surface (`mcp>=1.7.1`, `mcp.server.lowlevel.Server` + `stdio_server`) — this server is on `mcp>=2.3,<3`; and its self-containedness — it has no checkout to discover, so criteria 2-4 (runtime checkout discovery, failing loudly when absent) stay original work here.

Layout: src/megabonk_harness/{checkout,game_paths,launch_game,menu_input,run,mcp_server}.py; scripts/{run,game_paths,launch_game,mcp_server}.py are shims. Console scripts megabonk-mcp and megabonk-harness. Checkout discovery: MEGABONK_REPO, then cwd ancestors, then the tree the module loaded from (marker: taskfile.yml + src/megabonk_harness). `uv tool install --editable <checkout>` is the one-command install; a non-editable install needs MEGABONK_REPO.

Dependency authority (AC5): pyproject.toml. The PEP 723 headers were removed from the moved modules and from install_melonloader.py and il2cpp_dump.py (they import the package, so they now run in the project environment). Kept pyproject because uv tool install builds from it and it already carries exclude-newer; the old script pin list was a subset duplicate.

Verified from an unrelated cwd with scratch UV_TOOL_DIR: editable install returned 45 tools and a paths call; non-editable install exits 1 with an error naming MEGABONK_REPO and works when it is set; env_file/evidence_dir/example_forest_level resolve into the checkout. NOT verified: a screenshot landing in the checkout evidence dir needs a running game (unit tests cover evidence_dir resolution); AC2 left unchecked for that. Remote boxes need `uv sync` so scripts/run.py's shim can import the package (noted in docs/gamepadui.md). No commit made.

Live check (2026-11-09): from an unrelated cwd, the editable-installed megabonk-mcp ran `relaunch` (state: levelLoaded, killFloorArmed, editor true, 487 palette entries) and `screenshot`, which saved into the checkout's .tools/evidence. The first two frames were the Loading overlay, captured right after relaunch; a later capture showed the example forest in the editor. This corrects the earlier note that AC2 was unverified.

Registration changed from a one-time `uv tool install --editable` to `uvx --from git+https://github.com/pythoninthegrass/megabonk_mods megabonk-mcp` with `env.MEGABONK_REPO` passed through (`${MEGABONK_REPO:-}` in .mcp.json, `{env:MEGABONK_REPO}` in opencode.jsonc) so the entry has no per-machine path. Under uvx the code runs from uv's cache, so the source-tree fallback never applies; the checkout comes from MEGABONK_REPO or the client's cwd ancestors. Verified with a git+file clone: empty var from an unrelated cwd exits naming the checkout, MEGABONK_REPO set returns 45 tools, cwd inside the repo with an empty var returns 45 tools. The git URL only works once the commit is pushed. uvx ignores the checkout's uv.lock and exclude-newer and caches the built commit (uv cache clean megabonk-mods after a pull).

Committed (7191421, 266bfab) and pushed to origin/main. The exact registration URL was checked after the push: uvx --from git+https://github.com/pythoninthegrass/megabonk_mods megabonk-mcp with MEGABONK_REPO set returns the tool list from an unrelated cwd. Left In Progress pending the owner's restart-and-test.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-11-09T19:11:00Z

---

Reference implementation set to the sibling `osascript-mcp` MCP server (packaging shape only — see notes). The route is now decided as a `uv tool install`-able package rather than a patched loose-script entry, so the Modified files list is provisional: expect a new importable package directory and `scripts/*.py` reduced to shims or removed. Update that list once the package name and layout are chosen.

---
<!-- COMMENTS:END -->
