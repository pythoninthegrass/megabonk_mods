---
id: TASK-021.28
title: Relocate minibosses like Chunkham out of the Warehouse's suspended glass box
status: Done
assignee: []
created_date: '2026-11-06 23:09'
updated_date: '2026-11-09 05:26'
labels:
  - bug
  - enemies
  - thps-warehouse
dependencies: []
references:
  - TASK-021.24
  - TASK-021.25
  - TASK-021.26
documentation:
  - docs/development.md
  - docs/thps-warehouse-layout.md
parent_task_id: TASK-021
priority: medium
ordinal: 170000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
On the THPS Warehouse level, stage bosses summoned by the boss portal are teleported out of the suspended glass box to a walkable spot in the level interior (TASK-021.25, TASK-021.26). Minibosses do not get the same treatment: a playtester who played a full Windows-package run (beat the boss, infinite ghost wave) reported minibosses such as Chunkham ending up stuck in the suspended glass box, where the player cannot reach or defeat them.

Outcome: minibosses on the Warehouse level end up somewhere reachable instead of stuck in the glass box, using the same relocation behaviour bosses already get. A stuck miniboss should not be able to block or clutter a run.

Context: minibosses come from the game's timeline events (the first, MinibossPig, spawns about 3 minutes into a run), not from the boss portal. See the Boss section of docs/development.md and the miniboss actor classification (`EEnemyFlag.SummonerMiniboss`). Which miniboss types the game can spawn and exactly where each lands in the box is not yet confirmed; the implementer should reproduce it first.

Reproduce: `relaunch levels/thps.mblevel.json` (needs `MEGABONK_DEV=true` and the `thps` pack installed), let the timeline reach a miniboss or trigger one through the harness, and watch where it lands with the dev readout and `query_objects`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Reproduce a miniboss (Chunkham or another type) stuck in the suspended glass box on the Warehouse level and record where it spawned and which miniboss types are affected in docs/development.md
- [x] #2 Minibosses spawned on the Warehouse level are relocated to a reachable walkable spot in the level interior, away from the glass box, using the same rule bosses use
- [x] #3 Boss portal bosses and Boss Curse copies keep their current relocation behaviour; the miniboss change does not move unrelated enemies
- [x] #4 A Python or C# unit test covers the new miniboss relocation rule where it can run without the game
- [x] #5 Verified in the running game: a miniboss that previously stuck in the glass box now reaches the player, and the result is recorded in docs/development.md
- [x] #6 docs/development.md describes the miniboss relocation alongside the existing boss spawn redirect
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reproduce on the fedora Windows/Proton box: add a log line for every Boss-flag spawn that BossSpawnRedirectPatch does not consume (position, enemy name, portal spawner position) and read where the timeline miniboss (MinibossPig at ~3:00) lands against the glass box.
2. Tests first in tests/MegabonkLevels.Tests/boss_spawn_redirect_tests.cs for a Unity-free rule: a Boss-flag spawn outside the portal arming window, on a level that gets the redirect, is a miniboss to relocate; portal and curse spawns and non-boss enemies are unchanged.
3. Implement in BossSpawnRedirect/BossSpawnRedirectPatch: miniboss spawns reuse TryFindSpot/FloorPlacement, anchored on the level's InteractableBossSpawner position (looked up on demand, since a miniboss can spawn before the portal is used), same ring, kill-floor margin and spacing rules.
4. Rebuild, deploy to fedora, verify a miniboss reaches the player; update docs/development.md (reproduction, affected types, relocation, verification).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
DoD #1 (task check) left unchecked: 17 Python tests fail identically on a clean HEAD (test_installer_parity, test_thps_preservation, test_thps_attachments) on this host; the C# suite passes (2006).

Narrow rule chosen with the maintainer: relocate only a Boss-flag spawn that lands in the glass-box band around the portal, for every miniboss type.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Minibosses spawned inside the Warehouse glass box are now moved out with the portal-boss placement rule (commit d1fda03). Timeline minibosses spawn on a ring around the player, so they only land in the box when the player is near it at box height; BossSpawnRedirect.IsInsideBossBox (XZ < 35 of the portal, y from 2 below to 10 above it) gates the move for any Boss-flag spawn outside the portal arming window. Verified on the Linux Proton box: with the player in the box, MinibossPig (Chunkham the Terrible) spawned inside it and was moved 59 units away, then reached and was damaged by the player. docs/development.md has a Miniboss relocation section. Unit tests added for IsInsideBossBox.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
