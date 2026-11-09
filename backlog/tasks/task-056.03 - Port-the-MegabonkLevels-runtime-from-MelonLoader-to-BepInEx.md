---
id: TASK-056.03
title: Port the MegabonkLevels runtime from MelonLoader to BepInEx
status: To Do
assignee: []
created_date: '2026-11-08T23:31:00Z'
labels:
  - bepinex
dependencies:
  - TASK-056.02
modified_files:
  - src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj
  - src/MegabonkLevels.Mod/megabonk_levels_mod.cs
parent_task_id: TASK-056
priority: high
type: feature
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The spikes proved BepInEx loads and patches Megabonk; the mod source itself still targets MelonLoader everywhere (MelonMod lifecycle, MelonLogger, MelonCoroutines, MelonEnvironment paths). Until the runtime is ported, no harness or packaging work is useful. All work happens off main so main keeps building the MelonLoader version until cutover, per the parent's rollback strategy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The mod initializes under BepInEx (BasePlugin.Load) and no MelonLoader types remain in src/MegabonkLevels.Mod (logging, coroutines, environment paths, lifecycle all replaced)
- [ ] #2 Per-frame behavior runs through an interop-registered Unity component ticked by the plugin
- [ ] #3 All existing Harmony patches behave as before on the smoke path: relaunch, example-forest load, editor on
- [ ] #4 The csproj references BepInEx and interop assemblies and builds cleanly, with NLayer and other copy-local dependencies landing in the correct BepInEx folder on build
- [ ] #5 The F6 test-level load and the console overlay still work in-game
- [ ] #6 Loader-related docs (docs/development.md and any loader-specific docs) are updated for BepInEx
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
