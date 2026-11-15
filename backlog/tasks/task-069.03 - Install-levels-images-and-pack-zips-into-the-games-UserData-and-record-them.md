---
id: TASK-069.03
title: 'Install levels, images and pack zips into the game''s UserData and record them'
status: To Do
assignee: []
created_date: '2026-11-15 05:59'
labels:
  - installer
dependencies: []
references:
  - go/internal/content/content.go
  - go/internal/plan/plan.go
  - go/internal/proton/proton.go
  - src/MegabonkLevels.Mod/level_thumbnail_sidecar.cs
  - src/MegabonkLevels.Mod/pack_prefabs.cs
parent_task_id: TASK-069
priority: high
ordinal: 239000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The files the installer downloads must land exactly where the mod's loaders look for them, and the installer must remember what it installed so `--check` and `--uninstall` can work.

**Expected layout:**
- Level: `<game>/UserData/Levels/<slug>.mblevel.json`.
- Cover and biome icon: `<slug>.png` and `<slug>.biome.png` beside the level, matching `src/MegabonkLevels.Mod/level_thumbnail_sidecar.cs`.
- Pack: `<game>/UserData/LevelPacks/<id>/` holding the bundle `<id>`, `manifest.json` and `attachments.json` (`src/MegabonkLevels.Mod/pack_prefabs.cs`).

**Code to reuse in `go/internal/content`:** `ValidateLevelFile`, `ValidatePackSource`, `IsBundleName` and the path helpers.

**Zip extraction is currently duplicated** in `go/internal/plan/plan.go` and `go/internal/proton/proton.go`, both with zip-slip protection. Move it into one shared helper.

**The install record (`content.Record`) currently tracks MelonLoader state.** Change it to track:
- the installed mod version
- the BepInEx pack version
- levels: code to filename
- packs: id to version
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A level and its optional cover and biome image are written under UserData/Levels using the slug name; missing UserData folders are created
- [ ] #2 An existing level file of the same name is replaced and the replacement is reported
- [ ] #3 A pack zip is installed as UserData/LevelPacks/<id>/ and rejected if its contents fail pack validation
- [ ] #4 Archives with paths escaping the destination are rejected
- [ ] #5 Zip extraction exists in one place and the former duplicate copies are removed
- [ ] #6 The install record stores mod version, BepInEx pack version, installed levels and installed packs, and round-trips through save and load
- [ ] #7 Unit tests cover each behaviour using temporary directories
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
