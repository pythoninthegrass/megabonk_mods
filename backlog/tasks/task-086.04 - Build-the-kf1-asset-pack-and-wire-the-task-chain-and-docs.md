---
id: TASK-086.04
title: Build the kf1 asset pack and wire the task chain and docs
status: To Do
assignee: []
created_date: '2026-11-27 08:20'
updated_date: '2026-11-27 18:27'
labels:
  - level
  - kf1
dependencies:
  - TASK-086.02
  - TASK-086.03.01
documentation:
  - docs/kf1-mountain-pass.md
  - taskfiles/conker.yml
  - taskfiles/pack.yml
parent_task_id: TASK-086
priority: medium
ordinal: 303000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add `unity/pack-authoring/Assets/Editor/Kf1MountainPassPack.cs` (reusing `PackBuilder.cs`), `unity/pack-authoring/packs/kf1/manifest.json` (id `kf1`, asset `MountainPass`), and `taskfiles/kf1.yml` with verify, export, convert, pack and install, included from `Taskfile.yml` beside the Conker and THPS includes. The export stage reproduces the UCC and umodel steps recorded in docs/kf1-mountain-pass.md from a Killing Floor 1 install. Keep docs/kf1-mountain-pass.md current and add it to the wiki allowlist only if it should be public. Then verify in the running game: relaunch with the new level, enter editor mode, and screenshot the spawn, shop spots, map edges and a drop past the edge so walls and the kill floor are exercised. Confirm the log has no `pack 'kf1' is not installed` line.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `task kf1` runs verify, export, convert, pack and install end to end
- [ ] #2 The level loads in game with no pack-missing placeholder
- [ ] #3 Screenshots show the player, shrines, chests and boss spawner on the ground
- [ ] #4 A drop past the map edge is stopped by walls or the kill floor
- [ ] #5 docs/kf1-mountain-pass.md documents the full chain
<!-- AC:END -->



## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
