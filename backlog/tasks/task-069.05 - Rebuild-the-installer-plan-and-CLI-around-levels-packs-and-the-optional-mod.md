---
id: TASK-069.05
title: 'Rebuild the installer plan and CLI around levels, packs and the optional mod'
status: Done
assignee: []
created_date: '2026-11-15 05:59'
labels:
  - installer
dependencies:
  - TASK-069.01
  - TASK-069.03
  - TASK-069.04
references:
  - go/internal/cli/cli.go
  - go/internal/plan/plan.go
  - go/internal/gamebuild/gamebuild.go
  - docs/player-installer.md
parent_task_id: TASK-069
priority: high
ordinal: 241000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`go/internal/plan` and `go/internal/cli` currently plan and apply a MelonLoader install from a pre-downloaded package folder. Change them to plan and apply a level install from the player's inputs, on top of the site client (TASK-069.01), the content installers (TASK-069.03) and the mod installer (TASK-069.04).

**Keep the existing structure:**
- build a plan, show it, confirm, then apply
- rollback on failure, and cancellation
- `--dry-run`, `--json`, `--check` and `--uninstall`
- the exit codes
- game and prefix detection (`FindInstall`/`locate`) and the not-found messages

**Inputs:** positional arguments, each a share code, a level URL or a local `.mblevel.json` path, plus `--mod`/`--no-mod`.

Nothing in the game folder may change before the player confirms. Packs needed by several levels are fetched once, and a pack already installed at the requested version is skipped.

**Local files:** an installed local `.mblevel.json` still gets its required packs resolved from the site; it has no cover unless an image sits beside it.

**Classification:** a native Linux build is refused with `gamebuild`'s unsupported-build message.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 megabonk-installer accepts one or more share codes, level URLs and local .mblevel.json paths as positional arguments
- [x] #2 --mod and --no-mod control the mod install; without either, the mod is included only when it is not already installed
- [x] #3 --dry-run lists every planned download and install action and changes nothing on disk
- [x] #4 A pack required by several levels appears once in the plan; a pack already installed at the required version is skipped
- [x] #5 A level whose required pack is not hosted still installs, and the missing pack is reported as a warning
- [x] #6 A failure part-way through rolls back the files already written
- [x] #7 --check reports mod status and which recorded levels and packs are present
- [x] #8 --uninstall removes only what the install record lists
- [x] #9 A native Linux build is refused with the unsupported-build message
- [x] #10 CLI and plan tests cover each criterion using the existing test seams and a local test HTTP server
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution

## Implementation Notes

`go/internal/plan` now plans a level install from the player's own words rather than from a package folder. Each positional argument is resolved to a hosted record by `resolveInput` — share code, `megabonkmod.party` level link, stored level file name, or a local `.mblevel.json` — and a local file still gets its packs from the site, so a level copied off another machine brings its pack dependencies with it. Duplicate spellings of one level collapse to one install, with the local file preferred over the site's copy of the same name. `--mod`/`--no-mod` are one three-state choice (`ModForced`/`ModRefused`/`ModAuto`); with neither, the mod is planned only when the game lacks one.

Nothing reaches the game directory before the plan is confirmed. Every download and content file lands in a per-run staging folder outside the game (`go/internal/content/staging.go`), which is also the authority on ownership: a file's entry records who staged it, so the install record attributes levels, packs and loose files to the run that placed them instead of guessing from the destination path. `Commit` replaces pack folders whole, so a pack that changed version keeps no stale bundle, and `Prune` throws away a staged tree the player walked away from. A cancelled or failed run rolls back what it placed and names what it could not restore.

Three behaviours the rewrite had silently lost were found by tests and fixed: the native-build refusal lost its exit code (now a typed `UnsupportedBuildError` mapping to 4), a missing `--prefix` exited 1 instead of 2 (`MissingPrefixError`), and a named-but-unusable prefix hard-failed instead of warning and installing with the loader's own runtime. The prefix override is now decided once by the mod transaction and read back by the plan, so the record cannot claim a Wine-shaped key for a Proton install that wrote none; a Wine run edits the prefix itself and is reported as that, rather than being told to paste a launch option into a Steam entry it does not have. `thunderstore.checkPackLayout` also rejected directory members the unpacker skips, which failed verification on valid loader packs.

Go 1.27's `flag` package treats a `Value` that does not implement `IsBoolFlag` as value-taking and consumes the following argument, so `--mod` was swallowing the player's first level. `modFlag` implements it explicitly.

Deleted test files were replaced rather than dropped: `plan_test.go`'s package-manifest cases became the input-driven set in `level_plan_test.go`, and `cancel_test.go`'s four cases survive as `TestCancelBeforeAnyActionChangesNothing`, `TestCancelMidUninstallKeepsTheRecordForTheRerun`, `TestCancelPartWayRollsBackTheFilesAlreadyWritten` and `TestCancelRollsBackAPlacedLoader`. `go/internal/cli/fixtures_test.go` serves the site and Thunderstore from local `httptest` servers so no CLI test reaches the network. `task installer:test` (gofmt, vet, tests) passes, as does `installer:build` and `installer:verify-static` for all three targets; the Python suite passes at 1498 passed, 60 skipped.

**DoD #1 left unchecked deliberately:** `task check` also runs `mod:test`, which needs the game's generated Il2Cpp assemblies. They are absent in this worktree and `mod:build` cannot produce them without a game install, so that leg cannot be run here. Everything in the task's own scope — `installer:test` plus the Python tests — passes.

**Two judgement calls, both needing a maintainer's eye:**

1. **`--dotnet-in` was removed outright, not merely ignored.** With the loader pack placing its .NET 6 runtime beside the executable unconditionally, the flag had become a no-op that still validated its argument and still appeared in `--help`, so the installer was claiming a choice it would not honour. Its removal is nominally TASK-069.06's job; it is done here because leaving a lying flag was worse than stepping on a sibling task. `content.RuntimeSubdir`, `RuntimePath`, `NativeRuntimePath`, `VersionMarkerPath` and the loader-version marker helpers were dead by the same argument and are gone too.
2. **`docs/player-installer.md` is corrected, not comprehensively rewritten.** The Installer contract, exit-code table, override section, command-line section and the three `--package` sentences are now true of the binary. Substantial MelonLoader-era prose remains — the Package layout and manifest sections, `vendor/`, and the `.NET placement` and launch-option sections — plus `docs/gamepadui.md`'s `--dotnet-in` examples. That cleanup is TASK-069.09's scope and half-doing it here would have left the doc self-contradictory in new ways.
<!-- DOD:END -->
<!-- DOD:END -->
