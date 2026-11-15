---
id: TASK-073
title: Settle whether the stub failed-init mode actually reaches the game
status: Done
assignee: []
created_date: '2026-11-15 20:12'
updated_date: '2026-11-15 20:43'
labels:
  - mod
  - offline
  - tooling
dependencies: []
references:
  - tools/steamstub/steamstub.c
  - docs/development.md
  - taskfiles/steamstub.yml
modified_files:
  - docs/development.md
  - tools/steamstub/steamstub.c
  - src/MegabonkLevels.Mod/steam_readiness.cs
  - src/MegabonkLevels.Mod/game_build_id_patch.cs
  - src/MegabonkLevels.Mod/steam_library_report.cs
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/megabonk_harness/run.py
  - src/megabonk_harness/launch_game.py
  - scripts/swap_steam_stub.py
  - tests/test_gui_launch.py
  - tests/test_run.py
  - tests/test_swap_steam_stub.py
  - tests/MegabonkLevels.Tests/steam_readiness_tests.cs
  - tests/MegabonkLevels.Tests/steam_library_report_tests.cs
priority: medium
ordinal: 72600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
task steamstub:test:fail sets MEGABONK_STEAM_FAIL_INIT=1, which the stub's SteamAPI_IsSteamRunning honours by returning 0, and docs/development.md states this reproduces "no Steam client" behaviour. Observed instead: that mode reports steam-ready reason client-not-initialized, while the original shim with Steam unable to start reports steam-not-running from the very same managed call (Steamworks.SteamAPI.IsSteamRunning, reached through GameBuildIdPatch.IsSteamRunning, which returns null only if the call throws). Same Steamworks statics, same window (the harness answers commands before the game's own SteamManager initializes Steamworks), different answer.

Ruled out already, so do not re-do this work: the built stub exports SteamAPI_IsSteamRunning, SteamInternal_SteamAPI_Init, SteamInternal_CreateInterface and SteamAPI_ISteamApps_GetAppBuildId, and the binary carries the MEGABONK_STEAM_FAIL_INIT string; the installed shim is byte-identical to the built artifact; and the launcher does forward environment across the macOS GUI handoff, which the launch header proves by recording MEGABONK_DEV and MEGABONK_EVIDENCE_DIR in the Wine process env (launch_game.py watches WINE, DOTNET_, DYLD_, MVK_, DXVK_, MEGABONK_ and Steam prefixes).

Work: one launch with the variable set, reading the launch header line for MEGABONK_STEAM_FAIL_INIT to prove presence, then steam-ready twice (immediately, and again after the game's own SteamAPI_Init attempt has certainly run) so a pre-init race is distinguishable from a genuinely failed init. Record where the game's own "[Steamworks.NET] SteamAPI_Init() failed." line falls relative to the probe lines, since that line is not a shim discriminator. Then either correct docs/development.md's claim about what this mode reproduces, or fix the path that swallows the variable.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A launch with MEGABONK_STEAM_FAIL_INIT=1 has its env recorded in the BepInEx/wine-latest.log launch header, proving whether the variable reaches the Wine process
- [x] #2 steam-ready is sampled twice, before and after the game has certainly attempted its own SteamAPI_Init, so a race is distinguished from a real failed init
- [x] #3 The finding settles the open question in docs/development.md and the doc either corrects the claim about what the failed-init mode reproduces or names the fix
- [x] #4 task steamstub:test:ok and task steamstub:test:fail are documented with what each actually proves, and a reader is told which signals are and are not shim discriminators
- [x] #5 The environment is left as found: stub active, original shim untouched in the backup, no probe process running
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Two causes, both real, both fixed.

1. The variable never reached the game. The macOS GUI handoff copies only names in GUI_ENV_NAMES (src/megabonk_harness/launch_game.py), and MEGABONK_STEAM_FAIL_INIT was not among them, so task steamstub:test:fail launched an ordinary stub run. The first steam-ready sample reads not-ready in every run because the harness answers commands before the game attempts its own init, so a single early sample made the mode look like it worked.
2. Once the variable did arrive, the stub contradicted its own down state. Only SteamInternal_SteamAPI_Init honoured it; SteamAPI_ISteamApps_GetAppBuildId kept returning the canned build id, GetHSteamPipe/GetHSteamUser returned non-zero handles, and InitFlat/InitSafe/InitAnonymousUser returned success. The managed accessors only report an uninitialized client when the shim hands them no interface and no handles, so as soon as the game's own init ran, the verdict flipped to ready (build 21750826) at t+25. All of them now share one client_down() gate, and the build id returns 0, which the mod reads as no build id rather than as build zero.

Observed after both fixes, sampling at t+0, t+25 and t+50 with the shim identity pinned by hash and the packaged duplicate plugin moved aside: failed-init mode is not ready (steam-not-running) [steam=down, session=down, library=stub, failInitEnv=set] at all three samples, which is the same reason the original shim with no client holds; the normal stub is ready (build 21750826) [steam=up, session=up, library=stub, failInitEnv=unset] at all three. The Wine launch header shows MEGABONK_STEAM_FAIL_INIT='1', which is the proof AC#1 asked for.

Deliberately not done: a client-state veto in SteamReadiness.Probe. This Steamworks.NET build exposes no SteamAPI.IsInitialized (only InitEx/Init/Shutdown/RestartAppIfNecessary/RunCallbacks/IsSteamRunning/GetHSteamPipe/GetHSteamUser), and readiness has only ever been observed from a build id, so the probe reports steamSession, steamRunning, steamLibrary and failInitEnv as evidence and leaves the verdict build-id-derived.

Tooling that the verification depends on: swap_steam_stub.py install classified by marker string and returned early, so a rebuilt stub never deployed and an earlier matrix silently measured a stale binary; it now compares hashes. The probe self-reports shim identity and aborts when the installed file matches neither the artifact nor the backup, because verdicts are uninterpretable without that.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
