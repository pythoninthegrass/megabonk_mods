---
id: TASK-025.05
title: Generate a separate Warehouse level assembled from the construction pieces
status: Done
assignee: []
created_date: '2026-10-30T16:24:00Z'
updated_date: '2026-10-31T02:28:00Z'
labels:
  - level-editor
  - thps
dependencies:
  - TASK-025.01
  - TASK-025.03
  - TASK-025.04
references:
  - scripts/build_thps_level.py
  - levels/thps.mblevel.json
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
documentation:
  - docs/thps-warehouse.md
  - docs/thps-warehouse-layout.md
  - docs/level-format.md
  - docs/asset-bundles.md
modified_files:
  - scripts/build_thps_editable_level.py
  - levels/thps-editable.mblevel.json
  - src/MegabonkLevels.Mod/level_settings.cs
  - src/MegabonkLevels.Mod/editor_settings_panel.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
  - src/MegabonkLevels.Mod/editor_escape_input.cs
  - src/MegabonkLevels.Mod/editor_mode.cs
  - src/MegabonkLevels.Mod/level_file.cs
  - src/MegabonkLevels.Mod/pack_manifest.cs
  - src/MegabonkLevels.Mod/pack_prefabs.cs
  - src/MegabonkLevels.Mod/game_pack_version_check.cs
  - src/MegabonkLevels.Mod/level_loader_patch.cs
  - src/MegabonkLevels.Mod/live_edit_patch.cs
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - unity/pack-authoring/packs/thps/manifest.json
  - tests/test_build_thps_editable_level.py
  - tests/MegabonkLevels.Tests/level_settings_tests.cs
  - tests/MegabonkLevels.Tests/pack_kit_version_tests.cs
  - tests/MegabonkLevels.Tests/thps_editable_level_tests.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - taskfiles/thps.yml
  - docs/asset-bundles.md
  - docs/level-format.md
  - docs/thps-warehouse-layout.md
  - docs/thps-warehouse-pieces.md
parent_task_id: TASK-025
type: feature
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Depends on TASK-025.03 for the pieces and TASK-025.04 for their behaviour. The value of the kit is only realised when the Warehouse itself is expressed as an assembly of those pieces rather than one injected asset: that proves the set is complete, gives authors a working reference layout to take apart, and lets the same geometry be reused in new levels. It must be a second level file — the shipped levels/thps.mblevel.json and the assets it loads stay exactly as they are, which is what the preservation check exists to enforce.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A new level file reproduces the Warehouse layout from the individual pieces rather than one injected Warehouse asset
- [x] #2 Its appearance and gameplay match the shipped level, confirmed by side-by-side screenshots through the megabonk MCP harness
- [x] #3 Script-authored markers and settings that affect the arena — player and boss spawn placement, the boss portal, the radio, collectible placement, kill floor height and grind settings — are editable rather than fixed by the generator
- [x] #4 The shipped levels/thps.mblevel.json and the pack assets it loads are untouched, confirmed by the preservation check from TASK-025.01
- [x] #5 Pack versioning records the added assets so a level saved against the new kit reports a mismatch against an older pack
- [x] #6 Tests cover the generator's new piece-assembly logic, and docs describe how to regenerate the editable level and how it relates to the shipped one
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
1. Add a separate deterministic scripts/build_thps_editable_level.py and levels/thps-editable.mblevel.json. Consume pieces.json world transforms at scale79.2 and snapshot attachments.json. Exclude suppressed-post pieces and attached supports from roots; reserve stable owner/child IDs. Reuse legacy terrain, removals, portal, radio, collectibles and settings; never emit Warehouse or duplicate legacy rails. Write assembly tests first.
2. Add separately versioned kit metadata while preserving manifest version2.0.21 and the shipped baseline. Record/check kit revision only for levels referencing kit assets, warn on older missing/different revisions, and preserve legacy payloads. Cover save and both load paths.
3. Add editable player-start and independent boss-destination markers, and an editor settings panel backed by validated editor-local state with dirty tracking, undo/redo and save/load. Cover gameplay settings, music/presentation metadata, and guard generation changes against stale seed-specific edits. Keep ordinary portal/radio/collectible editing. Write pure C# tests first.
4. Generate and install the separate level, document regeneration and compatibility, add separate task commands, and preserve existing defaults.
5. Build/relaunch through megabonk MCP. Compare matched-camera shipped/assembled screenshots, collision/windows/grind seams/spawns, object counts/performance and edited settings/marker persistence via unique save/relaunch. Keep broader authoring walkthrough in025.06.
6. Run focused tests, full task check, standalone preservation check and diff check. Finalize only objectively verified criteria, conventional commit without attribution.

Final editor design: marker coordinates and marker-to-camera/locate actions live in the Level panel; settings use an explicit separate Undo/Redo history while Save/dirty state combines settings and object edits. Construction-kit compatibility uses optional manifest kitVersion/kitAssetPrefixes and level packKitVersions; no legacy version or preservation baseline change.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User approved proceeding with the researched handoff plan, including separate kit-revision compatibility metadata rather than changing the pinned legacy pack version. Initial working tree clean. Current sidecars:1766 assets,9 suppressed-post exclusions,17 attached supports,1740 roots plus58 children(41 rails/17 supports),1541 roof quads.

Implemented separate editable generator/output:1740 roots plus58 snapshotted children(41 rails/17 supports), all1541 roof quads, excluding9 archival remnants and duplicate support roots. Python tests first failed on missing module, then10 pass; C# kit/settings tests first failed on missing APIs, then focused tests/replay pass. First full check:1483 C# and669 Python tests pass, build0 warnings/errors; only a markdown blank-line lint failure, now fixed. Standalone preservation baseline matches.

Running-game evidence .tools/evidence/02505-comparison-{start,main,room,pocket,roof,patch}.png pairs identical cameras through MCP: visible geometry/layout match across the six views. Assembly loads2948 edits versus shipped1241. No missing piece prefabs seen. Settings player-start edit[110,38,-116] made dirty=true with unchanged edit count; settings Undo restored dirty=false, Redo dirty=true, Save cleared it. Unique02505-editable-settings-check save/relaunch retains changed marker and kit revision1. Further unique02505-editable-all-settings-check save/relaunch retains boss destination169,-4.933437,20, kill floor-36, slope87 and grindRequiresSlide=false. Live PlayerMovement.maxSlopeAngle reads87; KillFloor log arms at-36. Cyan marker is visible at edited start after relaunch. Normal damage/spawns remained enabled.

Implementation refinements: settings history has its own explicit Undo/Redo buttons, separate from object history; existing Save tracks either as dirty. Editor-only marker lines moved to DontDestroyOnLoad scene to avoid indexing them as generated scenery. Marker Locate uses editor camera pose rather than direct transform. Player-start watch now begins after synchronous edits finish, preventing large assemblies consuming its time budget. Map/stage/tier/seed changes under existing edits and in-place loads with a different generation are explicitly refused. Full pack rebuild and final runtime grind/window checks remain underway.

Final validation after complete Windows/Linux pack rebuild: task check passes (1483 C# tests,671 Python tests, build with0 warnings/errors, markdownlint and ruff); standalone preservation check and git diff --check pass. task thps:editable-install regenerates/installs the separate file successfully. A concurrent check during Unity regeneration briefly saw temporary missing generated assets; rerun after the rebuild completed is fully green.

Full-layout gameplay check:02505-kit-grind.log records a native catch and two distance0.00 main-north module seam handoffs, then a distance0.00 handoff onto the hip. Runtime MeshCollider queries show active scene colliders for the three main-north pieces and room wall frames, with no window-piece MeshColliders. The final rebuilt pack reproduces the matched-camera main view(02505-rebuilt-kit-main.png). The player-start log confirms placement after edits; after unpausing, the player is on the start slope.

Runtime compatibility check used the actual editor-saved02505-editable-settings-check file against an installed manifest with pre-revision metadata: warning explicitly reports saved kit revision1 versus installed missing(02505-old-kit-warning.log). Reinstalled the current manifest/bundle immediately afterward and freshly relaunched the reference assembly. Final game is in editor mode on thps-editable,2948 edits,dirty=false,normal damage/spawns and no forced slide override;02505-final-editor.png shows the cyan marker and settings panel. No source changes to levels/thps.mblevel.json, legacy generator or preservation fixture.

Implementation committed as e02dffd (feat(thps): assemble a separately editable Warehouse level). All six acceptance criteria verified; full check and preservation are green. Broader construction-kit authoring walkthrough remains in025.06, which was not started.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added levels/thps-editable.mblevel.json and its deterministic generator:1740 piece roots plus58 snapshotted children, with no merged Warehouse, duplicate supports or free-standing legacy grind paths. Added player-start/boss-destination marker controls and a validated Level settings panel with independent Undo/Redo, combined dirty tracking and save/relaunch persistence. Added separate kit revision metadata and warnings for older packs while preserving legacy version2.0.21 and the shipped Warehouse baseline. Documented regeneration, install, controls and compatibility; added thps:editable-level/install commands.

Verified task check(1483 C# tests,671 Python tests, build and lint), complete Windows/Linux pack rebuild, preservation CLI and diff check. MCP evidence covers six paired camera views, native module/hip grind handoffs, collision/window ownership, actual editor save/relaunch and a saved-file warning against pre-kit-revision manifest metadata. Final game is on the editable assembly in editor mode,clean2948-edit state,normal spawns/damage and no forced slide override.

Implementation commit:e02dffd. Full authoring walkthrough remains in the existing follow-up task025.06.
<!-- SECTION:FINAL_SUMMARY:END -->
