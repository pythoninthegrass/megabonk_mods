---
id: DRAFT-002
title: True god mode and noclip fly that keep the run going
status: Draft
assignee: []
created_date: '2026-11-08T07:55:00Z'
labels: []
dependencies:
  - TASK-054.02
references:
  - src/MegabonkLevels.Mod/player_invulnerability.cs
  - src/MegabonkLevels.Mod/editor_mode.cs
  - .tools/il2cpp_dump/dump.cs
parent_task_id: TASK-054
priority: low
type: feature
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Proposed while planning the console and not yet confirmed by the maintainer, so it stays a Draft until approved. Two Fallout staples have no faithful equivalent in the mod:
- **`tgm` (god mode):** the harness `invulnerable` command adds Mirror and Feathers item stacks. That makes the player hard to kill, but it is not true invulnerability. It changes the inventory, so it changes builds and screenshots, and it may not block every damage source. A real god mode would ignore damage without touching items.
- **`tcl` (noclip):** the map editor flies freely but freezes the run. There is no way to fly through geometry while enemies, timers and music keep running, which is what you want for checking level geometry and enemy pathing live.

The console verbs from TASK-054.02 alias `tgm` to the existing invulnerable command at first. If this task is approved, `tgm` should switch to true god mode, and the Mirror/Feathers behaviour stays reachable under its own verb so relaunch defaults keep working.

Constraints already known: Harmony-patching an engine icall, or a folded/shared method RVA, has crashed the game before (see docs/development.md and the project notes). Pick patch targets accordingly and verify them in game.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Maintainer approves scope before the task leaves Draft
- [ ] #2 god mode on: the player takes no damage from enemies, projectiles, hazards or fall damage without any change to the inventory; off restores normal damage
- [ ] #3 noclip on: the player flies through geometry with the run unpaused; off returns to normal movement without falling through the floor or tripping the kill floor
- [ ] #4 Both verbs are gated behind MEGABONK_DEV, have harness commands with run.py/MCP wrappers, and tests for their testable logic
- [ ] #5 docs/development.md documents both and how they differ from invulnerable and editor mode
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
