---
id: TASK-021.24
title: >-
  Keep bosses and enemies from getting stuck below the level or inside Warehouse
  structures
status: To Do
assignee: []
created_date: '2026-10-29 09:13'
labels:
  - bug
  - enemies
  - thps-warehouse
dependencies: []
references:
  - /Users/lance/Desktop/Screenshot 2026-10-29 at 4.09.48 AM.png
parent_task_id: TASK-021
priority: medium
ordinal: 117000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
On the THPS Warehouse level, bosses (and some other enemies) end up somewhere the player cannot reach them, which blocks the "Defeat the Boss" objective.

Observed in a playtest (Easy, 10:34 into the run, dev readout on):
- Lil Bark was trapped in the room above the main half pipe. The readout showed the boss at pos(174, 26, 26) while the player was at pos(165, 17, -11), with the kill floor at -60. The boss stayed in the upper room and never reached the player.
- Bosses also get stuck below the level, under the playable area.

Likely causes to investigate: the NavMesh does not connect the upper rooms and structures to the ground, and the outer forest terrain around the Warehouse lets enemies walk or fall off the play area. One option is to remove the outer forest level so the main play area is enclosed. Treat that as a proposal to evaluate, not a decision; the alternative is walls or kill/respawn handling.

Related: TASK-021.11 covers general Warehouse gameplay fit (reachability, vert surfaces, enemies). Reproduce with `relaunch levels/thps.mblevel.json`, and use the dev readout and `query_objects` to find where a boss ends up.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Reproduce a boss stuck in the room above the main half pipe and a boss stuck below the level, and record the positions and cause in docs/development.md or the task notes
- [ ] #2 Stage bosses and minibosses spawned on the Warehouse level can path to the player from every spawn point, or are relocated/respawned when they cannot
- [ ] #3 No boss ends up below the playable area or inside a Warehouse structure after a full run to the boss fight
- [ ] #4 Decision on removing the outer forest terrain versus containing enemies another way is recorded with the reason
- [ ] #5 A regression check (Python test or harness command) covers the containment or reachability rule where it can be tested without the game
- [ ] #6 Verified in the running game: the boss fight completes on the Warehouse level without a stuck boss
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
