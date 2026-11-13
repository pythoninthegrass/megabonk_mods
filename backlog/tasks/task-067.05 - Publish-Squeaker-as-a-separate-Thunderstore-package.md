---
id: TASK-067.05
title: Publish Squeaker as a separate Thunderstore package
status: To Do
assignee: []
created_date: '2026-11-12T22:18:00Z'
labels:
  - character
  - thunderstore
dependencies:
  - TASK-067.04
references:
  - thunderstore.toml
  - pkg/manifest.json
  - scripts/check_thunderstore_package.py
  - taskfiles/package.yml
documentation:
  - docs/thunderstore.md
parent_task_id: TASK-067
type: feature
ordinal: 231000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The core Megabonk_Level_Editor package is runtime-only and its package check requires exactly six files, so Squeaker's bundle cannot go into it. docs/thunderstore.md also says adding assets needs a licensing and layout review. Squeaker therefore ships as its own package that depends on Megabonk_Level_Editor, leaving the core package and its check unchanged.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A separate tcli config and manifest build a Squeaker package that declares a dependency on Megabonk_Level_Editor
- [ ] #2 A package check script verifies the Squeaker ZIP contents, modelled on the existing core package check
- [ ] #3 The core package manifest, thunderstore.toml and its six-file check are unchanged
- [ ] #4 The licence status of the Codex-generated mesh and its textures is reviewed and recorded in the package README
- [ ] #5 A README and icon for the package exist
- [ ] #6 The manual mod-manager import checklist in docs/thunderstore.md passes with the Squeaker package
- [ ] #7 The package is published to Thunderstore and its install is confirmed
- [ ] #8 docs/thunderstore.md documents the Squeaker package
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
