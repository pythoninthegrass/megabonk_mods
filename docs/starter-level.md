# Bramblecrown Hill

Bramblecrown Hill is the starter level included by default in player packages. It is a handcrafted composite of the game's five biomes (Forest, Graveyard, Dungeon, Desert and Hell) using only the game's own props, ground materials, enemies and music, built around one tall hill with a ruined watchpost on its crown. It plays on Forest's stage rules, so enemies, music and the boss are Forest's. No level packs or custom music are needed.

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

Five Charge Shrines are guaranteed every run, along with two or three more shrines drawn from Charge, Magnet and Greed, three to eight Moai shrines and three to eight Shady Guy merchants. The counts are rolled each run and the shrines are placed on 27 authored, clear-ground locations, so their positions vary between runs. These are this level's authored rules, not a claim about vanilla shrine counts.

The map uses the custom-level Tier 1 rules. It does not provide a chain of custom stages or a portal to a second custom map.

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
