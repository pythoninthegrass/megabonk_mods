---
id: TASK-086.05
title: Record the Mountain Pass look and layout from the KF2 playthrough frames
status: To Do
assignee: []
created_date: '2026-11-27 19:45'
updated_date: '2026-11-27 19:45'
labels:
  - level
  - kf1
dependencies:
  - TASK-086.01
references:
  - tools/kf2_mountain_pass_frames/
  - tools/videos/KF2_Mountain_Pass.webm
documentation:
  - docs/kf1-mountain-pass.md
  - docs/thps-warehouse.md
modified_files:
  - docs/kf1-mountain-pass.md
parent_task_id: TASK-086
priority: medium
ordinal: 300500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-086 rebuilds KF-MountainPass (Killing Floor 1, Unreal Engine 2) as a Megabonk level. TASK-086.01 exported the authoritative data (T3D actors and brushes, the 16-bit terrain heightmap, umodel glTF meshes and TGA textures, all under the gitignored `.tools/kf1/`) and docs/kf1-mountain-pass.md records it. That export says what the map contains but never how the place reads while you move through it: which side of the valley the buildings sit on, how steep the ground is, where the road runs, what the sky and fog do, and how a wave approaches. This task supplies that reading by working through playthrough frames and writing the result into docs/kf1-mountain-pass.md, so later tasks (BSP rebuild, pack, in-game verification) do not have to watch the video.

Reference footage: `tools/videos/KF2_Mountain_Pass.webm`, one complete Killing Floor 2 survival run of the Mountain Pass rework (2560x1440, 60 fps VP9, 16:25). It is already cut to 910 frames at 1 fps: `tools/kf2_mountain_pass_frames/frame_0001.jpg` to `frame_0910.jpg`, 2560x1440 JPEG, gitignored, 296 MB. Frame N is video time 20.483 + (N-1) seconds (the ffmpeg extraction lands 29 frames after the requested start; measured by MD5 against the source's own frame timestamps), `frame_0001` is spawn with the loadout overlay still up and `frame_0910` is the VICTORY screen after the final boss. The regeneration command is in the "Playthrough reference footage" section of docs/kf1-mountain-pass.md. Regenerate if the directory is missing; never invent a frame number.

Output is a look-and-layout reference inside docs/kf1-mountain-pass.md, modelled on the structure of docs/thps-warehouse.md: frame ranges by area, one section per physical feature with cited frames and size estimates that name their scale reference, a wave-flow section, a global look section, and an explicit Unresolved list.

KF2 caveat: the footage is Tripwire's Unreal Engine 3 KF2 rework, not the KF1 map. Meshes, materials, lighting and vegetation in the frames are KF2's own. Label look notes as KF2 look. The KF1 export stays the source of truth for anything built, so where the frames disagree with it (terrain extent, the 12 `PlayerStart` ring near (0, -1,500), the 157 `ZombieVolume` and 4 `ShopVolume` placements, the brush cluster far south at Y -10,000 to -12,000, the `BlackTexture` brushes of unknown purpose), record the conflict and defer to the export instead of reconciling it by guesswork. The HUD is fixed in every frame: Trader distance and wave counter top left, XP and health/armor bottom left, ammo, cash and inventory bottom right, weapon-pickup banners top center. Ignore all of it when reading geometry. No ripped frame, texture or map content goes into a commit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 docs/kf1-mountain-pass.md has a section per physical feature visible in the footage: terrain and valley shape, the road and its bridges, building complexes, fences and gates, vegetation, vehicles and props, interiors, and the map edges, each citing the frame numbers that show it best
- [ ] #2 Every size or height estimate names the scale reference it used and is given in KF1 world units where possible (the terrain grid is 64 units per heightmap sample) rather than in pixels
- [ ] #3 A wave-flow section says where enemies approach from, where the trader and shop volumes sit, and which routes the run takes, with cited frame numbers
- [ ] #4 Look notes (sky, fog density and color, palette, material families, time of day) are labeled KF2 look instead of being treated as KF1
- [ ] #5 Conflicts between the footage and the KF1 export are recorded with the export winning, not silently reconciled
- [ ] #6 Anything the frames cannot resolve is listed as unresolved rather than guessed
- [ ] #7 Only docs/kf1-mountain-pass.md changes, no frames or map content are committed, and task check passes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Confirm `tools/kf2_mountain_pass_frames/` holds frame_0001.jpg through frame_0910.jpg, all 2560x1440. If missing, regenerate with the ffmpeg command in the "Playthrough reference footage" section of docs/kf1-mountain-pass.md and re-verify the count.
2. Read all 910 frames in six parallel read-only passes of roughly 150 frames (1-150, 151-300, 301-450, 451-600, 601-750, 751-910). Per frame log: area identity, direction of travel, features visible, scale cues, and whether it is a shop, pause, loadout or results screen rather than play.
3. Build the area to frame-range index from the logs and pick the one to three best frames per feature.
4. Re-open every frame that will be cited, directly, before writing its claim. Reject any claim that does not survive the re-look.
5. Cross-check placement and extent claims against the Contents of the map, The BSP and Layout sections of docs/kf1-mountain-pass.md (12 PlayerStart ring, 157 ZombieVolume, 4 ShopVolume, the roughly 12,000-unit terrain bowl, the far-south brush cluster, the 29 BlackTexture brushes). Record agreements as corroboration and disagreements as conflicts with the export winning.
6. Write the new sections into docs/kf1-mountain-pass.md following docs/thps-warehouse.md's shape, and extend the existing Playthrough reference footage section with the frame-range index rather than duplicating it.
7. List everything the frames cannot resolve as Unresolved, each with what would resolve it (a render, the in-editor look, a second video angle).
8. Run task check, verify each acceptance criterion against cited frame numbers, and commit docs/kf1-mountain-pass.md alone with a conventional commit and no attribution.
Doc-only spike: there is no testable logic, so the test-first Definition of Done item does not apply; say so in Implementation Notes, as TASK-021.01 did.
<!-- SECTION:PLAN:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
