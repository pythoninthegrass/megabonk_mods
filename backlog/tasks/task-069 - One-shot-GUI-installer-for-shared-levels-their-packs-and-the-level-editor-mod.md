---
id: TASK-069
title: 'One-shot GUI installer for shared levels, their packs and the level editor mod'
status: To Do
assignee: []
created_date: '2026-11-15 05:58'
labels:
  - installer
dependencies: []
references:
  - go/
  - docs/player-installer.md
  - docs/modding-setup.md
  - docs/player-guide.md
priority: high
ordinal: 236000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Installing a shared level from megabonkmod.party takes several manual steps, and the audience is non-technical players:
- download the `.mblevel.json`
- find `UserData/Levels/`
- save the cover beside it under a matching name
- fetch each required pack's Windows bundle into `UserData/LevelPacks/<id>/`

The level editor mod itself needs a mod manager, or a 6-step manual BepInEx install with Wine/Proton caveats (`docs/modding-setup.md`).

The goal is to repurpose the legacy MelonLoader-era Go installer in `go/` (`megabonk-installer`) into one GUI-first installer, with the CLI as a secondary interface. A player gives it share codes, megabonkmod.party level links or local `.mblevel.json` files. The installer:
- finds the game, on Windows, Linux Proton, Flatpak Steam, or macOS Wine/CrossOver
- installs the levels, their cover and biome images, and their required hosted packs
- optionally installs or updates BepInExPack_IL2CPP and Megabonk_Level_Editor from Thunderstore

Decisions already taken by the maintainer:
- Repurpose the existing command rather than add a new one. The MelonLoader, vendor-manifest and .NET 6 paths are removed.
- The mod install is opt-in: a GUI checkbox or a CLI flag, defaulting to on when the mod is not detected.
- Inputs are share codes, level URLs and local files.
- The UI is the existing MyGo native window.

Reused as-is: `go/internal/steam`, `go/internal/vdf`, `go/internal/gamebuild` and `go/internal/ui`.

The mod runs only on the Windows build, so pack bundles are always the `windows` platform. A native Linux build (`Megabonk.x86_64`) is refused with the existing unsupported-build message.

Related: TASK-047.02 (stale standalone-installer claims in guides), TASK-050 (onboarding friction) and TASK-048 (public releases).

Plan file: `~/.claude/plans/i-want-to-reuse-hidden-mountain.md` (maintainer-local).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A player can install a level by share code on Windows, Linux Proton and macOS Wine/CrossOver using only the GUI
- [ ] #2 Required hosted packs for the chosen levels are installed without the player fetching them
- [ ] #3 The level editor mod and BepInEx can be installed from the same window when the player opts in
- [ ] #4 All subtasks are Done
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
