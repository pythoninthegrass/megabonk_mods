---
id: TASK-001
title: Scaffold repo tooling and build pipeline
status: Done
assignee:
  - Claude
created_date: '2026-10-06 21:38'
updated_date: '2026-10-06 22:55'
labels:
  - level-editor
  - tooling
dependencies: []
priority: high
type: chore
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Goal: stand up the build/test/tooling scaffolding for a third-party MelonLoader mod that will eventually become an in-game WYSIWYG level editor for Megabonk, so later tasks can start writing mod code and tests immediately instead of reinventing project plumbing.

## Project context

Megabonk is a Unity 2023.2.22f1 IL2CPP game (Steam app 3405340). It has no mod loader installed. We are building a MelonLoader-based mod. The repo is modeled on two sibling projects by the same author:

- `~/git/xeno_mods` — a MelonLoader/Harmony-style C# mod repo for another Unity game. Reuse its patterns:
  - `Directory.Build.props` per mod project defines `BottleFolder`/`GameFolder`/`ModInstanceFolder` MSBuild properties pointing into the CrossOver bottle, with an `<Import Project="Directory.Build.local.props" Condition="Exists(...)" />` escape hatch for per-machine overrides (that file is gitignored).
  - `.csproj` references game/loader DLLs via `<HintPath>$(GameFolder)/X.dll</HintPath><Private>False</Private>` — never vendor these DLLs into the repo.
  - An `AfterTargets="Build"` MSBuild target copies the built DLL + PDB + manifest into the game's Mods folder, so `dotnet build` alone deploys the mod.
  - Tests are a separate xUnit project (net10.0) that does NOT reference the mod project or any game DLL — it compile-links (`<Compile Include="../../src/X/foo.cs" Link="foo.cs" />`) only the pure-logic `.cs` files, keeping Unity/Harmony-dependent "patch" files (`*_patch.cs`) separate from pure logic files so logic is unit-testable without Unity loaded.
  - `.env.example` documents overridable env vars (bottle path, game dir, etc.), read via precedence: process env > `.env` > built-in default.
  - Backlog tasks are self-contained work orders; `AGENTS.md` only needs the Backlog.md MCP guidance block.
- `~/git/dope_wars` — reuse its Taskfile and Python tooling conventions:
  - Lowercase root `taskfile.yml` (not `Taskfile.yml`), starting with `# yaml-language-server: $schema=https://taskfile.dev/schema.json`, `version: "3.0"`, root-level `set: ["e","u","pipefail"]`, `shopt: ["globstar"]`, a `vars.MISE_SHIMS` + `env.PATH` prepend so mise-managed tools resolve, an `includes:` map to `taskfiles/<namespace>.yml` files, and a `default` task that runs `task --list`.
  - Per-namespace files each repeat the schema header + `version: "3.0"`. Internal setup/installer tasks are prefixed `_install-` and marked `internal: true`, each guarded by an idempotent `status:` check. Build tasks use `sources:`/`generates:` for incremental rebuilds. Cross-namespace task refs use a leading colon (`":core:build"`); same-file refs are bare. `desc:` is required on every task (including internal ones); `summary:` (a `|` block starting with a usage example) is used for longer/less-obvious tasks. Platform guards use `platforms: [...]` at task or command level, or Go-template `{{if eq OS "darwin"}}...{{end}}` in vars/scripts.
  - A root `check` task is the aggregate gate (calls into build/test/lint sub-tasks in order).
  - Python tooling lives in `tools/*.py` as PEP 723 "script" files: shebang `#!/usr/bin/env -S uv run --script`, header block:
    ```
    # /// script
    # requires-python = ">=3.13,<3.14"
    # dependencies = ["somepkg"]
    # ///
    ```
    Tasks invoke them explicitly as `uv run tools/x.py` (not by relying on the shebang). Self-tests are sibling `tools/test_x.py` files, also PEP 723 scripts, with a `main()` returning an exit code, run via `uv run tools/test_x.py` from a task (not pytest/unittest). Shared helpers are imported by inserting the script's own directory onto `sys.path`, not via a package. No ruff config exists in dope_wars itself (pre-commit's ruff hook used instead) — this repo should add a real `ruff.toml` (line-length ~130) since `.tool-versions` already pins ruff.

## What needs to exist when this task is done

- `taskfile.yml` at repo root + `taskfiles/mod.yml` (dotnet build/test/deploy), `taskfiles/game.yml` (install MelonLoader, launch the game on CrossOver/Windows, tail `MelonLoader/Latest.log`), `taskfiles/re.yml` (re-run Il2CppDumper into `.tools/il2cpp_dump/`, gitignored, using the mise-managed dotnet 10 SDK with `DOTNET_ROLL_FORWARD=LatestMajor` since Il2CppDumper's net7 build has no matching runtime otherwise).
- `tools/game_paths.py` (resolve bottle/game dir: env > `.env` > default for CrossOver bottle at `~/Library/Application Support/CrossOver/Bottles/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk`, plus a Windows path), `tools/install_melonloader.py` (download a pinned MelonLoader release by version with a checksum, apply the CrossOver bottle DLL override), `tools/il2cpp_dump.py` (wraps Il2CppDumper invocation). Each has a `tools/test_*.py` self-test.
- `src/MegabonkLevels.Mod/` — MelonLoader mod project, target framework matching MelonLoader's bundled runtime, `Directory.Build.props` + optional gitignored `Directory.Build.local.props`, referencing MelonLoader + Il2CppInterop-generated assemblies with `Private=false`, after-build deploy target copying into `<game>/Mods`.
- `tests/MegabonkLevels.Tests/` — xUnit project on net10.0 (matching the `.tool-versions` dotnet pin), compile-linking only non-Unity-dependent source files from the mod project.
- `.editorconfig`, `.markdownlint.jsonc`, `ruff.toml`, `.gitignore` additions (ignore `bin/`, `obj/`, `Directory.Build.local.props`, `.env`, `.task/`), `.env.example`.
- `docs/modding-setup.md` explaining how to install MelonLoader and point the build at a local game install.

Do not write any mod gameplay/editor logic in this task — that is covered by later tasks (TASK-002 onward). This task is pure scaffolding so those tasks have somewhere to put code and a `task check` to run.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 taskfile.yml + taskfiles/mod.yml, game.yml, re.yml exist following the dope_wars schema/version/set/shopt/includes/default conventions, and `task --list` shows all tasks
- [x] #2 task re:dump regenerates the Il2CppDumper output into .tools/il2cpp_dump/ (gitignored) using the mise-managed dotnet SDK with roll-forward, without requiring a separately installed net7 runtime
- [x] #3 tools/game_paths.py, tools/install_melonloader.py, tools/il2cpp_dump.py are PEP 723 uv scripts with passing tools/test_*.py self-tests runnable via `uv run`
- [x] #4 src/MegabonkLevels.Mod builds with `task mod:build` and the after-build target deploys the DLL+PDB+manifest into the configured game Mods folder without vendoring any game or MelonLoader DLL into the repo
- [x] #5 tests/MegabonkLevels.Tests runs with `task mod:test` (xUnit, net10.0) and does not reference any Unity/game/MelonLoader assembly
- [x] #6 Directory.Build.props exposes bottle/game path properties with a gitignored Directory.Build.local.props override point, mirroring the xeno_mods pattern
- [x] #7 .env.example documents every overridable path/env var with the same env > .env > default precedence used in tools/game_paths.py
- [x] #8 ruff.toml, .editorconfig, .markdownlint.jsonc and .gitignore are present and `task lint` runs cleanly against the scaffolded files
- [x] #9 docs/modding-setup.md documents MelonLoader installation and pointing a local build at a game install, for both CrossOver and Windows
- [x] #10 task check runs build, test, and lint in sequence and passes on a clean checkout
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
## Research findings (dope_wars + xeno_mods read directly)

**dope_wars taskfile conventions** (`~/git/dope_wars/taskfile.yml`, `taskfiles/re.yml`, `taskfiles/game.yml`):
- Root: `# yaml-language-server: $schema=...` header, `version: "3.0"`, `set: ["e","u","pipefail"]`, `shopt: ["globstar"]`, `vars.MISE_SHIMS`/`env.PATH` prepend, `includes:` map, `default` task = `task --list`, root `check` aggregates namespaced build/test/lint tasks.
- Namespace files repeat the schema header. `_install-*` tasks are `internal: true` with an idempotent `status:` check (e.g. `_install-ghidra` checks `test -x <headless>`, `_install-java` checks `mise where java@X`). Pinned downloads use `<TOOL>_VERSION`/`<TOOL>_SHA256`/`<TOOL>_BUILD` vars, `curl -fsSL` + `sha256sum -c -` before unzip. `{{if eq OS "darwin"}}...{{end}}` for platform branching; `platforms: [darwin]` at task level for darwin-only tasks (icon.icns build). Every task has `desc:`; longer ones get a `summary:` with a usage example (seen as a comment block above `gen:bridge-expectations` rather than a literal `summary:` key in this repo — I'll use the real Taskfile `summary:` field per the Taskfile schema since that's what TASK-001.01 asks for).

**PEP 723 tool script convention** (`tools/re/extract_beermat.py`, `tools/re/test_extract_beermat.py`, `tools/check_abi_exports.py`):
- Shebang `#!/usr/bin/env -S uv run --script`, `# /// script` block with `requires-python = ">=3.13,<3.14"` and `dependencies = [...]`, invoked as `uv run tools/x.py` from tasks.
- Self-test is a sibling `test_x.py`, same PEP 723 header, imports the target module via `sys.path.insert(0, str(Path(__file__).resolve().parent))` then `import x`. `main()` collects `test_*` callables from `globals()`, runs each in try/except, prints `FAIL <name>` + traceback on failure, prints `N/M passed`, returns `1 if failed else 0`; `sys.exit(main())`.
- No live network/game dependency in tests — synthetic fixtures only.

**xeno_mods C# project convention** (`src/x2_load_profiler/Directory.Build.props`, `.csproj`, `manifest.json`, `tests/x2_load_profiler.tests/*.csproj`):
- `Directory.Build.props` is per-mod-project (not repo-root) directory, defines `BottleFolder`/`GameFolder`/`ModInstanceFolder` as plain MSBuild properties (string paths, not real path logic), with `<Import Project="$(MSBuildThisFileDirectory)Directory.Build.local.props" Condition="Exists(...)" />` as the override hook.
- `.csproj` references game/loader DLLs via `<Reference Include="X"><HintPath>$(GameFolder)/X.dll</HintPath><Private>False</Private></Reference>`.
- `AfterTargets="Build"` target copies TargetPath+pdb (+ manifest.json, for xeno_mods's own loader) into `$(ModInstanceFolder)`.
- That repo's loader is the game's own Content Pack system (manifest.json), NOT MelonLoader — megabonk_mods instead needs MelonLoader's actual convention (MelonInfo/MelonGame assembly attributes on a `MelonMod` subclass, no manifest.json). Confirmed via MelonLoader's known plugin model; will double check in TASK-002/during implementation since TASK-002 is the hook-surface spike.
- Test project: plain xUnit (`Microsoft.NET.Test.Sdk`, `xunit`, `xunit.runner.visualstudio`), `<TargetFramework>net10.0</TargetFramework>`, `<Using Include="Xunit" />`, and `<Compile Include="../../src/.../foo.cs" Link="foo.cs" />` per logic file it needs — no reference to the mod project itself.

**MelonLoader version/target** (web search, Oct 2026): latest stable tag is `v0.7.3` (May 2026), still targets `net6.0` for Il2Cpp mod DLLs. Folder layout (MelonLoader's own convention, standard across its installs): `<Game>/MelonLoader/` (loader runtime + `Latest.log` + `Il2CppAssemblies/` after first run), `<Game>/Mods/` (drop-in mod DLLs), `<Game>/UserLibs/` (unpatched dependency DLLs). I'll pin `0.7.3` + record its release-archive sha256 when TASK-001.02's installer script is written.

## Plan, by subtask

**TASK-001.01 (Taskfile)**: root `taskfile.yml` + `taskfiles/mod.yml`, `game.yml`, `re.yml` per the dope_wars conventions above. `re:dump` reuses the already-proven invocation from this session's manual spike (`mise exec dotnet@10.0.108 -- dotnet Il2CppDumper.dll ...` with `DOTNET_ROLL_FORWARD=LatestMajor`) against the existing `.tools/il2cpp_dump/` output (already present in the repo from a prior manual run) - task should regenerate it from the live game install, gitignored. `game:run`/`game:log`/`game:melonloader:install` call into `tools/*.py` from TASK-001.02.

**TASK-001.02 (PEP 723 tools)**: `tools/game_paths.py`, `tools/install_melonloader.py`, `tools/il2cpp_dump.py` + `tools/test_*.py`, following the extract_beermat.py/test_extract_beermat.py shape exactly. `game_paths.py` precedence env > `.env` > CrossOver-bottle default (confirmed path already in use: `~/Library/Application Support/CrossOver/Bottles/Steam/drive_c/Program Files (x86)/Steam/steamapps/common/Megabonk`), exposes JSON-printing CLI + importable functions. `install_melonloader.py` pins MelonLoader `0.7.3`, downloads from GitHub releases, sha256-verifies, extracts, idempotent status check, applies the CrossOver Wine `version.dll` override (native,builtin) via the bottle's `wine reg add` — I will verify the exact override string against MelonLoader's own install docs before writing it, since getting this wrong silently breaks hooking. `il2cpp_dump.py` wraps the proven dotnet invocation.

**TASK-001.03 (C# scaffolding)**: `Directory.Build.props` under `src/MegabonkLevels.Mod/` (per-project, matching xeno_mods, not repo-root) + gitignored `Directory.Build.local.props` hook. `MegabonkLevels.Mod.csproj` targets `net6.0`, references `MelonLoader.dll`/`0Harmony.dll` via HintPath+Private=false from `$(GameFolder)` (MelonLoader's own managed dir, not Il2CppAssemblies, for those two - the Il2Cpp-interop game assemblies are a separate HintPath set that TASK-002 will fill in once real assembly names are known). Placeholder `MelonMod` subclass with `MelonInfo`/`MelonGame` attributes + `OnInitializeMelon` log line, no manifest.json (MelonLoader doesn't use one). `tests/MegabonkLevels.Tests` on net10.0, xUnit, zero game/Unity/MelonLoader references, one compile-linked placeholder logic file + test proving the wiring.

**TASK-001.04 (lint/docs)**: `.editorconfig` and `ruff.toml` already exist at repo root (verified) and already match the described baseline (130 line-length, LF, 2sp yaml/json, 4sp python) - this subtask should audit/extend rather than recreate them, add C#'s 4-space indent rule if missing, add `.markdownlint.jsonc`/`.markdownlintignore`, extend `.gitignore` (currently just `*.zip`, `.tools/`, `CLAUDE.md`) with `bin/`, `obj/`, `Directory.Build.local.props`, `.env`, `.task/`, add a `csharp` entry to `.serena/project.yml`'s `language_servers: []`, and write `docs/modding-setup.md`.

## Sequencing and open risk

Subtasks run in dependency order .01 -> .02 -> .03 -> .04 (.04 already declares that dependency). Within .01, `re:dump` and `game:*` tasks can be scaffolded before .02's scripts exist (per .01's own instructions) and wired up once .02 lands.

**Flagged for explicit user confirmation before touching live state** (installing MelonLoader into the real CrossOver bottle, downloading a third-party binary, running a real `task re:dump` against the live game, running `task mod:build` to deploy into the real Mods folder): these are state-changing actions against the user's actual Steam/CrossOver install, not just repo file edits. I will build and unit-test everything that doesn't require them, then check in before running the live-install/live-dump/live-deploy acceptance criteria (#2, #4 partially, #9 verification).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
All 4 subtasks have scaffolding written and self-verified: task --list shows every task, all tools/test_*.py self-tests pass (6/6, 7/7, 4/4), mod tests pass (1/1, zero game refs), task lint is clean. mod:build currently fails (expected, documented) because MelonLoader isn't installed on this machine.

User decision: they'll run the remaining live steps themselves (MelonLoader download/install, re:dump, mod:build/deploy) rather than me retrying network fetches in this sandbox or using dangerouslyDisableSandbox. Leaving TASK-001 and all subtasks In Progress, ACs that need a live install left unchecked, until the user reports results.

Found a pre-existing Il2CppDumper extraction (Il2CppDumper.dll + Mono.Cecil deps, dated Jul 2024) in a prior session's scratchpad at /private/tmp/claude-501/.../scratchpad/il2cppdumper/ - not vendored into the repo. User can copy it to .tools/Il2CppDumper/Il2CppDumper.dll (plus its Mono.Cecil*.dll siblings) to satisfy tools/il2cpp_dump.py's expected location, or fetch a fresh copy.

Handoff commands for the user: `task game:melonloader:install` (installs MelonLoader 0.7.3, warns with the computed sha256 since MELONLOADER_SHA256 is unpinned - report that digest back so it can be pinned in tools/install_melonloader.py), `task re:dump` (needs Il2CppDumper.dll present per above), `task mod:build`/`task check` (verifies the mod actually compiles and deploys once MelonLoader.dll/0Harmony.dll exist at the resolved path).

All 4 subtasks (TASK-001.01-.04) completed and marked Done. `task check` passes end to end against the real, live MelonLoader 0.7.3 install: build (mod compiles + deploys DLL/PDB into the game's real Mods/ folder), test (xUnit 1/1 + three Python self-test suites 6/6+7/7+4/4), lint (markdownlint + ruff) all green. `task re:dump` also independently verified against the live game install.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Stood up the full build/test/tooling scaffold for the MelonLoader-based Megabonk mod, modeled on ~/git/dope_wars (Taskfile/PEP 723 tooling conventions) and ~/git/xeno_mods (Directory.Build.props/csproj/test-project conventions), both read directly rather than from memory.

What landed:
- taskfile.yml + taskfiles/{mod,game,re}.yml - `task --list` shows every task; root `check` runs build+test+lint.
- tools/{game_paths,install_melonloader,il2cpp_dump}.py as PEP 723 scripts with tools/test_*.py self-tests (17 assertions total, all passing). install_melonloader.py's pinned sha256 is now a python-decouple default, overridable via MELONLOADER_SHA256 env/.env.
- src/MegabonkLevels.Mod/ (net6.0, Directory.Build.props, placeholder MelonMod) + tests/MegabonkLevels.Tests/ (net10.0 xUnit, zero game/Unity/MelonLoader references).
- .editorconfig, .markdownlint.jsonc/.markdownlintignore, .gitignore, .serena/project.yml (csharp), .env.example, docs/modding-setup.md.

Everything was live-verified against the user's real CrossOver/Megabonk install in this session, not just unit-tested: MelonLoader 0.7.3 downloaded+checksum-verified+installed, the CrossOver Wine DLL override applied, the mod built and deployed into the real Mods/ folder, and Il2CppDumper re-run against the live GameAssembly.dll/global-metadata.dat. `task check` passes cleanly end to end.

Fixed two real bugs discovered only by live execution: CrossOver's `wine` is a Perl wrapper that resolves bottles by `--bottle NAME`, not a WINEPREFIX path (my first attempt assumed plain Wine semantics); and go-task's own `status:` check on game:melonloader:install was short-circuiting past the DLL-override retry once the version marker existed, so it had to be removed in favor of the script's own internal idempotency.

Honest gaps: "tests written first" (TDD) is unchecked across subtasks - this was scaffolding mirroring established external conventions, written alongside its tests rather than strict red-green. AC#5 on TASK-001.01 (task game:log tailing a real Latest.log) is unverified since that requires actually launching the game with the mod loaded, which is TASK-002's job (the hook-surface spike), not this scaffolding task's. No commit has been made yet - pending user confirmation on commit message/scope.
<!-- SECTION:FINAL_SUMMARY:END -->
