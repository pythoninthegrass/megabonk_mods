---
id: TASK-075
title: Boot the Windows build with no Steam install at all under standalone Wine
status: In Progress
assignee: []
created_date: '2026-11-15 21:09'
labels:
  - mod
  - offline
  - tooling
dependencies: []
references:
  - docs/development.md
  - taskfiles/wine.yml
  - scripts/swap_steam_stub.py
  - src/megabonk_harness/launch_game.py
priority: medium
ordinal: 248000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The offline story so far proves the game launches and plays with the Steam client stopped, and that the mod's build-id read no longer needs the stub to answer CreateInterface. What has never been executed is the stronger claim: a machine where Steam's files are simply not there. Every run to date used the CrossOver bottle as the Wine prefix, so the bottle's Steam directory, its HKCU\\Software\\Valve registry keys and its Windows prerequisites were always present.

Newly established, and it changes the plan: every launch so far already went through standalone Wine. The launch header records argv as ~/Applications/wine11/Wine Devel.app/Contents/Resources/wine/bin/wine (wine-11.18, from task wine:install), and CrossOver's own wine is a Perl launcher that was never exec'd. CrossOver contributes only the prefix directory. So a CrossOver-free run is the normal case, not a new one.

Work: build a fresh Wine prefix, APFS-clone the game directory into it at the path the launcher expects, delete the game directory's only Steam artifact (steam.exe, 5,823,128 B; the sole steam_api64.dll is the one under Megabonk_Data/Plugins/x86_64), install DXVK into the prefix with task wine:dxvk, and launch through scripts/launch_game.py with MEGABONK_GAME_DIR and MEGABONK_WINE_PREFIX pointing only at the cold tree. Two configurations: stub installed, and original shim restored, so the mod's tolerance and the stub's stand-in are separated. Probe steam-ready at t+0, t+25 and t+50, load-level to the kill floor, save-level, and a screenshot. The fresh prefix also gives the genuinely cold profile for free, which is where the game's own save path question lives: with no saves_last_steamid key the resolved path is CloudDir\\0\\ and no account folder is created, observed in the CrossOver bottle.

Risks worth naming: a fresh prefix may lack Windows prerequisites the bottle picked up from Steam's installer, which shows up as err:module lines and is fixed by copying the named DLL from the bottle rather than by installing anything; the graphics stack needs DXVK in the prefix or the game dies at device creation; and every command must carry both MEGABONK_GAME_DIR and MEGABONK_WINE_PREFIX, because without them the harness resolves to the real bottle and quit would attribute processes to it. Nothing in the real bottle is to be modified; the experiment writes only into the gitignored cold tree.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The run uses no CrossOver code path: the launched argv is the standalone Wine binary and no CrossOver bundle path appears in the launch header or the loaded-module list
- [ ] #2 The game directory the run uses contains no Steam file at all (no steam.exe, no steamclient64/vstdlib/tier0, and steam_api64.dll present only as the development stub), and the prefix carries no Valve registry key
- [ ] #3 With the stub installed the game reaches the menu, steam-ready is sampled at t+0, t+25 and t+50, load-level arms the kill floor, save-level writes, and a screenshot shows rendered gameplay
- [ ] #4 The same observations are recorded with the original shim instead of the stub, so the mod's own offline tolerance is separated from the stub's contribution
- [ ] #5 The cold profile's save behaviour is recorded in a prefix with no prior game keys: the Rewired path lines, which CloudDir appears, and whether saves_last_steamid is written
- [ ] #6 Whatever the fresh prefix needs beyond a copy of the game directory is named from the log (err:module and trace:loaddll lines), not guessed
- [ ] #7 The real install is left byte-for-byte as found: bottle shim, steam.exe, user.reg and the Saves tree unchanged by hash, with no probe process running
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [ ] #5 No hostname, username, account id or host home path from the experiment appears in tracked files
- [ ] #6 Documentation change stays on the dev-only offline path; nothing about the shipped package changes
<!-- DOD:END -->
