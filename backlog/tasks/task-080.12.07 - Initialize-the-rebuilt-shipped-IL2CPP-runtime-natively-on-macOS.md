---
id: TASK-080.12.07
title: Initialize the rebuilt shipped IL2CPP runtime natively on macOS
status: In Progress
assignee: []
created_date: '2026-11-16T19:05:00Z'
updated_date: '2026-11-23T05:14:00Z'
labels:
  - native-macos
  - arm64
dependencies:
  - TASK-080.12.02
  - TASK-080.12.03
  - TASK-080.12.04
  - TASK-080.12.05
  - TASK-080.12.06
references:
  - scripts/native_bind_probe.py
  - scripts/native_bind_probe/host.c
documentation:
  - docs/development.md
parent_task_id: TASK-080.12
priority: high
type: enhancement
ordinal: 274000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The existing native-bind probe proves the official probe-player runtime on macOS and the shipped runtime on Linux separately, not the rebuilt shipped runtime on macOS. This integration gate consumes the calling interface, relocated image, platform services and complete lift from sibling tasks. It must load the shipped metadata rather than substitute the probe project's assemblies. No Unity window, graphics or mod-loader detour is required at this gate.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A bounded native arm64 host loads the rebuilt shipped runtime and matching metadata, initializes a non-null domain, attaches a thread and enumerates the expected game assemblies/classes.
- [ ] #2 The required public il2cpp API surface is callable and identified in the produced image; missing exports fail the integration check.
- [ ] #3 The managed-method ladder returns the shipped reference values, including a game-authored Assembly-CSharp method, with binary/metadata hashes and non-translated process evidence recorded.
- [ ] #4 Missing/mismatched metadata and startup failure are diagnosed without leaving orphan processes; regression tests and docs reproduce a clean startup and shutdown.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extend the existing native-bind host with a strict headless runtime gate; add a separate driver for pinned identities, bounded execution, and failure reports. Test with native synthetic images first.
2. Probe an existing pinned link without rebuilding it. Enforce public API exports, and report link/startup blockers to the platform-services task. Keep diagnostic execution separate from the integration gate.
3. Reuse the managed invocation ladder for a pinned native Linux control and the macOS candidate. Record process architecture, metadata and image hashes, and actual startup/shutdown evidence before closing criteria.

The fresh v13 stock link reproduces the export gate and all diagnostic stops. Next consume the platform layer's agreed startup contract and add production typed public entry points without replacing its service code. Re-run the full gate against a separately pinned link only after those pieces are available.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Native gate and regression tests committed in `9159c26`. Pinned ELF SHA-256 `a86fd434619dafb328ec741b6bc285992ee1f52e69533b2db8f35185c2ed5ba1`; metadata `53ca3fd0c07051c949329c03d377efdf7de556f97024cca82748e93ac8bc480e`. A fresh native Linux x86-64 capture of the same C host reports 72 assemblies and clean shutdown for Abs(-7) = 7, Concat(mega, bonk) = megabonk, and Assembly-CSharp InventoryUtility.GetWeaponMaxLevel() = 40. No Steam, Unity player, or real save profile was used. Local control: `.tools/native-runtime/linux-control.json`.

An earlier relocated-data arm64 link (`.tools/lift-link-data/libgameassembly.dylib`, digest `91949266c5ab5c096cd85cabf27746f0517c33bb07590fd2e00dbd252a2a36bb`) loads eagerly (`proc_translated=0`) but fails all 20 required public IL2CPP exports. Scratch-only adapters diagnose the uninitialized `std::string` at `il2cpp_set_data_dir`, the first `.init_array` constructor's `__cxa_atexit` abort, and a separate `il2cpp_init` call's `setlocale` abort. These are separate comments on the platform-services task, not substitute implementations. The v13 baseline is unchanged and a fresh stock link is building in `.tools/lift-link-runtime-v13`. No acceptance criteria checked.

Fresh stock build from `.tools/lift-image-full-v13`: `.tools/lift-link-runtime-v13/libgameassembly.dylib` SHA-256 `c926649e44e28bba3f8a808685887d78a93426bfef672eeff4287e140f4a7e8a` (link identity `b30e267e197fe9732f0f86e6435e6f7c6b5bb4ac3cbf18bc5c8c816591a4064b`), 259,102 bodies, 53 traps, 218 named-abort imports. Fresh arm64 non-translated subprocess loaded it but reported all 20 public exports missing; report `.tools/native-runtime/v13-exports/report.json`. Scratch-only adapter image SHA-256 `92de43b4958e131c950009689e307b03d754314a89a133cf787529cf7b4d45a9` reproduced SIGSEGV at `il2cpp_set_data_dir` (Mach-O offset `0x1e949a8`, invalid address `0xffffffffffffffe8`) and separate `setlocale` abort. An isolated ELF `DT_INIT` call aborts earlier at `__gmon_start__` because its weak GOT slot is erroneously non-null; the first array constructor still aborts at `__cxa_atexit`. Four distinct findings posted on the platform-services task. No game-derived artifacts were committed.

task check passed (2,941 Python passes, one skipped, one expected failure; 2,869 C# passes; lint passed). The native Linux control and macOS synthetic failure gates pass. All four acceptance criteria remain unchecked: public exports are missing, startup/metadata consumption and clean shutdown are not measured on the rebuilt image, and no macOS managed result exists. Confirm the production export and startup interface with the platform-services work before rebuilding.
<!-- SECTION:NOTES:END -->
