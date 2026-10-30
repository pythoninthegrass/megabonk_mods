---
id: TASK-025.04
title: 'Keep collision, grind and window behaviour attached to their pieces'
status: Done
assignee: []
created_date: '2026-10-30T16:24:00Z'
updated_date: '2026-10-30T23:54:00Z'
labels:
  - level-editor
  - thps
dependencies:
  - TASK-025.03
references:
  - scripts/build_thps_level.py
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - src/MegabonkLevels.Mod/grind_gate_patch.cs
documentation:
  - docs/development.md
  - docs/thps-warehouse-pieces.md
modified_files:
  - scripts/build_thps_attachments.py
  - unity/pack-authoring/packs/thps/attachments.json
  - src/MegabonkLevels.Mod/object_attachments.cs
  - src/MegabonkLevels.Mod/pack_attachments.cs
  - src/MegabonkLevels.Mod/edit_operations.cs
  - src/MegabonkLevels.Mod/edit_stack.cs
  - src/MegabonkLevels.Mod/level_state.cs
  - src/MegabonkLevels.Mod/live_edit_plan.cs
  - src/MegabonkLevels.Mod/live_edit_patch.cs
  - src/MegabonkLevels.Mod/editor_editing_support.cs
  - src/MegabonkLevels.Mod/editor_object_tools.cs
  - src/MegabonkLevels.Mod/object_tool.cs
  - src/MegabonkLevels.Mod/pack_prefabs.cs
  - taskfiles/pack.yml
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - tests/MegabonkLevels.Tests/object_attachments_tests.cs
  - tests/MegabonkLevels.Tests/pack_attachments_tests.cs
  - tests/test_thps_attachments.py
  - docs/asset-bundles.md
  - docs/development.md
  - docs/level-format.md
  - docs/thps-warehouse-pieces.md
parent_task_id: TASK-025
type: feature
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Depends on TASK-025.03, which provides the placeable pieces. Grind behaviour in the Warehouse currently lives in hidden game rails laid along mesh edges by the generator, and the pass-through windows are an exception baked into the pack's collision mesh by world bounds. Both are tied to fixed positions, so once a piece moves on its own they would be left behind: a moved ramp would keep grinding where the old one was, and a relocated window would either stay solid or open a hole in whatever wall it moved into. The behaviour has to travel with the geometry it belongs to.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Moving, rotating, scaling or deleting a ramp or rail piece moves or removes its grind path with it, leaving no grindable edge behind
- [x] #2 Duplicating a piece gives the copy its own collision and grind behaviour, independent of the original
- [x] #3 Pass-through window behaviour belongs to the window piece, so a relocated window opens its own opening and does not punch one through unrelated geometry
- [x] #4 Rail posts and other support geometry stay attached to the piece they support
- [x] #5 Joined ramp modules hand off grinds cleanly across their seams
- [x] #6 The shipped level's grind and collision behaviour is unchanged, confirmed by the preservation check from TASK-025.01
- [x] #7 Tests cover the behaviour-attachment logic that can be exercised outside Unity, and docs record how a piece carries its collision and grind data
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
1. Preserve the shipped level, legacy Unity assets and pack version 2.0.21; retain baked per-pane collision and verify moved panes do not carve adjacent solid frames.
2. Serialize explicit attachments as ordered named catalog/local-transform/hidden descriptors in object.place. Atomically reserve owner/child IDs and optional placementId values so independent edits, undo/branch/save/replay remain stable and old payloads remain unchanged.
3. Implement and test pure ownership, validation, transform, active-state, ID and lifecycle logic; instantiate real selectable child objects through Unity parenting. Default clicks choose a hidden path's visible owner; Ctrl-click chooses the path. Removing an owner/rail stops any active descendant grind.
4. Generate committed pack-attachments/1 defaults from pieces.json, inventoried source bounds and unchanged legacy rail constants. Attach 41 grind subpaths and 17 supports to 36 pieces, splitting only on module boundaries with no short/overlapping segments. Install the metadata and snapshot it into palette placements; do not change the shipped Warehouse assets or generator output.
5. Verify temporary fixtures for owner transform/copy/delete/undo, independent supports/paths, moved panes, transformed native grinds, bidirectional seam handoffs and editor save/relaunch. Verify fresh palette placement includes defaults, undo it, and leave the shipped level unchanged.
6. Update docs, run full task check and preservation CLI, commit conventionally, and finalize only verified criteria. Complete assembled-level work remains in the existing follow-up tasks.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User approved explicit owner/local-transform attachment links, retaining individual editability.

Implemented optional object.place attachments and explicit placementId fields. IDs are reserved atomically for owner + ordered children, survive undo/branch/save/replay, and never depend on changed pack defaults. Runtime children use Unity parenting, retain their own selection targets and colliders, and support independent move/remove. Removing a rail or owner also stops a player already grinding its descendant rail. Empty new fields are omitted to preserve old payloads.

Committed build inputs/defaults: scripts/build_thps_attachments.py derives pack-attachments/1 metadata from pieces.json, source module bounds and unchanged legacy rail constants. It assigns 41 grind subpaths and 17 supports to 36 pieces; source support assets remain independently placeable. Spanning coping paths split only at module boundaries, with no overlapping segments and all lengths above 3.5. Pack installation copies attachments.json; palette placements snapshot it into edits. No changes to ThpsPack or generated Unity assets were necessary because pane collision was already baked locally.

Final selection modifier is Ctrl-click for a hidden grind path, ordinary click for its visible owner. Ctrl avoids conflicting with the free-fly camera's Alt-to-descend key. Visible supports remain normally selectable.

Runtime evidence in .tools/evidence/: 02504-attachments.mblevel.json (small fixture, not full Warehouse assembly), 02504-saved.mblevel.json (actual editor Save to unique UserData/Levels/02504-attachments-check.mblevel.json, then relaunched), and 02504-transformed.mblevel.json. Owner100 rotation carries hidden rail/posts while copy200 stays unchanged; Delete disables descendant colliders via activeInHierarchy and leaves copy children active; toolbar Undo restores owner pose/visibility. A nonuniformly scaled owner at (92,6,25), yaw90, scale(118.8,158.4,79.2), moves its rail to (98.92,-2.84,25.11). An independently deleted post remains disabled after owner remove/restore, while an independently moved post retains its adjusted offset. Window400 moved to (84,1,51), yaw90 and nonuniform scale, still has no MeshCollider; adjacent wall401 retains its enabled MeshCollider and bounds.

Native grind evidence: 02504-seams-positive.txt records two main-north seam handoffs at distance0.00/progress0/direction+1; 02504-seams.txt records middle-to-west handoff at distance0.00/progress1/direction-1. 02504-transformed-grind.txt records a native catch on the moved/scaled rail at (98.9,5.6,25.1), railSpeed19.5, and ordinary departure at its end. 02504-delete-active-grind.txt records deleting owner100 while progress0.25: StopRail ran and a live PlayerMovement query confirmed rail=null. Terminal test grinds eventually fell into the kill floor; subsequent tests used fresh relaunches, never reload over dead runs.

Fresh palette check in the shipped level: searching piece-rail-big-straight, selecting it, and placing on the retained bootstrap tile created one owner and six named children from installed defaults. Undo restored the shipped 1241-edit list with dirty=false; no changes were saved to levels/thps.mblevel.json. The temporary editor save above was a separate, uniquely named test file.

Validation: 1463 C# tests and 659 Python tests pass in full task check, including build and lint; final modifier refinement is being rechecked before commit. Preservation CLI matches the shipped baseline. Full assembled-level visual/joint verification stays in the existing follow-up tasks. Final handoff must leave the shipped level in editor mode, normal spawns/damage, and no forced slide override.

Final verification passed on the finished code: task check (1463 C# tests, 659 Python tests, build, markdownlint and ruff), git diff --check, and standalone shipped-Warehouse preservation check. Ctrl-click was verified in a fresh instance: selected placement:101 (hidden path), R rotated only that path from yaw90 to180 while its copy stayed yaw90. Last relaunch restored levels/thps.mblevel.json in editor mode with 1241 edits, dirty=false, normal damage/spawns and no forced slide override.

Implementation committed as 96b1642 (feat(thps): attach grind paths and supports to construction pieces). All acceptance criteria and Definition of Done items verified.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented piece-owned grind and support attachments without changing the shipped Warehouse or its pack version.

- Added explicit serialized attachment descriptors and stable placement IDs, atomic owner/child ID reservation, independent editing, transform propagation, deletion/restore, undo/redo and save/replay. Removing a piece stops an active grind on its rails.
- Added deterministic attachments.json defaults: 41 grind subpaths and 17 supports on 36 owners. Coping splits follow source module boundaries with no duplicate catch regions or segments shorter than the handoff radius. Palette placements snapshot installed defaults; pack installation copies the sidecar.
- Normal clicks select the visible owner of a hidden catch collider; Ctrl-click selects the hidden path. Window panes retain baked pass-through collision without carving unrelated walls.
- Updated the asset-bundle, level-format, inventory and development docs.

Verification: task check passed (1463 C# tests, 659 Python tests, build and lint); git diff --check and the standalone preservation check passed. Running-game checks covered fresh palette placement, independent copies/supports/paths, transformed native catches, active-grind deletion, bidirectional ramp seam handoffs and editor save/relaunch. The shipped level was restored in editor mode with its original 1241 edits, dirty=false and normal gameplay settings.

Implementation commit: 96b1642. Full assembled-level generation and whole-layout verification remain in the existing subsequent tasks.
<!-- SECTION:FINAL_SUMMARY:END -->
