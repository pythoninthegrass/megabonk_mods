---
id: TASK-028
title: 'Randomize the shady guy, chests and Maoi shrine per run'
status: In Progress
assignee: []
created_date: '2026-11-02T04:32:00Z'
updated_date: '2026-11-02T05:51:00Z'
labels: []
dependencies: []
modified_files:
  - src/MegabonkLevels.Mod/editor_settings_panel.cs
  - src/MegabonkLevels.Mod/interactable_randomization.cs
  - src/MegabonkLevels.Mod/interactable_randomization_patch.cs
  - src/MegabonkLevels.Mod/level_file.cs
  - src/MegabonkLevels.Mod/level_loader_patch.cs
  - src/MegabonkLevels.Mod/level_settings.cs
  - src/MegabonkLevels.Mod/live_edit_patch.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - tests/MegabonkLevels.Tests/interactable_randomization_tests.cs
  - docs/level-format.md
  - docs/map-generation-determinism.md
priority: medium
type: feature
ordinal: 135000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In stock Megabonk the interactables that matter run to run land at fixed spots for a given seed: the shady guy merchant (InteractableShadyGuy; the catalog's ShadyGuy prefab), chests (InteractableChest) and the stone-head Maoi shrine (InteractableShrineMoai). The mod's seed-determinism work (docs/map-generation-determinism.md) pins every spawn phase, so a level replays identically every run — an author who wants replay variety gets none: same shopping trip, same chest spots, same Maoi, every time. Let a level re-roll where these specific interactables spawn on each run while the rest of the world stays deterministic.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 With randomization enabled, two runs of the same level file and seed place the shady guy, chests and Maoi at different spots
- [x] #2 Randomized placements stay valid: on the ground surface, upright, reachable, and not overlapping other spawned objects
- [x] #3 With randomization off (default), placement is unchanged and the seed-determinism guarantee from map-generation-determinism.md still holds
- [x] #4 Randomization can be toggled per object kind, e.g. randomize chests while pinning the shady guy
- [x] #5 Verified in game on Forest: consecutive runs show different spots, and turning it off restores today's placement exactly
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Implemented and verified:
1. Add default-false additive schema-3 randomizeShadyGuy/randomizeChests/randomizeMoai flags; preserve serialization/equality, editor settings/history, load paths and saves. Tests were written before implementation.
2. Preserve generation phase seeds and genId assignment. Apply saved edits, then, only when enabled, wait one frame for native Start callbacks before relocating generated target roots. Keep authored moves/removals/placements pinned and finish before releasing the startup cover.
3. Use private per-run RNG, bounded candidate search and a 4x4-per-tile ground sample graph constrained by edited tile topology and ground-following physical sweeps. Ignore player/spawn portal colliders for traversal. Reserve merchants/Maoi before chests.
4. Validate flat ground, full footprint support and renderer/collider clearance. Retain original ground-to-pivot offsets; align native model up axes (merchant Y, chest/Maoi Z) to world up. Warn/retain originals if no safe candidate; terrain-only maps warn/no-op.
5. Verify fresh offline Proton runs on wm2: all-enabled twice, chests-only, disabled restoration, authored move/remove/place, no-safe fallback. Compare live transforms against matching disabled baseline hashes, assert native up and ground offsets, and inspect in-game saves. Document the pre-existing seed-20261008 baseline variance rather than changing unrelated generation logic.
6. Update level-format/determinism docs, run task check, commit conventionally and record final verification.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Started in worktree /Users/lance/.local/share/opencode/worktree/0a2b8c/task-028-interactable-randomization from 41ba0a7. Main working tree contains unrelated in-progress harness/fall-damage changes; left untouched.

Worktree branch: feat/task-028-interactable-randomization. Research: seed_force_patch.cs seeds both shared RNGs per spawn phase, so changing phase seeds would perturb non-target objects. LiveEditPatch.OnGenerationComplete builds genId index before applying edits and calls StartupCover.OnContentReady afterward; selective relocation must preserve this identity/edit ordering. Existing ReachabilityValidator is tile-topology-only and cannot alone certify clearance around props. Required commands task/dotnet/uv are available. Worktree has no Directory.Build.props (also absent in main); inspect generated build settings and local game references before full build/deploy. No implementation changes yet; proposed author-pinning policy awaits user approval.

User approved the proposed approach and authored-object pinning policy.

Runtime target changed by user from fedora to wm2 because another agent is using Fedora. Fedora was inspected and received a separate ~/git/megabonk-task028 source directory only; no game launch, DLL deployment, Steam changes or checkout overwrite were performed there. Use wm2 for all runtime verification.

Implemented flags/settings/load/save wiring plus Unity-free policy and runtime adapter. First tests failed compilation before implementation, then passed (8 new cases, including settings toggles/history, pinning, bounded sampling and routing around obstructed tile centers). task check passed after linking the main checkout's gitignored THPS extraction, Unity Thps assets and OST into this isolated worktree; no tracked main files changed.

Offline runtime is on wm2 using the Windows build under Proton Experimental, directly launched as user systemd services (no Steam URI/account launch). Installed the existing offline shim with scripts/swap_steam_stub.py after backing up the original to steam_api64.dll.steamstub.bak; previous mod DLL also backed up at ~/megabonk-task028-backup. Isolated verification sources/artifacts are under ~/git/megabonk-task028/.tools/task028 on wm2 and .tools/task028 locally.

Runtime fixes: physics clearance must ignore the player's non-trigger collider and DetectPickups collider; a four-by-four physical sample grid avoids falsely treating tree-obstructed tile centers as unreachable. Ground-following sweeps handle slope transitions. Maoi root orientation is native Z-up (-90-degree asset rotation), so preserve it and remove source-ground alignment instead of replacing it with a Y-only Euler rotation. The apparent un-cloned ShadyGuy root was an inactive prefab, not a live stage placement; no genId/index changes were needed. Forest seed 20261007 had no live shady guys; seed 20261008 generates two, plus 44 normal/2 free chests and four Maoi.

Verified interim seed-20261007 run moved all 46 chests and four Maoi with zero fallback. Compared every clone root's position/rotation/scale against disabled baseline: only Chest and ShrineMaoi sets changed. All four moved Maoi native-up vectors dot world up approximately 1.0. Formal same-seed8 baseline/repeat/toggle/pinning/fallback matrix is running; criteria remain unchecked pending that evidence. One direct-Proton startup fault required stopping only its own systemd unit and retrying; switched launch verb to waitforexitandrun to avoid prefix shutdown races.

Completed the first seven-case offline wm2 matrix. Same-baseline all-enabled/chests-only/restored-off runs shared pre-pass objectsHash 655E98AC3061714E46FB21C57E40F0405F1B34F1577C52DEDA96B6FB111448E1 and tile hash DCB4AF0871BE067FCD67013D8360BD31AA487B2432C56DA99000CEA69188CEF2. All-enabled changed only Chest/ChestFree/ShadyGuy/ShrineMaoi clone-root transform sets (52 objects), chests-only changed only Chest/ChestFree (46), restored-off matched that cohort exactly. Two enabled runs produced different positions for every kind. Authored moved and placed chests stayed at [120,0,20] and [140,0,20], and the removed generated target was not randomized. In-game saves preserved three flags and retained 0 edits for generated-only runs or exactly 3 authored edits; no roll was baked into edits. No-safe-start fixture moved 0 and retained original target positions; the merchant's native look-at rotation follows the far-away test player, so fallback comparison uses its position/scale rather than that native rotation.

Existing baseline limitation found during verification: seed 20261008 has produced ABE1206D7F31EAE91DD71E8B6EBE704C46B8CD3180B733060BF23F03ABADB3BD, 655E98AC3061714E46FB21C57E40F0405F1B34F1577C52DEDA96B6FB111448E1 and FF86D0A8EFE7A84BBF56DC50B81FB89C9DE0CE0A83A6C76087ED8020B53B862F before the relocation callback, including disabled runs. Did not expand scope to change shared RNG/physics generation; documented this open baseline-drift limitation in docs/map-generation-determinism.md and used baseline-matched comparisons to isolate this feature.

Final upright correction: source-ground alignment is not a reliable proxy for the object's current up axis (chests do not consistently inherit source slope tilt). Added tests first for native local up axes (merchant Y, chest/Maoi Z), then align the transformed native axis directly to world up while retaining heading. Final-build runtime matrix and task check are rerunning after this correction. Interim native-up dot checks confirmed all randomized merchants and Maoi upright; chest checks caught the issue before finalization.

Final runtime sequencing fix: native InteractableChest.Start (RVA 0x453AB0 in the inspected Windows build) rotates yaw and adds random tilt after generation completes. Aligning during A_GenerationComplete was therefore overwritten. The enabled-only FinishRandomizedGeneration coroutine now yields one frame, verifies session identity, relocates/straightens targets after native Start, then releases content readiness and arms the kill floor. Disabled runs retain their original synchronous path. No native Start callback is skipped, so its RNG draws remain intact.

Final-build offline wm2 evidence: all-after-start and all-after-start-B each moved all 52 targets (2 shady guys, 44 normal chests, 2 free chests, 4 Maoi); every target kind had different final positions between runs. All 52 live native-up vectors dotted world up >0.9999, and every relocation log had groundOffset within 0.001 of zero. Both enabled runs and chests-after-start matched disabled off-native's pre-pass objectsHash ABE1206D7F31EAE91DD71E8B6EBE704C46B8CD3180B733060BF23F03ABADB3BD. Their only changed clone-root transform sets were the enabled target kinds; chests-only moved exactly 46 and left merchants/Maoi unchanged. off-after-start (baseline hash 655E98...) matched the earlier disabled off-seed8-restored snapshot exactly, confirming disabled restoration independently of the documented baseline cohorts.

Final authored fixture moved 50 eligible generated targets while preserving the moved chest at [120,0,20], placed chest at [140,0,20], and removal target. Saved generated-only files contained 0 edits; saved authored files contained exactly the original 3 edits, with all flags intact. Final no-safe fixture moved 0; all target positions/scales matched the disabled cohort and chest/Maoi original rotations were retained. Numeric comparison assertions passed; artifacts and summary are under .tools/task028/final-verification-summary.json and the corresponding *after-start* logs/snapshots/saved files.

Final task check passed: mod build clean, 1,562 C# tests passed, 919 Python tests passed, markdownlint and ruff passed. git diff --check passed. Native-up policy, compatibility defaults/migration, independent toggles/history/copy, authored pinning, bounded candidate rejection and sample routing have 13 new Unity-free test cases. Unity Thps assets were materialized into an ignored test-assets directory after the temporary directory symlink showed as untracked; no asset symlink is being committed.
<!-- SECTION:NOTES:END -->
