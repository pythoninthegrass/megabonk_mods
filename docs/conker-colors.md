# Conker: Colors

Build the Nintendo 64 Colors arena from your own US retail copy of *Conker's Bad Fur Day*. In Megabonk it is a stock survival level: start in the SHC base, cross the valley, and summon the boss on the Tediz side. It does not add capture the flag, Conker characters, or weapon pickups.

## Quickstart

1. Set up Megabonk, the mod, mise, and Unity 2023.2.22f1 with Windows and Linux Build Support as described in the [Warehouse quickstart](thps-warehouse.md#quickstart). Skip the Warehouse disc and soundtrack steps. The mod needs to be built from a revision that supports the Colors vertex tint shader.
2. Put your own US retail big-endian `.z64` ROM at `tools/conker/rom/baserom.us.z64`, or set `CONKER_ROM` to its path. Run `task conker:verify-rom` to check it against the SHA-256 pin. Other revisions and byte orders are not supported.
3. Install Rust and check out the pinned extractor. These commands put a separate checkout beside this repo; if you already have a clean checkout at the pinned revision, reuse it by setting `CONKER_EXTRACTOR_DIR`.

   ```sh
   mise install rust@1.100.0
   git clone https://github.com/LuaxY/conker.wtf.git ../conker_wtf
   git -C ../conker_wtf checkout --detach 9eaf19e4624f058b58b0a63b8cc2fecf4f22f8ef
   ```

4. Quit Megabonk, run `task conker`, and relaunch the modded game. Choose **Conker: Colors** in Map Selection.

`task conker` verifies the ROM even when extraction is cached, prepares the map, builds both platform bundles, and installs the pack and level into `UserData/LevelPacks/conker` and `UserData/Levels`. The installer picks the Windows bundle under Wine and the Linux bundle on native Linux. On Linux running Proton, manually copy the Windows bundle over the installed `conker` bundle. To send a build to another machine you control, use the bundle for that game's platform, the manifest, and `.tools/conker/conker-colors.mblevel.json`.

## Map source and adaptation

- The [Colors reference](https://conker.fandom.com/wiki/Colors) describes the original CTF mode and landmarks. The original also uses this arena for Deathmatch. Both share scene `0x30`; the extractor's Deathmatch-filtered geometry and collision are the build inputs.
- The bases, entrances, sniper nests, main path, bridge, and hillsides come from the ROM. The `tools/conker/videos/` captures are optional visual references, not part of the build. Original lift transitions, animated effects, and Conker-specific doors and props are not recreated.
- The render mesh, original collision, and placement anchors use the same scale. The arena is 40 percent larger than the initial import to give Ogre (the tallest stock capsule at 4.75 units) room in doors and bunker corridors. Original Conker lift transitions are not recreated.
- Invisible walls follow the exterior of the original collision mesh, including steep hillsides. Two-unit ground cells trace the outline without cutting across slopes below the crest. Every wall rises to the same height, 1,000 units above the highest source collision vertex, so there are no low sections to jump over. The pit lies inside the outline and stays open to the kill floor. No arena-wide underlay or added mountains are built. Timeline minibosses use approved outdoor ground near their requested spawn; the portal uses its stock size without the pedestal.
- Colors shares Warehouse’s chest-luck range and shrine mix: two to three Charge Shrines plus one each of Magnet, Challenge, Curse, and Moai. Colors also rolls a location for the Shady Guy and up to one microwave, and two starting power-ups. Tomes still come from normal upgrade offers, not ground pickups.
- Shrines and power-ups use approved open-ground spots outside doors, tunnels, windows, and bridges. A shrine that cannot fit at an approved spot is tried elsewhere rather than shoved into a route. Later random power-up drops also use approved spots; XP and gold stay where they drop.
- The pit's floor faces are dropped from the render mesh, so nothing catches a fall through it. Below `y = -46`, falls deal 15 base damage, bypassing shield, and return the player to their last supported footing or the start. A fallen chest returns to its original position without resetting its loot. Ordinary enemies and elites die below the threshold; minibosses and bosses are exempt. Other levels keep their original kill-floor behavior unless they opt in.
- The pack includes its own `MegabonkLevels/Colors Vertex Tint` shader to retain the original vertex colors and material alpha modes. The [pack loader](asset-bundles.md#shader-remap) preserves this exact shader instead of replacing it with MK.Toon.
- `conker.wtf` is used as an external build tool, not copied into this repo. The [decompilation project](https://github.com/DevOldSchool/conkers-bfd-decomp) provides an independent reference for the US ROM and its formats; it is not needed to build Colors.

## Troubleshooting

- **ROM check fails:** check that your copy is the supported US retail big-endian dump, not a byte-swapped image, a patched ROM, or a different revision.
- **Extractor check fails:** set `CONKER_EXTRACTOR_DIR` to a clean checkout at the revision above. Use a separate checkout rather than switching a tree with local changes.
- **Unity fails or the level is a placeholder:** see [Warehouse troubleshooting](thps-warehouse.md#troubleshooting). If the textures or extracted files are missing after a partial build, run `task conker:extract --force` and then `task conker`.
- **The level loads pink or loses its original vertex colors:** rebuild and install the current mod with `task mod:build`, then relaunch the game.

The ROM, extracted assets, generated Unity assets, and platform bundles stay local. This repository does not distribute them.
