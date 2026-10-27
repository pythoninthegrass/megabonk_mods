---
id: TASK-015
title: Explore static recomp of GameAssembly.dll
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-23T17:43:00Z'
updated_date: '2026-10-27T05:40:00Z'
labels:
  - research
  - native
dependencies: []
references:
  - docs/development.md
  - src/MegabonkLevels.Mod/dev_harness.cs
  - 'https://github.com/LoreanXavier/pt-pc'
priority: low
ordinal: 65000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The mod currently runs inside the game through MelonLoader, which loads the mod DLL into the Il2Cpp runtime. This task explores whether the game code could be statically recompiled into a separate native library instead, so the mod could run without Steam or MelonLoader.

A static recomp of `GameAssembly.dll` is a large lift (114,472 methods, ~18,200 types, 52 MB x86-64). Ghidra auto-analysis of the binary already takes ~12 minutes per REA session. REA (`/morluto/rea`) is an analysis CLI/MCP that decompiles and traces, but it does not emit compilable source — reconstruction is still hand-authored.

This task is an exploration, not an implementation. The goal is to produce a concrete feasibility assessment and a recommended path, not to ship a recomp.
<!-- SECTION:DESCRIPTION:END -->

## Background

<!-- SECTION:BACKGROUND:BEGIN -->
- `GameAssembly.dll` is a Windows x86_64 il2Cpp assembly; the game ships a native Linux build, so a recomp buys no portability.
- The game tolerates a missing Steamworks client: `Steamworks.SteamApps.GetAppBuildId()` throws `InvalidOperationException: Steamworks is not initialized` under Wine, and the mod already retries through that failure.
- MelonLoader loads the mod DLL via `LD_PRELOAD` (Linux native) or a `version.dll` override (CrossOver); a recomp would need a proxy entry point and a way to bind the game's managed types.
<!-- SECTION:BACKGROUND:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The entry point is mapped: how a recomp would get control (`version.dll`/`game.dll` proxy, `dllmain`, or a hook into the native executable) and what the first call back into the game must be
- [ ] #2 The interop surface is scoped: which game types/methods the mod needs to bind (Il2Cpp reflection, `Il2CppSystem.Type`, delegate marshalling, `Il2CppString`), and whether they are reachable from a native library
- [ ] #3 The Steamworks question is resolved: whether the game's own code calls Steamworks at startup in a way a recomp must replicate or avoid, and what the non-throwing readiness probe would be
- [ ] #4 The build/relink question is resolved: whether the recomp would be a plain DLL, a plugin, or a patched executable, and how it links against the game's runtime
- [ ] #5 A written feasibility assessment in `docs/development.md` with a recommended path (recomp vs. keep MelonLoader vs. hybrid), rough effort, and the smallest first step to de-risk it
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Findings are concrete: named APIs, named files, named risks — not generalities
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Goals: native macOS support, and running several game copies at once across devices to speed up mod development. Work is static only (dump, binaries, Ghidra/REA, asset files) so it never contends for the single Steam session.

Facts established (read-only checks, 2026-10-26):
- Unity 2023.2.22f1 (`globalgamemanagers`). `GameAssembly.dll` 54.8 MB, `UnityPlayer.dll` 30.7 MB, both AMD64 PE. Linux build (`GameAssembly.so`, `UnityPlayer.so`) is on `mf`. No macOS build exists; the Mac runs the Windows build under CrossOver.
- libil2cpp is statically linked into `GameAssembly.dll`, which exports 240 `il2cpp_*` functions (`rabin2 -E`).
- `Assembly-CSharp` (TypeDefIndex 4606 to 5826): 1,221 types and 8,697 methods. 841 of them are the shared empty stub at RVA `0x3321E0`/`0x3321F0`, leaving about 7,850 real bodies. The other images (73 in total) are Unity modules and third-party packages.
- `SteamManager` (TypeDefIndex 4919): `[RuntimeInitializeOnLoadMethod] InitOnPlayMode` `0x18052AB30`, `Load` `0x18052AC00`, `IsInitialized` `0x18052ABB0`, `Update` `0x18052B310`, `.cctor` `0x18052B3B0`. Steamworks.NET exposes `SteamAPI.RestartAppIfNecessary`. There is no `steam_appid.txt` in the game dir.
- pt-pc is a reimplementation, not a static recomp. It ignores the eboot and rebuilds the logic in C++ on its own engine, reading the original assets at runtime. It is the model for route C below.

Gate 0: multi-copy depends on Steam, not macOS. Steam allows one session per account across all devices, so a native macOS build launched through Steam still conflicts. Several copies need either (1) the game running without a Steam session, which only counts if the game itself tolerates a failed `SteamAPI.Init()` and never calls `RestartAppIfNecessary`. Bypassing a Steam gate is out of scope. Or (2) separate accounts or licences. If (1) holds, several copies work today on CrossOver, Linux and the Windows VM, with no recomp.

Steps:
1. Probe A, Steam startup: open `GameAssembly.dll` in REA (`provider_id: "ghidra"`, try `.tools/GameAssembly/ghidra.rea-snapshot` first, otherwise about 12 minutes of analysis). Decompile the `SteamManager` methods above and resolve callees through `dump.cs` RVAs (VA - 0x180000000). Run `xrefs` on `SteamManager.IsInitialized` and `GetAppBuildId` to find menus, saves or loads that need Steam. Result: runs without Steam yes / no / degraded, with RVAs.
2. Probe B: read `forceSingleInstance` from `Megabonk_Data/globalgamemanagers` with UnityPy (`uv run --with unitypy`, read-only). This decides whether two copies can share one machine.
3. If macOS-native is still wanted, size three routes, each with effort order, main blocker, and cost per game update:
   A. Full static recomp (XenonRecomp style) of Linux `UnityPlayer.so` and `GameAssembly.so` (SysV ABI, Vulkan), plus a Linux-to-macOS shim (libc, windowing, Vulkan through MoltenVK). About 85 MB of x86-64; no maintained lifter produces rebuildable code at this scale (McSema archived, remill lifts but its output does not rebuild at this scale). Largest.
   B. Re-host GameAssembly only: translate Linux `GameAssembly.so` into a macOS x86-64 dylib (running under Rosetta) paired with Unity's official 2023.2.22f1 macOS player (icalls resolve by name; `global-metadata.dat` reused). Blockers: libil2cpp's Linux OS layer (Boehm GC thread suspension, signals) on macOS, and shaders. Shipped data has only DX11/12 or Vulkan/GL blobs, while macOS needs Metal (SPIR-V to MSL through SPIRV-Cross, repacked). Count shader variants with UnityPy.
   C. pt-pc-style reimplementation: AssetRipper export, reimplement the ~7,850 `Assembly-CSharp` bodies in C# from `dump.cs` and Ghidra pseudocode, add the packages (TMP, ProBuilder, Localization, Addressables, Splines, PostProcessing, AI Navigation, Steamworks.NET and Coffee.UIParticle are free or OSS; Rewired and MK.Toon are paid), and build for macOS. The mod becomes source in the project with no loader. Risk: behaviour drifting from the shipped game. Inventory what AssetRipper recovers (shaders are the weak spot).
4. Correct the notes below and `docs/development.md` "Static recomp": "IL2CPPLauncher" does not exist; the ~18,200 types are the game's, not the mod's; 73 images, with the Assembly-CSharp figures above; there is no separate runtime to embed; `SteamClient.IsValid()` is Facepunch API, while the game's probe is `SteamManager.IsInitialized()`; "tolerates a missing Steam client" is unproven until Probe A; "a recomp buys no portability" is wrong, since it buys macOS-native.
5. Write-up (AC 5) in `docs/development.md`: Gate 0, Probe A/B results, routes A/B/C with numbers, recommendation. Expected shape, pending the probes: if the game runs without Steam, multi-copy is solved now and macOS-native becomes a separate cost-benefit choice (B or C, A last). Propose rewording AC 1, 2 and 4 to "path to native macOS", since entry point and interop differ per route.
6. Create (don't start) follow-ups: "Launch Megabonk without a Steam session" (runtime check, once the Steam session is free), and a spike for the chosen macOS route (B: `GameAssembly.so` from `mf` + the 2023.2.22f1 macOS player + shader variant count; C: AssetRipper inventory).
7. Commit `docs:` / `docs(backlog):` with no attribution. Leave unrelated uncommitted work alone.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Probe B (2026-10-27): `Megabonk_Data/globalgamemanagers` PlayerSettings has `forceSingleInstance` False, `runInBackground` True. Unity itself does not block a second copy on one machine; only Steam's single session does. (UnityPy needs `--python 3.12`; the free-threaded 3.14t fails to build brotli. `parse_as_dict(check_read=False)` is needed: the PlayerSettings typetree reads 804 of 805 bytes.)

Probe A (Steam startup), 2026-10-27, static only (GameAssembly.dll in Ghidra via REA, callees resolved through dump.cs, RVA = VA - 0x180000000).

Verdict: degraded. The game's own code runs without Steam: a failed SteamAPI.Init() logs and continues, with no Application.Quit and no throw. Not run-time verified.

SteamManager statics (dump.cs): initialized +0x0, Instance +0x8, APP_ID +0x10 (cctor 0x52B3B0 sets 3405340, clears steamId), A_UpdateComponents +0x18, A_Initialized +0x20, steamId +0x28, A_PlayerInformationArrived +0x30.

Load (0x52AC00), in order:
1. UnityEngine.Object.op_Inequality(Instance, null) (0x22B3B70) true: Object.Destroy(gameObject) (0x22B1180, get_gameObject 0x22A7010), return (duplicate manager).
2. Instance = this. If `initialized` already set: throw (noreturn 0x2698D0), only on a second Load after a successful init.
3. Object.DontDestroyOnLoad (0x22B12C0). Packsize.Test() (0x5E9750) false: Debug.LogError(msg, this) (0x226F5B0). DllCheck.Test() (0x383DB0) false: Debug.LogError(msg, this). Both continue.
4. SteamAPI.RestartAppIfNecessary (0x5E63E0), the only call site in code is 0x18052ADF5 inside Load. Argument is AppId_t.Invalid (AppId_t TypeInfo static +0x0, i.e. 0), not SteamManager.APP_ID. A true result calls Debug.LogError(msg) (0x226F680) and returns: no Application.Quit, `initialized` stays false. Whether Steam returns false for an invalid id is not verified here.
5. initialized = SteamAPI.Init() (0x5EB1C0). False: Debug.LogError(msg, this) (0x226F5B0), return. No Quit, no throw, no retry; steamId stays 0 and InitComponents never runs.
6. True: InitComponents (0x52AA20) = SteamAchievementsManager.Init 0x3EB8C0, SteamStatsManager.Init 0x3EE690, SteamRichPresenceManager.Init 0x3ED850, SteamLeaderboardsManagerNew.Init 0x5288D0 (subscribes to A_UpdateComponents), then registers Callback<PersonaStateChange_t> -> OnPersonaStateChange 0x52B2A0. Then initialized = true, steamId = SteamUser.GetSteamID() (0x5F2A20), invoke A_Initialized if subscribed, LogInBuild (0x3E4EF0).

Other methods: InitOnPlayMode 0x52AB30 only resets statics (initialized false, Instance null). IsInitialized 0x52ABB0 returns the `initialized` byte, no side effects. Update 0x52B310: if initialized, SteamAPI.RunCallbacks (0x5EB1F0) then invoke A_UpdateComponents; otherwise nothing.

Callers of the flag. The compiler inlined IsInitialized: its only xrefs are two data addresses (0x182F20580, 0x183487788, method-table entries), so callers were found by xref on the SteamManager TypeInfo (0x182F88468) and named through dump.cs (nearest preceding method; names approximate):
- LanguageStartup.CheckSteamLanguage 0x569990 and SetSystemLanguage 0x56A9F0: not initialized skips the Steam language (SteamApps.GetCurrentGameLanguage 0x58ADE0), falls back. Degrades.
- PauseHandler.Start 0x5566C0 and DiscordRichPresence.RunStarted 0x4A8F60: the Steam parts (callback registration, GetServerRealTime 0x5F48F0) run only if initialized.
- VersionNumber.Start 0x52DF70 / OnDestroy 0x52DDA0: subscribe to and unsubscribe from A_Initialized. Chatbox.SendMessage 0x52EFA0: passes steamId to AppendMessage 0x52E960 (sender id 0 without Steam).
- SaveManager.Load(bool) 0x523C90: passes steamId to Load(ulong steamId, bool, out, out) 0x523E00. With Steam absent it uses steamId 0; whether that path finds the existing save is unverified.
- Leaderboards.UploadScore 0x3E2820, SteamLeaderboardNew.OnDownloadResultsFriends 0x3EC1B0, SteamStatsManager (Init, OnDestroy, OnUserStatsReceived), SteamLeaderboardsManagerNew (Init, OnDestroy), LeaderboardEntryUi Awake/OnDestroy 0x56AE60/0x56B000: Steam-only features.
No caller was found that blocks the main menu, level load or gameplay on initialized.

xrefs: Steamworks.NET SteamApps.GetAppBuildId (0x58A960) has only two data refs and no code callers. SteamAPI.IsSteamRunning (0x5E5F10) has only three data refs and no code callers. The game never uses either.

Non-throwing readiness probe for the mod: SteamManager.IsInitialized() (0x52ABB0, static bool). It reports the game's own Init result and cannot throw (class-init check, static read). SteamAPI.IsSteamRunning only reports whether a Steam client process exists, not whether Init succeeded, and the game does not call it.

Not covered: any DRM wrapper outside GameAssembly (UnityPlayer.dll, exe), what Steam returns for RestartAppIfNecessary(0), and the actual save path. Confirm in a live run once the Steam session is free.
<!-- SECTION:NOTES:END -->

## Exploration Notes (AC 1–4)
<!-- SECTION:NOTES:BEGIN -->
Findings from initial exploration. The mod source is `src/MegabonkLevels.Mod/` (net6.0, ~14k lines), all interop is through MelonLoader + Il2CppInterop; the game dump is `.tools/il2cpp_dump/dump.cs` (114,472 methods across 58 images, `Image 3: Assembly-CSharp.dll`).

**AC 1 — Entry point.** The mod is a MelonLoader plugin: `megabonk_levels_mod.cs` carries `[assembly: MelonGame("", "Megabonk")]` and `[assembly: MelonInfo(...)]`, and `MelonMod.OnInitializeMelon()` is the hook. MelonLoader's Il2Cpp bootstrap loads `MelonLoader/Il2CppAssemblies/*.dll` stubs and a set of `version.dll` overrides (see `launch_game.py`: `version=n,b;d3d11,d3d10core=n,b`). A recomp's first call back into the game therefore has two candidate entry points: (a) a `version.dll`/`game.dll` proxy that MelonLoader already uses, or (b) the native executable's own import table. Either way the first managed call must be a Unity/Mono/Ill2Cpp entry (`Il2CppSystem.Reflection.Assembly.LoadFrom` or a game `dllmain`-style hook) to resolve types — there is no "just call the game's main" without the runtime. The recomp would need to either embed a minimal runtime or bind the game's existing runtime by symbol from the patched executable.

**AC 2 — Interop surface.** The mod binds ~18,200 types. Concrete dependencies seen in source: `Il2Cpp` (root namespace), `Il2CppAssets.Scripts.*` (Managers, Actors/Player, Steam, MapGeneration/ProceduralTiles, Game/Other), `Il2CppTMPro`, `Il2Cppcom.rlabrecque.steamworks.net` (SteamApps.GetAppBuildId), `Il2CppSystem.Action`, `Il2CppSystem.Collections.Generic.List<GameObject>`, `Il2CppReferenceArray<T>`, `Il2CppConsistentRandom`. It already mirrors the game's `EMap` flags enum by value (`level_file.cs`) and the dump confirms methods carry `// RVA: 0x... Offset: 0x... VA: 0x18...` (VA = image base + RVA). The interop surface is not just game code — it spans every Unity module (Core, Physics, ParticleSystem, UI, IMGUI, TextCore, etc.) plus Rewired, Discord, Newtonsoft, ProBuilder, Localization. A recomp must reproduce the Il2Cpp reflection/marshalling layer (IL2CPPLauncher-style type resolution, delegate marshalling, Il2CppString) or the mod code cannot bind. This is the single largest chunk — it is essentially reimplementing the il2cpp runtime's managed/native bridge.

**AC 3 — Steamworks.** The game already initializes Steam itself before mod code runs (`steam-ready: done` after retries). The mod's only Steam coupling is `Il2CppSteamworks.SteamApps.GetAppBuildId()` in `game_build_id_patch.cs`, called from the harness `SteamReady` case with no guard — that is exactly the `InvalidOperationException: Steamworks is not initialized` trace in the repro. The game tolerates a missing Steamworks client (it retries and proceeds), so a recomp does not need to fully reimplement Steam: the first step is to confirm whether the game calls Steam at startup in a way that hard-fails when the client is absent, or only lazily (as GetAppBuildId does). The non-throwing readiness probe would be `SteamClient.IsValid()` / `SteamAPI.IsSteamRunning()` (from `com.rlabrecque.steamworks.net`) instead of calling `GetAppBuildId()` blind. The trace in the repro is NOT the editor-close trace (AC 1 of TASK-014); it is the startup Steamworks one, and the editor opened cleanly (`editor: done`) with no close trace captured.

**AC 4 — Build/relink.** The mod builds to `MegabonkLevels.Mod.dll` + `.pdb`, deployed to `$(GameFolder)/Mods/` by the csproj `CopyOutputToModsFolder` target; it references `MelonLoader.dll`, `0Harmony.dll`, `Il2CppInterop.Runtime.dll`, and the Il2Cpp stub assemblies as `<Reference>` (not copied, `<Private>False`). A recomp's output shape is open: (a) a plain DLL that the recomp'd executable loads via its import table, (b) a proxy `version.dll` (the existing MelonLoader entry point, but that is MelonLoader, not a recomp), or (c) a patched executable. The linking question is decisive: a recomp must link against the game's native runtime (IL2CPPLauncher + Unity native). If it links the game's own runtime, it is a DLL that must be loaded by the patched exe; if it bundles a runtime, it is effectively a redistributable. Net: the recomp is a native DLL (or patched exe), not a managed assembly, and the runtime-linking decision gates everything.

**Effort / de-risking.** The interop/runtime bridge is the make-or-break; everything else (per-function reconstruction) is tedious but bounded. Smallest first step: confirm the game's startup Steamworks behavior under a recomp — does a non-Steam launch hard-fail, or is Steam lazy? That determines whether AC 3 is a weekend task or a blocker. Second: confirm the recomp can bind the game runtime by symbol (native call into `Assembly-CSharp`) with a single "hello world" function decompiled from `dump.cs`.
<!-- SECTION:NOTES:END -->
