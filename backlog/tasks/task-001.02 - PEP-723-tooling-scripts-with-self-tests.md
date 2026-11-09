---
id: TASK-001.02
title: PEP 723 tooling scripts with self-tests
status: Done
assignee:
  - Claude
created_date: '2026-10-06 21:39'
updated_date: '2026-10-06 22:55'
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
- [x] #1 tools/game_paths.py resolves game/data/MelonLoader/Mods/log paths with env > .env > default precedence for both macOS CrossOver and Windows, with a CLI that prints resolved paths as JSON
- [x] #2 tools/install_melonloader.py installs a pinned, checksum-verified MelonLoader release into the resolved game directory, is idempotent (skips a correct existing install), and applies the CrossOver Wine DLL override needed for IL2CPP hooking on macOS
- [x] #3 tools/il2cpp_dump.py reproduces the manually-verified Il2CppDumper invocation from this session (mise dotnet 10 + DOTNET_ROLL_FORWARD=LatestMajor against the net7 Il2CppDumper build) and writes output to .tools/il2cpp_dump/
- [x] #4 Each script has a passing tools/test_*.py self-test runnable via `uv run tools/test_x.py`, covering pure logic without live network or game-install dependencies
- [x] #5 All three scripts are valid PEP 723 script files (uv run --script shebang + script header) and pass `ruff check`
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Follow parent TASK-001's recorded plan. Writing this before .01's taskfiles so the taskfiles can call real scripts instead of stubs (routine sequencing, not a scope change - .01 explicitly allowed either order). Three PEP 723 scripts + test_*.py siblings, modeled on dope_wars tools/re/extract_beermat.py + test_extract_beermat.py shape exactly (shebang, script header, sys.path.insert import, main()-collects-test_* self-test runner).

game_paths.py: precedence env > .env (simple parser, no dependency) > built-in default. Vars: MEGABONK_BOTTLE (macOS CrossOver drive_c), MEGABONK_GAME_DIR, MEGABONK_DATA_DIR override. Default macOS: ~/Library/Application Support/CrossOver/Bottles/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk. Default Windows: C:\Program Files (x86)\Steam\steamapps\common\Megabonk. Exposes: game_dir(), melonloader_dir(), mods_dir(), userlibs_dir(), latest_log_path(), and a CLI printing all as JSON.

install_melonloader.py: pin MELONLOADER_VERSION=0.7.3, MELONLOADER_SHA256=<fill once downloaded and verified>, download from https://github.com/LavaGang/MelonLoader/releases/download/v0.7.3/MelonLoader.x64.zip, verify sha256, extract into game_dir(), idempotent (checks MelonLoader/net6/MelonLoader.dll + a version marker), separate is_installed(version) from install(). CrossOver Wine DLL override (version.dll=native,builtin) applied via `wine reg add 'HKCU\\Software\\Wine\\DllOverrides' /v version /d native,builtin /f` run inside the bottle (CX_BOTTLE env + crossover wine wrapper) - documents this is unverified until run live per the batched live-action checkpoint.

il2cpp_dump.py: wraps `mise exec dotnet@10.0.108 -- dotnet Il2CppDumper.dll <GameAssembly.dll> <global-metadata.dat> <outdir>` with DOTNET_ROLL_FORWARD=LatestMajor, paths from game_paths.py, output to .tools/il2cpp_dump/ (already gitignored via existing .tools/ entry).

Self-tests cover: path precedence resolution (env/.env/default) via tmp dirs and monkeypatched env, version comparison/idempotency logic, and argument construction for the dotnet invocation - no live network or game install touched.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Wrote tools/game_paths.py, tools/install_melonloader.py, tools/il2cpp_dump.py + test_*.py siblings. All self-tests pass (6/6, 7/7, 4/4) via `uv run tools/test_*.py`. ruff check tools/ is clean. .env.example added documenting MEGABONK_BOTTLE/MEGABONK_GAME_DIR.

install_melonloader.py: MELONLOADER_SHA256 is left blank with a visible TODO - downloading the real archive to compute/verify it requires network access that the sandbox's auto-mode classifier denied (untrusted-code-integration policy on fetching an executable zip). Script works and warns at runtime if the checksum is unset; filling it in is part of the batched live-action checkpoint with the user.

il2cpp_dump.py expects Il2CppDumper.dll at .tools/Il2CppDumper/Il2CppDumper.dll (not vendored, not yet fetched for the same reason) - acquiring it is also part of the live checkpoint. .tools/il2cpp_dump/ already existed in the repo from a prior manual session and is already gitignored.

Live run by the user (`task game:melonloader:install`) succeeded through download+extract (sha256 reported: 5b2b2f3d1cd42b59ec886c5bdc2663edae87a0097a4f4a8f58c0965a99dda416, now pinned as MELONLOADER_SHA256's default) but failed applying the CrossOver Wine DLL override: plain `wine` isn't on PATH under CrossOver (it ships its own wrapped binary), and _lookup_bottle_root was returning drive_c itself instead of the bottle root (WINEPREFIX).

Fixed: _find_crossover_wine() locates CrossOver's wine binary (checks CROSSOVER_WINE_BIN env override, then /Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine, confirmed present on this machine). _lookup_bottle_root now returns drive_c's parent. _apply_crossover_dll_override sets WINEPREFIX via env instead of cwd. install() restructured so the DLL override is retried on every run (idempotent - wine reg add overwrites the same value) even when the version marker already shows installed, since the override itself isn't tracked by that marker. Also removed taskfiles/game.yml's redundant task-level `status:` check, which was short-circuiting the whole script (including the override retry) once the marker existed - go-task's own status check conflicted with the script's internal idempotency and is now just the script's job.

Per user request, MELONLOADER_SHA256 now uses python-decouple (`config("MELONLOADER_SHA256", default="...")`) so it's overridable via env var/.env without editing the script, consistent with the env > .env > default precedence used elsewhere. Added python-decouple>=3.8 to both install_melonloader.py's and test_install_melonloader.py's PEP 723 dependency headers. All 7 self-tests still pass; verified the env override manually (MELONLOADER_SHA256=deadbeef overrides the default). `task tools:test` (6/6, 4/4, 7/7) and `task lint` both clean after these changes.

Still pending: user needs to re-run `task game:melonloader:install` with the wine-path fix to confirm the DLL override actually applies now.

Live-verified end to end by the user: `task game:melonloader:install` downloaded MelonLoader 0.7.3 (sha256 matches the pinned default), extracted it, and applied the CrossOver Wine DLL override (`reg: The operation completed successfully`) after two rounds of fixes (wrong wine binary/invocation, then wrong bottle-identification mechanism - CrossOver's wine wrapper resolves bottles by --bottle NAME, not WINEPREFIX path). Re-running the task a second time correctly reported already-installed and still re-applied the override (idempotent). AC#2 checked.

Live-verified: copied a pre-existing Il2CppDumper build (Il2CppDumper.dll + Mono.Cecil*.dll + config.json, found in a prior session's scratchpad, not downloaded fresh) into .tools/Il2CppDumper/, disabled its RequireAnyKey config flag (would otherwise block waiting for a keypress in non-interactive use), and ran `task re:dump` successfully against the live game install - full dump.cs/il2cpp.h/script.json/stringliteral.json/DummyDll output regenerated. AC#3 checked.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Wrote three PEP 723 scripts (tools/game_paths.py, tools/install_melonloader.py, tools/il2cpp_dump.py) + tools/test_*.py self-tests, modeled on dope_wars's extract_beermat.py/test_extract_beermat.py pattern. All self-tests pass (6/6, 7/7, 4/4), ruff check is clean, .env.example documents the overridable vars.

All three scripts were live-verified against the real system in this session:
- game_paths.py correctly resolves the CrossOver bottle's Megabonk install.
- install_melonloader.py downloaded, checksum-verified (sha256 now pinned as python-decouple's default, overridable via MELONLOADER_SHA256 env/.env per user request), extracted MelonLoader 0.7.3, and applied the CrossOver Wine DLL override - required two live-debugging fixes (CrossOver's wine is a Perl wrapper needing `--bottle NAME`, not a plain wine binary with WINEPREFIX).
- il2cpp_dump.py successfully reproduced the proven Il2CppDumper invocation against the live game install.

Also fixed along the way: taskfiles/game.yml's melonloader:install task had a redundant `status:` check that was short-circuiting past the DLL-override retry once the version marker existed; removed it since the script already handles its own idempotency internally.

DoD: task check passes, docs updated (.env.example, in-code docstrings). "Tests written first" honestly unchecked (written alongside implementation, not strict TDD). Commit pending user confirmation, to be combined with the other three TASK-001 subtasks.
<!-- SECTION:FINAL_SUMMARY:END -->
