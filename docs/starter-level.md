# Bramblecrown Hill

Bramblecrown Hill is an original example level, supplied separately from the
Megabonk Level Editor package. Its five visual districts use Forest, Graveyard,
Dungeon, Desert and Hell props and ground materials around a tall hill with a
ruined watchpost. Gameplay uses Forest stage 0: foreign materials do not change
stock enemy rosters or generation rules. The level's explicit boss/miniboss pools
override eligible boss picks, not ordinary enemies. No level packs or custom
music are needed.

## First play

Copy `levels/bramblecrown-hill.mblevel.json` from the source repository into the
game's `UserData/Levels/`. For its selection illustration, copy
`levels/bramblecrown-hill.png` alongside it. The Thunderstore package contains the
editor runtime only; see the [player guide](player-guide.md) for installation.

Choose **Play**, choose a character, then select **Bramblecrown Hill** on Map Selection and confirm Tier 1. The entry has a green hill illustration; the illustration is not an in-game screenshot.

You start in an open meadow with a free chest to the left, a distinctive rock ahead and to the right, and a tall wall of hillside straight ahead with the watchpost tower above it. A fence line of rocks and bushes leads from the meadow to the foot of the hill. The terrain graph connects every cell without jumping or jump-height upgrades; the spiral was reported walkable during manual testing, while the remaining routes still need physical checks. Drops of up to two height steps are configured to be safe (`fallDamageFreeHeight:40`); larger drops retain normal character fall damage. This expanded landing allowance still needs runtime verification and does not protect against lava, combat or the kill floor.

The hill's only walk-up route is a spiral path that climbs three quarters of a turn around it: a ramp west, a ramp north, a ramp east, a ramp south, then the flat summit where the boss spawner stands, ringed by ruined pillars. The summit is sixteen cell transitions from the start, so the climb is a deliberate trip rather than a shortcut. Descending one height step at a time is configured to be safe; skipping several steps can still cost health.

Around the hill, a ring of districts each has its own biome, a chest and shrine locations:

| District | Biome | What to expect |
| --- | --- | --- |
| Spawn meadow | Forest | Open ground for the first fight, the free chest, and one more chest in the far corner |
| West gully | Graveyard | A sunken trench behind a stone arch, with gravestones, dead trees, broken fences, pumpkins and pots, cobble patches, the coffin tile and a chest in the far corner |
| West ridge | Forest | Wooded ledges above the gully, with a chest at the high corner |
| North ruins | Dungeon | A raised plateau with crypt-stone floor, barrels, crates, bones, coins and braziers, with a chest and a view of the summit's back |
| East pen | Hell | A raised enclosure with fires, dark rocks and a corner chest; an optional lower stone court has side walls, two rectangular lava bands, a dry bypass, two north ramps and new west/south exits |
| East highland | Desert | Sand underfoot, adobe houses, cacti, bare desert trees and sandstone landmarks, with a ramp up to a peak holding the best chest |
| Spiral | Forest | The path itself, with a chest on its first landing as a reward for climbing |

The routes form loops: the meadow, ridge and ruins connect around the back of the hill, and the pen connects to the highland and on to the ruins, so no district is a long dead end.

The plan requests five Charge Shrines, two or three extras drawn from Charge, Magnet and Greed, three to five Moai shrines and two or three Shady Guy merchants, for 12 to 16 planned shrines from 27 authored candidate locations. These are planned counts, not guaranteed successful placements. Moai require 120 units of horizontal separation from other Moai placed by the pass (`shrineKindSpacing`), including after nudging; elevation does not make nearby heads count as spread out. No fallback relaxes that gap: an unplaceable shrine logs `placement unmet` rather than being forced into a cluster. Other kinds retain the ordinary 12.5-unit minimum gap.

At least one Moai and one Shady Guy are requested outside the spawn meadow (`shrineGuarantees`): the first of each kind is drawn only from spots beyond the meadow and checked against its placed position, with a `guarantee unmet` warning when no such shrine could be placed. Static spot-selection checks cover 256 seeds without physics failures. Paused runtime checks on seeds 0, 1, 7 and 42 placed every planned shrine and satisfied the gap and outside-meadow rules; physical route clearance and budget playtesting remain pending.

The level seed fixes shrine count/kind/order planning and the custom placement draws. Boss/miniboss replacements use a separate seeded stream: identical controlled spawn-call sequences repeat picks until their shared unused-name pool is exhausted, after which vanilla picks stand. All streams reset at generation start, and seed 0 is valid. Physics clearance can still change successful shrine placements; ordinary enemies, loot, combat and boss spawn offsets remain random. The authored grid, spiral and explicit prop transforms do not reroll with this seed.

The map uses the custom-level Tier 1 rules: survival continues after the boss, with no next-stage portal or chain of custom stages.

## Your first edit

1. Start Bramblecrown Hill and press **F8** to enter the editor. The run pauses.
2. Find the rock just ahead and to the right of the starting point. Use the **Select** tool (6), then click the rock.
3. Drag it a short distance across the flat meadow, keeping it away from the spawn, the fence line and chests. Leave the terrain and boss spawner alone for this first edit.
4. Change the save-name field to **my-bramblecrown** and click **Save**. This writes `my-bramblecrown.mblevel.json` without overwriting the original level.
5. Select that saved file in the editor's Load list and click **Load**. Leave the editor with F8 to play the saved copy. The rock should remain where you moved it, while the original Bramblecrown Hill remains unchanged.

The copy retains the level title. The editor's filename distinguishes it from the original; do not expect the selection illustration to be copied automatically. You can share the saved `.mblevel.json` without an asset pack.

## Design

The layout follows the structure of a classic open hub level: one landmark visible from the start, a leading line toward it, a spiral ascent to a flat boss arena, and a ring of distinct districts that each reward a detour. The pacing runs rest in the meadow, tension in the sunken graveyard and the hell pen, rest again on the dungeon plateau, then the spiral climb into the boss.

The grid is 13 by 12 cells (156 cells, 30.7% less ground area than the earlier 15 by 15 layout), with heights from -1 to 4 and sixteen one-step ramps. The generator uses a 13 by 13 array with an unoccupied final row; coordinates use its centre index 6, 40-unit cells and 20-unit height steps. Horizontal world bounds use the authored rectangle, not that square array: X `[-260,260]`, Z `[-260,220]`, with centre Z=-20. The spiral retains its 5 by 5 footprint and 3 by 3 summit. Cell and height numbers are authored in `scripts/build_starter_level.py` (`height`, `RAMPS`, `HILL`, `DISTRICTS`); object placement uses a fixed seed, so regeneration is reproducible.

The three summit ruin origins are inset to `(±36,80,±36)` at their authored corners. Their conservative measured renderer footprints fit at least two units inside the plateau's X/Z `[-60,60]` edges; origin-only support checks are not enough for these wide tower bases. The central boss area remains clear.

Each biome is a district plus a `groundZones` entry (desert sand, crypt floor and hell rock under the matching district; see [level-format.md](level-format.md)) and a scatter table of that biome's props. Every prop is registered with the euler X the game authored it with (most props, chests and trees are authored lying down at 270, rocks and ruin tiles at 0) and a scale chosen for this level's cell size, so everything stands upright; a test fails when a placed prop has no registered rotation. Props from other maps are placed by catalog id, which keeps their own map prefix, so no pack is needed.

The east pen's optional lava court borrows the Graveyard intro's architectural treatment: hard-edged pools flush with crypt-stone floor, walls at the sides, alternating dry ground and lava, and ramps back to the raised pen. Two `lavaZones` with matching `LavaCrypt` ground zones burn a standing player, away from chests and shrine spots. `LavaCrypt` is the actual native material observed on the loaded Graveyard intro pools. A material-only change still looked flat in the first runtime screenshot, so the renderer also reuses a readable native rectangular pool mesh and its original UV channels, fitted to the authored cell with upward-facing triangles. A close-up on the corrected build shows a textured orange surface. It does not clone the native damage scripts or colliders; the existing lava zones remain the damage source. The west exit rises toward `(181,2,-130)` and the south exit toward `(223,2,-219)`; adjoining wall segments are removed, and a lowered western entry keeps the dry route connected. The spawn can never be on lava. Wall collision, actual escape movement and damage on this revision still need runtime checks.

The dungeon flat-prefab assemblies that appeared as buried pillars near `(-82,22,119)` and `(121,22,202)` are omitted; smaller dungeon props and the other plateau landmarks remain.

Stage-boss spawns are drawn from Ent and Pharaoh (`bossPool`: `Ent1`-`Ent3`, `Pharaoh1`-`Pharaoh3`), with Bandit and Bush left out. The miniboss roster remains unchanged: `MinibossPig`, `MinibossGolem`, `MinibossGolemSand`, `MinibossScorpion`, `Ghostham`, `CalciumDad`. Arena suitability is not yet verified. Per-biome sky and fog are not part of the level format, so the level plays on Forest's rules, and the Graveyard coffin tile is placed as scenery whose enemy behaviour is untested.

## Content and distribution

The starter content is exactly these three files under `levels/`:

- `bramblecrown-hill.mblevel.json`: authored terrain and references to native game prefabs, not copies of the game assets.
- `bramblecrown-hill.png`: original hill selection illustration.
- `bramblecrown-hill.biome.png`: original cropped hill icon.

The illustrations are drawn from geometric shapes by `scripts/build_starter_level.py`, using Pillow's bundled default font. No game textures, screenshots, website images, THPS assets or soundtrack files are used to produce them. The source recipe is kept with the level for review and regeneration; this does not grant redistribution rights to the game's assets.

Regenerate all three starter files with:

```sh
uv run python scripts/build_starter_level.py
```

The default `task package:linux`, `task package:windows` and `task package:macos` content selection names only this starter. The pack list is empty. Existing development fixtures remain in the repository but are not part of the default player package. Explicit `LEVELS` and `PACKS` overrides still support local development packages; this default selection is not the public-release content enforcement policy.

## Packaged runtime smoke test

Use a fresh package extraction and an owned Windows game install. On Linux, run the Windows game under Proton; this is not a test of the native Linux build.

1. Build the default package for the target platform and verify it with `task package:check`. Inspect its manifest: the only `content/` entries must be the three starter files above, with no `content/packs/` or music entries.
2. Quit the game and install the extracted package with its bundled installer, pointing at the actual game directory and active Proton or Wine prefix. Run the installer's `--check` and require exit 0.
3. Preserve any existing `UserData/Levels`, `UserData/LevelPacks` and `UserData/CustomMusic` in a separate backup location. Test with only the three packaged starter files in `UserData/Levels` and no optional packs or music. Restore the preserved directories after testing; never delete player content.
4. Launch a fresh game. Check that all three native map entries remain, only Bramblecrown Hill is added, both starter images display, and selecting it offers only Tier 1. Launch through the normal character/map menus.
5. Confirm the authored spawn, the fence line, visible trees/rocks/ruins, supported rewards, working ramps, enemy spawns and an accessible boss spawner on the summit. Run a normal combat interval and exercise the boss interaction. Inspect the fresh game log for missing prefabs/packs, placeholders, failed edits and exceptions.
6. Perform the first-edit tutorial above. Inspect the saved copy for the moved rock, reload it in a fresh run, and confirm its placement and collision.
7. Keep the package manifest, installer check, fresh logs, selection/play/editor screenshots and saved-copy diff as evidence. Distinguish harness-assisted checks from an unassisted survival playthrough.

Automated checks in `tests/test_starter_level.py` and `tests/MegabonkLevels.Tests/starter_level_tests.cs` verify the file recipe, native-only references, placement parsing, terrain connectivity, the length of the climb to the summit, chest coverage of every district and selection art. Package tests check the default content selection and manifest hashes.

### Verified runtime

Runtime evidence below is tied to the stated file/build hashes. The latest revision has a fresh visual/baseline check, but physical access to the additional exits, removal checks on foot and one-step landing health outcomes remain pending.

Repeated manual drops from the same one-level location still caused damage on the body-height-sampling build. A read-only diagnostic measured a 22.073524-unit drop against the 20.25-unit cutoff; cumulative HP loss alone does not isolate individual landings. The replacement measures supporting-floor heights instead, retaining the 20-unit allowance rather than increasing it. Regression tests cover inflated body samples and missing/distant support. The revised diagnostics include both surface heights, the exemption decision and before/after landing HP; zero-damage one-level falls and normal larger-fall damage still require a fresh-build manual check. The failed runtime baseline is `.tools/evidence/bramblecrown-compact/fall-contact-fix/before.json`.

After the floor-contact fix, manual feedback described overall fall damage as good, but identified the drop from `(-58,82,14)` to `(-84,42,39)` as the maximum fall that should be safe. Its diagnostic measured support heights approximately 80 and 40, a 40-unit drop, no exemption under the old 20-unit setting, and landing HP 87 to 73; the ordinary reduction stat was 0 afterward. This confirms surface measurement for that landing, not a failure of the contact fix. The starter allowance is now 40 units with the existing 0.25-unit contact tolerance; tests cover the boundary and rejection of larger falls. The expanded setting has not yet been loaded or physically checked.

The native-lava revision loaded seed 0 as Calcium with zero Feathers, HP 100, no invulnerability and spawns off. Both surfaces used the native Graveyard template `pb_Mesh148722` with four vertices/four UVs; measured output normals were `(0,1,0)`. The final close-up shows textured orange lava, unlike the preceding material-only flat result and the first incorrectly facing mesh attempt. All 14 planned shrines were placed with no content/placement errors. `fall-damage` reported the 20-unit allowance active and Calcium's ordinary reduction stat still 0 between landings; no manual landing outcome was measured yet.

Evidence for this revision is `.tools/evidence/bramblecrown-compact/native-lava-runtime/capture.json`, `session.log` and `lava-native-close.png`. Level SHA-256: `76b1311d96f1946f47e93fc62b696be6698d0590dcfc4c08e5a89f86e3bc18e9`; DLL SHA-256: `c2d1034d9bedbe541953ea35cef99749d8f2154eafbcff04b22abfc01d643f9b`. The earlier `lava-native-mesh.png` in that folder is failed diagnostic evidence from the pre-winding build, not the final visual result. Player camera and manual control were restored at the authored spawn, with the game unpaused and enemies still off.

#### Compact-layout placement check

The multi-seed placement checks below predate the rectangular world-bounds fix and tower inset. Manual walking subsequently exposed a 40-unit gap between the northern ground edge and the native barrier near `(99,22,217)`; the spiral itself was reported walkable. The earlier build's placement results do not establish perimeter safety.

Five fresh-process offline plain-Wine runs with the Steam stub covered seed 0 twice and seeds 1, 7 and 42 once each. All used Calcium, zero Feathers, no harness invulnerability, spawns off and the editor paused; both development stage/terrain overrides were off. The effective assets were `StageForest1` and `ParamForest1(Clone)`, with a 13 by 13 generator array, 40-unit cell spacing and 20-unit height steps.

| Seed | Planned / placed | Moai | Shady Guy | Smallest horizontal Moai gap |
| --- | --- | --- | --- | --- |
| 0, twice | 14 / 14 | 4 | 2 | 163.2 |
| 1 | 14 / 14 | 5 | 2 | 205.5 |
| 7 | 15 / 15 | 5 | 3 | 126.5 |
| 42 | 13 / 13 | 3 | 2 | 231.4 |

Every run satisfied the outside-meadow guarantees, with no placement/guarantee failure. The two seed-0 runs produced identical timestamp-stripped shrine logs and identical queried position/scale values for all 14 placements. Their two merchants had different rotations, so the result is not full-transform determinism; the cause of that rotation difference was not established. Live transform snapshots include positions, quaternion rotations, scales, cells and district membership. No boss/miniboss calls were exercised in this pass.

Evidence is in gitignored `.tools/evidence/bramblecrown-compact/`, including per-run logs and `capture.json`, `comparison.json` and independent regeneration outputs. Level SHA-256: `f7976404fa388d05fc12f05f265fa3a5905dd8c123b92cb44360a4570a799781`; deployed DLL SHA-256: `6682599b3a627f6452b9fb7e09996b96595c2377c077f9faddf9b543f243b035`. One read-only item probe used the invalid singular `Feather` and was rejected; the corrected `Feathers` query returned zero without changing inventory. These checks do not certify physical walking, interaction access, combat, lava escape or packaged first play.

A later fresh-process seed-0 run with both corrections measured matching horizontal bounds on the native edge collider and ground mesh: X `[-260,260]`, Z `[-260,220]`. The four summit tower mesh renderers were at least 2.425 units inside the plateau's horizontal edges. All 14 planned shrines were placed, with a minimum Moai gap of 163.2 units and no content/placement errors. Calcium again had zero Feathers and no invulnerability; measurements were made paused with spawns off. This is live bounds/placement evidence, not physical collision-contact testing, and repeated-seed checks for this corrected content/build pair are still pending.

The corrected run is recorded under `.tools/evidence/bramblecrown-compact/boundary-and-towers-fixed/`, with full bounds, placement transforms, logs and byte-identical independent regeneration. Its level SHA-256 is `c615f7087bc769485f9c103fc499cce86e05b65a39d1a77d345b3bb71f998940`; DLL SHA-256 is `0f584a0c5e85b1dc7f9058f9b1de105e7858e73de90f931e286ba153729c3a55`. Control was returned at the authored spawn with the editor off, the game unpaused and spawns still off for the next manual walk.

#### Earlier layouts

The following checks concern earlier 15 by 15 layouts, not the current compact layout. They are historical observations only. Do not use them to certify the compact layout's placement spacing, physical routes, interactions or packaged first play.

Loading `levels/bramblecrown-hill.mblevel.json` through the development harness on macOS under plain Wine built all 225 authored tiles and placed the boss spawner on the summit, with no missing-prefab, failed-edit or exception lines in the log. Live checks from that session: the shrines the mod spawns carry the game's own rotations (Charge at 0, Greed, Magnet and Moai at 270) and the chests stand at 270 with the game's small random tilt; a run rolled 19 shrines (5 guaranteed Charge, 6 Moai, 6 Shady Guy and 2 extras) from the 27 spots; a spawned Shady Guy opened the Shady Guy shop through `interact`; and views of the graveyard gully, hell pen, dungeon plateau and desert highland showed each biome's ground and props.

Later checks in the same session: standing on the lava pool cost 3 hit points per half second; two boss portal spawns were rewritten by the pool (`Ent1` to `Ent2`, then `Ent1` to `Pharaoh2`, whose boss bar and model appeared normally behind the summit portal); a timeline miniboss spawn (`GhostGrave1`, flag `Boss`) became `MinibossGolem`; and the grass filter removed the blades on the lava, hell rock and desert sand while the Forest meadow kept its grass.

These were harness-assisted checks. The following were not repeated for this layout and still need a pass using the smoke test above: walking each ramp with native input, a combat interval with spawns on, the boss interaction, the Moai and coffin interactions, the first-edit tutorial and the packaged selection screen.

### Seeded-stream lifecycle smoke check

Offline plain Wine with the Steam stub was used for two fresh-process loads
with seed 0, the actual death-screen Confirm → summary Restart buttons, and a
third fresh process loading an editor-saved copy. Both development stage/terrain
overrides were off. Calcium had zero Feathers, no harness invulnerability grant,
and spawns enabled; measurements were made paused in the editor. The effective
assets were `StageForest1`/`ParamForest1`, with spacing 40 and height step 20.

All four generations logged the same ordered 16-kind plan, all 16 successful
placement positions (reported to three decimal places), golden outcomes and
first boss replacement (`Ent1` → `Bush`, drawn from the earlier eight-boss roster, which has since dropped Bush). No placement failure or tight fallback
was logged. Restart restored the authored start `(0, 0, -240)` and repeated the
first boss replacement after it had already been used in the previous run.
The saved copy retained seed 0, `baseline:none`, Forest stage 0 and Tier 1.

A later offline plain-Wine pass covered the 12-16 budget, the outside-meadow guarantee and the six-boss roster: two fresh-process seed-0 loads logged identical 14-kind plans and placements, and seeds 1, 7 and 42 planned 14, 15 and 13 shrines with 3-5 Moai and 2-3 Shady Guy each. In every run the first Moai and first Shady Guy stood outside the meadow rectangle (all of them did in seeds 1, 7 and 42; seed 0 had a second Shady Guy inside it, which the guarantee allows), with no `guarantee unmet`, placement-failure or content-load line. A forced boss spawn (`Ent1` → `Pharaoh3`) came from the new roster. These runs used the editor harness with Calcium and zero Feathers; the guarantee was not seen failing, so only its passing path is measured, and positions are at logged three-decimal precision.

Identity and local evidence:

- Generated level SHA-256: `7a35e663f152722606f21101a2eb15879e73b1b4c40aae1c97de5245c9b1d6da`.
- Measured DLL SHA-256: `de66290af0f550827b9c81f1e56f40a615ae13e4ebedb6986873fdfedf09ab22`.
- Gitignored `.tools/evidence/bramblecrown-seeded/` holds fresh logs,
  `comparison.json`, `lifecycle-comparison.json`, stage/inventory/state reads and
  the saved diagnostic copy.

Regenerating all three starter files into a separate directory produced
byte-identical JSON and artwork. The death-button driver logged three expected
Confirm refusals while its button was still inactive, then succeeded; these
are recorded harness errors, not content-load failures.

This establishes a bounded position-log comparison, not full-precision transform
or district guarantees. The portal was activated through the harness from a
distance with `CanInteract` true, not reached on foot. Only the first stage-boss
pick was compared live; miniboss sequences, curse copies and pool exhaustion
are covered by pure tests, not runtime evidence. The saved copy had no moved
rock, so this is lifecycle replay evidence, not the first-edit tutorial. These
checks do not establish roster suitability, ramp/enemy traversal, pack-free
packaged selection, interaction accessibility or an unassisted survival clear.
