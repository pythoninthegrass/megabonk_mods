---
id: TASK-025.03
title: Expose the inventoried Warehouse pieces as editor-placeable assets
status: Done
assignee: []
created_date: '2026-10-30T16:24:00Z'
updated_date: '2026-10-30T17:43:00Z'
labels:
  - level-editor
  - thps
dependencies:
  - TASK-025.02
references:
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - unity/pack-authoring/packs/thps/manifest.json
  - src/MegabonkLevels.Mod/pack_palette_entries.cs
  - unity/pack-authoring/Assets/Editor/WarehouseRoof.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - scripts/check_thps_preservation.py
documentation:
  - docs/asset-bundles.md
  - docs/thps-warehouse-pieces.md
  - docs/thps-warehouse.md
  - docs/development.md
parent_task_id: TASK-025
type: feature
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Depends on TASK-025.02, whose inventory (docs/thps-warehouse-pieces.md) names every piece and defines the kit's pivot and mating conventions. This task makes those pieces real pack assets: the builder partitions the extracted mesh by the inventory's Markdown tables (the declared machine-readable source of truth, so no competing face manifest), builds one prefab per piece with its own collision and a convention pivot, emits a placements sidecar, and lists everything in the pack manifest so the existing palette shows the pieces with no mod code change.

Scope is mesh geometry only: the 214 source-face pieces plus the pack-added pieces — the 10 rail posts (added-post-0..9), the floor patch (added-floor-patch-0) and one asset per emitted roof quad (added-roof-quad-NN, count discovered at build time and deterministic). Out of scope: the hidden grind and coping paths (TASK-025.04), and every game-prefab placement or level setting — boss portal and its spawn redirect, radio, piles, letters, tape, bonus chests, player start, tile bootstrap, clutter removals and the settings-* rows (TASK-025.05 places those through the generator). The shipped bundle:thps/Warehouse prefab, its collision mesh and levels/thps.mblevel.json stay untouched.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every piece in scope exists as its own prefab in the thps pack, listed in manifest.json, named by its inventory ID verbatim (piece-taxi, added-post-0, ...), and appears in the editor's Packs palette
- [x] #2 Pieces share the existing Warehouse_* materials with no duplicated materials or textures; each piece prefab carries its own collision mesh except window pieces, which ship render-only so their pass-through behaviour travels with the piece; window frames stay solid inside their wall pieces
- [x] #3 Ramp modules follow the pivot conventions in docs/thps-warehouse-pieces.md (pivot at the lower riding edge midpoint, +Y up, +Z toe toward lip; decks and flats at walking-surface centres; corners at extended-lip intersections; props and walls bottom-centre; roof panels at lower-face centre) and keep every profile vertex, so sections placed end to end form a continuous riding surface without seams or steps
- [x] #4 A placed piece can be selected, moved, rotated, scaled, duplicated and deleted with the existing object tools, verified in the running game; no mod code change is expected
- [x] #5 The original single Warehouse asset and its collision mesh are still built byte-identically, still listed first in the manifest, and still loadable so the shipped level is unaffected; the TASK-025.01 preservation check stays green
- [x] #6 Tests written first cover the partition, pivot and placement logic outside Unity, and docs describe the palette, the module set, piece naming, per-piece collision rules and the additive-assets version exception
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
1. Inventory-driven partition. New Unity-free C# file unity/pack-authoring/Assets/Editor/WarehousePieces.cs (no UnityEngine types, the CoplanarLayering/WarehouseRoof pattern) parses the source-face tables of docs/thps-warehouse-pieces.md, handling multi-group rows ("9D14F7B5, 041DA60F") and comma-separated inclusive face ranges ("278-280,285-296"), resolves selectors against the parsed OBJ face ordinals, and asserts every face has exactly one owner. ThpsPack resolves the doc path relative to the repo with a -piecesDoc override following the -warehouseSource pattern.

2. Piece prefabs in ThpsPack.Build. Partition AFTER SeparateCoplanarFaces so the global lifts stay with the geometry when a piece moves; take the suppressed-post faces from BEFORE RemoveRailLeftovers (the merged Warehouse mesh still drops them; the archival pieces keep them). Posts, floor patch and roof quads become added-post-N, added-floor-patch-0 and added-roof-quad-NN assets from the existing AddRailPosts/AddFloorPatches/AddRoof paths in emission order. Each piece: root GameObject named exactly the asset name, MeshFilter + MeshRenderer sharing the existing Warehouse_* materials, MeshCollider from a per-piece collision mesh (window pieces: no collider, render-only), layer 8 via SavePrefab. Keep SaveWarehouse/SaveCollisionMesh byte-identical and Warehouse first in the bundle asset list.

3. Pivots and placements sidecar. Re-express each piece's vertices relative to its convention pivot per docs/thps-warehouse-pieces.md "Coordinates and preservation rules". Emit a committed unity/pack-authoring/packs/thps/pieces.json with the per-asset original world placement and inverse pivot transform so TASK-025.05 can reassemble without re-deriving face math in Python.

4. Manifest and consistency tests. List every piece asset in unity/pack-authoring/packs/thps/manifest.json; ThpsPack fails the build when manifest assets and built prefabs disagree. Python tests assert manifest assets match the asset-emitting inventory IDs exactly and that pieces.json covers the same set (extend tests/test_thps_piece_inventory.py or add tests/test_thps_pack_pieces.py). Add WarehousePieces.cs to tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj via Compile Include Link, and add warehouse_pieces_tests.cs with synthetic faces (the coplanar_layering_tests pattern); write tests before the partition implementation per the Definition of Done.

5. Verify in game. task pack:thps, task pack:install, relaunch (packs load once per session); through the megabonk MCP: the palette lists the pieces and a taxi board and a wall transition can be placed, moved, rotated, scaled, duplicated and deleted, with screenshots at each step. task check (C# tests, Python tests, build, lint) and the standalone preservation CLI must pass.

6. Docs. docs/asset-bundles.md: the piece assets, verbatim inventory-ID naming, render-only window pieces, the pieces.json sidecar, and amend the "bump the manifest version and PACK_VERSION together" rule with the additive exception in the notes. docs/thps-warehouse-pieces.md: update the header line and closing audit note that still claim the pieces are not in the palette. docs/development.md only if the dev loop changes. Conventional commit with no attribution.
<!-- SECTION:PLAN:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-10-30T17:03:00Z

---

Scoping decisions confirmed with the user on 2026-10-30, before implementation starts:

- Per-piece placement metadata (original world transform plus inverse pivot) is a build-emitted committed sidecar, unity/pack-authoring/packs/thps/pieces.json, validated against the inventory by tests. Chosen over re-deriving pivots from the OBJ in build_thps_level.py, which would duplicate the partition logic in a second language.
- Window pieces ship render-only in this task: pass-through is their behaviour, so it travels with the piece from the start and TASK-025.04 only has to formalise and document it. Frames stay solid inside their wall pieces.
- Piece asset names are the inventory IDs verbatim, so one ID namespace spans the inventory tables, manifest.json, bundle:thps/<asset> catalogIds and the TASK-025.05 generator, and manifest/inventory consistency is directly testable.
- Pack-added mesh geometry (roof quads, floor patch, rail posts) is in scope as assets. Hidden grind and coping paths belong to TASK-025.04 and the game-prefab placements and settings-* rows to TASK-025.05: no bundle prefab is built for the boss portal, radio, piles, letters, tape, bonus chests or player start.

---

created: 2026-10-30T17:03:00Z

---

Constraints found while planning, with evidence:

- The pack version must stay 2.0.21. PACK_VERSION is inside the generated level bytes (scripts/build_thps_level.py line 577) and scripts/check_thps_preservation.py baselines both the exact level text and the manifest version, so bumping either fails byte-exact regeneration and the preservation check. The docs/asset-bundles.md "bump together whenever the bundle changes" rule predates this initiative and is incompatible with its hard constraint; this task amends it so additive kit assets do not bump while the shipped level pins the version. The 432 legacy asset fingerprints in the baseline are the real guard.
- Reproducibility carries over to every new asset: Pinned GUIDs, PinFileIds and ordinal ordering everywhere, so two builds stay byte-identical.
- Mirroring stays out of scope: the inventory notes a reflected module needs reversed winding and normals, not a negative collider scale, and both facings already exist as separate pieces. TASK-025.06 can revisit if authors need mirrors.
- Around 250 palette entries is expected and fine; the palette has a pager and search. The 65,535-vertex cap is per mesh, so the small piece meshes are unaffected; the bundle grows at most by roughly a second copy of the mesh.

---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Built the additive Warehouse construction kit in the thps pack. ThpsPack now partitions the extracted mesh by the inventory tables in docs/thps-warehouse-pieces.md (parsed at build time by the new Unity-free Assets/Editor/WarehousePieces.cs) and emits 214 source-face prefabs plus 1,552 pack-added prefabs (1,541 roof quads, 10 rail posts, one floor patch) alongside the untouched merged Warehouse and its collision mesh. Each piece: pivot-relative vertices in raw OBJ units under its convention pivot (RidingTransition, SurfaceCentre, CornerLipIntersection, LowerFaceCentre, BottomCentre), one submesh per material in ordinal order sharing the Warehouse materials, a per-piece collision mesh except render-only window pieces, and root localScale 79.2 so the editor's place tool spawns pieces at world size (found via in-game MeshRenderer bounds: unscaled clones were 20 cm pebbles).

The build rewrites the committed unity/pack-authoring/packs/thps/pieces.json sidecar (schema thps-pieces/1: module, convention, pivot, yaw, world position, collider flag per asset, plus meshToWorld scale) and manifest.json from the built asset list, keeping id/name/author/version; the pack version stays 2.0.21 per the additive-assets exception.

Tests written first: 49 C# tests (tests/MegabonkLevels.Tests/warehouse_pieces_tests.cs) over the parser and pivot maths, 9 Python tests (tests/test_thps_pack_pieces.py) cross-checking manifest, sidecar and prefab root scale. task check green (588 Python tests, C# tests, build, lint) and scripts/check_thps_preservation.py matches the shipped baseline.

Verified in the running editor through the megabonk MCP harness: palette lists 1843 entries, Tab:Packs and search filter find pieces by name with thumbnails; piece-taxi, added-post-0 and piece-room-window-se place at correct world extents (7.9x4.4x5.4, 0.5x2.7x0.5, flat pane); selection (red ring, 'selected placement:48 via nearest'), R rotation (yaw 0->90), Shift-drag move, stack guard ('place ignored, already stands'), Delete, and Undo/Redo both directions all logged; editor edits were restored to the 1241-edit baseline with nothing saved to levels/thps.mblevel.json.

Docs: docs/asset-bundles.md gained a Warehouse pieces section (naming, collision rules, sidecar, root-scale rationale, additive version exception); docs/thps-warehouse-pieces.md header and closing audit note now reflect live palette assets and separate harness-verified behaviour from open items (joint collision, hidden grind paths, save/reload, visual equivalence).

Committed as `feat(thps): expose Warehouse pieces as editor-placeable assets` (see git log). Open work deliberately deferred: grind/coping paths (TASK-025.04), game-prefab placements and settings-* rows (TASK-025.05).
<!-- SECTION:FINAL_SUMMARY:END -->
