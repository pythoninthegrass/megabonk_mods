---
id: TASK-002.01
title: MelonLoader hello-mod on CrossOver and Windows
status: To Do
assignee: []
created_date: '2026-10-06 21:40'
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

Using TASK-001's scaffold (`task game:melonloader:install`, `src/MegabonkLevels.Mod`, `task mod:build`/deploy, `task game:run`, `task game:log`): install MelonLoader into the Megabonk install on the CrossOver/macOS bottle, build and deploy the placeholder mod, launch the game, and confirm in `MelonLoader/Latest.log` that the mod initialized. Add a Harmony patch (postfix) on `MapGenerationController`'s method that raises `A_GenerationComplete` (or a subscriber to that static Action, whichever Il2CppInterop exposes more cleanly — confirm which once you have real Il2Cpp-interop assemblies from the install step) that logs the current `mapSeed` and a count of spawned tiles.

Repeat the same build (no code changes) on a Windows install of Megabonk and confirm identical behavior in its `MelonLoader/Latest.log`.

Record any CrossOver/Wine-specific friction (DLL override quirks, path translation issues, crashes specific to Wine) separately from genuine MelonLoader/game issues, since Windows is the reference platform per TASK-002's framing — if CrossOver behaves differently, that's noted as a known gap, not treated as a mod bug to chase.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 MelonLoader is installed via task game:melonloader:install on both a CrossOver/macOS Megabonk install and a Windows Megabonk install
- [ ] #2 The placeholder mod, built once and deployed via task mod:build, loads on both platforms and logs a message on MelonLoader initialization visible in Latest.log
- [ ] #3 A Harmony patch or Action subscriber fires when MapGenerationController reaches A_GenerationComplete and logs the active mapSeed plus a spawned-tile count, on both platforms
- [ ] #4 Any CrossOver/Wine-specific friction encountered is documented separately from platform-agnostic findings
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
