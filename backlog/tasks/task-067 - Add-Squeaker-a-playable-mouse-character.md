---
id: TASK-067
title: 'Add Squeaker, a playable mouse character'
status: To Do
assignee: []
created_date: '2026-11-12T22:18:00Z'
labels:
  - character
dependencies: []
references:
  - tools/simple_mouse.blend
  - src/MegabonkLevels.Mod/character_override.cs
  - src/MegabonkLevels.Mod/character_screen_patch.cs
documentation:
  - docs/development.md
  - docs/asset-bundles.md
  - docs/thunderstore.md
priority: medium
type: feature
ordinal: 226000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The mod has only ever restricted and reordered the stock characters (Calcium, Tony McZoom); it has never added one. Squeaker, a mouse, is the first new playable character, built from the Codex-generated tools/simple_mouse.blend in the same low-poly toon style as the stock cast. He throws a stale cookie the way Calcium throws a bone, and his unique trait is Tiny target: a smaller hitbox and higher base evasion, offset by lower max HP.

Decisions already made (restated for whoever picks this up):
- Integration: aim for a true new ECharacter slot (21, after Roberto=20) registered at runtime. The reverse-engineering subtask makes the go/no-go call on that. If it is no-go, fall back to a CharacterData cloned from Calcium that still appears as its own character-grid button.
- Packaging: ship as a separate Thunderstore package that depends on Megabonk_Level_Editor and carries the asset bundle. The core package stays asset-free and its six-file check is unchanged.
- The subtasks run in order: reverse engineering, Blender rework, Unity bundle, runtime registration, Thunderstore package, wiki and site.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
