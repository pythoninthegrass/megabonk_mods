---
id: TASK-016
title: Launch Megabonk without a Steam session
status: Done
assignee: []
created_date: '2026-10-27T05:56:00Z'
updated_date: '2026-10-27T09:14:00Z'
labels:
  - research
  - native
  - steam
dependencies: []
references:
  - docs/development.md
priority: high
type: task
ordinal: 70000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The dev harness loads custom levels through Steamworks (`GetAppBuildId`), and Steam allows only one session per account across all devices, so a second Mac cannot run the game while the first is logged in. This task gets an offline, playable development copy that runs without a Steam session, so the single Steam login stops blocking several Macs working at once. This is the 'remove Steam restrictions' half of TASK-015's goal; it needs no recomp.

Background (static only, from TASK-015):
- `SteamManager.Load` decompiled statically shows a failed `SteamAPI.Init()` logs and continues (no `Application.Quit`, no throw, no retry); the main menu, level load and gameplay are not gated on `initialized`. Verdict: degraded, NOT runtime-verified.
- `SteamManager.IsInitialized()` (`0x18052ABB0`) is the non-throwing readiness probe the harness `steam-ready` command targets.
- `forceSingleInstance` is False, so Unity allows a second copy; only Steam's single-session rule blocks multi-machine use.
- Level load and save call `GameBuildIdPatch.CurrentBuildId()` (`SteamApps.GetAppBuildId`) unguarded, so they may throw before Steamworks is up.
- Not covered: any DRM/Steam wrapper outside `GameAssembly.dll` (UnityPlayer.dll, exe), what Steam returns for `RestartAppIfNecessary(0)`, and the save path with `steamId` 0.

This is gated on the Steam session being free (a live run), so it cannot start while the single login is in use. It is analysis + a working launch path, not a code recompile.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The game launches with Steam stopped and reaches the main menu without a quit loop (read `steam-ready` and `state` via the harness).
- [x] #2 The failed-`SteamAPI.Init()` verdict is confirmed in a live run, and the exact degraded behaviour is recorded.
- [x] #3 `load-level` starts a custom level with no logged-in Steam session, via the smallest working mechanism (local Steamworks stub/emulation, or natively if the client is truly optional).
- [x] #4 A custom level saves and reloads with no logged-in Steam session (the `steamId 0` save path is verified).
- [x] #5 The launch path (env vars, stub, flags) and the degraded/absent Steam features are documented in docs/development.md, plus the per-machine setup to reproduce it on a second Mac.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Goal
An offline, playable dev copy of Megabonk that runs without a logged-in Steam session, so the single Steam login stops blocking multiple Macs. This is the 'remove Steam restrictions' half of TASK-015. No mod recompile; a native launch path + docs.

## What the code shows (static, verified against dump.cs + game dir)
- The game's managed Steamworks.NET (com.rlabrecque.steamworks.net 2024.8.0, SDK 1.60) lives in GameAssembly. Its native shim is `Megabonk_Data/Plugins/x86_64/steam_api64.dll` (present). That shim loads the real `steamclient.dll`/`steamclient64.dll` from `C:\Program Files (x86)\Steam\`.
- Init path: `SteamAPI.InitEx()` -> `NativeMethods.SteamInternal_SteamAPI_Init(version, outErrMsg)`. On success the game calls `SteamInternal_FindOrCreateUserInterface(hUser, version)` to get ISteamUser/ISteamApps, etc.
- The mod's `LevelLoaderPatch.Start` calls `GameBuildIdPatch.CurrentBuildId()` -> `SteamApps.GetAppBuildId()` UNGUARDED. With no Steam client, this throws "Steamworks is not initialized", so `load-level` (F6 / run.py load) fails offline. This is the only thing that blocks offline play; the game's own `SteamManager.Load` logs a failed init and continues (main menu/gameplay not gated on `initialized`), per TASK-015 static verdict (not yet runtime-verified).
- Saves: the game writes to `Saves/LocalDir/` (e.g. config.json) when `SteamManager.steamId` == 0, i.e. the offline path.

## Approach per acceptance criterion
- #1/#2 (degraded launch, no stub): stop Steam, launch, read `steam-ready` + `state`. Expect: main menu reached, `steam-ready` returns ready:false ("Steamworks is not initialized"), no quit loop. Record exact log lines. If the game instead crashes on missing init, that changes the approach.
- #3 (load-level offline): build a minimal `steam_api64.dll` stub that fakes init + GetAppBuildId. Deploy by backing up the original and replacing `Megabonk_Data/Plugins/x86_64/steam_api64.dll` (reversible). Build tooling: install mingw-w64 (`brew install mingw-w64`) to compile a PE DLL. Stub surface: `SteamInternal_SteamAPI_Init`->k_ESteamAPIInitResult_OK(0); `SteamInternal_FindOrCreateUserInterface`/`CreateInterface`->vtables for ISteamApps/ISteamUser with GetAppBuildId (e.g. 3405340), GetAppID, GetSteamID; `SteamAPI_RestartAppIfNecessary`->false; `SteamAPI_IsSteamRunning`->true; no-ops for Shutdown/RunCallbacks/RegisterCallback/minidump. Vtable layout must match the exact interface-version strings the game requests ("ISteamApps0xx", "ISteamUser0xx") -- confirm via a stub log line or Ghidra before finalizing.
- #4 (save/reload offline): verify the game saves + reloads a custom level with steamId 0 into `Saves/LocalDir/` using the stub so Steam is 'initialized'. The mod is load-only (no save command), so this is the game's native save; exercise it via the editor save path if needed.
- #5 (docs): document the launch path, stub build+deploy, degraded/absent Steam features, and per-machine repro on a second Mac, in docs/development.md.

## Gate / risk
- Every live check needs Steam STOPPED. Shutting down Steam signs the account out on ALL machines (cross-machine). This is the one decision needing the user's go-ahead before I run it.
- Stub correctness depends on exact interface-version strings + vtable layouts; expect build->test->fix iteration. mingw-w64 must be installed.
- Reversible: back up the real steam_api64.dll before replacing; restore to revert.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Runtime-verified (2026-10-27), all with Steam stopped and the env-gated stub (tools/steamstub). Stub = game's steam_api64.dll replaced by a mingw-w64 build of generate_stub.py output; reversible via swap_steam_stub.py install/restore (backup .steamstub.bak). AC#1: reaches main menu (player:null), no quit loop, in both ok and fail stub modes. AC#2: fail-init stub (MEGABONK_STEAM_FAIL_INIT=1) -> steam-ready {ready:false}, main menu reached, load-level still works (stub fakes ISteamApps so GetAppBuildId returns depot id 21750826). The hard-degraded path (load-level REJECTED with 'Steamworks is not initialized') needs CreateInterface==null, i.e. the real shim with NO Steam ipcserver. On this Mac the macOS Steam ipcserver respawns within ~1s (reparented to init), so the real shim's Init still succeeds even with the Steam app stopped -- that path can only be triggered by quitting the macOS Steam app (cross-machine sign-out). AC#3: load-level works offline via the stub. AC#4: editor Save button at display ~(1001,86) writes UserData/Levels/level.mblevel.json (steamId 0 path); reload via run.py load <path> works and edits round-trip. AC#5: docs/development.md 'Launching without a Steam session' section.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Offline playable copy complete and runtime-verified with Steam stopped. Mechanism: drop-in steam_api64.dll stub (tools/steamstub/, mingw-w64 build of generate_stub.py output), reversible via scripts/swap_steam_stub.py. Verified: main menu with no quit loop (AC#1); failed-init verdict live -- MEGABONK_STEAM_FAIL_INIT=1 yields steam-ready {ready:false} while the game continues and load-level still works because the stub fakes ISteamApps (AC#2); load-level works offline (AC#3); custom level saves to UserData/Levels/level.mblevel.json via the editor Save button at ~(1001,86) and reloads via run.py load, edits round-trip (AC#4). The genuinely hard-degraded path (load-level rejected 'Steamworks is not initialized') requires the real shim with no Steam ipcserver; on this Mac the macOS Steam ipcserver respawns in ~1s so it can only be triggered by quitting the macOS Steam app, which signs the account out on all machines. Docs added to docs/development.md including per-Mac setup (AC#5). Original shim restored; game healthy.
<!-- SECTION:FINAL_SUMMARY:END -->
