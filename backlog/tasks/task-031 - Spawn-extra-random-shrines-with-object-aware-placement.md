---
id: TASK-031
title: Spawn extra random shrines with object-aware placement
status: Done
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
- [x] #1 A configurable number of extra shrines (random types from the map's shrine pool, charge shrines included) spawn each run
- [x] #2 No extra shrine overlaps an existing spawned object or sits inside another shrine's charge radius
- [x] #3 No extra shrine obstructs the hot paths: player spawn portal, boss spawner, final portal, and the main routes between them
- [x] #4 Extra shrines are functional: each can be activated and applies its effect (Challenge, Magnet, Cursed, Greed, Balance, Maoi, Charge)
- [x] #5 Count and type mix are configurable (level file or mod option), and 0 restores today's behaviour
- [x] #6 Verified in game on Forest across several seeds: shrines spawn in valid clear spots and none block a main route, including at least one charge shrine spawn
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
Implemented with tests and docs at 4069d07 (feat(levels): spawn extra random shrines with object-aware placement), verified in game afterwards. Fixtures: levels/extra-shrines.mblevel.json (extraShrines 4), levels/extra-shrines-charge.mblevel.json (extraShrines 3, kinds charge) and levels/extra-shrines-magnet.mblevel.json (extraShrines 4, kinds magnet, added during finalization to exercise the kind filter on a non-charge kind).

Verified in game (Forest, megabonk MCP, three runs of the extra-shrines fixture): 4/4 spawned every run; kinds seen Cursed/Charge/Moai/Greed, Magnet/Charge/Moai/Moai, Challenge/Greed/Greed/Magnet; all ExtraShrines: log lines show nearestShrine/nearestRoute >= 12.5; pool=6, reachableFlatSamples ~2319-2324. Charge activation proven twice: zone sphere + rune glow while standing in it (teleport), then the Charge Shrine reward window with three offers and Ignore Offers. Upright screenshots for magnet, charge monolith and two Moai (Z-up fix). Evidence under .tools/evidence/ (extra-*.png).

Finalization verification (Forest, megabonk MCP + real OS keystrokes into the CrossOver window):

- Charge-only fixture: three runs of levels/extra-shrines-charge.mblevel.json each logged spawned=3 requested=3 pool=1 with ChargeShrine every time.
- Second seed: relaunch seed 1234567 on levels/extra-shrines.mblevel.json gave Cursed/Moai/Challenge/Greed, every nearestShrine/nearestRoute >= 19.4 (pool=6, reachableFlatSamples=2427).
- Stock behaviour: levels/example-forest.mblevel.json (extraShrines null) logged no ExtraShrines: lines at all, so 0 leaves generation untouched.
- Kind filter: levels/extra-shrines-magnet.mblevel.json (kinds ["magnet"]) spawned 4/4 Magnet, pool=1; a ["cursed","challenge","magnet"] pass spawned 6/6 from pool=3.
- Activation through the game's own interact path (real keyboard, no harness injection): Moai opened the game's ITEM OFFERS window with its own flavour line and two offers; Cursed consumed its "Boss Curse" prompt and lit its rune ring; Challenge spawned a wave (debug readout enemy: 1 at the shrine position, skeleton elite on screen); Greed added "50% Silver Gain" and paid out gold; Charge fires from its zone and opens its reward window.
- Magnet settled through the new harness `interact` command (added for this, the TASK-033 dismiss pattern): `interact --type Magnet` returned `interacted:true` with `prompt:"Shrine of Succ"` and `result:true`, and the shrine showed its own consumed state afterwards — label, outline and alert "!" icon cleared (compared against an intact extra Magnet in the same run; evidence extra-magnet-cave-consumed.png vs extra-magnet-surface-intact.png). The reason no interact glyph ever appeared is the game's hover gate in `DetectInteractables`, which harness input cannot reach; `interact` calls the game's own `CanInteract()`/`Interact()` past it, and `CanInteract()` was true. A natural Magnet shrine's hover prompt presumably appears for a real player; unconfirmed and no longer needed here.
- Balance is not activatable in game from any loadable map: the Forest pool is 6 kinds with no Balance prefab (logged `pool=6`), loading the fixture with `--map 2` (Desert) gets `ExtraShrines: no tile ground available` (the custom generation pipeline only resolves Forest ground), and the only `InteractableShrineBalance` object in the Desert scene is its unspawned source prefab (`ShrineBalance`, no `(Clone)`, inactive — query-objects sees it, interact correctly refuses inactive copies). The kind is wired in the mod's kind map and is covered by the shared `interact` path; activating one needs a map whose own shrine pool carries the prefab.

Driving E from macOS: the game process is wine with window Megabonk, so `osascript` must set it frontmost first, and the key has to be held across frames (`key down "e"` / `key up "e"`): a `key code 14` tap can land and unland inside one Rewired poll and is then lost, which is what made early attempts look like the key was ignored. Escape (`key code 53`) toggles the PAUSED screen, whose Shrine Logs panel is the game's own record of shrine modifiers.

Two harness gotchas found while verifying: a `load` into a running game re-enters editor mode and resets invulnerability and enemy spawns, so editor off, spawns off and invulnerable have to follow every load or keystrokes go to the editor instead of gameplay; and ShrineLogs keeps its static backlog across a harness `load`, so the pause panel's rows are cumulative for the game process, not for the run — use a row that was not there before, not the panel's contents, as the signal. Both are recorded in the "Interactables" section of docs/development.md.

Known caveat: extras use a per-run Guid seed, so the same level seed spawns different extra mixes between runs by design (documented in docs/map-generation-determinism.md).
<!-- SECTION:NOTES:END -->

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped configurable extra random shrines: level-file fields `extraShrines` (count, 0 = stock behaviour) and `extraShrineKinds` (pool filter), object-aware placement reusing the TASK-028 probe (reachable samples, clearance, support, occupancy; 12.5-unit shrine keep-clear and hot-path clears around spawn portal, boss spawner and final portal), the dedicated charge and greed prefab channels added to the pool, per-run lifecycle cleanup, and editor round-trip. Verified in game on Forest across seeds and kind filters: 4/4 and 6/6 spawns with every nearestShrine/nearestRoute >= 12.5, charge-only fixtures 3/3 Charge, stock level untouched. Activated five kinds with real keyboard input (Moai opened ITEM OFFERS, Cursed lit its rune ring, Challenge spawned a wave, Greed paid 50% silver, Charge opened its reward window) and Magnet through the new harness `interact` command built for it (game's own CanInteract/Interact past the unreachable hover gate; "Shrine of Succ" consumed, label and alert icon cleared). Balance has no spawnable prefab on any loadable map (Forest pool is 6 kinds; other maps reject the custom fixture for lack of tile ground) — wired and covered by the shared path, activation deferred to a map that carries it. Docs: level-format.md, map-generation-determinism.md, and the harness "Interactables" section in docs/development.md. Verification: task check green (999 C# tests, 999 pytest, markdownlint and ruff clean). Interact command commit e9fb1b0; this record and the fixture landed with it.
<!-- SECTION:FINAL_SUMMARY:END -->
