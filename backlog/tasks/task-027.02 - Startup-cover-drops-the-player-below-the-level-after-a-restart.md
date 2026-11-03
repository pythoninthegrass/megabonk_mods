---
id: TASK-027.02
title: Startup cover drops the player below the level after a restart
status: To Do
assignee: []
created_date: '2026-11-03 03:51'
labels:
  - thps-warehouse
  - harness
  - startup
dependencies: []
references:
  - src/MegabonkLevels.Mod/startup_cover.cs
  - src/MegabonkLevels.Mod/startup_gate.cs
  - docs/development.md
  - levels/thps.mblevel.json
  - scripts/run.py
parent_task_id: TASK-027
priority: high
type: bug
ordinal: 146000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Restarting into the THPS Warehouse (loading levels/thps.mblevel.json into a game that already ran, e.g. scripts/run.py relaunch) consistently leaves the player below the level; the first boot into the level works. The player rests on the warehouse mesh's underside at y=-18.075 near (108, -18, 5.7): the level's floor is about y=-4.9 and the authored kill floor is -35, so the player is stuck under the floor without dying, and the run cannot be tested.

Live evidence (2026-11-02, fedora, Windows build under Proton Experimental, MelonLoader/Latest.log):
- 21:47:16 DevHarness: load-level thps.mblevel.json; 21:47:17 StartupCover: held where the game put the player; 21:47:18 KillFloor armed at y=-35.
- 21:47:19 DevHarness: teleport to (60.80, 18.60, -70.50) succeeded (state confirmed the position), then 21:47:22 StartupCover: player placed at the level start (109.00, 36.08, -116.00) overwrote it 3 s later.
- 21:48:44 and 21:48:45 two further StartupCover placements a second apart while KillFloor re-armed: a fall-through -> kill -> respawn loop. Later harness state shows the player at (108.3, -18.075, 5.73), below the floor and above the kill floor.

Context a fresh implementer needs: the Warehouse is one bundle-placed mesh (bundle:thps/Warehouse, scripts/build_thps_level.py), not tiles. The generated tile mesh (LiveEditPatch.GroundCollider()) does not cover the bundle mesh (independent live finding on 2026-11-02: BossSpawnRedirect down-rays against it logged "no ground under the boss" for both spawns). The startup cover (src/MegabonkLevels.Mod/startup_cover.cs, gated by startup_gate.cs, see "Custom-level startup cover" in docs/development.md) releases the player at the authored playerStart; if the bundle mesh's colliders are not ready at that moment on a restart, the player falls through the mesh skin onto its underside skirt, which is above the kill floor, so nothing kills them and they stay stuck. The cover also re-placing after a harness teleport breaks scripted verification.

Wanted outcome: after a restart the player stands on the level's floor at the authored start, and a harness teleport sent after load is not overwritten by the cover. Root cause (collider readiness vs cover timing, cover re-arming, or both) to be established from the running game before choosing the fix; the harness, state readout and logs are documented in docs/development.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Relaunching levels/thps.mblevel.json on a Proton host leaves the player standing on the level's floor: a state readout taken at least 5 seconds after the last StartupCover placement reports the player above the floor surface (not at y about -18), on a second and third restart of the same game process
- [ ] #2 A harness teleport sent after load is not undone by the startup cover: no 'StartupCover: player placed at the level start' log line follows a 'DevHarness: teleport' line, and state still reports the teleport point
- [ ] #3 No fall-through loop after a restart: KillFloor does not re-arm repeatedly at startup and no repeated StartupCover placements appear within a second of each other
- [ ] #4 First-boot into the level and stock non-custom startup behave exactly as before, and the TASK-027.01 guarantees (no spawn resets, no baseline-map flash) still hold
- [ ] #5 The established root cause is recorded in the task with the log evidence, and the 'Custom-level startup cover' section of docs/development.md covers the restart case
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
