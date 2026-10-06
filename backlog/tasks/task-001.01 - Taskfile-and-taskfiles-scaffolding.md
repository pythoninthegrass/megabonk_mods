---
id: TASK-001.01
title: Taskfile and taskfiles/ scaffolding
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
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-001 first for full context on why this repo exists and the conventions to copy.

Build `taskfile.yml` (lowercase, repo root) and `taskfiles/mod.yml`, `taskfiles/game.yml`, `taskfiles/re.yml`, following `~/git/dope_wars`'s conventions exactly (read its `taskfile.yml` and `taskfiles/*.yml` directly, don't rely on secondhand description):

- Root: schema comment header, `version: "3.0"`, `set: ["e","u","pipefail"]`, `shopt: ["globstar"]`, `vars.MISE_SHIMS` + `env.PATH` prepend, `includes:` map, `default` task running `task --list`, and a root `check` task that calls into the namespaced build/test/lint tasks in order.
- `taskfiles/mod.yml` (namespace `mod`): `build` (dotnet build with `sources:`/`generates:`), `test` (dotnet test), `deploy` (relies on the csproj after-build target from TASK-001.03, so this can just be an alias for build, or a no-op with a comment explaining why).
- `taskfiles/game.yml` (namespace `game`): `melonloader:install` (calls `tools/install_melonloader.py` via `uv run`), `run` (launch the game — platform-guarded: `open` the CrossOver bottle app on darwin, direct exe launch on windows/linux), `log` (tail the MelonLoader `Latest.log` from the configured game dir).
- `taskfiles/re.yml` (namespace `re`): `dump` task that re-runs Il2CppDumper into `.tools/il2cpp_dump/` using the mise-managed dotnet SDK with `DOTNET_ROLL_FORWARD=LatestMajor` (this was already proven working manually in this session — net7 Il2CppDumper build + dotnet 10 runtime via `mise exec dotnet@10.0.108 -- dotnet Il2CppDumper.dll <GameAssembly.dll> <global-metadata.dat> <outdir>`). Use `tools/game_paths.py` for the game install path and `tools/il2cpp_dump.py` to wrap the actual invocation (that script itself is TASK-001.02's job — this task can stub/call it and adjust once it lands, or coordinate — check if TASK-001.02 is done first).
- Internal/installer-style tasks use the `_install-` prefix, `internal: true`, and an idempotent `status:` check, exactly like dope_wars's `_install-venv`/`_install-mise-tools`.
- Every task has a `desc:`. Longer ones get a `summary:` block with a usage example line.

Do not write the Python tooling scripts themselves (tools/game_paths.py, tools/install_melonloader.py, tools/il2cpp_dump.py) — that's TASK-001.02. This task can reference them by the paths/CLI contract described in TASK-001.02 even if they land slightly out of order; coordinate via comments if needed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 taskfile.yml exists at repo root (lowercase) with the schema header, version, set/shopt, mise PATH vars/env, includes map, and a default task running `task --list`
- [ ] #2 taskfiles/mod.yml, game.yml, re.yml exist as separate namespaced files following the dope_wars internal-task/status-check/sources-generates conventions
- [ ] #3 task --list shows every task from all three namespaces plus the root default and check tasks
- [ ] #4 task re:dump successfully regenerates .tools/il2cpp_dump/ output against the installed Megabonk build
- [ ] #5 task game:log tails MelonLoader's Latest.log from the resolved game directory
- [ ] #6 Every task has a desc:, and multi-step tasks have a summary: block with a usage example
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
