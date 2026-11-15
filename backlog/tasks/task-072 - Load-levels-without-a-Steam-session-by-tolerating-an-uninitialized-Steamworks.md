---
id: TASK-072
title: Load levels without a Steam session by tolerating an uninitialized Steamworks
status: Done
assignee: []
created_date: '2026-11-15 19:18'
updated_date: '2026-11-15 19:36'
labels:
  - mod
  - offline
dependencies: []
references:
  - docs/development.md
  - src/MegabonkLevels.Mod/game_build_id_patch.cs
modified_files:
  - src/MegabonkLevels.Mod/game_build_id_patch.cs
  - src/MegabonkLevels.Mod/steam_readiness.cs
  - src/MegabonkLevels.Mod/dev_harness.cs
  - tests/MegabonkLevels.Tests/steam_readiness_tests.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
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
- [x] #1 With the original shim installed and Steam unable to start, a harness load-level succeeds and the log still shows SteamAPI_Init() failed, proving the load no longer needs a Steamworks client
- [x] #2 Exactly one guarded Steamworks build-id accessor exists, returning a documented fallback when the client is unavailable, with no unguarded GetAppBuildId call left in the harness, level load or save paths
- [x] #3 The fallback is logged once per run, not per level load, and the harness steam-ready reporting distinguishes client-not-initialized from init-failed
- [x] #4 The stub configurations still work: with the stub installed, and with MEGABONK_STEAM_FAIL_INIT=1, level load and save still succeed, so the guarded path and the stub path agree
- [x] #5 A regression test covers the not-initialized branch without needing a live Steam client
- [x] #6 docs/development.md records that level loading no longer depends on the offline stub
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Executed approach, with two deviations from the plan recorded at the start. (1) The guard was extracted from game_build_id_patch.cs into a pure BuildIdSource (build_id_source.cs, added to the test csproj Compile list) so the three rules that actually matter are unit-testable without a Steam client: a not-initialized fault reads as null, it is reported once per run, and it is retried rather than cached, because availability changes while the game starts. GameBuildIdPatch now holds one BuildIdSource plus the log-once notice and a SteamAPI.IsSteamRunning probe that returns bool? (null when the call itself cannot be consulted, so a missing entry point is never reported as Steam being down). (2) A gap the plan had not anticipated: with the accessor returning null, GameBuildIdCheck.MismatchWarning reported "the running game is build ''," asserting a mismatch it could not know about. It now stays silent when either side is empty, the same rule GamePackVersionCheck already uses, which also makes levels saved offline (empty gameBuildId) never warn later. SteamReadiness grew a Reason and treats a null build id as not-ready; the existing overload and its expectations, including that an unrelated InvalidOperationException propagates, are unchanged.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Live verification, Windows build under Wine, three configurations, each with the harness verbs steam-ready and load-level (and save-level in the last):

stub installed: build id 21750826 read, "DevHarness: Steamworks ready (build 21750826)", level loads and arms the kill floor.

stub with MEGABONK_STEAM_FAIL_INIT=1: build-id read throws, "GameBuildId: Steamworks is not initialized; levels load and save without a game build id." logged once, "DevHarness: Steamworks not ready (client-not-initialized)", level loads.

original shim with the bottle steam.exe renamed aside: same single warning line, "DevHarness: Steamworks not ready (steam-not-running)", "[Steamworks.NET] SteamAPI_Init() failed." present from the game's own bootstrap, load-level accepted, kill floor armed, and save-level wrote a level whose gameBuildId is the empty string. The warning appeared once across all three reads in that run (steam-ready, load, save), which is the log-once criterion.

AC #3 deviation stated plainly: the AC asked to distinguish client-not-initialized from init-failed. What is shipped and observed distinguishes client-not-initialized from steam-not-running. The requested split is not observable through Steamworks.NET: in the stub's failed-init mode the client state is unavailable too, so it also reads client-not-initialized. Whether the env var reaches the game process, or the managed IsSteamRunning wrapper consults client state first, is unconfirmed and is recorded in docs/development.md as an open question.

A trap worth knowing when reproducing this: "[Steamworks.NET] SteamAPI_Init() failed." is not evidence that the original shim is active, because the line appears with the stub installed as well. Confirm with task steamstub:status.

Environment after the runs, verified: stub active, steam_api64.dll.steamstub.bak holding the untouched original, steam.exe restored at its original size, Saves tree byte-identical (six files), UserData/Levels back to its four pre-run entries with the probe level removed, and no game or Wine process left running.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Level load and save no longer depend on a working Steamworks client, so the mod runs on a machine with no Steam session and without the offline stub.

What changed: Steamworks.SteamApps.GetAppBuildId() is read through one guarded accessor. An uninitialized client, which is the normal case when the game could not initialize Steam, now reads as null instead of throwing InvalidOperationException out of InteropHelp.TestIfAvailableClient; the guard lives in a pure BuildIdSource so the null-on-unavailable, log-once and retry-dont-cache rules are covered by tests. A null build id means unknown everywhere it lands: GameBuildIdCheck.MismatchWarning returns null when either side is empty (matching GamePackVersionCheck) rather than claiming "the running game is build ''," and levels saved offline record an empty gameBuildId, which the same rule keeps from warning later. steam-ready gained a reason field, steam-not-running only when SteamAPI.IsSteamRunning() answers negatively and client-not-initialized otherwise, surfaced both in the mod log and on the run.py steam-ready line, which previously printed only done/rejected.

Tests: 2852 C# pass (15 new: seven BuildIdSource cases covering null-on-not-initialized, propagation of other faults, retry-until-available, log-once across repeated reads, no-notice-on-success, and caching after success; eight SteamReadiness cases for the null build id, both reasons, an unconsultable Steam-running probe, reason in ToJson, and IsNotInitialized matching); 1639 Python pass (two new for the printed verdict), no new warnings, task lint clean.

Verified live on the Windows build under Wine rather than only against the stub, which is what hid this bug: the stub answers CreateInterface, so every prior run had the client available. With the original shim and Steam unable to start, the log now shows GameBuildId: Steamworks is not initialized once, DevHarness: Steamworks not ready (steam-not-running), the game's own SteamAPI_Init() failed line, load-level accepted with the kill floor armed, and save-level writing gameBuildId ''. Both stub configurations load as before, so the guarded path and the stub path agree.

Docs: docs/development.md's offline-gate section carries the three-configuration matrix and the SteamAPI_Init() failed red herring; the stub section no longer says the load survives because CreateInterface answers; the harness section documents the reason field; docs/gamepadui.md's SteamAppId guidance now says the real consequence (no build id recorded) rather than the old rejection. Two claims the runs disproved were corrected on the way: the mod's UserData/Levels path is not the steamId-keyed tree (it is BepInEx Paths.GameRootPath, shared by all profiles), and steam-ready never targeted the game's SteamManager.IsInitialized.

Risks and follow-ups: levels authored offline carry an empty gameBuildId and so skip the stale-layout check even after being opened on a machine with Steam, which is intended but worth remembering if stale levels start circulating; the fresh-profile case (no saves_last_steamid key) remains unverified and looks like it begins a new progression; and the unexplained difference between the two not-ready reasons is left as an open question in the docs rather than guessed at.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
- [x] #5 The experiment leaves the shim, steam.exe and the Saves tree exactly as found, with no probe process still running
- [x] #6 No hostname, username or home path from the experiment appears in tracked files
<!-- DOD:END -->
