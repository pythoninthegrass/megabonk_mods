---
id: TASK-056.05
title: Package MegabonkLevels for Thunderstore and verify the manager install
status: To Do
assignee: []
created_date: '2026-11-08T23:31:00Z'
updated_date: '2026-11-08T23:31:00Z'
labels:
  - bepinex
  - thunderstore
dependencies:
  - TASK-056.04
  - TASK-056.01
modified_files:
  - thunderstore.toml
parent_task_id: TASK-056
priority: medium
type: task
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The migration exists so users can install from Thunderstore with a mod manager. The package must carry the manifest, readme and icon, declare the BepInExPack dependency, publish via tcli, and install cleanly through r2modmac into the Wine-hosted game. Licensing for any bundled level or pack content must be decided before the first publish.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Package source (thunderstore.toml, manifest.json, README.md, 256x256 icon.png) lives in the repo and tcli build produces a valid package
- [ ] #2 The manifest declares the dependency BepInEx-BepInExPack_IL2CPP-6.0.788
- [ ] #3 The package installs through r2modmac into the Wine-hosted game and the mod loads and runs in-game from that install
- [ ] #4 The last MelonLoader-only build is tagged before the first publish, and the licensing decision for bundled level/pack content is recorded
- [ ] #5 Publishing uses the Thunderstore team account with no personal credentials in the repo, and any superseded release is deprecated, not deleted
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
