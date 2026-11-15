---
id: TASK-069.04
title: Install BepInEx and the level editor mod into the game folder
status: To Do
assignee: []
created_date: '2026-11-15 05:59'
labels:
  - installer
dependencies:
  - TASK-069.02
  - TASK-069.03
references:
  - docs/modding-setup.md
  - scripts/repair_bepinex.py
  - go/internal/proton/proton.go
  - pkg/README.md
parent_task_id: TASK-069
priority: high
ordinal: 240000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
When the player opts in, the installer replaces the manual BepInEx install in `docs/modding-setup.md` ("Installing by hand"). It works from the downloads that TASK-069.02 resolves.

**Steps:**
1. Extract everything under the BepInEx pack zip's `BepInExPack/` next to `Megabonk.exe`. This includes `dotnet/`, `.doorstop_version` and `changelog.txt`, which r2modmac's Apply misses.
2. Merge the mod zip's `BepInEx/` into the game folder.
3. Park a leftover MelonLoader `version.dll` as `version.dll.bak`.
4. Make sure Wine loads the native `winhttp`:
   - Plain Wine or CrossOver prefix: write `winhttp=native,builtin` into the prefix's `user.reg`. `go/internal/proton` already has `SetDllOverride` and `ReadDllOverride` for this.
   - Proton: give the player the Steam launch option `WINEDLLOVERRIDES="winhttp=n,b" %command%` through the existing `ShowLaunchOption` Copy UI.
   - Native Windows: no override.

`scripts/repair_bepinex.py` is the reference for the expected file set and the `version.dll` handling.

Detecting whether the mod is already installed, so the GUI checkbox can default sensibly, belongs here as well: `BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll` together with the install record.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 After install, the game folder contains every file from the pack's BepInExPack/ tree, including dotnet/, .doorstop_version and changelog.txt, and the mod's BepInEx/plugins/MegabonkLevels/ files
- [ ] #2 An existing version.dll is renamed to version.dll.bak and restored on uninstall
- [ ] #3 A Wine or CrossOver prefix has the winhttp native,builtin override after install and it is removed on uninstall
- [ ] #4 Under Proton the player is shown the WINEDLLOVERRIDES launch option with a copy button
- [ ] #5 Native Windows installs set no override
- [ ] #6 Whether the mod is already installed, and at which version, is detectable
- [ ] #7 Unit tests cover each platform branch with temporary game folders and prefixes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
