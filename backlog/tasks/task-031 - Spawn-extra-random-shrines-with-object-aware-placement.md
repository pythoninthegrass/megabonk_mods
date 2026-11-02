---
id: TASK-031
title: Spawn extra random shrines with object-aware placement
status: In Progress
assignee: []
created_date: '2026-11-02T04:32:00Z'
updated_date: '2026-11-02T06:26:00Z'
labels: []
dependencies: []
priority: medium
type: feature
ordinal: 138000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Shrines are the game's core risk-reward choice, but a map spawns a fixed set per seed. Spawning additional shrines at random spots each run adds variety and choice density. The pool includes charge shrines (ChargeShrine, spawned through the dedicated RandomObjectPlacer.chargeShrineSpawns channel rather than MapData.shrines[]), a shrine kind placed nowhere in the Warehouse today, so this also puts one in the run. The constraint is placement awareness: a shrine's interaction trigger is huge (its charge sphere is 12.5 units, per the editor picking notes in docs/development.md), so a badly placed shrine dominates the space around it — it can overlap trees, rocks and chests, or sit right on the routes players run (spawn portal, points of interest, boss portal) and effectively wall off a hot path with a trigger the player keeps bumping. Placement must probe the surface, keep clear of already-spawned objects, and keep the main routes clear. The spot-finding logic can share the placement-probing work of TASK-028 (relocating the shady guy, chests and Maoi) but is deliverable independently.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A configurable number of extra shrines (random types from the map's shrine pool, charge shrines included) spawn each run
- [ ] #2 No extra shrine overlaps an existing spawned object or sits inside another shrine's charge radius
- [ ] #3 No extra shrine obstructs the hot paths: player spawn portal, boss spawner, final portal, and the main routes between them
- [ ] #4 Extra shrines are functional: each can be activated and applies its effect (Challenge, Magnet, Cursed, Greed, Balance, Maoi, Charge)
- [ ] #5 Count and type mix are configurable (level file or mod option), and 0 restores today's behaviour
- [ ] #6 Verified in game on Forest across several seeds: shrines spawn in valid clear spots and none block a main route, including at least one charge shrine spawn
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
Implemented as a level-file feature sharing TASK-028's post-generation placement machinery.

1. Tests first (tests/MegabonkLevels.Tests/extra_shrines_tests.cs): additive schema-3 fields extraShrines (int, default 0) and extraShrineKinds (string[] | null); old-schema defaults; settings round-trip/undo/redo/CopyTo; kind-name validation ({challenge,magnet,cursed,greed,balance,moai,charge}, empty/absent = full pool); pure hot-path geometry (keep-clear around spawn/boss/final anchors and the straight spawn→boss→boss→final corridor, radius = 12.5 charge-zone reach); shrine-to-shrine keep-clear 12.5; pool filtering by kinds; count semantics (0 = no pass).
2. Pure policy in src/MegabonkLevels.Mod/extra_shrines.cs (Unity-free): ExtraShrineKind enum + type-name mapping, Enabled, KindFilter, HotPathClear, ShrineClear.
3. Runtime src/MegabonkLevels.Mod/extra_shrines_patch.cs: runs in FinishRandomizedGeneration after relocation, before cover release/kill-floor arm. Pool = MapData.shrines[] (CatalogPrefabs.TryFindMap) + RandomObjectPlacer.chargeShrineSpawns.prefabs + greedShrineSpawns.prefabs, filtered to live shrine components and configured kinds. Reuse TASK-028 probe (extract shared internal PlacementProbe from InteractableRandomizationPatch: reachable samples, surface/clearance/support/occupancy). Existing-shrine positions from the gen-id index plus placed objects. Anchors: spawnPortal, spawnPlatform, bossPortal, bossPortalFinal, graveyardBossPortal, player start. TryChoose budget 256; native-up alignment like TASK-028; Instantiate prefab (same pattern as editor SpawnObject); per-spawn log line + summary; fewer than requested with warnings when no spot found.
4. Lifecycle: static list of spawned extras; stale extras destroyed at the top of OnGenerationComplete before BuildIndex so they never leak into the index, edits, or a following vanilla run.
5. Wiring: level_file.cs fields + Equals; level_settings.cs Fields/Validate/CopyTo; live_edit_patch.cs editor-save round-trip and gate (randomize* || extraShrines > 0); editor_settings_panel.cs next-run message for extra* fields.
6. Verify in game on Forest via megabonk MCP: fixture levels derived from levels/example-forest.mblevel.json; several seeds; one run with extraShrineKinds ["charge"] to prove a charge shrine spawn; logs carry per-shrine positions checked against keep-clear numbers; screenshots of each placement from close camera; activation evidence: charge zone standing (progress UI in screenshot) and real-keyboard interact on a regular shrine via scripts/run.py menu drive; extraShrines 0 restores stock shrine count.
7. Docs: level-format.md table rows + Extra shrines section; map-generation-determinism.md private-RNG note; task check; conventional commit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Paused with implementation, tests and docs committed at 4069d07 (feat(levels): spawn extra random shrines with object-aware placement). task check green at pause: 1662 C# + 959 pytest + lint. Fixtures levels/extra-shrines.mblevel.json (extraShrines 4) and levels/extra-shrines-charge.mblevel.json (extraShrines 3, kinds charge) are in the commit.

Verified in game (Forest, megabonk MCP, three runs of the extra-shrines fixture): 4/4 spawned every run; kinds seen Cursed/Charge/Moai/Greed, Magnet/Charge/Moai/Moai, Challenge/Greed/Greed/Magnet; all ExtraShrines: log lines show nearestShrine/nearestRoute >= 12.5; pool=6, reachableFlatSamples ~2319-2324. Charge activation proven twice: zone sphere + rune glow while standing in it (teleport), then the Charge Shrine reward window with three offers and Ignore Offers. Upright screenshots for magnet, charge monolith and two Moai (Z-up fix). Evidence under .tools/evidence/ (extra-*.png).

Remaining for finalization: (1) run levels/extra-shrines-charge.mblevel.json and confirm Charge-only spawns; (2) a second seed (e.g. relaunch with seed override 1234567); (3) example-forest run showing no ExtraShrines: lines and stock shrine count for extraShrines 0; (4) real Interact evidence for a regular (non-charge) shrine. Item 4 needs OS-level input because harness key/mouse inject into EditorInput.Queue and never reach Rewired gameplay UI (Escape/E no-ops; menu drive is Linux-only) — the dismiss commands from TASK-033 are the intended unblock, so finish TASK-033 first or use osascript keystrokes into the CrossOver window.

Known caveat: extras use a per-run Guid seed, so the same level seed spawns different extra mixes between runs by design (documented in docs/map-generation-determinism.md).
<!-- SECTION:NOTES:END -->
