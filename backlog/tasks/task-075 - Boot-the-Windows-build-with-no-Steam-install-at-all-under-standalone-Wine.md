---
id: TASK-075
title: Boot the Windows build with no Steam install at all under standalone Wine
status: Done
assignee: []
created_date: '2026-11-15 21:09'
updated_date: '2026-11-15 21:39'
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
modified_files:
  - docs/development.md
  - scripts/swap_steam_stub.py
  - tests/test_swap_steam_stub.py
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
- [x] #1 The run uses no CrossOver code path: the launched argv is the standalone Wine binary and no CrossOver bundle path appears in the launch header or the loaded-module list
- [x] #2 The game directory the run uses contains no Steam file at all (no steam.exe, no steamclient64/vstdlib/tier0, and steam_api64.dll present only as the development stub), and the prefix carries no Valve registry key
- [x] #3 With the stub installed the game reaches the menu, steam-ready is sampled at t+0, t+25 and t+50, load-level arms the kill floor, save-level writes, and a screenshot shows rendered gameplay
- [x] #4 The same observations are recorded with the original shim instead of the stub, so the mod's own offline tolerance is separated from the stub's contribution
- [x] #5 The cold profile's save behaviour is recorded in a prefix with no prior game keys: the Rewired path lines, which CloudDir appears, and whether saves_last_steamid is written
- [x] #6 Whatever the fresh prefix needs beyond a copy of the game directory is named from the log (err:module and trace:loaddll lines), not guessed
- [x] #7 The real install is left byte-for-byte as found: bottle shim, steam.exe, user.reg and the Saves tree unchanged by hash, with no probe process running
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Booted the Windows build in a throwaway Wine prefix with no Steam files anywhere, under the repo-pinned standalone Wine (wine-11.18); CrossOver is not in the launch path at all, its bottle only ever supplied a prefix directory.

Environment: fresh prefix from wineboot --init, APFS clone of the game directory (cp -c -R, 1.43 GB), steam.exe deleted (the game directory's only Steam file; the sole steam_api64.dll is the one under Megabonk_Data/Plugins/x86_64), DXVK installed with task wine:dxvk, a Windows profile created for the launcher's WINDOWS_USER, stub installed. Every command carried MEGABONK_GAME_DIR and MEGABONK_WINE_PREFIX.

Three configurations, all booting to rendered gameplay:
- stub: steam-ready ready (build 21750826) at t+0/+25/+50; load-level armed the kill floor; save-level wrote cold-boot-test.mblevel.json with gameBuildId 21750826; screenshot showed the editor over the loaded level.
- original Valve shim, no Steam files, no client: steam-ready not ready (steam-not-running) at all three samples, the game's own [Steamworks.NET] SteamAPI_Init() failed. line present, and load-level plus save-level still worked, the saved file carrying an empty gameBuildId. The mod's guarded build-id read, not the stub, is what carries this case.
- stub with SteamAppId and SteamGameId removed from the launch environment: boots, loads, saves, renders, so the offline launch genuinely needs neither variable.

Zero err:module and zero err:seh lines in all three runs: a fresh prefix needs nothing beyond DXVK and a matching user profile. With no profile matching the launcher's Windows user, Unity drops persistentDataPath into the game directory and Player.log plus Saves appear inside the install, silently.

Cold profile: the game creates AppData/LocalLow/Ved/Megabonk/Saves/CloudDir/0/ with progression.json and stats.json plus Saves/LocalDir/config.json, writes no saves_last_steamid, and has no Software\\Valve hive in user.reg. CloudDir is keyed by Steam identity (an install signed in once also carries a folder named after the account's 64-bit SteamId); 0 is the no-identity bucket. Rewired logs CloudDir\\69\\ and CloudDir\\0\\ per run, only 0 is created, and 69 matches the patch of the adjacent Playing on version 1.0.69 line.

Two findings that outlived the experiment. (1) doorstop_config.ini in the real install records target_assembly and dll_search_path_override as absolute Z:-prefixed paths into that install, so the first cold clone ran the real bottle's BepInEx core, plugin, interop and log: the clone's LogOutput.log never appeared, its harness marker was never read, and the real install's LogOutput.log grew. BepInEx/cache/chainloader_typeloader.dat caches absolute paths the same way. Because both trees share the same C:\\Program Files (x86)\\Steam\\... path, the only discriminator is the Z: lines in the loaddll trace. Both trees were re-made with relative values and the isolation assertion (no Z: loads, no steamclient/vstdlib/tier0/steam.exe loads) passed on every run. (2) The game sits on the Loading overlay for roughly half a minute after editor on: a shot at +8s is a ~50 KB Loading frame and at +33s a ~4.6 MB rendered level, so an early screenshot looks like a failed load.

The real install was verified byte-for-byte unchanged against a baseline covering the shim, steam.exe, user.reg, UserData/Levels, the LocalLow Saves tree, BepInEx, UserData and doorstop_config.ini; the cold prefix was removed and no process was left running. task check passes (1644 Python, 6 skipped). Docs: a new "A prefix with no Steam installed at all" subsection in docs/development.md, and the GetSteamID bullet corrected now that the cold-machine save path is observed.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
- [x] #5 No hostname, username, account id or host home path from the experiment appears in tracked files
- [x] #6 Documentation change stays on the dev-only offline path; nothing about the shipped package changes
<!-- DOD:END -->
