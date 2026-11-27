---
id: TASK-086.03.03
title: Inventory KF1 terrain layers and recover their source textures
status: Done
assignee: []
created_date: '2026-11-27 21:46'
updated_date: '2026-11-27 22:14'
labels:
  - kf1
  - level
dependencies:
  - TASK-086.02
references:
  - scripts/kf1_mountain_pass.py
  - tests/test_kf1_mountain_pass.py
documentation:
  - docs/kf1-mountain-pass.md
  - docs/asset-bundles.md
parent_task_id: TASK-086.03
priority: high
ordinal: 306000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use the verified .tools/kf1/export/KF-MountainPass.t3d TerrainInfo1, not the KF2 rework. Read Layers(0–4,6,7); retain numeric slots across the gap at 5. Pair package-qualified Texture and AlphaMap references, UScale/VScale and TerrainMatrix. Inspect KF1 package properties for ground versus decoration semantics, especially Main_DecoGrass used as a texture in slot 7. Follow the documented UCC/umodel export from the original install. Leave extracted files under .tools/kf1/.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A reproducible export recipe locates the Landscape_T soil and grass, WyreTex mud and map-local rock, gravel, vegetation and masks by original package and object.
- [x] #2 A table records every occupied slot, role, diffuse and mask paths, mask channel, dimensions and UV settings; slot 5 is not synthesized.
- [x] #3 Synthetic tests cover sparse slots, package-name collisions and a missing required input; missing inputs report the qualified object name rather than substituting gray.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first in tests/test_kf1_mountain_pass.py: Layers(0-4,6,7) parse to those numeric slots with no entry for 5; qualified Package.Group.Object resolution keeps same-named objects in different packages or groups distinct; a missing required input raises naming the qualified object rather than substituting gray; mask channel detection from the exported TGA (alpha-only variation, rgb, constant).
2. scripts/kf1_mountain_pass.py: parse_terrain_layers reads TerrainInfo1 Layers(n) and DecoLayers(n) keyed by numeric slot; parse_qualified splits Package.Group.Object; resolve_layer_inputs finds each exported file (group directory then Texture/) and records diffuse and mask paths, dimensions, mask channel and weight summary plus UScale/VScale and the TerrainMatrix repeat; terrain_inventory writes .tools/kf1/terrain_layers.json and prints the markdown table. New CLI verb terrain-inventory.
3. Recover source textures on the Linux player box (Docker plus the source-built umodel, game packages under .tools/kf1/game): targeted -export of Landscape_T Soil.earth_1051 and Grass.grass_2589, WyreTex Common.MudGround, and the DecoLayers meshes WyreStatics Forest.WyreMiddleFoliage and map-local GUP-GrassLOD with their textures; copy the new trees into .tools/kf1/out/; rerun the inventory until no row is missing.
4. Inspect UE2 texture properties with umodel -dump (Format, USize/VSize, clamp modes, bMasked) for each inventoried object and record the ground versus decoration semantics, including Main_DecoGrass serving as slot 6 alpha map, DecoLayers(1) density map and slot 7 diffuse.
5. docs/kf1-mountain-pass.md: Terrain layers section with the slot table (role, diffuse and mask paths, mask channel, dimensions, UV settings), the semantics findings, and the export plus property-inspection recipes; prune the terrain line from the TODO.
6. task check, conventional commit with no attribution, check the acceptance criteria, final summary.
Risks: umodel -groups directory layout is unverified and is what keeps group-qualified names from colliding; umodel already refuses the G16 heightmap, so anything it cannot write is reported rather than faked.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
TerrainInfo1 is now inventoried by scripts/kf1_mountain_pass.py terrain-inventory, which parses Layers(n) and DecoLayers(n) by their numeric slots (0-4, 6, 7; slot 5 is absent in the export and nothing is synthesized into it), resolves every package-qualified diffuse, mask, density map and decoration mesh against the umodel export through package/group/object, and writes .tools/kf1/terrain_layers.json plus the markdown table now in docs/kf1-mountain-pass.md.

Findings: the layer weight is the mask's alpha channel - all seven KF-MountainPass Main_* masks are 256x256 RGBA with RGB flat at 127 and a full-range alpha, so reading color would give every layer a constant half weight; the channel is detected per texture from the exported TGA rather than assumed. TerrainMatrix encodes tiling exactly (XPlane == 1/(64 * UScale)), so layers repeat every 64 * UScale units: 128, 128, 128, 96, 128, -, 64, 64. Weights are not normalized (sum mean 2.04, max 5.3), so the blend must renormalize. Heightmap statistics corroborate the channel: Main_Grass and Main_Forest sit on high gentle ground (mean height 407 and 411 against 101 everywhere), Main_Gravel on the steepest (slope 1.16 against 0.85). Slot 7's diffuse is KF-MountainPass.Main_DecoGrass, the same object that is slot 6's alpha map and DecoLayers(1)'s density map, so it paints flat mid-gray wherever Main_DecoFoliage weights it; KF1 Texture properties carry no ground or decoration flag, so intent is unresolved and left to the blend. Slot 6's GUP-MountainGrass is TEXF_DXT3 1024x256, TC_Clamp and bMasked - a masked strip, not a tiling ground texture.

Recovered with umodel on the Linux player box and copied into .tools/kf1/out/: Landscape_T Soil.earth_1051 and Grass.grass_2589, WyreTex Common.MudGround, and the decoration mesh WyreStatics Forest.WyreMiddleFoliage with its two diffuses WyreTex Static.WyreFoliageTex and Statics.FoliageBTex. umodel needs -out=/out and -groups (without groups, group-qualified names flatten into <package>/Texture/ and collide - WyreTex holds both a Static and a Statics group), and its container writes as root.

Tests: 16 new cases in tests/test_kf1_mountain_pass.py written first and confirmed red, covering sparse slots, same-named objects in different groups and packages, class-folder fallback, mask-channel detection (alpha, color, constant), the mask-used-as-surface role, deco linkage, table rows, and a missing required input that reports the qualified object name instead of substituting gray, plus a skipif-guarded pass over the real T3D. task check passes, prepare output is byte-identical to before, commit 94949c9.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
