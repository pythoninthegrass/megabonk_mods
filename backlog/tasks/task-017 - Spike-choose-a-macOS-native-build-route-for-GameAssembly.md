---
id: TASK-017
title: 'Spike: choose a macOS-native build route for GameAssembly'
status: Done
assignee: []
created_date: '2026-10-27T05:57:00Z'
updated_date: '2026-11-15 08:47'
labels:
  - research
  - native
dependencies: []
references:
  - docs/development.md
priority: low
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
- [x] #1 Route A is explicitly ruled out with the reason (no maintained lifter at ~85 MB of x86-64).
- [x] #2 Route B's top blocker is named with a rough size (libil2cpp OS-layer port, shader/Metal effort, variant count).
- [x] #3 Route C's scope is scoped (what AssetRipper recovers, pure-logic vs serialized share, shader gap).
- [x] #4 Cost per game update is estimated for B and C.
- [x] #5 A one-page pick (B or C) with the smallest first step is written into docs/development.md.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Read-only spike; the only file written is docs/development.md 'Static recomp'. Inputs are gitignored .tools artifacts (read from the main checkout) plus the shipped data in .tools/thunderstore-smoke-game.
1. Baseline: read docs/development.md 'Static recomp' and the prior exploration notes so the new text extends rather than repeats them.
2. Route A: verify the 'no maintained lifter at ~85 MB' claim as of now (McSema, remill, MCToolkit, and anything newer), and record the named reason for ruling it out.
3. Route B: measure the shader blocker with UnityPy over the shipped data: Shader objects, subshaders, passes, shader-variant count, and which GPU blob formats are present (DXBC/DXIL vs SPIR-V/GLSL source), which decides the Metal repack.
4. Route B: size the libil2cpp OS-layer port by symbol inventory over the Linux GameAssembly.so (il2cpp::os:: / os::Linux:: surface, GC_* Boehm exports, signal handlers, thread suspension). Pull it from the Linux Steam install or the depot read-only if not present locally.
5. Route C: classify the ~7,850 Assembly-CSharp bodies from dump.cs into generated/accessor vs real logic; inventory the package images a reimplementation must supply (free vs paid); check whether shipped Shader objects carry any source (m_ScriptSource / snippets) that AssetRipper could recover.
6. Cost per game update for B and C: patch cadence, what must be re-run per patch in each route, and the drift surface for C.
7. Append a one-page pick (B vs C) with the top blocker and the smallest first step to docs/development.md; rule out A explicitly; check ACs, then commit docs: with no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Checks run in the worktree: mod build 0 warnings 0 errors, 2836 xUnit tests, 1498 Python tests (60 skipped), installer Go tests, and lint (markdownlint, ruff, deno fmt/lint). task check itself cannot run in a fresh worktree: the csproj resolves its Unity and BepInEx reference assemblies from the game folder, whose path comes only from the gitignored .env, so without it every UnityEngine type fails with CS0246 (1228 errors). Reproduced by copying the .env in and pointing ModInstanceFolder at a temp directory so the build could not write into the real game install; both files were removed again afterwards.

Loader correction folded in after review: the mod is a BepInEx IL2CPP BasePlugin injected by doorstop, not a MelonLoader plugin. The section's Scale, Entry point, Interop surface, Build/relink and Recommendation text now name BepInEx.Core, BepInEx.Unity.IL2CPP, the BepInEx/interop stubs, the CopyOutputToPluginsFolder deploy into BepInEx/plugins/MegabonkLevels, and doorstop as the injector. Linux GameAssembly.so exports 480 il2cpp_* (the Windows DLL 240).

Does not change the pick: B over C stands, same top blocker. BepInEx makes B's loader half cheaper (an official Unity.IL2CPP-macos-x64 build plus doorstop's libdoorstop.dylib exist, so injection and interop generation are not to be written) and adds one blocker to probe (interop generation on Apple silicon under Rosetta has open upstream failures: preloader loads with no config/LogOutput.log/interop folder, and a second report needs a doorstop symbol newer than the doorstop BepInEx pinned).

New dated risk for B, not for C: the translated dylib is an Intel-only app, and Apple names macOS 27 as the last release running Intel-only apps on Apple silicon. The smallest-first-step list now also carries a loader probe: run Unity.IL2CPP-macos-x64 plus universal doorstop against a macOS player under Rosetta and score it on whether BepInEx/interop and LogOutput.log appear.

Left alone deliberately: MelonLoader remnants that are still live tooling, not stale prose (scripts/install_melonloader.py, game:melonloader:install, crossover:melonloader:install, the BepInEx-vs-MelonLoader rollback notes in this doc, and ~70 mentions across 11 other docs). Worth a separate cleanup decision.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Outcome: route B (re-host the shipped x86-64 GameAssembly under a compatibility layer) over route C (hand-port the managed layer onto an upstream il2cpp runtime). Written up as '### Route decision: B over C' in the Static recomp section of docs/development.md, ~780 words, with the three Routes bullets corrected to measured numbers. Analysis only; nothing was built and no game was launched.

AC1 route A ruled out: McSema archived read-only by its owner and IDA-gated for CFG recovery; remill lifts instructions only; nothing maintained rebuilds ~85 MB of x86-64 (GameAssembly.so 87,741,504 B + UnityPlayer.so 32,545,400 B).

AC2 B's top blocker, sized: the Metal shader container repack, not libil2cpp's OS layer. 141 baked shaders, each with a GLSL source chunk (7,305 programs, 34,969,460 B) and a per-program blob (13,336 entries, 54,764,176 B, no SPIR-V magic); no macOS build exists to copy a Metal chunk from, and macOS OpenGL was removed in Unity 2023.1. 7,305 programs is a scripted pass. The OS layer measured 304 undefined libc-family symbols with 0 undefined symbols naming Unity.

AC3 route C scoped: ~7,856 real bodies (8,697 RVAs minus 841 shared stubs) across 73 images, 2,522 distinct managed classes, 52,545 serialized objects in 76 types with the asset split in the doc, ~31 non-builtin shaders with MK.Toon and Rewired paid, and the shader gap identical to B's. AssetRipper is not a shader answer (its decompilation was removed from master).

AC4 cost per update at ~15 depot pushes/month: B 0.5-1 scripted dev-day with a Unity-version-bump cliff; C 40-240 hours per content patch with no oracle but playtesting. Marked as an estimate: no second GameAssembly version exists on any reachable host to diff.

AC5 smallest first step: script all 7,305 GLSL programs through glslangValidator, spirv-cross --msl and xcrun metal -c and report failures, plus one archive check on whether Unity 2023.2.22f1 still ships macOS Build Support, plus the cheaper ask of upstream for a macOS player build.

Follow-up worth its own task: run the shader translation pass. It is the cheapest experiment that can still kill route B, and a 100 percent failure rate on the first variant flips the decision to C.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
