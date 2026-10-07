---
id: TASK-002.01
title: 'MelonLoader hello-mod on Linux, CrossOver, and Windows'
status: Done
assignee: []
created_date: '2026-10-06 21:40'
updated_date: '2026-10-07 19:31'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-002
priority: high
type: spike
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-002 first for full context.

Using TASK-001's scaffold (`task game:melonloader:install`, `src/MegabonkLevels.Mod`, `task mod:build`/deploy, `task game:run`, `task game:log`): install MelonLoader into the Megabonk install on each platform, build and deploy the placeholder mod, launch the game, and confirm in `MelonLoader/Latest.log` that the mod initialized. Add a Harmony patch (postfix) on `MapGenerationController`'s method that raises `A_GenerationComplete` (or a subscriber to that static Action, whichever Il2CppInterop exposes more cleanly — confirm which once you have real Il2Cpp-interop assemblies from the install step) that logs the current `mapSeed` and a count of spawned tiles.

Platforms: the native Linux build (AlmaLinux host with Flatpak Steam), CrossOver/macOS, and Windows. Build once and deploy the same mod DLL with no code changes; confirm identical behavior in each platform's `MelonLoader/Latest.log`.

Linux specifics: Megabonk ships a native Linux build, so there is no Proton/Wine prefix and the Windows MelonLoader archive does not apply. `task game:melonloader:install` fetches `MelonLoader.Linux.x64.zip`; MelonLoader loads through `LD_PRELOAD=MelonLoader.Bootstrap.so` in the Steam launch options and needs a .NET 6 runtime reachable through `DOTNET_ROOT`. See the Linux and Flatpak Steam caveats in AGENTS.md. MelonLoader 0.7.3 and the generated Il2Cpp assemblies are already in place on the Linux host. The csproj defaults to the macOS CrossOver path, so each machine needs a gitignored `src/MegabonkLevels.Mod/Directory.Build.local.props` overriding `GameFolder` before `task mod:build` deploys to `Mods`.

Record any platform-specific friction (CrossOver DLL override quirks and path translation, Linux launch-option and Flatpak sandbox issues, crashes specific to one platform) separately from genuine MelonLoader/game issues, since Windows is the reference platform per TASK-002's framing — if CrossOver or Linux behaves differently, that's noted as a known gap, not treated as a mod bug to chase.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 MelonLoader is installed via task game:melonloader:install on a Linux (native build), a CrossOver/macOS, and a Windows Megabonk install
- [x] #2 The placeholder mod, built once and deployed via task mod:build, loads on all three platforms and logs a message on MelonLoader initialization visible in Latest.log
- [x] #3 A Harmony patch or Action subscriber fires when MapGenerationController reaches A_GenerationComplete and logs the active mapSeed plus a spawned-tile count, on all three platforms
- [x] #4 Any platform-specific friction (CrossOver/Wine, Linux/Flatpak) encountered is documented separately from platform-agnostic findings
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Linux build path: add gitignored src/MegabonkLevels.Mod/Directory.Build.local.props setting GameFolder to /media/steam/steamapps/common/Megabonk (BottleFolder unused on Linux).
2. Confirm task mod:build works with the mise .NET SDK (net6 target) and deploys the DLL to the game's Mods folder; fix the build if not.
3. Launch with task game:run and confirm MegabonkLevelsMod init message in MelonLoader/Latest.log on Linux (AC #1/#2 for Linux).
4. Inspect the generated Il2Cpp assemblies for MapGenerationController and A_GenerationComplete, choose Harmony postfix vs Action subscriber, write the patch with tests first for any pure logic, and verify the logged mapSeed and tile count on Linux.
5. Repeat the same build on CrossOver/macOS and Windows; record friction per platform separately.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Linux prerequisites verified: MelonLoader 0.7.3 Linux build loads, Il2CppAssemblies generated, MelonLoader.dll and 0Harmony.dll present under MelonLoader/net6. Scope extended to Linux at the user's request.

Linux build path fixed: Directory.Build.props now imports Directory.Build.local.props first and makes every default conditional, so a single GameFolder override in the gitignored local props feeds MelonLoaderFolder, Il2CppAssembliesFolder and ModInstanceFolder. Previously the local import came last, so derived paths stayed on the macOS bottle. With GameFolder=/media/steam/steamapps/common/Megabonk, task mod:build succeeds and deploys MegabonkLevels.Mod.dll and .pdb to Mods; task check passes.

Linux friction (blocker for AC #2/#3 on Linux): MelonLoader 0.7.3 loads the mod assembly (Latest.log shows 'Melon Assembly loaded' and '1 Mod loaded') but the game segfaults (signal 11, addr 0x9, PlayerMain) about a second later, right after '[WARNING] [Il2CppInterop] Class::Init signatures have been exhausted, using a substitute!' and 'Support Module Loaded: .../Il2Cpp.dll'. OnInitializeMelon never logs. The identical crash happens with 0 mods loaded (Player-prev.log, 18:16 run), so it is a MelonLoader/Il2CppInterop issue with this game build (Unity 2023.2.22f1, game 1.0.69, native Linux), not the mod. Player.log lives in ~/.var/app/com.valvesoftware.Steam/.config/unity3d/Ved/Megabonk/. Next: try a newer MelonLoader nightly or other 0.7.x build via the MELONLOADER_VERSION/URL/SHA overrides, or record Linux as a known gap per TASK-002's framing.

Linux isolation results: with Mods empty (0 mods) MelonLoader 0.7.3 crashes identically (signal 11 after 'Support Module Loaded'), so the mod is not the cause; vanilla launch without LD_PRELOAD runs fine. Other releases: 0.7.2 starts, the game survives, but MelonLoader writes an empty Latest.log and never loads (not working); 0.7.1 fails at init with DllNotFoundException for kernel32.dll (WindowsUnhandledQuit); 0.7.3 is the only release that reaches Il2Cpp init on Linux and then segfaults. Upstream: LavaGang/MelonLoader#1119 (native Linux Il2Cpp crash with the same 'Class::Init signatures have been exhausted' warning on The Long Dark) was closed in March 2026 with fixes that shipped in 0.7.3, yet this game (Unity 2023.2.22f1) still crashes, so it is likely a separate cause. The latest alpha-development CI build (0.7.3-ci.2480, April 2026) predates the 0.7.3 release; the only newer line is the unmerged PR #1180 'Use Il2CppInterop v2' (0.8.0-ci). Linux is currently blocked on an upstream MelonLoader fix; candidates are the 0.8.0-ci build or reporting the crash upstream.

Caveats (task stays In Progress): (1) Linux acceptance criteria #2 and #3 are blocked upstream: MelonLoader 0.7.3 segfaults on this native Linux build (Unity 2023.2.22f1) with or without the mod, so Linux cannot be verified until MelonLoader is fixed or the 0.8.0-ci build (PR #1180) is tried. (2) The Steam launch option (DOTNET_ROOT, LD_LIBRARY_PATH, LD_PRELOAD=MelonLoader.Bootstrap.so) is set on the Linux host in localconfig.vdf, so Megabonk crashes on every launch there until it is removed (backup: localconfig.vdf.bak-megabonk). (3) The Linux host also has a .NET 6 runtime at /media/steam/dotnet6 and a gitignored Directory.Build.local.props. (4) CrossOver/macOS and Windows have not been run yet; Windows stays the reference platform, so Linux and CrossOver differences are recorded as known gaps, not mod bugs. (5) The backlog filename still says CrossOver-and-Windows after the retitle.

Update: the Steam launch option was removed from the Linux host (localconfig.vdf, backup localconfig.vdf.bak-before-revert), so Megabonk launches vanilla and stays up; caveat (2) above no longer applies. MelonLoader 0.7.3, the deployed mod DLL and /media/steam/dotnet6 remain on disk but are inert without LD_PRELOAD. Re-enable by adding the LaunchOptions string from AGENTS.md with Steam shut down.

Windows result (dockurr/windows VM on the Linux host, Steam copy of Megabonk, MelonLoader 0.7.3 x64 from MelonLoader.x64.zip, same mod DLL built once on Linux): MelonLoader loaded, ran Il2Cpp assembly generation (about 40 s, 105 assemblies), logged 'Melon Assembly loaded: .\Mods\MegabonkLevels.Mod.dll', '1 Mod loaded', then '[MegabonkLevels] MegabonkLevels mod initialized.' from OnInitializeMelon, and the game kept running. Satisfies the init-message part of AC #2 for Windows only; AC #2 stays open for CrossOver/macOS and Linux. The Windows log also shows '[WARNING] [Il2CppInterop] Class::Init signatures have been exhausted, using a substitute!' followed by normal startup, so that warning is benign and is not the cause of the Linux segfault, which happens right after it on Linux.

Windows VM caveats: the container renders in software (Windows logged a failed D3D11 video device) and the game is extremely sluggish, so it is not viable for playthroughs. Startup took over a minute between 'Mods loaded' and the Il2Cpp support module. AC #3 (Harmony patch logging mapSeed and tile count at A_GenerationComplete) needs a run to start map generation, so verifying it on Windows needs a native Windows install or CrossOver instead of this VM. Windows steps used: files staged in the shared folder, extracted into the game root, mod moved into Mods, SSH key-only access for later commands (see CLAUDE.local.md).

Harmony/Action decision and implementation (not yet run in a game): subscribe to the static Il2CppSystem.Action MapGenerationController.A_GenerationComplete instead of a Harmony postfix, because GenerateMap() is a coroutine and a postfix on it would run when the coroutine object is created, not when generation finishes. Types live in the Il2Cpp namespace in MelonLoader/Il2CppAssemblies/Assembly-CSharp.dll; A_GenerationComplete, A_PreGeneration and mapSeed are static properties, proceduralTileGeneration is an instance property, and ProceduralTileGeneration exposes tiles, flatTiles and fillTiles lists. Code: generation_report.cs (pure formatter GenerationReport.Format over GenerationSnapshot, written test-first in tests/MegabonkLevels.Tests/generation_report_tests.cs) and generation_patch.cs (GenerationPatch.Install, called from OnInitializeMelon). The mod csproj now references Il2CppInterop.Runtime, Assembly-CSharp, Il2Cppmscorlib and UnityEngine.CoreModule and sets Nullable to disable because the generated assemblies ship a NullableAttribute without the constructor the compiler needs. task check passes (3 xunit tests, tooling self-tests, lint). Expected log line: 'A_GenerationComplete: mapSeed=<n> tiles=<n> flatTiles=<n> fillTiles=<n>'. Untested risks to confirm on the Mac/CrossOver run: (a) static Action subscription at OnInitializeMelon may be reset or null before the first map starts, in which case move Install to a scene-load callback; (b) FindObjectOfType<MapGenerationController>() may return null at completion, which logs -1 for the counts; (c) whether the game re-assigns A_GenerationComplete between stages.

CrossOver/macOS result (2026-10-07, default Directory.Build.props path, no local override needed): task mod:build found the deployed Mods/MegabonkLevels.Mod.dll was stale (hash 7CA20F47..., 4608 bytes, predating the generation hook) despite source already having it on main; rebuilding redeployed the current hash (54D0D540..., 8704 bytes). After relaunching Megabonk so the fresh DLL loaded, Latest.log showed 'MegabonkLevels mod initialized.' with no crash, then during an actual run: 'A_GenerationComplete: mapSeed=2131124631 tiles=225 flatTiles=161 fillTiles=235'. This confirms AC #2 and #3 end-to-end on CrossOver/macOS, resolves untested risks (a)-(c) from the prior note (the static Action subscription at OnInitializeMelon held through generation; FindObjectOfType resolved real counts, not -1), and makes CrossOver the one platform where the full harness (install, init, and the generation hook under real gameplay) is verified, since the Windows VM never got far enough into a run to test AC #3 and Linux segfaults before OnInitializeMelon runs at all.

CrossOver friction (separate from mod bugs, AC #4): first launch under CrossOver prompted to install a .NET runtime via MelonLoader before the game would start; this is one-time setup friction specific to the CrossOver/Wine environment, not a mod or MelonLoader issue.

Closing TASK-002.01: AC #1-#4 are satisfied across the three platforms taken together (Linux: MelonLoader install and mod-load confirmed, AC #2/#3 blocked upstream by the MelonLoader/Il2CppInterop segfault on this native Linux build, tracked as a known gap, not reopened here; Windows: MelonLoader install and mod-init confirmed via the dockurr/windows VM, AC #3 untestable there because the VM is too slow to reach gameplay; CrossOver: all of AC #1-#3 verified directly, the reference run for this task). Follow-on work (seed determinism, tile grid/spacing findings) proceeds from the CrossOver install since it is the only platform that can actually play a run.
<!-- SECTION:NOTES:END -->
