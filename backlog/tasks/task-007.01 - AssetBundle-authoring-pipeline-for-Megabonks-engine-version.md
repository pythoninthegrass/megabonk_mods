---
id: TASK-007.01
title: AssetBundle authoring pipeline for Megabonk's engine version
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-06 21:44'
updated_date: '2026-10-26T22:16:00Z'
labels:
  - level-editor
  - assets
dependencies: []
parent_task_id: TASK-007
priority: low
type: spike
ordinal: 33000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-007 first for full context, especially the engine-version/render-pipeline mismatch with `.tools/mb_terrain_generator`.

Establish a documented, repeatable way to build a Unity AssetBundle that Megabonk (Unity 2023.2.22f1, built-in render pipeline) can load correctly:

- Determine whether a minimal fresh Unity 2023.2.22f1 project (built-in pipeline) is sufficient to build and test a first AssetBundle, or whether upgrading `.tools/mb_terrain_generator` to 2023.2.22f1 + built-in pipeline is actually needed as a private authoring sandbox (it is paid third-party content — never redistribute it or commit its assets; any conversion work stays local/gitignored).
- Document the exact Unity Editor version, build settings, and AssetBundle build API calls (`BuildPipeline.BuildAssetBundles` or the newer Scriptable Build Pipeline) needed to produce a bundle Megabonk's IL2CPP runtime can deserialize (Unity's AssetBundle format is generally version-sensitive — confirm cross-version loading actually works or document the exact matching-version requirement).
- Produce one working test AssetBundle (a simple prop, e.g. a cube or a basic tree-like mesh) as a proof of concept, and confirm it loads without errors via `AssetBundle.LoadFromFile`/`LoadAsset` in a minimal MelonLoader test harness.

This is the foundation the other TASK-007 subtasks build on — if this proves infeasible or much harder than expected (e.g. AssetBundle version incompatibility that can't be worked around), flag that to Lance before continuing with TASK-007.02-.04.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A documented decision exists on whether a fresh minimal Unity project or an upgraded .tools/mb_terrain_generator sandbox is used for authoring, with reasoning
- [ ] #2 The exact Unity Editor version, render pipeline setting, and AssetBundle build process needed for Megabonk-compatible bundles is documented step by step
- [ ] #3 A test AssetBundle containing a simple prop is built and successfully loaded via AssetBundle.LoadFromFile/LoadAsset in a minimal MelonLoader test harness
- [ ] #4 Any infeasibility or major difficulty discovered is explicitly flagged to Lance rather than worked around silently
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Find out whether Unity 2023.2.22f1 is available on any host (not found under /Applications, /opt or ~ on the Mac as of 2026-10-26; check Unity Hub and mf). If none, ask Lance how to get it before going further.
2. Decide fresh minimal project vs upgrading .tools/mb_terrain_generator and record the reasoning (AC #1). Default is a fresh built-in-pipeline project, since the sandbox is URP/2022.3 and paid content.
3. Build a cube or simple-prop AssetBundle with BuildPipeline.BuildAssetBundles targeting the standalone Linux/Windows player; record editor version, pipeline setting and build steps in docs/ (AC #2).
4. Load it with AssetBundle.LoadFromFile/LoadAsset from a minimal MelonLoader harness and check the log (AC #3).
5. If the bundle will not deserialize or Unity is unobtainable, stop and flag it to Lance (AC #4).
<!-- SECTION:PLAN:END -->
