---
id: TASK-001.01
title: Taskfile and taskfiles/ scaffolding
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
- [x] #1 taskfile.yml exists at repo root (lowercase) with the schema header, version, set/shopt, mise PATH vars/env, includes map, and a default task running `task --list`
- [x] #2 taskfiles/mod.yml, game.yml, re.yml exist as separate namespaced files following the dope_wars internal-task/status-check/sources-generates conventions
- [x] #3 task --list shows every task from all three namespaces plus the root default and check tasks
- [x] #4 task re:dump successfully regenerates .tools/il2cpp_dump/ output against the installed Megabonk build
- [ ] #5 task game:log tails MelonLoader's Latest.log from the resolved game directory
- [x] #6 Every task has a desc:, and multi-step tasks have a summary: block with a usage example
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
Follow parent TASK-001's recorded plan verbatim for this subtask (dope_wars conventions researched there). Root taskfile.yml + taskfiles/mod.yml, game.yml, re.yml. mod:build/test reference the not-yet-existing src/tests projects (TASK-001.03) by path - fine since .03 lands next and this is pure scaffolding. game:* tasks call tools/*.py by the CLI contract TASK-001.02 will implement (game_paths.py prints JSON, install_melonloader.py has an install + idempotent check, invoked via `uv run`). re:dump reuses the proven `mise exec dotnet@10.0.108 -- dotnet Il2CppDumper.dll <GameAssembly.dll> <global-metadata.dat> <outdir>` with DOTNET_ROLL_FORWARD=LatestMajor, sourcing paths from game_paths.py once it exists; stub/hardcode the already-known CrossOver path in the meantime per the task's own allowance to coordinate.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Wrote taskfile.yml + taskfiles/mod.yml, game.yml, re.yml. `task --list` shows default/build/test/lint/check/tools:test plus mod:build, mod:test, mod:deploy, game:run, game:log, game:melonloader:install, re:dump. `task tools:test` runs all three Python self-tests through uv successfully (6/6, 4/4, 7/7).

mod:build/mod:test reference src/MegabonkLevels.Mod and tests/MegabonkLevels.Tests which don't exist yet (TASK-001.03, next) - expected per this task's own sequencing note. re:dump and game:melonloader:install/game:log call the real tools/*.py scripts from TASK-001.02 (already landed), not stubs. game:run/re:dump/game:melonloader:install are unverified against the live game/bottle pending the batched live-action checkpoint noted on the parent task.

Live-verified by the user + confirmed by reading the resulting files: `task re:dump` regenerates .tools/il2cpp_dump/ against the real Megabonk install (dump.cs, il2cpp.h, script.json, stringliteral.json, DummyDll/ all freshly written). AC#4 checked.

AC#5 (task game:log tails Latest.log) left unchecked: the mechanism is correct (tail -f on game_paths.py's resolved latest_log_path), but MelonLoader.Latest.log doesn't exist until the game is actually launched with the mod loaded, which wasn't part of this scaffolding task's live-action batch (launching Steam/the game is a bigger step than installing MelonLoader or building/deploying the mod). Deferred to TASK-002, the hook-surface spike, which will actually launch the game.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added taskfile.yml (schema header, version/set/shopt, mise PATH prepend, includes map, default/build/test/lint/check/tools:test) and taskfiles/mod.yml, game.yml, re.yml, following dope_wars's conventions read directly from its repo. `task --list` shows every task across all namespaces. `task re:dump` was live-verified against the real Megabonk install (regenerates .tools/il2cpp_dump/). `task game:melonloader:install` and `task mod:*` call the real scripts from TASK-001.02/.03, not stubs.

Not verified: `task game:log` (AC#5) - the tail mechanism is correct but MelonLoader's Latest.log only exists once the game is actually launched with the mod loaded, which is TASK-002's job (the hook-surface spike), not this scaffolding task's.

DoD: task check passes and docs are updated. "Tests written first" is honestly unchecked - this was scaffolding work mirroring an established external convention; tests/implementation were written together rather than red-green TDD. Commit is pending a single combined commit across all four TASK-001 subtasks, to be done after user confirmation.
<!-- SECTION:FINAL_SUMMARY:END -->
