---
id: TASK-006.04.01
title: Linux player installer
status: To Do
assignee: []
created_date: '2026-10-31T03:12:00Z'
labels:
  - tooling
dependencies: []
references:
  - AGENTS.md
  - 'https://melonwiki.xyz/#/README?id=linux-instructions'
documentation:
  - docs/modding-setup.md
  - docs/development.md
parent_task_id: TASK-006.04
priority: medium
type: feature
ordinal: 121000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Linux is where the manual setup is worst and where this repo has real machines to verify against. Two maintainer Linux machines exist: an AlmaLinux 10 host that runs Steam only as a Flatpak, whose Steam client and library were relocated outside the home directory to a path granted to the sandbox with a flatpak override, and a CachyOS host running native Steam where Megabonk is installed as the Windows build played under Proton with a gamepad. A player on either machine has to find their own Steam library among several possible layouts, choose between two game builds, and supply a .NET 6 runtime their distribution may not offer at all. This subtask delivers the Linux half of the package contract so that is one command rather than a wiki page.

The build choice is not obvious to a player and the installer has to handle it: Megabonk ships a native Linux binary, but the pinned MelonLoader fails to initialize against that build and the upstream fix is unreleased, while the Windows build under Proton works and is the path the player guide recommends. Detecting which build is installed, and steering the player instead of silently installing into a build that cannot load the mod, is core scope — the native build's LD_PRELOAD launch-option recipe in AGENTS.md is contributor tooling for a path that does not currently work.

How the .NET 6 runtime reaches the loader under Proton — a runtime directory placed inside the game folder, versus installing the runtime into the Proton prefix — and whether any DLL-override launch option is required, are settled by the verification run of the player guide on these same two machines. Implement whichever that run confirms and keep the other as a fallback.

Packs are per-platform: the windows bundle is the one that matters on the recommended Proton path.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 From a wiped mod install, running the installer on both Linux test machines leaves the game launchable with the mod loaded: MelonLoader at the pinned version (checksum-verified), the mod DLL, and the .NET 6 runtime all in place
- [ ] #2 The Steam install and the Megabonk directory are detected in the supported layouts: native Steam, Flatpak Steam including a client and library relocated outside the default path, and a library on removable media
- [ ] #3 The installer distinguishes the native Linux build from the Windows build and steers the player to the working one, stating why the native build cannot be used with the current MelonLoader
- [ ] #4 Re-running is a no-op when everything is at the expected version, and repairs only what is missing or stale when it is not
- [ ] #5 Optional inputs are honored: a chosen level file lands in UserData/Levels/, a pack bundle and its manifest land in UserData/LevelPacks/<id>/, and UserData/Levels/ is created when absent
- [ ] #6 Progress shows through a GUI progress dialog in a desktop session and as plain text when run headless, such as over ssh; a failure it cannot resolve exits nonzero with a message that says what to do
- [ ] #7 Uninstall restores a vanilla game
- [ ] #8 The verified command sequence is documented and the player guide's Linux section points at the installer
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
