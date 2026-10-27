---
id: TASK-017
title: 'Spike: choose a macOS-native build route for GameAssembly'
status: To Do
assignee: []
created_date: '2026-10-27T05:57:00Z'
labels:
  - research
  - native
dependencies: []
references:
  - docs/development.md
priority: low
type: spike
ordinal: 71000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-015 sized three routes to a macOS-native, Steam-free build of Megabonk, largest first:
- A - Full static recomp of the Linux `UnityPlayer.so`/`GameAssembly.so` (SysV ABI, Vulkan) plus a Linux-to-macOS shim. ~85 MB of x86-64 to lift; no maintained lifter produces rebuildable code at this scale. Largest.
- B - Re-host `GameAssembly` only: translate the Linux `GameAssembly.so` into a macOS x86-64 dylib (Rosetta) paired with Unity 2023.2.22f1's macOS player, reusing `global-metadata.dat`, icalls resolved by name. Blockers: libil2cpp's Linux OS layer (Boehm GC thread suspension, signals) on macOS, and shaders (DX11/12 or Vulkan/GL blobs; macOS needs Metal via SPIRV-Cross, repacked).
- C - pt-pc-style reimplementation: AssetRipper export, reimplement the ~7,850 `Assembly-CSharp` bodies in C# from `dump.cs` + Ghidra pseudocode, add the packages (TMP, ProBuilder, Localization, Addressables, Splines, PostProcessing, AI Navigation, Steamworks.NET, Coffee.UIParticle are free/OSS; Rewired and MK.Toon are paid). Risk: behaviour drifting from the shipped game.

TASK-015's recommendation: keep MelonLoader now, and treat the macOS-native build as a separate cost-benefit choice (B or C, A last), chosen only if running under CrossOver/Wine is itself the bottleneck.

This spike decides B vs C so a later implementation task has a path. It is analysis only and does not build anything. It does not need the Steam session.

Investigate:
- Route B blockers: how much of libil2cpp's Linux OS layer needs porting; count shader variants (UnityPy) and judge the Metal/SPIRV-Cross repack.
- Route C scope: what AssetRipper recovers (shaders are the weak spot) and how much of the ~7,850 bodies is pure logic vs editor/serialized data.
- Cost per game update for each route (how much drifts when the game patches).

Deliverable: a one-page pick of B vs C with the top blocker and the smallest first step, appended to the 'Static recomp' section of docs/development.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Route A is explicitly ruled out with the reason (no maintained lifter at ~85 MB of x86-64).
- [ ] #2 Route B's top blocker is named with a rough size (libil2cpp OS-layer port, shader/Metal effort, variant count).
- [ ] #3 Route C's scope is scoped (what AssetRipper recovers, pure-logic vs serialized share, shader gap).
- [ ] #4 Cost per game update is estimated for B and C.
- [ ] #5 A one-page pick (B or C) with the smallest first step is written into docs/development.md.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
