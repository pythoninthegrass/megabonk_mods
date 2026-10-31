---
id: TASK-006.04.03
title: macOS player installer
status: To Do
assignee: []
created_date: '2026-10-31T03:12:00Z'
labels:
  - tooling
dependencies: []
references:
  - scripts/install_melonloader.py
documentation:
  - docs/modding-setup.md
  - docs/development.md
parent_task_id: TASK-006.04
priority: low
type: feature
ordinal: 123000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Megabonk has no macOS build, so a Mac player runs the Windows build under Wine or CrossOver — the same mechanism this repo's own contributor flow uses. Their setup is the most manual of the three platforms: a Wine prefix or CrossOver bottle to get right, the DLL override that MelonLoader's own installer would normally set for version.dll, a .NET 6 runtime inside that prefix, and the windows-platform pack bundles. The contributor tooling already solves most of it — game-directory and prefix resolution, the DLL override, the pinned loader version — but only for someone with a repo checkout and the task toolchain, which a player does not have.

This subtask delivers the macOS half of the package contract so a Mac player has one command too. CrossOver is commercial software, so the flow has to work with free Wine as well and must not assume CrossOver is installed. A notarized .dmg is not required; a script with a GUI progress surface is the accepted deliverable.

Until this lands, the player guide covers macOS only by pointing at the contributor setup doc, which is not a route a non-technical player can follow.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Running the installer on a Mac with Megabonk installed leaves the game launchable with the mod loaded: MelonLoader at the pinned version (checksum-verified), the mod DLL placed, and the game's Windows build running under the prefix
- [ ] #2 It works with both plain Wine and CrossOver's Wine, and does not require the commercial product to be installed
- [ ] #3 It applies the DLL override the loader needs and installs the .NET 6 runtime into the prefix when absent
- [ ] #4 The prefix and game directory are discovered without asking the player to install the repo's toolchain, with an explicit override for a non-default location
- [ ] #5 Re-running is a no-op when everything is at the expected version, and repairs only what is missing or stale when it is not; uninstall restores a vanilla game
- [ ] #6 Optional inputs are honored: a chosen level file lands in UserData/Levels/, a pack bundle and its manifest land in UserData/LevelPacks/<id>/, and UserData/Levels/ is created when absent
- [ ] #7 Progress shows through a GUI progress dialog in a desktop session and as plain text when run headless; a failure it cannot resolve exits nonzero with a message that says what to do
- [ ] #8 Verified end to end on the macOS machine, documented, and the player guide's macOS section becomes a real install route pointing at the installer rather than the contributor doc
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
