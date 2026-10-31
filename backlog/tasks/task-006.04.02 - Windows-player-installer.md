---
id: TASK-006.04.02
title: Windows player installer
status: To Do
assignee: []
created_date: '2026-10-31T03:12:00Z'
labels:
  - tooling
dependencies: []
references:
  - 'https://github.com/LavaGang/MelonLoader/releases'
documentation:
  - docs/modding-setup.md
  - docs/development.md
parent_task_id: TASK-006.04
priority: medium
type: feature
ordinal: 122000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Windows is where most players are, and the manual setup still means finding the game folder, fetching the loader archive by hand, and making sure the .NET 6 Desktop Runtime the loader needs is actually present. MelonLoader's own Windows installer normally handles that runtime, and this package deliberately ships a script rather than a signed installer, so that responsibility belongs to us.

The repo has never confirmed the mod loading on a real Windows install: development happens on macOS under CrossOver/Wine and on Linux, and Windows has been carried as the assumed reference platform rather than a tested one, which is why the player guide's Windows section is marked untested. Confirming the manual flow on a Windows machine and correcting the guide wherever reality differs is part of this task and has to happen before the automation is written against it, otherwise the script automates an unverified recipe.

This subtask delivers the Windows half of the package contract. A code-signed executable is not required; a script with a GUI progress surface is the accepted deliverable, and the install stays inside the game directory at user scope.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The manual Windows install flow is verified on a real Windows install first, and any difference from the player guide's Windows section is corrected there before the installer is written against it
- [ ] #2 Running the installer on a Windows machine leaves Megabonk launchable with the mod loaded: MelonLoader at the pinned version (checksum-verified), the mod DLL placed, and the .NET 6 Desktop Runtime present, installed by the installer when missing
- [ ] #3 The game directory is found from Steam's recorded library folders, including a library that is not on the default location
- [ ] #4 Nothing requires administrator elevation: every write is inside the game directory and at user scope
- [ ] #5 Re-running is a no-op when everything is at the expected version, and repairs only what is missing or stale when it is not; uninstall restores a vanilla game
- [ ] #6 Optional inputs are honored: a chosen level file lands in UserData/Levels/, a pack bundle and its manifest land in UserData/LevelPacks/<id>/, and UserData/Levels/ is created when absent
- [ ] #7 Progress shows through a GUI progress dialog, and a failure it cannot resolve exits nonzero with a message that says what to do
- [ ] #8 The verified command sequence is documented and the player guide's Windows section points at the installer instead of being marked untested
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
