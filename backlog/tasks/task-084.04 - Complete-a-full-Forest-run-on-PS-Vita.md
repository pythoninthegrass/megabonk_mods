---
id: TASK-084.04
title: Complete a full Forest run on PS Vita
status: In Progress
assignee: []
created_date: '2026-11-18T06:02:00Z'
updated_date: '2026-11-19T06:56:00Z'
labels:
  - ps-vita
  - vita-delivery
dependencies:
  - TASK-084.03
documentation:
  - .agents/skills/vita-port/SKILL.md
parent_task_id: TASK-084
type: feature
ordinal: 289000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Start only after the PCH-2000 swarm gate explicitly records GO (recorded in TASK-084.03; see docs/vita-combat.md "Gate verdict"). Turn the graybox loop into the first end-to-end stage. Use the pinned build as the behavioral reference and OpenBonk's reconstructed C# as the readable spec for gameplay systems, transliterated into the host-tested C core under vita/combat/. Credit OpenBonk as the source of the reused logic. Scope this task to a vertical slice: one character through Forest, with every other character, stage and content category left to TASK-084.05. Keep all game-derived artifacts local-only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 On a physical PCH-2000, one character goes from character selection through Forest map generation, traversal, combat and upgrades to a boss and normal run resolution.
- [ ] #2 Death and restart work, and earned offline progression survives a clean relaunch without touching desktop saves.
- [ ] #3 A representative full run records frame pacing, peak memory and any regressions against the GO benchmark.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Research (2026-11-18): the GO spike core is `vita/combat/` (combat.c 199 lines, one weapon, 2 upgrades, 240-slot enemy pool, flat 40-unit arena, no map, no character select, no boss, no persistence). The Vita is reachable on the home endpoint, and `task vita:combat:deploy` with `VITA_COMBAT_SSH` installs a VPK. OpenBonk spec lives in `unity/OpenBonk/Assets/Scripts/Assembly-CSharp/` (MapGenerator, MapGenerationController, MapGenerationFinalBoss, EnemySpawner, UpgradePicker, CharacterData, InteractableBossSpawner*, ProceduralTiles/*).

Proposed order, each step host-tested first in `vita/combat/test_*.c` and run via `tests/test_vita_combat.py`:
1. Run state machine: character select -> Play -> Upgrade -> Boss -> Resolved/Defeat -> restart (extends CombatPhase).
2. Character + weapon for one character (data table transliterated from OpenBonk CharacterData).
3. Forest enemy set and EnemySpawner pacing, XP/level curve and UpgradePicker offers.
4. Forest map generation (MapGenerator/ProceduralTiles port) producing a collision grid; traversal on it.
5. Boss spawner and run resolution.
6. Offline progression save under the Vita app data path (never desktop saves), clean-relaunch test.
7. Local-only Forest asset conversion (`.tools/`, not in repo or VPK) and renderer upgrade from graybox.
8. Device run: frame pacing and peak memory logged against the GO benchmark (p95 16.73 ms, 26 MiB MAIN / 23 MiB CDRAM bounds); docs/vita-combat.md updated with OpenBonk credit.

Open decisions for the maintainer before step 1: character choice, map-gen fidelity (exact port vs simplified layout), and whether step 7 uses converted game meshes or stays graybox for this slice.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decisions (maintainer, 2026-11-18): Tony McZoom; exact port of MapGenerator/ProceduralTiles; graybox rendering first, asset conversion last.

Step 1 partial (host-tested, uncommitted): COMBAT_VICTORY phase, boss spawner (`combat_interact`, 5-unit range, one boss per run), boss kill resolves the run, defeat then `combat_start` restart. COMBAT_BOSS_HP=60 is a placeholder until the Forest boss stats are ported from OpenBonk (SpawnStageBoss). Not yet wired into main.c/render.c, and no character select, map generation, persistence or device run yet. No acceptance criteria are met.

Correction (maintainer, 2026-11-18): the slice follows tier 1 like the native game; there is no victory screen. Boss kill opens the portal and play continues. OpenBonk spec (SummonerController.StartFinalSwarm, SwarmSummoner, CombatScaling): the final swarm starts when the stage timer reaches the stage time max (not on boss death), `finalSwarmTimer` restarts at 0, normal summoners stop, and ghosts spawn endlessly (Ghost, then GreaterGhost after 60 s, GhostPurple after 360 s, GhostRed after 720 s) at a 0.5 s interval toward a target of 50 + clamp(t*2.5, 0, 400 if t<120 else 300). Run ends by death or portal exit.

Implemented host-tested (uncommitted): COMBAT_VICTORY removed; boss_defeated/portal_open; final_swarm with swarm_ticks and combat_timer_ticks (HUD timer resets to 0:00); ghost tiers; ghost HP ceil(1.3 * 2^(t/30)) (assumption: how OpenBonk composes the 1.3 swarm multiplier with 2^(t/30)-1 is unconfirmed).

Open, confirm against the pinned build: Forest stageTime (COMBAT_STAGE_TICKS is a 600 s placeholder; the value is in a serialized asset), whether the swarm also fires on a timer expiry before the boss is killed, ghost speed scaling (1.2 plus clamp(0.5*(2^(t/30)-1), 0, 20)), and the swarm target multiplier (treated as 1). Not yet wired into main.c/render.c (no HUD timer, portal or ghost rendering).

Maintainer confirmed (2026-11-18): the final swarm starts when the stage timer reaches the stage time max, as in OpenBonk; the existing implementation already does this. Added boss-death `PickupAllXp` parity (collect_all_xp, host-tested; may open the upgrade menu).

Device finding (2026-11-19): after the boss died the swarm did not start. Cause: OpenBonk `SummonerController.OnBossDied` also destroys all normal summoners and raises the stage timer to stageTimeMax - 10 s (bossDeadGracePeriod), so the final swarm starts 10 s after the boss kill. Implemented host-tested (COMBAT_BOSS_GRACE_TICKS; normal spawning stops on boss defeat). Not yet reinstalled on the Vita. Supersedes the earlier note that boss death only opens the portal.

Device check (2026-11-19, PCH-2000): after the boss kill the swarm began after the 10 s grace period, matching OpenBonk. Ghost tiers, HP growth and portal exit still unchecked on device.

Portal exit (uncommitted, host-tested, VPK builds, not yet installed): after the boss dies, Square within 5 units of the portal ends the run with a RUN COMPLETE summary (COMBAT_EXITED; Cross restarts). OpenBonk's non-final portal loads the next stage (InteractablePortal.DoLoadNextStage); the slice has no next stage, so the summary stands in for it and mirrors the completesExternalRun path (stats screen).

Device check (2026-11-19, PCH-2000): portal exit works as designed (prompt, Square, RUN COMPLETE, Cross restart). Still uncommitted.

Character data (committed f448e1f, host-tested, VPK builds, not installed): vita/combat/character.c holds Tony McZoom and Wireless Dagger values read from the pinned build; move speed x1.3 applied. Health 70, shield, pickup range and the dagger are staged until Forest enemy HP/damage are ported (native units would break the spike balance). The dagger is a bouncing projectile, not the spike's hitscan beam, so it needs a projectile simulation. WeaponData.baseStats read back as raw garbage through query_objects; upgrade modifiers list is raw ids only (see docs/vita-combat.md).

Upgrade offers (host-tested, VPK builds, not installed): vita/combat/upgrades.c ports OpenBonk's offer rules (3 distinct offers, new-vs-owned draw, luck-weighted rarity, rarity multipliers, weapon 1-2 modifier rule, stat formula with tome accumulators); replaces the spike's Power/Haste menu. Pool is the dagger plus 13 enabled non-achievement tomes read from the pinned build; 2 tome slots. Effects wired: move speed, attack speed (shot interval), pickup range. Everything else is accumulated and displayed only. Open: achievement-locked tomes assumed unavailable on a fresh profile; other weapons not offered; tome raw values (e.g. Regen Flat 40) unverified against in-game text.
<!-- SECTION:NOTES:END -->
