---
id: TASK-069.05
title: 'Rebuild the installer plan and CLI around levels, packs and the optional mod'
status: To Do
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
- [ ] #1 megabonk-installer accepts one or more share codes, level URLs and local .mblevel.json paths as positional arguments
- [ ] #2 --mod and --no-mod control the mod install; without either, the mod is included only when it is not already installed
- [ ] #3 --dry-run lists every planned download and install action and changes nothing on disk
- [ ] #4 A pack required by several levels appears once in the plan; a pack already installed at the required version is skipped
- [ ] #5 A level whose required pack is not hosted still installs, and the missing pack is reported as a warning
- [ ] #6 A failure part-way through rolls back the files already written
- [ ] #7 --check reports mod status and which recorded levels and packs are present
- [ ] #8 --uninstall removes only what the install record lists
- [ ] #9 A native Linux build is refused with the unsupported-build message
- [ ] #10 CLI and plan tests cover each criterion using the existing test seams and a local test HTTP server
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
