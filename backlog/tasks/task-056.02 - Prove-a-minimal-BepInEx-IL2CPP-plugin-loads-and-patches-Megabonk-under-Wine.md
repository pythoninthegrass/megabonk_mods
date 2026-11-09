---
id: TASK-056.02
title: Prove a minimal BepInEx IL2CPP plugin loads and patches Megabonk under Wine
status: Done
assignee: []
created_date: '2026-11-08T23:31:00Z'
updated_date: '2026-11-09 00:54'
labels:
  - bepinex
dependencies: []
references:
  - 'https://github.com/BepInEx/BepInEx'
  - 'https://docs.bepinex.dev/articles/dev_guide/plugin_tutorial/index.html'
parent_task_id: TASK-056
priority: medium
ordinal: 1200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Before committing to the port, prove the runtime model: a BepInEx 6 IL2CPP BasePlugin plus a per-frame tick component loads in Megabonk, logs, and one small Harmony patch applies against BepInEx-generated interop assemblies. This retires the port's biggest technical risk in a scratch project without touching the main mod source or the working MelonLoader setup. Timebox: one working session; ends with a recorded go/no-go.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A scratch plugin project separate from the main mod source builds against BepInEx 6 IL2CPP references and the game's interop assemblies
- [x] #2 The plugin loads: its startup lines appear in BepInEx/LogOutput.log during a launch of the Windows build under Wine
- [x] #3 A per-frame tick callback demonstrably runs (repeated log lines) and one small Harmony patch on a game method applies without breaking the game
- [x] #4 The MelonLoader launch still works afterward (loaders coexist or BepInEx is disabled per the rollback manifest; state recorded)
- [x] #5 Go/no-go decision recorded on this task within the timebox of one working session
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
State verified: game dir (CrossOver bottle) is BepInEx-active (winhttp.dll + doorstop_config.ini live, version.dll parked as version.dll.bak); BepInEx/interop assemblies already generated. Work continues on branch bepinex-spike (off main per parent rollback strategy).
1. Scratch project spikes/bepinex-boot/ separate from src/: net6.0 csproj referencing BepInEx/core (BepInEx.Core.dll, BepInEx.Unity.IL2CPP.dll, 0Harmony.dll, Il2CppInterop.Runtime.dll) and BepInEx/interop (Assembly-CSharp.dll, Il2Cppmscorlib.dll, UnityEngine.CoreModule.dll, ...) with Private=False; path derivation mirrors src Directory.Build.props (MEGABONK_GAME_DIR env). Copy target deploys to BepInEx/plugins/BepInExBootSpike/ on build.
2. Plugin code (3 small files): BasePlugin subclass whose Load() logs startup lines and applies Harmony via CreateAndPatchAll; per-frame tick component registered with ClassInjector.RegisterTypeInIl2Cpp and spawned on a DontDestroyOnLoad GameObject, logging throttled ~once/5s; one benign Harmony prefix on a small game method chosen from .tools/il2cpp_dump/dump.cs, guarded to log once.
3. Verify AC #2/#3: dotnet build, confirm DLL in BepInEx/plugins, launch via task game:run (winhttp override already in bottle user.reg from 056.01), read BepInEx/LogOutput.log + ErrorLog.log for startup lines, repeated tick lines, patch-applied line, no exceptions, game process alive. Quit game.
4. Restore MelonLoader per rollback manifest (AC #4): rename winhttp.dll/doorstop_config.ini out, version.dll.bak back to version.dll, relaunch via run.py load + editor on, confirm DevHarness: enabled / EditorMode: entered in Latest.log. BepInEx stays installed but disabled; final state recorded.
5. Record (AC #5): findings appended to task notes, go/no-go decision recorded, short 'developing a plugin' subsection added to docs/development.md 'Running BepInEx under Wine', conventional commit(s) on bepinex-spike.
Risks: Il2CppInterop version coupling (reference only BepInEx core + BepInEx-generated interop, never MelonLoader's); injected-MonoBehaviour registration is the top crash risk - fallback is proving the tick via a Harmony prefix on an already-per-frame game method; timebox one session, record findings either way.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-08 Spike closed GO for the BepInEx IL2CPP runtime model. Scratch plugin at spikes/bepinex-boot/ (commit 1889a19); docs in docs/development.md under 'Developing a BepInEx plugin'.
- Build (AC #1): net6.0 library referencing only the game dir's BepInEx/core (BepInEx.Core, BepInEx.Unity.IL2CPP, 0Harmony, Il2CppInterop.Runtime) and BepInEx/interop (Assembly-CSharp, Il2Cppmscorlib, UnityEngine.CoreModule), all Private=False, no NuGet packages; builds in ~2s with the repo dotnet.
- Load (AC #2): 'Loading [BepInEx Boot Spike 0.1.0]', plugin Load() lines, 'Registered mono type BepInExBootSpike.SpikeTick in il2cpp domain' and 'Chainloader startup complete' in BepInEx/LogOutput.log; ErrorLog.log empty.
- Tick + patch (AC #3): BasePlugin.AddComponent<T>() auto-registers the injected MonoBehaviour (IntPtr ctor only, no manual ClassInjector.RegisterTypeInIl2Cpp call needed); tick logged every 5s from chainloader start (16+ lines in one run); [HarmonyPatch(typeof(MainMenu), "Awake")] via Harmony.CreateAndPatchAll fired when the menu opened; screenshot shows the game in normal gameplay with the patch applied.
- Environment gotchas: with Steam down, SteamAPI_Init() fails as a Unity error line but the game still boots to the menu and into a run - it is not a mod failure. run.py quit works in BepInEx runs but ends in force-kill (the dev harness is MelonLoader-only, port planned with the harness rework).
- Coexistence (AC #4): BepInEx disabled state = winhttp.dll and doorstop_config.ini renamed to .bak, version.dll.bak restored to version.dll; MelonLoader relaunch then verified end to end (DevHarness: enabled, Steamworks ready, EditorMode: entered, KillFloor: armed). Flip back to BepInEx is the two renames; the spike plugin stays deployed under BepInEx/plugins/BepInExBootSpike/ (inert while the doorstop is disabled).
- GO decision (AC #5): the port can proceed on this runtime model; the reference set, injection pattern and Harmony behavior for the runtime port are proven. Findings for the sure-thing tasks: reference only BepInEx core + BepInEx-generated interop (never MelonLoader's interop copies); deploy one folder per mod under BepInEx/plugins/; BasePlugin.AddComponent is the tick registration path.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Proved the BepInEx 6 IL2CPP runtime model in Megabonk under plain Wine, closing the migration's biggest technical risk with a GO decision.
What changed: new scratch project spikes/bepinex-boot/ (separate from src/): BasePlugin plugin with Load() logging, a per-frame tick MonoBehaviour added via BasePlugin.AddComponent<T> (auto class injection), and a Harmony prefix on MainMenu.Awake built against BepInEx-generated interop; build deploys to BepInEx/plugins/BepInExBootSpike/. docs/development.md gained a 'Developing a BepInEx plugin' subsection (reference set, injection pattern, deploy layout, no-harness verification, Steamworks-offline gotcha).
Verification: task scripts:test 1158 passed (no Python changes); in-game - plugin load lines, repeating tick lines, patch-applied line and 'Chainloader startup complete' in BepInEx/LogOutput.log, ErrorLog.log empty, OS screenshot of normal gameplay, then the MelonLoader launch restored and verified end to end via relaunch (DevHarness: enabled, EditorMode: entered, KillFloor: armed).
Result: GO for porting the mod runtime to BepInEx. No testable logic to unit-test in a spike; no main-branch changes (branch bepinex-spike).
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
