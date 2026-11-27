---
id: TASK-085
title: Port Conker Colors as a Megabonk survival level
status: In Progress
assignee: []
created_date: '2026-11-22T02:18:00Z'
updated_date: '2026-11-22T07:07:00Z'
labels: []
dependencies: []
references:
  - 'https://conker.fandom.com/wiki/Colors'
documentation:
  - docs/thps-warehouse.md
  - docs/asset-bundles.md
  - docs/conker-colors.md
type: feature
ordinal: 296000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make the N64 Colors arena available as a second locally built level alongside Warehouse. Use stock Megabonk survival, without Conker match rules, characters or weapons.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A verified US ROM can build and install Colors and its pack with one documented command; wrong ROMs are rejected and generated assets remain local.
- [ ] #2 Both bases and the routes between them have aligned visible geometry and collision; stock survival starts at one base and can summon a boss at the other.
- [x] #3 Colors appears in Map Selection without replacing Warehouse, with automated importer tests and a live smoke check.
- [ ] #4 The largest playable character can pass through the arena’s intended doors, tunnels, dugouts, and sniper-tower openings; authored chests stand upright.
- [x] #5 Colors pits kill normal enemies, spare bosses and minibosses, and return the player to recent safe ground with damage.
- [x] #6 Stock shrines, merchants, and map pickups vary between runs and stay clear of narrow routes.
- [ ] #7 Colors places timeline minibosses on verified arena ground and blocks the reported two-Feather perimeter escape.
- [ ] #8 Colors conceals its lowered pit threshold and returns fallen authored chests to safe positions.
- [x] #9 Colors uses Warehouse’s shrine mix and chest luck, while rolling merchants and microwaves on approved open spots.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Validate the pinned US revision and export only scene 0x30 with the external conker_wtf extractor. Inspect bounds, spawn samples, and route geometry; write failing synthetic importer tests before implementing coordinate conversion and generation. Package the render mesh and dedicated collision as a separate Unity bundle in the existing pack pipeline, generate a stock-survival level, wire the local-only task and document usage. Run Python and pack checks, then verify Map Selection, traversal, player/monster collision, and boss summoning with the live game.

Measure player bounds and source opening clearances; adjust the shared render/collision transform and use Warehouse item orientation. Add an opt-in recovery floor and choose only open author-approved spots for randomized interactables; regression-test legacy levels and validate in Wine.

Inspect Forest Tier 1 containment. Add a cliff-backed collision perimeter, darken deep pit geometry, and ground late encounter spawns at approved points. Recover chests from the pit and share Warehouse encounter counts/loot settings; verify without changing Warehouse behavior.

Close the gaps and corner seams in the cliff backdrop with one visual-only rock basin, including a bottom beneath the recovery threshold. Add a geometry regression test for the upper sightlines and verify the rebuilt level visually.

Replace the added mountains with an invisible polygon fence derived from the original arena's projected collision footprint; keep only a low visual underlay. Correct microwave orientation and restore stock portal size while hiding its pedestal and preserving its interactable.

Reproduce the pinched bridge-side hillside and Tony McZoom’s southwest ridge escape. Use the exterior of the full above-pit collision projection rather than the slope cutoff to find the ridge, check nearby crest heights so the barrier does not dip along the approach, and add regressions for bridge clearance, rim continuity and the open pit. Verify the two-Feather route in live play before claiming containment.

The player still escaped the southwest rim. Replace the local jump-height estimate with a deterministic shared ceiling far above the highest source collision vertex. Keep the geometry-derived exterior, prove full exterior edge coverage without pit exceptions in the assertion, and separately prove the pit remains open. Rebuild and install without resuming or restarting the frozen game.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The pinned scene 0x30 export built both Unity bundles; task conker installed the Windows bundle and the survival level into the local Wine game. A wrong-ROM run failed before cache reuse. Six Colors importer and 28 shader policy tests pass. Live Map Selection registered Colors and Warehouse together; the arena rendered, supported the character on sampled terrain, and spawned stock enemies, two Charge Shrines, six chests, and a boss through the stock portal. A full continuous base-to-base traversal has not been verified; route collision checks used sampled positions and the source route evidence. Repository-wide task check is blocked by four failures in the pre-existing pcode lift work. Uncommitted.

Follow-up: increased shared scale 40%; stock data and active Ogre capsule report 4.75 height / 0.85 radius. Wine playtest moved Ogre through the SHC spawn exit into the valley and checked sampled tower/dugout interiors; did not traverse every opening or a continuous base-to-base route. Nine roof-clearance samples pass, and the upright chest visual was verified. Reported pit (now about -29.4,-36,88.2 at bottom after rescale) returned the player to the last ledge; Tony HP 70 to 55 with shield unchanged; all six spawned ordinary enemies in the pit were killed. Boss/miniboss exemptions verified by unit tests, not live. Two runs rolled different Shady Guy, shrine and power-up locations on approved spots; strict shrine placement no longer falls back into routes. Windows/Linux bundles built and Windows reinstalled. 2,868 C# tests and seven targeted Python tests pass; task check still fails the same four unrelated pcode tests.

Polish: inspected the built-in Forest Tier 1 through stock Map Selection. The Colors boundary now has four collision walls and a textured rock backdrop. The pit threshold is -46 and in-game recovery fired below it at -50.89. Added authored-chest recovery using the same policy; live forced chest-drop verification remains open. Added approved outdoor ground anchors for miniboss relocation; a live timeline spawn was not observed in the smoke run. Verified a live microwave and full Warehouse-style shrine roll on open spots. Both bundles rebuilt, the Windows one reinstalled, and task check passed. Latest Colors run is at the SHC start in the editor with enemy spawns off, normal damage and two Feathers.

Sealed the cliff backdrop into a continuous visual-only rock basin, closing the corner seams and hiding sky below the arena without changing collision or pit recovery. Nine Colors tests and task check passed. Rebuilt and reinstalled both platform bundles; checked steep downward live camera views at the east lip and north corner. Left Colors paused in editor at SHC spawn with enemy spawning disabled and two Feathers.

Removed generated mountains; 20 invisible walls follow the original collision footprint's convex outline and a visual-only floor remains far below the arena. Live verified the microwave stands upright and the unscaled portal with BottomPiece hidden can still summon a boss. task check passed. Left the rebuilt Colors run paused at SHC with spawning disabled and two Feathers.

Boundary rebuilt to trace the terrain rim: the collision mesh's faces gentler than 45 degrees are rasterized into two-unit cells, the mask is kept only where it is reachable from the level's own chest, shrine, power-up and miniboss anchors and above the pit floor, and one oriented box closes each straight run of exposed cell sides (558 boxes, 3036 world units, over 12885 cells). Rasterizing had claimed cells the faces do not cover; a wrong barycentric weight, now cross-checked against the sampled drop raycast. Nothing is generated below the map, and the boxes that would have stood over the pit are dropped so a fall still reaches the kill floor. Deleted the unused mesh-edge helpers and their tests. Eleven Colors tests and task check (2882) passed; rebuilt and reinstalled both bundles and confirmed 558 active boundary colliders in the running game, with the character resting on a box top after a drop, and a live fall through the pit to recovery. Left Colors paused in editor at the SHC spawn with enemy spawning disabled, normal damage and two Feathers.

Player testing invalidated the perimeter smoke check: the player got trapped between invisible walls at (-60, 13, 102) and jumped over the southwest mountain barrier. The collision mesh has continuous terrain at the trap (surface y ≈ 11.2, slope ≈ 66 degrees), but the 45-degree filter drops that terrain from the outline and puts several fence runs on the lower slope. Exact southwest takeoff and crossing still need localization; landing on one wall top did not validate containment.

Tony McZoom’s reported escape was near the overhead bridge. Geometry near the west crest had a wall top around y=86 near higher terrain at y=81. Updated the projected boundary to include steep terrain and use nearby takeoff surfaces for wall heights, while filtering pit edges before merging runs. The new bridge regression was red on the old generator, then passed with the full rim and pit regressions (58 focused tests total). Actual jump replay still outstanding.

The bridge-side jump still escaped the finite local-height barrier. Replaced local height estimates with a common top 1,000 units above the highest collision vertex (approximately y=1,110). The full extracted terrain perimeter is covered end to end with no pit exceptions; the pit stays open inside that perimeter. The regression failed on the old generator and passed on the replacement; reversing input face order produces identical wall data. All 58 focused tests passed. At user request this pass tested pure logic only; no bundle build, install, or game launch.
<!-- SECTION:NOTES:END -->
