---
id: TASK-007.01
title: AssetBundle authoring pipeline for Megabonk's engine version
status: Done
assignee:
  - '@claude'
created_date: '2026-10-06 21:44'
updated_date: '2026-11-09 05:26'
labels:
  - level-editor
  - assets
dependencies: []
parent_task_id: TASK-007
priority: low
ordinal: 33000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-007 first for full context, especially the engine-version/render-pipeline mismatch with `.tools/mb_terrain_generator`.

Establish a documented, repeatable way to build a Unity AssetBundle that Megabonk (Unity 2023.2.22f1, built-in render pipeline) can load correctly:

- Determine whether a minimal fresh Unity 2023.2.22f1 project (built-in pipeline) is sufficient to build and test a first AssetBundle, or whether upgrading `.tools/mb_terrain_generator` to 2023.2.22f1 + built-in pipeline is actually needed as a private authoring sandbox (it is paid third-party content — never redistribute it or commit its assets; any conversion work stays local/gitignored).
- Document the exact Unity Editor version, build settings, and AssetBundle build API calls (`BuildPipeline.BuildAssetBundles` or the newer Scriptable Build Pipeline) needed to produce a bundle Megabonk's IL2CPP runtime can deserialize (Unity's AssetBundle format is generally version-sensitive — confirm cross-version loading actually works or document the exact matching-version requirement).
- Produce one working test AssetBundle (a simple prop, e.g. a cube or a basic tree-like mesh) as a proof of concept, and confirm it loads without errors via `AssetBundle.LoadFromFile`/`LoadAsset` in a minimal MelonLoader test harness.

This is the foundation the other TASK-007 subtasks build on — if this proves infeasible or much harder than expected (e.g. AssetBundle version incompatibility that can't be worked around), flag that to the maintainer before continuing with TASK-007.02-.04.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A documented decision exists on whether a fresh minimal Unity project or an upgraded .tools/mb_terrain_generator sandbox is used for authoring, with reasoning
- [x] #2 The exact Unity Editor version, render pipeline setting, and AssetBundle build process needed for Megabonk-compatible bundles is documented step by step
- [x] #3 A test AssetBundle containing a simple prop is built and successfully loaded via AssetBundle.LoadFromFile/LoadAsset in a minimal MelonLoader test harness
- [x] #4 Any infeasibility or major difficulty discovered is explicitly flagged to the maintainer rather than worked around silently
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Find out whether Unity 2023.2.22f1 is available on any host (not found under /Applications, /opt or ~ on the Mac as of 2026-10-26; check Unity Hub and mf). If none, ask the maintainer how to get it before going further.
2. Decide fresh minimal project vs upgrading .tools/mb_terrain_generator and record the reasoning (AC #1). Default is a fresh built-in-pipeline project, since the sandbox is URP/2022.3 and paid content.
3. Build a cube or simple-prop AssetBundle with BuildPipeline.BuildAssetBundles targeting the standalone Linux/Windows player; record editor version, pipeline setting and build steps in docs/ (AC #2).
4. Load it with AssetBundle.LoadFromFile/LoadAsset from a minimal MelonLoader harness and check the log (AC #3).
5. If the bundle will not deserialize or Unity is unobtainable, stop and flag it to the maintainer (AC #4).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-26: Unity 2023.2.22f1 installed via Hub with Windows and Linux Mono modules. A Unity 6.6 (6000.6.7f1) editor is also installed but was not used: bundles are version-sensitive and the game is 2023.2.22f1. Batch builds needed a Personal licence activated through Hub.

Windows bundle built with task pack:build and loaded in the Wine-hosted game through the new load-bundle harness command: assets [TestProp:GameObject], no errors in Player.log.

AC 3 deviation: AssetBundle.LoadFromFile and LoadFromMemory cannot be used (interop span marshalling throws, and the game's AssetBundle class has the sync loaders stripped), so the loader uses LoadFromFileAsync and LoadAllAssetsAsync(Type), reading .assetBundle and .allAssets to block. Details in docs/asset-bundles.md.

Open, flagged to the maintainer: Linux bundle not loaded (no harness on native Linux), a different-editor-version bundle not tried, Standard shader rendering not checked (007.03), custom scripts cannot ship in bundles.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Built a repeatable AssetBundle pipeline for Megabonk's Unity 2023.2.22f1. unity/pack-authoring is a minimal built-in-pipeline project; task pack:build runs Assets/Editor/PackBuilder.cs in batch mode to produce a cube-prop bundle for Windows and Linux under .tools/bundles. A fresh project was chosen over converting the URP 2022.3 sandbox. Added a load-bundle dev-harness command (run.py bundle) and verified the Windows bundle loads in the game with the prefab resolved. The synchronous AssetBundle loaders are unusable through the Il2Cpp interop, so loading goes through the async API. Documented the decision, build steps, interop limits and open items in docs/asset-bundles.md. task check passes (806 C# tests, 186 Python tests, lint).
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
