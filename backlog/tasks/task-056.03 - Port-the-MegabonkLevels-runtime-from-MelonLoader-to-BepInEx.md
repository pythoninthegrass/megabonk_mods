---
id: TASK-056.03
title: Port the MegabonkLevels runtime from MelonLoader to BepInEx
status: Done
assignee: []
created_date: '2026-11-08T23:31:00Z'
updated_date: '2026-11-09 01:16'
labels:
  - bepinex
dependencies:
  - TASK-056.02
modified_files:
  - src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj
  - src/MegabonkLevels.Mod/megabonk_levels_mod.cs
parent_task_id: TASK-056
priority: high
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The spikes proved BepInEx loads and patches Megabonk; the mod source itself still targets MelonLoader everywhere (MelonMod lifecycle, MelonLogger, MelonCoroutines, MelonEnvironment paths). Until the runtime is ported, no harness or packaging work is useful. All work happens off main so main keeps building the MelonLoader version until cutover, per the parent's rollback strategy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The mod initializes under BepInEx (BasePlugin.Load) and no MelonLoader types remain in src/MegabonkLevels.Mod (logging, coroutines, environment paths, lifecycle all replaced)
- [x] #2 Per-frame behavior runs through an interop-registered Unity component ticked by the plugin
- [x] #3 All existing Harmony patches behave as before on the smoke path: relaunch, example-forest load, editor on
- [x] #4 The csproj references BepInEx and interop assemblies and builds cleanly, with NLayer and other copy-local dependencies landing in the correct BepInEx folder on build
- [x] #5 The F6 test-level load and the console overlay still work in-game
- [x] #6 Loader-related docs (docs/development.md and any loader-specific docs) are updated for BepInEx
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approved by maintainer: proceed with runtime port and direct BepInEx log smoke verification, leaving run.py relaunch/log-path migration to TASK-056.04.
1. Branch bepinex-port from bepinex-spike; keep main untouched and preserve reversible loader installation.
2. Replace MelonMod entry with BasePlugin.Load, explicit assembly Harmony patching, and AddComponent tick with Update/LateUpdate and shutdown cleanup. Replace logger, environment paths and two coroutine starts with mod-owned adapters backed by BepInEx/Unity. Preserve UserData and harness locations; F6 file beside plugin.
3. Switch csproj/props to BepInEx core + generated interop only; deploy plugin, symbols and NLayer to BepInEx/plugins/MegabonkLevels. Resolve generated namespace/file-name differences.
4. Write tests first for testable new path/adapter logic; run focused tests, C# suite, Python suite and task check.
5. Activate BepInEx reversibly and verify startup, example-forest load/editor, screenshot coroutine, F6, console and music dependency resolution through harness queue and direct LogOutput.log reads. Record final loader state.
6. Update developer loader/build docs; leave installer/packaging and script-path rework for subsequent subtasks. Commit conventionally without attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented on bepinex-port (branched from bepinex-spike), main untouched. BasePlugin.Load installs subsystem loggers and explicitly patches the assembly; AddComponent<ModTick> runs Update/LateUpdate and application-quit music cleanup. BepInEx's built-in WrapToIl2Cpp adapter hosts both existing coroutines via Unity StartCoroutine; no custom scheduler needed. Replaced loader logging with ModLogger and environment paths with ModPaths; generated namespace/file-name differences resolved against BepInEx-only interop. Copy-local deployment contains plugin DLL/PDB and NLayer in BepInEx/plugins/MegabonkLevels.

Tests: new content-path test first failed on missing implementation, then passed. Final task check passed (build, installer checks, 2781 C# tests, 1158 Python tests, markdownlint and ruff). Mod build has zero warnings/errors; existing nullable warnings remain in the test project. git diff --check passes.

Runtime verification: clean BepInEx boots under plain Wine using existing bottle prefix; registered ModTick, plugin initialization and chainloader completion logged with no plugin errors (offline SteamAPI_Init error is unchanged). Example-forest harness load produced generation reports, KillFloor: armed and editor entry; editor/palette rendered. End-of-frame screenshot succeeds through BepInEx's coroutine adapter. Console toggle, rendered history/help and music.list work; MP3 probe decode resolved NLayer beside plugin and produced 44100Hz stereo, 12789504 samples, peak 1.0414. Fresh launch plus injected F6 starts Forest from the newly staged example fixture beside the plugin. Evidence in gitignored .tools/evidence/bepinex-port-*.png and bepinex-port-f6.log.

Rollback verified during this task: quit, park winhttp.dll/doorstop_config.ini as .bak and restore version.dll, then existing MelonLoader DLL completed run.py relaunch/load/editor smoke. Its screenshot also shows the lingering startup cover seen on the no-playerStart example fixture under BepInEx; not a new port regression. No unrelated startup-gate changes made. Final state restored to BepInEx: winhttp.dll and doorstop_config.ini active, version.dll.bak parked; original MelonLoader DLL and configuration retained. Game left in example-forest editor with spawns off and invulnerability enabled for safe review. F6 example fixture intentionally remains beside plugin. Script log scraping/relaunch and packaging remain subsequent tasks, per approved scope.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Ported MegabonkLevels from MelonLoader to BepInEx 6 IL2CPP on isolated branch bepinex-port (runtime commit bf84dc4); main remains unchanged. BasePlugin.Load initializes the mod and explicitly installs all assembly Harmony patches. AddComponent<ModTick> preserves per-frame update order, late camera override and quit cleanup; BepInEx's coroutine adapter preserves Unity yield semantics. Logging and content paths are loader-independent wrappers; content/harness locations remain compatible, while F6 now reads beside the plugin. References use BepInEx/core and BepInEx/interop only; build deploys plugin/PDB and copy-local NLayer into BepInEx/plugins/MegabonkLevels. Updated developer/build, F6 and music documentation and added a test-first content-path regression test.
Verification: task check passed (2781 C# tests, 1158 Python tests, installer checks and lint); mod builds with zero warnings/errors. In-game verified plugin boot, generation patches/example-forest/editor, palette, end-of-frame screenshots, F6, console render/help/music commands and real MP3 decode/NLayer resolution. Restored and successfully relaunched MelonLoader as a rollback check, then restored BepInEx. The example fixture's lingering startup cover also reproduces on the unmodified MelonLoader DLL; no unrelated fix included. Final game state is BepInEx-active in editor with spawns off/invulnerability for safe review. Script log/relaunch migration remains TASK-056.04, per explicit approval; packaging remains TASK-056.05.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
