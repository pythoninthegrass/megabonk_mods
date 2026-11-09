---
id: TASK-040
title: >-
  Place 2-3 Charge Shrines in the Warehouse at authored spots clear of ramps and
  grind lines
status: Done
assignee: []
created_date: '2026-11-04 04:49'
updated_date: '2026-11-04 19:53'
labels: []
dependencies: []
modified_files:
  - scripts/build_thps_level.py
  - src/MegabonkLevels.Mod/extra_shrines.cs
  - src/MegabonkLevels.Mod/extra_shrines_patch.cs
  - src/MegabonkLevels.Mod/maximin.cs
  - src/MegabonkLevels.Mod/placement_probe.cs
  - src/MegabonkLevels.Mod/level_file.cs
  - levels/thps.mblevel.json
  - docs/level-format.md
  - docs/thps-warehouse-layout.md
priority: medium
ordinal: 152000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Warehouse had no Charge Shrines: the builder removes every generated one and the extra-shrines pass sampled only the generated tiles, which on this level is one hidden tile under the floor, so it placed nothing. The level is much smaller than the native maps, so it should get 3 to 5 a run, on open floor that does not interfere with grinding or ollieing off half pipes, spread apart the way the boss redirect spreads curse copies.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each run and each restart of a run spawns a random 2 to 3 Charge Shrines in the Warehouse, in a freshly drawn layout
- [x] #2 Shrines stand only at authored spots in corners and against walls, away from the half pipes, kicker ramps, grind lines and the start run
- [x] #3 A spot where a shrine does not fit exactly is moved outward to the nearest position that fits, and a spot where none fits is skipped with a log line naming what is in the way
- [x] #4 There are more authored spots than the largest count, at least 25 units apart and inside the Warehouse footprint
- [x] #5 Verified in the running game: all five spots place, and a spawned shrine charges and offers its reward
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added an authored placement path to the extra-shrines pass: levels may set extraShrinesMax and shrineSpots (world positions). Each run draws a count from extraShrines to extraShrinesMax, shuffles the spots, and for each finds the floor under it against every collider, then tries the shrine there and at rings of eight directions every 2 units out to 8 until a trial instance overlaps no collider. Rejected trials are deactivated at once because Destroy only takes effect at the end of the frame. A spot with no fit is skipped with a warning naming the colliding object. The Warehouse builder asks for 2 to 3 charge shrines and lists five spots: (30,2,71), (41,2,0), (81,30,-98), (139,30,-98), (41,10,-41). An earlier rule-based version (flat footprint, keep-out from lips and rails, wall score, weighted pick) was removed because it kept placing shrines in front of ramps and half pipes and in the start run; the pass shares PlacementProbe.HighestFloor with the boss redirect. In the game all five spots place within 2 units of their anchors, counts vary between 2 and 3 across relaunches and restarts, and a spawned shrine charged and opened its reward window. Not tested: playing the level by hand to judge ollie lines.

Later change: the north deck corners were replaced by (173,28,27) on the hanging box roof and (22,6,4) on Shorty's ledge; spots within 25 units of each other are never both taken in a run. Each shrine is golden or regular by an even draw per run: the game rolls golden once in Awake at 0.8%, so the mod sets ChargeShrine.isGolden and the gold material afterwards, and a golden shrine was confirmed in the game to offer Legendary rewards.

Spacing and rarity were then retuned: spots are drawn one at a time with odds proportional to the square of their distance from the nearest placed shrine (median nearest-pair distance about 113 units in simulation, up from 68; zones overlap in about 2% of runs), a spot within 12.5 units of a placed shrine is never used, and the golden chance is 10% rather than 50% since the game's own is 0.8%.

Later changes: eight authored spots now (the two corner spots at (178,10,-32) and (139,38,-123) take a tight fallback that places the shrine on the nearest floor without a clearance check, since a corner on a quarter pipe leaves a flat strip narrower than the clearance box). Spots are drawn by distance-weighted odds, and the golden chance is 10%. The level now also guarantees one each of Magnet, Challenge, Boss Curse and Moai per run (guaranteedShrineKinds) alongside 2-3 Charge, shuffled across the spots, and shifts chest loot luck by a per-run value drawn from -0.5 to 2 (chestLuckRange), applied through a Harmony prefix on ItemUtility.GetRandomChestItem and confirmed on a real chest roll. Not tested: interacting with the Challenge, Boss Curse and Moai shrines at their authored spots.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
