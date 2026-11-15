---
id: TASK-072
title: Load levels without a Steam session by tolerating an uninitialized Steamworks
status: To Do
assignee: []
created_date: '2026-11-15 19:18'
labels:
  - mod
  - offline
dependencies: []
references:
  - docs/development.md
  - src/MegabonkLevels.Mod/game_build_id_patch.cs
modified_files:
  - src/MegabonkLevels.Mod/game_build_id_patch.cs
  - docs/development.md
priority: medium
ordinal: 72500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Level loading currently depends on a working Steamworks client, and that dependency is the only real blocker to running the mod on a machine with no Steam session. The game itself is fine: measured on the Windows build under Wine with the original steam_api64.dll shim and Steam unable to start, Steamworks.NET logs "SteamAPI_Init() failed", the game reaches the menu, and SaveManager still resolves its real Saves/CloudDir/<steamId>/ folder from the saves_last_steamid PlayerPrefs value. The mod is what fails.

The failure, verbatim from BepInEx/LogOutput.log: "DevHarness: 'LoadLevel' failed: System.InvalidOperationException: Steamworks is not initialized." thrown by Steamworks.InteropHelp.TestIfAvailableClient() from Steamworks.SteamApps.GetAppBuildId(). The build id is read from game_build_id_patch.cs, called from the harness SteamReady case and from level load and save. Because the offline stub in tools/steamstub/ answers CreateInterface even when it fails init, every run so far has hidden this: the stub is load-bearing for level loading rather than a convenience.

Work: make the Steamworks build-id lookup tolerate an uninitialized client. Ask whether the client is available (SteamAPI.Init result / SteamClient.Initialized) or catch InvalidOperationException, resolve once, and fall back to a documented local value. Keep one guarded accessor rather than try/catch at each call site, and log the fallback once rather than per level load.

Verification needs the configuration that exposes the bug, not the stub configuration. Recipe on the CrossOver host: rename the bottle's steam.exe aside first, because launching the Windows build with the original shim while Steam is stopped lets steam_api64.dll start Steam, which logs the account in and can sign other machines out; then put the original shim back by copying Megabonk_Data/Plugins/x86_64/steam_api64.dll.steamstub.bak over steam_api64.dll (scripts/swap_steam_stub.py refuses to act until the stub artifact is built, so copying by hand is fine), launch, confirm "SteamAPI_Init() failed" is in the log, and only then send a harness load-level. Restore both the stub and steam.exe afterwards, and leave the Saves tree as found.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 With the original shim installed and Steam unable to start, a harness load-level succeeds and the log still shows SteamAPI_Init() failed, proving the load no longer needs a Steamworks client
- [ ] #2 Exactly one guarded Steamworks build-id accessor exists, returning a documented fallback when the client is unavailable, with no unguarded GetAppBuildId call left in the harness, level load or save paths
- [ ] #3 The fallback is logged once per run, not per level load, and the harness steam-ready reporting distinguishes client-not-initialized from init-failed
- [ ] #4 The stub configurations still work: with the stub installed, and with MEGABONK_STEAM_FAIL_INIT=1, level load and save still succeed, so the guarded path and the stub path agree
- [ ] #5 A regression test covers the not-initialized branch without needing a live Steam client
- [ ] #6 docs/development.md records that level loading no longer depends on the offline stub
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [ ] #5 The experiment leaves the shim, steam.exe and the Saves tree exactly as found, with no probe process still running
- [ ] #6 No hostname, username or home path from the experiment appears in tracked files
<!-- DOD:END -->
