---
id: TASK-069.06
title: >-
  Remove the MelonLoader package, vendor manifest and .NET 6 paths from the
  installer
status: To Do
assignee: []
created_date: '2026-11-15 06:00'
labels:
  - installer
dependencies:
  - TASK-069.05
references:
  - go/internal/manifest/manifest.go
  - go/internal/proton/proton.go
  - taskfiles/package.yml
  - scripts/build_player_package.py
parent_task_id: TASK-069
priority: medium
ordinal: 242000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The maintainer chose to repurpose the legacy installer rather than keep it alongside the new one. Once the CLI and plan no longer use the MelonLoader-era machinery (TASK-069.05), remove it.

What goes:
- `go/internal/manifest`: the package manifest with sha256 vendor checks.
- From `go/internal/proton`: MelonLoader vendor extraction and the .NET 6 runtime install and removal.
- The `--package` and `--dotnet-*` flags.
- `ResolvePackageDir`.
- `scripts/build_player_package.py`, because the binary is now self-contained and needs no package folder.
- The internal `package:linux`, `package:windows` and `package:macos` tasks in `taskfiles/package.yml`.

Before deleting anything, find every other caller with `rg`: Python tests, the taskfiles, docs and CI. Keep the Thunderstore `package:thunderstore*` tasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 go/internal/manifest and the MelonLoader and .NET 6 runtime code are gone along with their tests
- [ ] #2 scripts/build_player_package.py and the package:linux, package:windows and package:macos tasks are gone, and nothing else references them
- [ ] #3 The package:thunderstore tasks still work
- [ ] #4 task check passes after the removal
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
