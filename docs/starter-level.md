# Bramblecrown Hill

Bramblecrown Hill is the starter level included by default in player packages. Its five visual districts use Forest, Graveyard, Dungeon, Desert and Hell props and ground materials around a tall hill with a ruined watchpost. Gameplay uses Forest stage 0: foreign materials do not change stock enemy rosters or generation rules. The level's explicit boss/miniboss pools override eligible boss picks, not ordinary enemies. No level packs or custom music are needed.

## First play

Choose **Play**, choose a character, then select **Bramblecrown Hill** on Map Selection and confirm Tier 1. The entry has a green hill illustration; the illustration is not an in-game screenshot.

You start in an open meadow with a free chest to the left, a distinctive rock ahead and to the right, and a tall wall of hillside straight ahead with the watchpost tower above it. A fence line of rocks and bushes leads from the meadow to the foot of the hill. Every route is walkable without jumping or jump-height upgrades. Avoid jumping off cliffs: normal character movement and fall damage still apply.

The hill's only way up is a spiral path that climbs three quarters of a turn around it: a ramp west, a ramp north, a ramp east, a ramp south, then the flat summit where the boss spawner stands, ringed by ruined pillars. The summit is eighteen steps from the start, so the climb is a deliberate trip rather than a shortcut. Stepping off the edge on the way down is allowed but costs health.

Around the hill, a ring of districts each has its own biome, a chest and shrine locations:

| District | Biome | What to expect |
| --- | --- | --- |
| Spawn meadow | Forest | Open ground for the first fight, the free chest, and one more chest in the far corner |
| West gully | Graveyard | A sunken trench behind a stone arch, with gravestones, dead trees, broken fences, pumpkins and pots, cobble patches, the coffin tile and a chest in the far corner |
| West ridge | Forest | Wooded ledges above the gully, with a chest at the high corner |
| North ruins | Dungeon | A raised plateau with crypt-stone floor, barrels, crates, bones, coins and braziers, with a chest and a view of the summit's back |
| East pen | Hell | A raised enclosure with hell rock underfoot, brick walls along its west side and columns flanking the ramp gate, fires and dark rocks, with a chest tucked into the far corner |
| East highland | Desert | Sand underfoot, adobe houses, cacti, bare desert trees and sandstone landmarks, with a ramp up to a peak holding the best chest |
| Spiral | Forest | The path itself, with a chest on its first landing as a reward for climbing |

The routes form loops: the meadow, ridge and ruins connect around the back of the hill, and the pen connects to the highland and on to the ruins, so no district is a long dead end.

The current plan requests five Charge Shrines, two or three extras drawn from Charge, Magnet and Greed, three to eight Moai shrines and three to eight Shady Guy merchants, using 27 authored candidate locations. These are planned counts, not verified successful-placement or district guarantees. Tighter budgets and useful district coverage still need curation and playtesting.

The level seed fixes shrine count/kind/order planning and the custom placement draws. Boss/miniboss replacements use a separate seeded stream: identical controlled spawn-call sequences repeat picks until their shared unused-name pool is exhausted, after which vanilla picks stand. All streams reset at generation start, and seed 0 is valid. Physics clearance can still change successful shrine placements; ordinary enemies, loot, combat and boss spawn offsets remain random. The authored grid, spiral and explicit prop transforms do not reroll with this seed.

The map uses the custom-level Tier 1 rules: survival continues after the boss, with no next-stage portal or chain of custom stages.

## Your first edit

1. Start Bramblecrown Hill and press **F8** to enter the editor. The run pauses.
2. Find the rock just ahead and to the right of the starting point. Use the **Select** tool (6), then click the rock.
3. Drag it a short distance across the flat meadow, keeping it away from the spawn, the fence line and chests. Leave the terrain and boss spawner alone for this first edit.
4. Change the save-name field to **my-bramblecrown** and click **Save**. This writes `my-bramblecrown.mblevel.json` without overwriting the packaged starter.
5. Select that saved file in the editor's Load list and click **Load**. Leave the editor with F8 to play the saved copy. The rock should remain where you moved it, while the original Bramblecrown Hill remains unchanged.

The copy retains the level title. The editor's filename distinguishes it from the original; do not expect the selection illustration to be copied automatically. You can share the saved `.mblevel.json` without an asset pack.

## Design

The layout follows the structure of a classic open hub level: one landmark visible from the start, a leading line toward it, a spiral ascent to a flat boss arena, and a ring of distinct districts that each reward a detour. The pacing runs rest in the meadow, tension in the sunken graveyard and the hell pen, rest again on the dungeon plateau, then the spiral climb into the boss.

The grid is 15 by 15 cells, the largest Forest stage 0 allows, with heights from -1 to 4 and twelve one-step ramps. Cell and height numbers are authored in `scripts/build_starter_level.py` (`height`, `RAMPS`, `HILL`, `DISTRICTS`); object placement uses a fixed seed, so regeneration is reproducible.

Each biome is a district plus a `groundZones` entry (desert sand, crypt floor and hell rock under the matching district; see [level-format.md](level-format.md)) and a scatter table of that biome's props. Every prop is registered with the euler X the game authored it with (most props, chests and trees are authored lying down at 270, rocks and ruin tiles at 0) and a scale chosen for this level's cell size, so everything stands upright; a test fails when a placed prop has no registered rotation. Props from other maps are placed by catalog id, which keeps their own map prefix, so no pack is needed.

The east pen holds a lava pool (`lavaZones` plus a `Lava` ground zone) that burns a standing player, away from the ramps, chests and shrine spots, and the spawn can never be on it. Stage-boss spawns are drawn from a pool of Forest, Desert and other bosses (`bossPool`) and minibosses from a mixed pool (`minibossPool`). Per-biome sky and fog are not part of the level format, so the level plays on Forest's rules, and the Graveyard coffin tile is placed as scenery whose enemy behaviour is untested.

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
first boss replacement (`Ent1` → `Bush`). No placement failure or tight fallback
was logged. Restart restored the authored start `(0, 0, -240)` and repeated the
first boss replacement after it had already been used in the previous run.
The saved copy retained seed 0, `baseline:none`, Forest stage 0 and Tier 1.

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
