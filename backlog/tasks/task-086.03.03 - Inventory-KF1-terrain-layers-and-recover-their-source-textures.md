---
id: TASK-086.03.03
title: Inventory KF1 terrain layers and recover their source textures
status: To Do
assignee: []
created_date: '2026-11-27 21:46'
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
- [ ] #1 A reproducible export recipe locates the Landscape_T soil and grass, WyreTex mud and map-local rock, gravel, vegetation and masks by original package and object.
- [ ] #2 A table records every occupied slot, role, diffuse and mask paths, mask channel, dimensions and UV settings; slot 5 is not synthesized.
- [ ] #3 Synthetic tests cover sparse slots, package-name collisions and a missing required input; missing inputs report the qualified object name rather than substituting gray.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
