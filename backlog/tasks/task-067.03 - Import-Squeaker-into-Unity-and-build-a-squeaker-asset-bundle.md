---
id: TASK-067.03
title: Import Squeaker into Unity and build a squeaker asset bundle
status: To Do
assignee: []
created_date: '2026-11-12T22:18:00Z'
labels:
  - character
  - assets
dependencies:
  - TASK-067.02
references:
  - unity/pack-authoring/Assets/Editor/PackBuilder.cs
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - taskfiles/pack.yml
  - taskfiles/thps.yml
  - src/MegabonkLevels.Mod/pack_prefabs.cs
documentation:
  - docs/asset-bundles.md
  - docs/characters.md
parent_task_id: TASK-067
type: feature
ordinal: 229000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Blender exports from TASK-067.02 need to become a Squeaker character prefab and a stale cookie projectile prefab inside an asset bundle the mod can load at runtime. Existing bundles carry only level props and audio, built from unity/pack-authoring through Editor scripts and the pack taskfiles, so a character bundle has to follow the same build, install and shader-remap path.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A Unity prefab for Squeaker and a prefab for the stale cookie exist in unity/pack-authoring and meet the prefab requirements in docs/characters.md
- [ ] #2 An editor build method produces a squeaker bundle for both Windows and Linux
- [ ] #3 Tasks to build and install the squeaker bundle exist, mirroring the existing pack and thps tasks
- [ ] #4 The built bundle installs into the game's UserData and its prefabs resolve through the mod's pack loader with the toon shader remap applied
- [ ] #5 A pytest checks the built prefab and skips, rather than fails, when the generated bundle is absent
- [ ] #6 The import and build steps are documented in docs/characters.md
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
