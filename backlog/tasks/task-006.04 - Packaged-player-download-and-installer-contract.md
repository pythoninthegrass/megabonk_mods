---
id: TASK-006.04
title: Packaged player download and installer contract
status: Done
assignee: []
created_date: '2026-10-31T03:12:00Z'
updated_date: '2026-11-06T23:23:00Z'
labels:
  - tooling
dependencies:
  - TASK-006.02
references:
  - 'https://github.com/LavaGang/MelonLoader/releases'
  - scripts/install_melonloader.py
  - taskfiles/pack.yml
documentation:
  - docs/modding-setup.md
  - docs/development.md
parent_task_id: TASK-006
priority: medium
ordinal: 120000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Players who only want to play a level a friend shared still have to do contributor setup by hand: fetch the pinned MelonLoader archive, place the mod DLL, supply the .NET 6 runtime the loader needs, and put level files and asset packs into the right UserData folders. The player guide (TASK-006.02) has to document every step of that as prose because nothing else exists. This task defines the packaged distribution those steps point at: one downloadable per-platform package plus an installer script that performs the setup, so the guide's recommended route is "download and run this" with the manual steps demoted to the documented fallback.

A code-signed executable, notarized .dmg, or equivalent is explicitly not required. A script the player runs, which shows progress through a GUI progress surface and falls back to plain terminal output when no desktop session is available, is an acceptable deliverable.

The three platform subtasks implement one shared contract, defined here, so a player's experience is the same everywhere apart from how the script is launched: locating the Steam install and the Megabonk directory within it; identifying which game build is in place (the Windows build versus the native Linux build); installing MelonLoader at the repo's pinned version with checksum verification, reusing the pins and checksums scripts/install_melonloader.py already holds; providing the .NET 6 runtime the Il2Cpp loader requires; placing the mod DLL; creating UserData/Levels/; importing a chosen level file; installing an asset pack; reporting what it did and what it could not do; and supporting idempotent re-run, re-run after a game update, and uninstall.

Asset packs need care: a pack is built locally from gitignored .tools/ output and installed today only through task pack:install, which copies the per-platform bundle (windows on Wine/Proton, linux on the native build) and its manifest into UserData/LevelPacks/<id>/. A player has no repo checkout, so whatever the pack installer consumes has to travel in the package or as a companion download.

Hosting and publishing are in scope only to the extent that a player needs a URL to download from and the guide needs to link it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 One reproducible command in the repo produces the per-platform player package carrying MelonLoader at the pinned version, the mod DLL, and the .NET 6 runtime, with no repo checkout or contributor toolchain needed on the player's machine
- [x] #2 The shared installer contract is written down in docs/ as the single source the three platform installers implement: game-directory detection, MelonLoader install with checksum verification, .NET 6 runtime delivery, mod DLL placement, UserData/Levels creation, level import, pack install, idempotent re-run, re-run after a game update, uninstall, and failure reporting
- [x] #3 Asset packs are distributable: the package or a companion download carries the per-platform pack bundle and manifest a player needs, rather than assuming the local task pack:install flow
- [x] #4 The player guide recommends the packaged installer as the install route on every platform it covers and keeps the manual steps as the fallback
- [x] #5 The package records the game build and MelonLoader version it was verified against, so a player can tell whether it matches the game they have installed
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approved approach (AC #2, #4, #5; #1 and #3 already met).

A. Docs: add an "Installer contract" section to docs/player-installer.md as the single source the Python, Go and platform installers implement (game-directory detection, build classification, MelonLoader plus checksum, .NET 6 delivery, mod DLL, UserData/Levels, level import, pack install, idempotent re-run, re-run after a game update, uninstall, failure reporting); platform sections point at it. Add a manual-install fallback section for players to docs/modding-setup.md (AC #4), linking the player guide from TASK-006.02.

B. Build-match check (AC #5), tests first in both implementations (scripts/player_installer and go/internal) plus a parity scenario: read buildid from appmanifest_3405340.acf during discovery; on install and --check print installed build against the build the package was verified against; a mismatch is a warning only (no exit-code change); record the installed build in the install record as an optional key, schema stays megabonk-levels-install/1; a missing appmanifest reports unknown.

C. task check, docs, conventional commit with no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Checked against the docs, task files and code, without rebuilding the packages. AC 1: task package:linux, package:windows and package:macos exist and carry the pinned MelonLoader, the mod DLL and the vendored .NET 6 runtime; the Go static binary means no player toolchain. The Windows package has been run in a software-rendered VM only. AC 3: the package builder takes --pack and stages the per-platform bundle and manifest; installing a pack on a real game is covered by unit tests only, and the Windows subtask's levels-and-packs criterion is still open.

AC 2 is open: docs/player-installer.md has layout, manifest, install record, exit codes and a parity contract, but no single contract section and nothing on re-running after a game update.

AC 4 is open: docs/modding-setup.md points Linux, Windows and macOS players at the installer, but keeps no manual fallback for players; its manual sections are contributor setup.

AC 5 is open: melonloader_version and game_buildid are in the manifest and echoed by --check, but game_buildid is the build the shipped levels were authored against and nothing compares it to the installed game, so a player cannot tell whether the package matches.

Blocked on TASK-006.04.02 (Windows installer), still In Progress with four open criteria, including verifying the manual flow on real Windows. The Definition of Done is untouched.

AC 2: docs/player-installer.md gained an Installer contract section (eleven ordered steps, re-running, re-run after a game update, uninstall) that the platform sections and tests/test_installer_parity.py point at. AC 4: docs/player-guide.md recommends the installer on Windows, Linux and macOS and links the manual fallback in docs/modding-setup.md. AC 5: both installers now read buildid from appmanifest_3405340.acf, print whether it matches the build the package was verified against (warning only, unknown when there is no appmanifest) and record it as the optional installed_game_buildid key under the unchanged megabonk-levels-install/1 schema. Python and Go tests added first; task check and go test pass.

Not established: what a Steam update or file verification does to the loader files, listed under Still pending in docs/player-installer.md. tests/test_installer_parity.py was already failing on Linux before this change: the Go closing message is capitalised since the progress-window commit, and the Go uninstall also clears loader leftovers (d78ac31) that the Python reference does not. With capitalisation ignored, only the three uninstall scenarios fail, and the new build-match line matches between the two implementations.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
