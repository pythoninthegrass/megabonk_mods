---
id: TASK-025.07
title: Consolidate the Warehouse kit into reusable assets and larger roof modules
status: Done
assignee: []
created_date: '2026-10-31T02:56:00Z'
updated_date: '2026-10-31T03:40:00Z'
labels:
  - thps
  - level-editor
dependencies:
  - TASK-025.05
references:
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - unity/pack-authoring/Assets/Editor/WarehousePieces.cs
  - unity/pack-authoring/Assets/Editor/WarehouseRoof.cs
  - scripts/build_thps_editable_level.py
  - scripts/build_thps_attachments.py
documentation:
  - docs/thps-warehouse-pieces.md
  - docs/asset-bundles.md
  - docs/thps-warehouse-layout.md
parent_task_id: TASK-025
type: feature
ordinal: 5500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The face-by-face kit exposes1541 generated roof quads and spatially named duplicates rather than useful reusable construction modules. Authors need a compact palette with larger roof sections and shared props. User explicitly approves discarding old kit catalog IDs without aliases: only levels/thps.mblevel.json and installed UserData/Levels/forest_custom.mblevel.json and their dependencies must be preserved. The latter currently has0 edits and no pack dependencies; SHA256 b8d44d467f94130d0a45cc4a02f2a4902a6eb3dac1b4d60314f17ca4f877fc8a. The separate editable assembly may be regenerated.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The palette exposes reusable sign/banner/poster, board/kicker and other matching prop assets rather than separate entries for identical instances; distinct artwork, geometry and collision remain distinct.
- [x] #2 Generated roof modules cover larger areas and reduce roof placements substantially while retaining the existing ceiling shape, steps, skirts and collision.
- [x] #3 The editable Warehouse uses consolidated assets and retains piece-local support/grind behavior, with no obsolete kit assets or compatibility aliases exposed or bundled.
- [x] #4 thps.mblevel.json and forest_custom.mblevel.json remain byte-identical and their dependencies remain intact, verified by preservation checks.
- [x] #5 Tests cover deduplication, transforms, roof consolidation and assembly coverage; docs explain the new palette and regeneration.
- [x] #6 The rebuilt kit and editable assembly are verified through the running-game harness, including visual parity, selection and attached behavior.
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
1. Preserve the existing Warehouse generation path and both protected level bytes; forest_custom is installed UserData/Levels only and has no pack references. Write pure tests before consolidation logic.
2. Add Unity-free kit geometry canonicalization keyed by transformed geometry, UVs, material, winding and collision behavior. Emit reusable assets for matching signs/banners/posters, boards/kickers/posts and other props; keep the source inventory as placement/coverage metadata rather than palette IDs. Preserve differently shaped/artworked variants. No aliases or obsolete bundled kit prefabs.
3. Consolidate the existing emitted roof quads into larger coplanar modules before kit export only; do not change RoofCell, spill calculation or legacy mesh bytes. Reuse normalized panel assets where possible and retain nonrectangular edge geometry.
4. Extend pieces.json instance metadata with canonical asset and full placement transform; regenerate attachment defaults and editable level using canonical references, preserving independent supports/grind paths. Bump kit revision and update tests/docs.
5. Rebuild Windows/Linux pack, regenerate/install editable assembly, run full check and strict preservation after Unity finishes, verify protected forest hash and test visuals/selection/grinds through the game harness. Commit conventionally and leave025.06 unstarted.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
MCP tools recovered after the restart; continuing on the existing task. Tests were written first for canonical geometry frames, reconstruction, artwork/UV/collision identity, rigid sizing, roof unions/clipping, disconnected sign copies, thin skirts and shared-vertex boxes. New pure tests exposed and fixed frame selection on tiny roof faces and closed shared-vertex posts.

Roof consolidation now clips the baked roof into40x40-world-unit footprint sections containing ceiling/steps/skirts. The old1541 quad instances became32 roof sections; the original merged Warehouse mesh/collision and its generation algorithm are unchanged. Source signs with disconnected state copies split into independent placements, retaining sourceId/face provenance. Sidecar instance IDs are not catalog IDs: catalogAsset plus full rotation/scale refer to reusable prefabs. No aliases or obsolete prefab files are retained.

Strict equality alone left all24 loose plank entries because the extraction gives each tiny skew/edge/triangulation differences. Within the approved greenfield consolidation, known loose planks are standardized by artwork/material/crop variant and fitted to each original size/pose. Riding kickers remain rigid and their two different top artworks remain separate. Other props/signs use strict transformed geometry/UV/collision signatures. Per-instance attachment snapshots remain separate from canonical palette defaults; source support IDs prevent duplicate root placements.

Final Windows/Linux pack rebuilt and installed: 201 total prefabs (200 construction assets versus 1,766), 32 roof placements versus 1,541, 21 roof assets including 12 placements sharing added-roof-panel-flat; 24 loose planks share 6 artwork variants, 40 sign instances share 25 assets, 35 prop instances share 8 assets. Palette is 277 entries; regenerated reference has 1,444 edits versus 2,948. No obsolete prefabs or aliases remain.

Validation: task check passed with 1,495 C# and 673 Python tests, zero build warnings/errors, markdownlint and Ruff. Latest docs passed task lint; git diff --check passed. check_thps_preservation.py passed after final build; forest_custom SHA-256 remains b8d44d467f94130d0a45cc4a02f2a4902a6eb3dac1b4d60314f17ca4f877fc8a. Both protected levels successfully loaded.

Runtime evidence under .tools/evidence/02507-*: six matched-camera visual comparisons, canonical palette, 32 live roof colliders (12 flat panels), no old roof-quad objects, kicker selection/rotation/undo and attached-frame save/relaunch. Native grind crossed both main-north seams and continued onto hip with three distance-0.00 handoffs; log saved as 02507-grind-save-replay.log. Final-pack save 02507-final-kit-check.mblevel.json reloaded cleanly with 1,444 edits and no Missing: objects. Restored levels/thps-editable.mblevel.json in editor mode with normal damage/spawns and device-controlled slide input. TASK-025.06 remains To Do; unrelated Linux installer task edits are excluded.

Committed implementation, generated metadata/reference, tests/docs and TASK-025.06 dependency as e6bebf0 (feat(thps): consolidate reusable kit assets and roof sections). No attribution footer; unrelated TASK-006.04.01 changes left unstaged.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Consolidated the Warehouse construction kit into 200 reusable assets and 32 large roof sections, with canonical instance transforms, standardized plank artwork variants and preserved local attachments/grinds. Regenerated the editable reference and documented revision 2; legacy Warehouse version and both protected levels/dependencies remain unchanged. Full checks and running-game visual, collision, selection, attachment replay and grind-seam checks passed. Intentional breaking change: old greenfield kit IDs are removed without aliases. TASK-025.06 remains unstarted.
<!-- SECTION:FINAL_SUMMARY:END -->
