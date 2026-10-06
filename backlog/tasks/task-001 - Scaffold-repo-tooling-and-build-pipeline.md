---
id: TASK-001
title: Scaffold repo tooling and build pipeline
status: To Do
assignee: []
created_date: '2026-10-06 21:38'
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
- [ ] #1 taskfile.yml + taskfiles/mod.yml, game.yml, re.yml exist following the dope_wars schema/version/set/shopt/includes/default conventions, and `task --list` shows all tasks
- [ ] #2 task re:dump regenerates the Il2CppDumper output into .tools/il2cpp_dump/ (gitignored) using the mise-managed dotnet SDK with roll-forward, without requiring a separately installed net7 runtime
- [ ] #3 tools/game_paths.py, tools/install_melonloader.py, tools/il2cpp_dump.py are PEP 723 uv scripts with passing tools/test_*.py self-tests runnable via `uv run`
- [ ] #4 src/MegabonkLevels.Mod builds with `task mod:build` and the after-build target deploys the DLL+PDB+manifest into the configured game Mods folder without vendoring any game or MelonLoader DLL into the repo
- [ ] #5 tests/MegabonkLevels.Tests runs with `task mod:test` (xUnit, net10.0) and does not reference any Unity/game/MelonLoader assembly
- [ ] #6 Directory.Build.props exposes bottle/game path properties with a gitignored Directory.Build.local.props override point, mirroring the xeno_mods pattern
- [ ] #7 .env.example documents every overridable path/env var with the same env > .env > default precedence used in tools/game_paths.py
- [ ] #8 ruff.toml, .editorconfig, .markdownlint.jsonc and .gitignore are present and `task lint` runs cleanly against the scaffolded files
- [ ] #9 docs/modding-setup.md documents MelonLoader installation and pointing a local build at a game install, for both CrossOver and Windows
- [ ] #10 task check runs build, test, and lint in sequence and passes on a clean checkout
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
