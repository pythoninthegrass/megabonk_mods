---
id: TASK-007
title: Custom asset packs
status: Done
assignee: []
created_date: '2026-10-06 21:43'
updated_date: '2026-10-27T22:25:00Z'
labels:
  - level-editor
  - assets
dependencies:
  - TASK-004
priority: low
type: feature
ordinal: 30000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Goal: let players import entirely new, third-party assets (not just existing game prefabs) into levels, so the mod eventually supports Steam-Workshop-style community content without first-party Valve/developer approval — the original long-term ask behind this whole project. This is explicitly the furthest-out, lowest-priority parent task; it depends only on TASK-004 (runtime playback working), not on TASK-005/TASK-006, since asset-pack authoring and loading can be developed somewhat independently of the in-game editor UI.

## Context

Megabonk ships Unity 2023.2.22f1 using the **built-in render pipeline** (confirmed — the game references Post Processing v2 and MK.Toon, not URP). AssetBundles built for this game must be built from Unity 2023.2.22f1 with the built-in pipeline, or materials/shaders will not render correctly when loaded into the running game.

The `.tools/mb_terrain_generator` project (AlexK's paid Patreon Unity project, gitignored, reference/sandbox only — never redistribute it or its assets) is currently Unity 2022.3 and URP. It is NOT directly usable as an asset-pack authoring project as-is; it would need upgrading to 2023.2.22f1 and conversion to the built-in pipeline before it could serve as a private authoring sandbox for test asset bundles. This conversion work is in scope for TASK-007.01 if a sandbox project is needed, but is not required if a minimal fresh Unity project proves sufficient for the first AssetBundle.

This whole parent task is exploratory/lower-confidence compared to TASK-001 through TASK-006 — expect the subtasks to surface design questions that may need to go back to Lance before implementation, rather than being fully resolvable from research alone.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A documented, repeatable pipeline exists for building a Unity AssetBundle targeting Megabonk's exact engine version and render pipeline (built-in, not URP)
- [x] #2 A pack loader can load an AssetBundle at runtime and make its contained prefabs available under a bundle: catalogId, resolvable by TASK-004.02's existing catalogId resolution logic
- [x] #3 Materials/shaders from an imported asset render correctly in-game via a shader remap step, verified visually on at least one non-trivial imported model
- [x] #4 A pack manifest format exists covering pack identity, version, and the assets it provides, with a basic compatibility/version check comparable to the level file's gameBuildId check
- [x] #5 Risks or design gaps discovered during this task that need Lance's input are explicitly flagged rather than silently resolved with a guess
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-26: started ahead of TASK-006 at Lance's request. TASK-007 depends only on TASK-004 (Done). First subtask is TASK-007.01.

2026-10-27: all subtasks 007.01-007.07 Done. AC3 accepted on the TestModel composite (brick texture, cel lighting, fog). DoD #2 left unchecked at parent level: it is satisfied per subtask where logic was testable.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Custom asset packs work end to end: a repeatable Unity 2023.2.22f1 built-in-pipeline AssetBundle build (task pack:build), a pack loader resolving bundle:<pack>/<asset> catalog ids through the same edit pipeline as game prefabs, a toon-shader remap for imported materials, and a pack manifest with a level-side version check. Packs list in the editor palette, and editor object editing was confirmed on Tiles maps and on the ProceduralMesh maps Desert and Hell (007.07 fixed a MapData lookup that omitted Hell). Everything is documented in docs/asset-bundles.md and docs/development.md. Open items: the Linux bundle has not been loaded, other editor versions are untried, and pack placement has not been run on Hell.
<!-- SECTION:FINAL_SUMMARY:END -->
