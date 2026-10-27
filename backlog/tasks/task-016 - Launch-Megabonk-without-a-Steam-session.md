---
id: TASK-016
title: Launch Megabonk without a Steam session
status: In Progress
assignee: []
created_date: '2026-10-27T05:56:00Z'
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
- [ ] #1 The game launches with Steam stopped and reaches the main menu without a quit loop (read `steam-ready` and `state` via the harness).
- [ ] #2 The failed-`SteamAPI.Init()` verdict is confirmed in a live run, and the exact degraded behaviour is recorded.
- [ ] #3 `load-level` starts a custom level with no logged-in Steam session, via the smallest working mechanism (local Steamworks stub/emulation, or natively if the client is truly optional).
- [ ] #4 A custom level saves and reloads with no logged-in Steam session (the `steamId 0` save path is verified).
- [ ] #5 The launch path (env vars, stub, flags) and the degraded/absent Steam features are documented in docs/development.md, plus the per-machine setup to reproduce it on a second Mac.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
