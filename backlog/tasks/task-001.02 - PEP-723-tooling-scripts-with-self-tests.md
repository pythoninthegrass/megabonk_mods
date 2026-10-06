---
id: TASK-001.02
title: PEP 723 tooling scripts with self-tests
status: To Do
assignee: []
created_date: '2026-10-06 21:39'
labels:
  - level-editor
  - tooling
dependencies: []
parent_task_id: TASK-001
priority: high
type: chore
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-001 first for full context.

Write three `tools/*.py` PEP 723 "script" files following `~/git/dope_wars`'s `tools/re/extract_beermat.py` pattern exactly (read it directly): shebang `#!/usr/bin/env -S uv run --script`, a `# /// script` header block with `requires-python` and `dependencies`, invoked explicitly via `uv run tools/x.py` from task definitions rather than relying on the shebang. Each gets a sibling `tools/test_x.py` self-test (also a PEP 723 script, a `main()` returning an exit code, run via `uv run tools/test_x.py`, not pytest/unittest), following the dope_wars `tools/test_*.py` pattern. Shared helpers are imported by inserting the script's own directory onto `sys.path`, not via a package — see how dope_wars's `check_abi_exports.py` imports `abi_symbols`.

1. **`tools/game_paths.py`**: resolves the Megabonk install directory and related paths (data dir, MelonLoader dir, Mods dir, Latest.log path). Precedence: process env var(s) > `.env` file (via a minimal parse, no heavy dependency needed, or `python-decouple` if that's the dope_wars/xeno_mods convention — check xeno_mods's `.env.example` and `scripts/run.py` for the exact var names/precedence used there) > built-in default. Built-in default for macOS is the CrossOver bottle path: `~/Library/Application Support/CrossOver/Bottles/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk`. Also support a Windows default path pattern (e.g. `C:\Program Files (x86)\Steam\steamapps\common\Megabonk`, detected or overridden via env on that platform). Expose both a CLI (print resolved paths as JSON) and importable functions for the other two scripts to use.

2. **`tools/install_melonloader.py`**: downloads a pinned MelonLoader release (pin a specific version — check https://github.com/LavaGang/MelonLoader releases for a current 0.7.x release compatible with Unity 2023.2 IL2CPP, and pin its exact version + a sha256 of the downloaded archive, following the dope_wars `GHIDRA_VERSION`/`GHIDRA_SHA256` pinning pattern in `taskfiles/re.yml`), extracts it into the resolved game directory (from `game_paths.py`), and on macOS/CrossOver applies the necessary Wine DLL override (`version.dll` native,builtin — verify the exact override MelonLoader's own install docs specify) via `wine reg add` or equivalent through the CrossOver bottle. Idempotent: skip if already installed at the pinned version (this backs the taskfile's `status:` check too, so expose a way to query "is it installed at version X" separately from "install").

3. **`tools/il2cpp_dump.py`**: wraps the Il2CppDumper invocation already proven manually in this session (download/locate the net7 Il2CppDumper release, run it via `mise exec dotnet@10.0.108 -- dotnet Il2CppDumper.dll <GameAssembly.dll path> <global-metadata.dat path> <output dir>` with `DOTNET_ROLL_FORWARD=LatestMajor` in the environment since the system only has .NET 9/10 runtimes), writing output to `.tools/il2cpp_dump/` (gitignored). Get the game paths from `game_paths.py`.

Each script's self-test should cover its pure logic (path resolution precedence, version comparison/idempotency check, argument construction) without actually hitting the network or a real game install in the test — mock/stub or use fixture directories.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tools/game_paths.py resolves game/data/MelonLoader/Mods/log paths with env > .env > default precedence for both macOS CrossOver and Windows, with a CLI that prints resolved paths as JSON
- [ ] #2 tools/install_melonloader.py installs a pinned, checksum-verified MelonLoader release into the resolved game directory, is idempotent (skips a correct existing install), and applies the CrossOver Wine DLL override needed for IL2CPP hooking on macOS
- [ ] #3 tools/il2cpp_dump.py reproduces the manually-verified Il2CppDumper invocation from this session (mise dotnet 10 + DOTNET_ROLL_FORWARD=LatestMajor against the net7 Il2CppDumper build) and writes output to .tools/il2cpp_dump/
- [ ] #4 Each script has a passing tools/test_*.py self-test runnable via `uv run tools/test_x.py`, covering pure logic without live network or game-install dependencies
- [ ] #5 All three scripts are valid PEP 723 script files (uv run --script shebang + script header) and pass `ruff check`
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
