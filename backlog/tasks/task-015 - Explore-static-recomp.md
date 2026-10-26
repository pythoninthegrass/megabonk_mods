---
id: TASK-015
title: Explore static recomp of GameAssembly.dll
status: To Do
assignee: []
created_date: '2026-10-23T17:43:00Z'
labels:
  - research
  - native
dependencies: []
references:
  - docs/development.md
  - src/MegabonkLevels.Mod/dev_harness.cs
priority: low
type: research
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

## Exploration Notes (AC 1–4)
<!-- SECTION:NOTES:BEGIN -->
Findings from initial exploration. The mod source is `src/MegabonkLevels.Mod/` (net6.0, ~14k lines), all interop is through MelonLoader + Il2CppInterop; the game dump is `.tools/il2cpp_dump/dump.cs` (114,472 methods across 58 images, `Image 3: Assembly-CSharp.dll`).

**AC 1 — Entry point.** The mod is a MelonLoader plugin: `megabonk_levels_mod.cs` carries `[assembly: MelonGame("", "Megabonk")]` and `[assembly: MelonInfo(...)]`, and `MelonMod.OnInitializeMelon()` is the hook. MelonLoader's Il2Cpp bootstrap loads `MelonLoader/Il2CppAssemblies/*.dll` stubs and a set of `version.dll` overrides (see `launch_game.py`: `version=n,b;d3d11,d3d10core=n,b`). A recomp's first call back into the game therefore has two candidate entry points: (a) a `version.dll`/`game.dll` proxy that MelonLoader already uses, or (b) the native executable's own import table. Either way the first managed call must be a Unity/Mono/Ill2Cpp entry (`Il2CppSystem.Reflection.Assembly.LoadFrom` or a game `dllmain`-style hook) to resolve types — there is no "just call the game's main" without the runtime. The recomp would need to either embed a minimal runtime or bind the game's existing runtime by symbol from the patched executable.

**AC 2 — Interop surface.** The mod binds ~18,200 types. Concrete dependencies seen in source: `Il2Cpp` (root namespace), `Il2CppAssets.Scripts.*` (Managers, Actors/Player, Steam, MapGeneration/ProceduralTiles, Game/Other), `Il2CppTMPro`, `Il2Cppcom.rlabrecque.steamworks.net` (SteamApps.GetAppBuildId), `Il2CppSystem.Action`, `Il2CppSystem.Collections.Generic.List<GameObject>`, `Il2CppReferenceArray<T>`, `Il2CppConsistentRandom`. It already mirrors the game's `EMap` flags enum by value (`level_file.cs`) and the dump confirms methods carry `// RVA: 0x... Offset: 0x... VA: 0x18...` (VA = image base + RVA). The interop surface is not just game code — it spans every Unity module (Core, Physics, ParticleSystem, UI, IMGUI, TextCore, etc.) plus Rewired, Discord, Newtonsoft, ProBuilder, Localization. A recomp must reproduce the Il2Cpp reflection/marshalling layer (IL2CPPLauncher-style type resolution, delegate marshalling, Il2CppString) or the mod code cannot bind. This is the single largest chunk — it is essentially reimplementing the il2cpp runtime's managed/native bridge.

**AC 3 — Steamworks.** The game already initializes Steam itself before mod code runs (`steam-ready: done` after retries). The mod's only Steam coupling is `Il2CppSteamworks.SteamApps.GetAppBuildId()` in `game_build_id_patch.cs`, called from the harness `SteamReady` case with no guard — that is exactly the `InvalidOperationException: Steamworks is not initialized` trace in the repro. The game tolerates a missing Steamworks client (it retries and proceeds), so a recomp does not need to fully reimplement Steam: the first step is to confirm whether the game calls Steam at startup in a way that hard-fails when the client is absent, or only lazily (as GetAppBuildId does). The non-throwing readiness probe would be `SteamClient.IsValid()` / `SteamAPI.IsSteamRunning()` (from `com.rlabrecque.steamworks.net`) instead of calling `GetAppBuildId()` blind. The trace in the repro is NOT the editor-close trace (AC 1 of TASK-014); it is the startup Steamworks one, and the editor opened cleanly (`editor: done`) with no close trace captured.

**AC 4 — Build/relink.** The mod builds to `MegabonkLevels.Mod.dll` + `.pdb`, deployed to `$(GameFolder)/Mods/` by the csproj `CopyOutputToModsFolder` target; it references `MelonLoader.dll`, `0Harmony.dll`, `Il2CppInterop.Runtime.dll`, and the Il2Cpp stub assemblies as `<Reference>` (not copied, `<Private>False`). A recomp's output shape is open: (a) a plain DLL that the recomp'd executable loads via its import table, (b) a proxy `version.dll` (the existing MelonLoader entry point, but that is MelonLoader, not a recomp), or (c) a patched executable. The linking question is decisive: a recomp must link against the game's native runtime (IL2CPPLauncher + Unity native). If it links the game's own runtime, it is a DLL that must be loaded by the patched exe; if it bundles a runtime, it is effectively a redistributable. Net: the recomp is a native DLL (or patched exe), not a managed assembly, and the runtime-linking decision gates everything.

**Effort / de-risking.** The interop/runtime bridge is the make-or-break; everything else (per-function reconstruction) is tedious but bounded. Smallest first step: confirm the game's startup Steamworks behavior under a recomp — does a non-Steam launch hard-fail, or is Steam lazy? That determines whether AC 3 is a weekend task or a blocker. Second: confirm the recomp can bind the game runtime by symbol (native call into `Assembly-CSharp`) with a single "hello world" function decompiled from `dump.cs`.
<!-- SECTION:NOTES:END -->
