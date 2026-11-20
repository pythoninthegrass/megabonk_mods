---
id: TASK-069.06
title: >-
  Remove the MelonLoader and .NET 6 paths from the installer and rebuild
  package:linux, package:windows and package:macos as thin installer zips
status: Done
assignee: []
created_date: '2026-11-15 06:00'
updated_date: '2026-11-20T00:18:00Z'
labels:
  - installer
dependencies:
  - TASK-069.05
references:
  - go/internal/manifest/manifest.go
  - go/internal/proton/proton.go
  - taskfiles/package.yml
  - taskfiles/installer.yml
  - scripts/build_player_package.py
  - scripts/notarize_macos.py
parent_task_id: TASK-069
priority: medium
ordinal: 242000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The maintainer chose to repurpose the legacy installer rather than keep it alongside the new one. The installer is still distributed on Linux, Windows and macOS, but it now installs the level editor mod, levels and packs (characters later) from the site and Thunderstore at run time. The distributable therefore needs no bundled mod DLL, MelonLoader, .NET 6 runtime, vendor manifest or content, and building it must not depend on Thunderstore.

What goes:
- `go/internal/manifest`: the package manifest with sha256 vendor checks.
- From `go/internal/proton`: MelonLoader vendor extraction and the .NET 6 runtime install and removal.
- The `--package` and `--dotnet-*` flags and `ResolvePackageDir`.
- `scripts/build_player_package.py` and `scripts/package_contract/` as they exist today: they assemble a package folder with the mod DLL, vendor archives and levels.

What stays or is rebuilt:
- `task package:linux`, `task package:windows` and `task package:macos` become public tasks (no `internal: true`). Each builds the platform installer through `installer:build` and writes a zip holding exactly the installer binary and a short README, with no Thunderstore step. The zip name carries the platform and version.
- `package:macos` keeps `APPLE_SIGNING_IDENTITY` codesigning and notarization, so `scripts/notarize_macos.py` and its test stay; the zip glob it submits must match the new zip name.
- `package:check` verifies that a built zip contains exactly the binary and the README.
- The `package:thunderstore*` tasks are unchanged.

Before deleting anything, find every other caller with `rg`: Python tests, the taskfiles, docs, CI and .env.example. The superseded attempt on branch `TASK-069.06-superseded` removed the Go side correctly and is a reference for it (`git show TASK-069.06-superseded:<path>`); review anything taken from it, because the same attempt also deleted the macOS notarizer and every package task, which this task must not do.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 go/internal/manifest and the MelonLoader and .NET 6 runtime code, the --package and --dotnet-* flags and ResolvePackageDir are gone along with their tests
- [x] #2 scripts/build_player_package.py and scripts/package_contract are replaced by a small tested builder that zips the installer binary and a README, with no mod DLL, vendor archives, levels, packs or Thunderstore input
- [x] #3 task package:linux, package:windows and package:macos are public tasks that each build their platform installer and produce a zip containing exactly the binary and the README
- [x] #4 package:macos still codesigns with APPLE_SIGNING_IDENTITY and notarizes when credentials are set; scripts/notarize_macos.py and its test are kept and the notarized zip matches the new name
- [x] #5 package:check fails on a zip with any entry other than the binary and the README and passes on a built one, covered by tests
- [x] #6 The package:thunderstore tasks still work and task check passes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Removed the MelonLoader vendor extraction and the .NET 6 runtime install/removal from go/internal/proton (RuntimeTarget/RuntimeInstalled/ExtractRuntime/RemoveRuntime/LaunchOption/WindowsPath/ProtonRoots/PickProton/ProtonWineBin/UsablePrefix) and their tests; legacy_test.go now guards the removed surface. scripts/build_player_package.py and scripts/package_contract are replaced by scripts/installer_package.py, which writes a zip of exactly the installer binary and a README.txt (mode 0755/0644, honoring SOURCE_DATE_EPOCH) and checks a built zip for any stray entry; tests/test_installer_package.py covers all three platforms. package:linux/windows/macos are public tasks that run installer:build for their target and emit megabonk-installer-<version>-<os>.zip; package:macos keeps APPLE_SIGNING_IDENTITY codesigning and the scripts/notarize_macos.py step against the new zip name. package:check runs the builder's checker. package:thunderstore is untouched. Verified with task check (go vet+test, 2858 C#, 2521 Python, ruff, markdownlint, deno) and a real package:linux/windows/macos build whose zips pass package:check and fail when a mod DLL is added.
<!-- SECTION:NOTES:END -->
