---
id: TASK-006.04
title: Packaged player download and installer contract
status: To Do
assignee: []
created_date: '2026-10-31T03:12:00Z'
updated_date: '2026-10-31T03:12:00Z'
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
type: chore
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
- [ ] #1 One reproducible command in the repo produces the per-platform player package carrying MelonLoader at the pinned version, the mod DLL, and the .NET 6 runtime, with no repo checkout or contributor toolchain needed on the player's machine
- [ ] #2 The shared installer contract is written down in docs/ as the single source the three platform installers implement: game-directory detection, MelonLoader install with checksum verification, .NET 6 runtime delivery, mod DLL placement, UserData/Levels creation, level import, pack install, idempotent re-run, re-run after a game update, uninstall, and failure reporting
- [ ] #3 Asset packs are distributable: the package or a companion download carries the per-platform pack bundle and manifest a player needs, rather than assuming the local task pack:install flow
- [ ] #4 The player guide recommends the packaged installer as the install route on every platform it covers and keeps the manual steps as the fallback
- [ ] #5 The package records the game build and MelonLoader version it was verified against, so a player can tell whether it matches the game they have installed
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
