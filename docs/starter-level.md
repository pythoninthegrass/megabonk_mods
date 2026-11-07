# Mosswatch Hollow

Mosswatch Hollow is the starter level included by default in player packages.
It is a handcrafted woodland using Forest's own terrain, trees, rocks, ruins,
enemies and music. No level packs or custom music are needed.

## First play

Choose **Play**, choose a character, then select **Mosswatch Hollow** on Map
Selection and confirm Tier 1. The entry has a green woodland illustration;
the illustration is not an in-game screenshot.

You start in an open clearing with a free chest to the left and a distinctive
rock ahead and to the right. The low hollow gives you room to fight. Ramps lead
to the wooded western ridge and northern terrace; the ruined watchpost and
boss spawner are on the highest northwestern ground. Walkable routes connect
every tile without requiring extra jumps or jump-height upgrades. Avoid jumping
off cliffs: normal character movement and fall damage still apply.

Chests encourage exploration across the clearings and ridges. Two Charge
Shrines and two or three additional shrines use six authored, clear-ground
locations; the shrine types and assignment to locations vary between runs.
These are this level's authored rules, not a claim about vanilla shrine counts.

The map uses the custom-level Tier 1 rules. It does not provide a chain of
custom stages or a portal to a second custom map.

## Your first edit

1. Start Mosswatch Hollow and press **F8** to enter the editor. The run pauses.
2. Find the rock just ahead and to the right of the starting point. Use the
   **Select** tool (6), then click the rock.
3. Drag it a short distance across the flat clearing, keeping it away from the
   spawn and chests. Leave the terrain and boss spawner alone for this first edit.
4. Change the save-name field to **my-mosswatch** and click **Save**. This writes
   `my-mosswatch.mblevel.json` without overwriting the packaged starter.
5. Select that saved file in the editor's Load list and click **Load**. Leave
   the editor with F8 to play the saved copy. The rock should remain where you
   moved it, while the original Mosswatch Hollow remains unchanged.

The copy retains the level title. The editor's filename distinguishes it from
the original; do not expect the selection illustration to be copied automatically.
You can share the saved `.mblevel.json` without an asset pack.

## Content and distribution

The starter content is exactly these three files under `levels/`:

- `mosswatch-hollow.mblevel.json`: authored terrain and references to native game
  prefabs, not copies of the game assets.
- `mosswatch-hollow.png`: original woodland selection illustration.
- `mosswatch-hollow.biome.png`: original cropped woodland icon.

The illustrations are drawn from geometric shapes by
`scripts/build_starter_level.py`, using Pillow's bundled default font. No game
textures, screenshots, website images, THPS assets or soundtrack files are used
to produce them. The source recipe is kept with the level for review and
regeneration; this does not grant redistribution rights to the game's assets.

Regenerate all three starter files with:

```sh
uv run python scripts/build_starter_level.py
```

The default `task package:linux`, `task package:windows` and
`task package:macos` content selection names only this starter. The pack list
is empty. Existing development fixtures remain in the repository but are not
part of the default player package. Explicit `LEVELS` and `PACKS` overrides
still support local development packages; this default selection is not the
public-release content enforcement policy.

## Packaged runtime smoke test

Use a fresh package extraction and an owned Windows game install. On Fedora,
run the Windows game under Proton; this is not a test of the native Linux build.

1. Build the default Linux package and verify it with `task package:check`.
   Inspect its manifest: the only `content/` entries must be the three starter
   files above, with no `content/packs/` or music entries.
2. Quit the game and install the extracted package with its bundled installer,
   pointing at the actual game directory and active Proton prefix. Run the
   installer's `--check` and require exit 0.
3. Preserve any existing `UserData/Levels`, `UserData/LevelPacks` and
   `UserData/CustomMusic` in a separate backup location. Test with only the three
   packaged starter files in `UserData/Levels` and no optional packs or music.
   Restore the preserved directories after testing; never delete player content.
4. Launch a fresh game. Check that all three native map entries remain, only
   Mosswatch Hollow is added, both starter images display, and selecting it
   offers only Tier 1. Launch through the normal character/map menus.
5. Confirm the authored spawn, visible trees/rocks/ruins, supported rewards,
   working ramps, enemy spawns and accessible boss spawner. Run a normal combat
   interval and exercise the boss interaction. Inspect the fresh game log for
   missing prefabs/packs, placeholders, failed edits and exceptions.
6. Perform the first-edit tutorial above. Inspect the saved copy for the moved
   rock, reload it in a fresh run, and confirm its placement and collision.
7. Keep the package manifest, installer check, fresh logs, selection/play/editor
   screenshots and saved-copy diff as evidence. Distinguish harness-assisted
   checks from an unassisted survival playthrough.

Automated checks in `tests/test_starter_level.py` and
`tests/MegabonkLevels.Tests/starter_level_tests.cs` verify the file recipe,
native-only references, placement parsing, terrain connectivity and selection
art. Package tests check the default content selection and manifest hashes.

### Verified runtime

The Linux package was installed and checked on Fedora 42 with Proton
Experimental, the Windows game build `21750826` (1.0.69) and MelonLoader 0.7.3.
Testing used no optional packs or custom music. The normal selection screen
displayed the title, both images and a single Tier 1 choice. Calcium, with zero
Feathers and normal damage, walked ramps to both raised elevations; chest and
boss-spawner interactions succeeded. A short combat check reached 27 game
seconds and 21 kills, not a complete survival clear.

Dragging the arrival rock, saving a separate copy, quitting and loading that
copy in a fresh process preserved its new position. The packaged original
remained byte-identical. The replay log contained no missing-content or failed
edit errors. Existing levels, optional packs and custom music were restored
after the isolated test, and the final installer check passed again.
