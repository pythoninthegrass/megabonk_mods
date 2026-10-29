---
id: TASK-021.22
title: End a grind before a wall with a StopRail patch
status: Done
assignee:
  - '@claude'
created_date: '2026-10-29 03:41'
updated_date: '2026-10-29T19:10:00Z'
labels:
  - thps
  - mod
dependencies:
  - TASK-021.21
documentation:
  - docs/thps-warehouse-layout.md
  - src/MegabonkLevels.Mod/rail_handoff_patch.cs
parent_task_id: TASK-021
priority: medium
ordinal: 113000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A grind that runs off the end of a rail launches the player along the rail's tangent. On the Warehouse coping rails (TASK-021.21), a lip that ends at a wall launches the player into it and the skater bails; the report was near (178, 7, 46), the east end of the main half pipe's south lip. Shortening the rail (WALL_ENDS and WALL_MARGIN in scripts/build_thps_level.py) does not fix it: the player coasts along the flat lip into the wall anyway.

The outcome is that a grind detaches from the lip with room to spare before a wall, instead of ending in a collision. Context for a fresh implementer: RailHandoffPatch (src/MegabonkLevels.Mod/rail_handoff_patch.cs) already postfixes PlayerMovement.StopRail on custom levels to hand a grind to the next rail. Extending that patch, or adding a sibling, to end the grind early when a wall lies ahead along the rail tangent is the likely route. docs/thps-warehouse-layout.md ("Coping rails on the half pipes and wall quarter pipes") records the wall ends found by probing the mesh and the harness limit: a harness drop only grinds west, so an eastbound grind needs a manual test.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Grinding a coping rail toward a wall ends the grind before the player reaches the wall, with no bail, at the east end of the main half pipe lips near (178, 7, 46) and the wall ends listed in WALL_ENDS
- [x] #2 Grinds that do not run toward a wall are unchanged, including the handoff between chained rails
- [x] #3 The detach distance and wall detection are covered by tests, written first, and the behaviour is documented in docs/thps-warehouse-layout.md and level-format.md where it applies
- [x] #4 Checked in game with an eastbound grind into the east wall
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Probe the API: PlayerMovement.RailMovement is what advances a grind each frame; StopRail, IsGrinding, Rail.Cooldown/IsOnCooldown. Wall ends are the lip table in docs/thps-warehouse-layout.md.
2. Tests first: rail_wall_end.cs holds the pure decision (DetachDistance, WallNormalMaxY, FacingDotMin, MinSpeed, MaxDismountSpeed, DismountHop, IsMoving, IsWall, ShouldDetach, DismountSpeed); tests/MegabonkLevels.Tests/rail_wall_end_tests.cs linked into the test csproj.
3. Patch: RailWallEndPatch postfixes PlayerMovement.RailMovement, gated on CustomLevelState.IsActive and IsGrinding(). Raycast ahead along the horizontal velocity; when a near-vertical face pointing back at the player sits within DetachDistance and no other rail within RailHandoff.SearchRadius is off cooldown to take the grind, StopRail, cap the horizontal speed, hop, and cooldown the rail. Chained joints keep handing off.
4. In game: task mod:build, relaunch the flipped-rail scratch level for the eastbound case, editor off, spawns off, teleport for the run-up; then relaunch levels/thps.mblevel.json for the westbound and handoff regressions.
5. Docs: the "Wall ends" and "Checked in game" bullets in docs/thps-warehouse-layout.md; level-format.md unchanged, no level field involved. task check, one conventional commit with no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation notes (final):

- Decision logic lives in src/MegabonkLevels.Mod/rail_wall_end.cs (Unity-free, so the net10 test project links it): DetachDistance 5, WallNormalMaxY 0.3, FacingDotMin 0.7, MinSpeed 2, MaxDismountSpeed 6, DismountHop 5, with IsMoving/IsWall/ShouldDetach/DismountSpeed.
- Patch: RailWallEndPatch (rail_wall_end_patch.cs), a Harmony postfix on PlayerMovement.RailMovement registered from megabonk_levels_mod.cs. Gated on CustomLevelState.IsActive and IsGrinding() so vanilla runs are untouched. It raycasts along the horizontal velocity, skips the player's own root and the rail being ground, requires a near-vertical face pointing back at the player, and defers to RailHandoffPatch whenever another rail sits within RailHandoff.SearchRadius off cooldown, which keeps the joint and pocket-tip chains intact.
- Detaching alone was not enough: the player keeps the grind's 19.5 speed and coasts into the wall anyway, so the detach also caps horizontal speed at 6 and adds an upward hop. Without the hop the player slides along the coping and the game re-catches the same rail several times; a hop of 8 was no better than 5.
- Dead end worth recording: PlayerMovement.canJumpOffRailAtTime does not gate the game's grind catch. Setting it to Time.time + 100 still re-caught the same coping 0.5s after the detach, so the line was removed rather than kept as decoration. Rail.Cooldown(playerCollider) is still called; it matters to RailHandoff's own PickNearest.
- Tuning history for DetachDistance: 10, then 16 while diagnosing the coast, then 10, then 5 at the user's request to bail closer to the wall. Verified bail fires 4.83 units short.
- AC1 wording names WALL_ENDS in scripts/build_thps_level.py; that constant was removed with the shortening approach, so the wall ends are the lip table in docs/thps-warehouse-layout.md.
- AC4: a harness drop only ever grinds west (a coping rail's progress 0 end), so an eastbound grind was run from a scratch copy with the two main-pipe coping rails rotated 180 degrees, .tools/evidence/thps-east-wall-scratch.mblevel.json. Same 57 unit run-up, same 19.5 grind speed, so the momentum is the game's own; the remaining harness gap is player-driven entry (ollie into a grind), which needs a keyboard.
- level-format.md needed no change: no level field is involved, and the sibling rail patches are documented in the layout doc only.
- Evidence: task check green (1235 mod tests, 487 python tests, lint clean). In game, eastbound: RailWallEnd ended the grind 4.83 short of a wall at (174.1, 7.9, 43.8), progress 0.058, speed 19.5 kept 6.0, player alive 70/70, no DeathRestart. Westbound regression on levels/thps.mblevel.json: chains onto the west diagonal (RailHandoff moved onto rail at distance 0.00, direction 1.0) with no RailWallEnd line. Detaches also observed at the north wall pipe's west end (3.71 short at 44.6, 11.0, -27.1) and the south wall lip (4.92 short at 26.1, 10.6, 101.1); the Shorty's ledge chain handed off seven times with no detach.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A grind on a Warehouse coping rail now lets go of the rail before the wall at its end instead of being launched into it.

Added RailWallEndPatch (src/MegabonkLevels.Mod/rail_wall_end_patch.cs), a Harmony postfix on PlayerMovement.RailMovement registered from megabonk_levels_mod.cs, and RailWallEnd (rail_wall_end.cs) holding the Unity-free decision logic and tuning constants. On a custom level only, while grinding and moving at least 2 units/s, it raycasts along the horizontal velocity for a near-vertical face pointing back at the player; when one comes within 5 units and no other rail within RailHandoff.SearchRadius is off cooldown to take the grind, it calls StopRail, caps the horizontal speed at 6 and adds an upward 5, then cools the rail down. Deferring to the handoff is what keeps chained joints, the pocket tip and the west diagonal intact.

Why the cap and the hop: releasing the rail alone left the player at the grind's own 19.5, coasting into the wall regardless. With both, Tony leaves the coping about 5 units out and comes to rest beside the wall at full health.

Verification: task check green (1235 mod tests including the 22 new rail_wall_end tests written before the implementation, 487 python tests, lint clean). In game, eastbound into the east wall from a 57 unit run-up: "RailWallEnd: ended the grind 4.83 short of a wall at (174.1, 7.9, 43.8), progress 0.058, speed 19.5 kept 6.0", player alive 70/70 with no DeathRestart. Westbound on levels/thps.mblevel.json still chains onto the west diagonal with no detach; the north wall pipe and south wall lip also detach at their west wall ends, and the Shorty's ledge chain handed off seven times untouched. Evidence: .tools/evidence/task-021.22-east-wall-detach.png.

Risks and follow-ups: the detach is tuned against the Warehouse lips, so a level with a much longer wall approach may still let the player touch the wall at low speed. The game re-catches the same rail once at low speed about half a second after the detach and its own StopRail ends that; PlayerMovement.canJumpOffRailAtTime looked like the gate for it but does not affect the catch at all (a 100 second window changed nothing), so it is left alone. The eastbound check used a scratch copy with the two main-pipe coping rails rotated 180 degrees, because a harness drop only ever grinds west; a player-driven entry into a grind (an ollie onto the coping) still needs real keyboard input.
<!-- SECTION:FINAL_SUMMARY:END -->
