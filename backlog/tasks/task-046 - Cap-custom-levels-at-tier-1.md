---
id: TASK-046
title: Cap custom levels at tier 1
status: Done
assignee: []
created_date: '2026-11-05T20:20:00Z'
updated_date: '2026-11-05 23:38'
labels:
  - custom-levels
dependencies: []
references:
  - backlog/tasks/task-043 - Log-boss-spawn-and-defeat-events-in-the-mod.md
priority: medium
ordinal: 166000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Taking the tier 2 portal from a custom level dropped the player through the level, because no custom level is built for tier 2. Custom levels should not offer progression past tier 1: find where the game decides the next tier or portal destination after a custom level's boss fight and cap it at tier 1, so a custom level never advances to a tier 2 stage. Related: tier 1 behaviour was observed in TASK-043 (A_BossDefeated True, waves continue after the kill).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A custom level cannot lead to a tier 2 stage: the tier 2 portal is absent, inert, or redirected, decided and recorded in the task
- [x] #2 The behaviour is verified in the running game by completing the boss fight on the Warehouse
- [x] #3 Vanilla runs are unaffected and still advance to tier 2
- [x] #4 The rule is documented in docs/development.md
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Observed target (done): in-game Tier 1 (harness tier 0) has no portal after the boss; waves continue. Tier 2 (harness tier 1) activates a portal to a vanilla stage.
2. Decision (AC #1): absent. Custom runs always start the game at tier index 0, so the game never offers a portal; no portal patch is needed (the portal never activates, so Interact is unreachable).
3. TDD: Unity-free `CustomTierCap.Clamp(int tier)` (returns 0 for any tier above 0) with xunit tests written first, seen failing.
4. Apply it at the single chokepoint, LevelLoaderPatch.PrepareRun (`mapTierIndex`), and log one line when a level's tier was capped. The file schema and the four entry paths are unchanged.
5. Verify in game: relaunch the Warehouse with `--tier 1`, kill the boss, confirm the log line, no active portal and waves continuing (AC #2). Vanilla is untouched by construction since PrepareRun only runs for custom loads; confirm a stock run still reaches the Tier 2 portal if the menu can be driven (AC #3).
6. Document the rule in docs/development.md and the `tier` row of docs/level-format.md; task check; conventional commit with no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Observation 1 (example-forest, harness tier 1, spawns on): boss kill logs A_StageBossDied, A_BossDefeated True, A_NumBossesDefeated 1. One of three PortalBlue InteractablePortal objects becomes active. Interacting with it loads a freshly generated vanilla stage (A_GenerationComplete with a new mapSeed, Forest2 particles), and the HUD shows 'Tier 2 / DEEP FOREST'. So the harness tier argument is 0-based: harness tier 1 is the in-game Tier 2. The in-game Tier 1 is harness tier 0, which has not been observed yet.

Observation 2 (example-forest, harness tier 0 = in-game Tier 1, editor off, invulnerable, spawns off): boss kill logs A_StageBossDied, A_BossDefeated False, A_NumBossesDefeated 1. No InteractablePortal is active 10 s after the kill (all three PortalBlue inactive). The HUD objectives become 'Find the Boss Portal' done, 'Defeat the Boss' done, 'Survive...' with a countdown from about 10:00. The Tier 2 portal is presumably spawned when that countdown ends; not yet confirmed. An earlier tier 0 attempt made with the editor still on proved nothing: the player died and no portal appeared, so tests must run with `editor off`.

Finding (confirmed by the maintainer): in-game Tier 1 (mapTierIndex 0) never activates a portal after the boss; waves continue. Tier 2 (mapTierIndex 1) activates a portal that loads a vanilla-generated Tier 2 stage, which is the drop-through when a custom level runs there. Every committed level has tier 0, but tier can still reach 1+ through four paths: the level file `tier` field, the harness load override, new-level, and the editor level settings. The single chokepoint is LevelLoaderPatch.PrepareRun, which builds `mapTierIndex = level.Tier`.

Implemented CustomTierCap (custom_tier_cap.cs, tested first: red on the missing file, then green) and applied it in LevelLoaderPatch.PrepareRun. Verified on the Warehouse with `relaunch --tier 1`, editor off, invulnerable: log `LevelLoader: tier 1 capped to 0`, boss kill logged A_BossDefeated False, all three PortalBlue stayed inactive, HUD objective 'Survive...'. Decision for AC #1: the portal is absent (the game never activates it at tier index 0). AC #3 not run in the game: vanilla runs never reach PrepareRun, but a stock run to the Tier 2 portal was not driven through the menu.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Custom levels now always run at the game's Tier 1 (mapTierIndex 0). CustomTierCap (custom_tier_cap.cs, unit tested) clamps the tier and LevelLoaderPatch.PrepareRun applies it, so the level file tier, the harness load override, new-level and the editor settings are all capped; a capped load logs `LevelLoader: tier <n> capped to 0`. Tier 1 never activates a portal after the boss, which removes the drop-through into a vanilla Tier 2 stage. Verified on the Warehouse at `--tier 1`: cap logged, A_BossDefeated False, all PortalBlue inactive, objective 'Survive...'. Vanilla runs never reach PrepareRun, so AC #3 was accepted by construction rather than driven through the stock menu. Rule documented in docs/development.md ("Custom tier cap") and docs/level-format.md.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
