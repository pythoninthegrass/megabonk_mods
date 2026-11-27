# Killing Floor 1 Mountain Pass

Notes for building a level from KF-MountainPass, the Killing Floor 1 map by Kevin "DrGuppy" Butt that ships in the Killing Floor 1 base game as `Maps/KF-MountainPass.rom` (36.9 MB, sha256 `d1cdbf58a2ba8fe2de7b222fa2836fe25956adee3143e820200a659a0be5bff6`, one of 39 `.rom` maps). It is an Unreal Engine 2 package (version 128/29, game id 200001). Nothing extracted from the map is committed; all of it stays under the gitignored `.tools/kf1/`.

## Why not the Killing Floor 2 version

The first attempt used the Killing Floor 2 rework (Steam Workshop item 857015700, consumer app 232090, package `KF-MountainPass_zfix`), because it is the version players know. It was abandoned for these reasons:

- **Static meshes cannot be read.** The workshop map is an Unreal Engine 3 package (file version 871, licensee version 1117, 2,433 names, 38,672 exports, 1,721 imports). umodel lists every export but fails on the first `StaticMesh3` with `RawArray item size mismatch: expected 12, serialized 12`, in both the 2022 Linux release and a build from the UEViewer source (commit `a0bfb46`, February 2024). Its game table lists only the original Killing Floor, so Killing Floor 2 is an unsupported game and the static mesh layout differs from the stock reader by a few bytes. umodel does not export BSP or actor placements in any case, so a custom reader would have been needed for all of the geometry and the actor transforms.
- **The editor route is expensive and unconfirmed.** The Killing Floor 2 SDK (app 232150) is a 166 MB add-on with no content of its own; it installs into the base game's folder, and the base game (app 232090) is 95 GB. Whether the editor would open the map is unknown. The file ships in `BrewedPC/` and Tripwire's upload tool brews maps, which suggests a cooked package the editor refuses, but the header shows the cooked flag (`0x8`, package flags `0x20024001`) clear and editor-only imports (`EditorResources`, `MapTemplates`, `MaterialTemplates`, `TechArtTests`) still present. That evidence conflicts, and the only way to settle it was the 95 GB install.
- **Most of the data is in other packages.** The map imports from about 140 stock Killing Floor 2 packages (`ENV_*_MESH`, `ENV_*_TEX`, `ENV_*_MAT`, `FX_*`, `Engine*`, `KFGame`), so the meshes and textures would also need extracting from the game depot.

The workshop item itself downloads anonymously (`workshop_download_item 232090 857015700` with steamcmd, about 158 MB; sha256 of the package `6c0cb4f1f76aba5910ce75c24db07f1823efb741a74eea1be28bf452494e31b8`). `scripts/kf2_package_info.py <package> [--imports]` prints a UE3 package header and its import list, and is what produced the numbers above.

The Killing Floor 1 original avoids all of this: it is the same author's map, it is an official part of the base game, the engine is Unreal Engine 2 (which umodel supports), the install is 6 GB, and the Killing Floor SDK's `UCC.exe` can export a whole level headlessly.

## Playthrough reference footage

`tools/videos/KF2_Mountain_Pass.webm` (1,346,697,421 bytes, sha256 `bade7b0330b38447180287296ab0837be21b92879f1eee17ee8ba10cbe972d42`, 2560x1440, 60 fps VP9 with Opus audio, 16:25) is one complete Killing Floor 2 survival run of the Mountain Pass rework. The T3D, brush and umodel exports say what the map contains but never how it reads while moving through it, so this footage is the oracle for the terrain silhouette, where the road, buildings and treelines sit, and the direction waves come from. The KF2 rework is Tripwire's Unreal Engine 3 rebuild, not the KF1 map: meshes, materials, lighting and vegetation are its own. Use the frames for layout, scale and pacing, and the KF1 export for anything built.

Frames are extracted in the same manner as `tools/thps_warehouse_frames/`, as an untriaged dump for a later agent to decide what to keep: 910 frames at 1 fps with `-q:v 2` at native 2560x1440, covering video time 00:20 to 15:30, `tools/kf2_mountain_pass_frames/frame_0001.jpg` to `frame_0910.jpg`. Both the frames and the video are gitignored. Regenerate with:

```sh
ffmpeg -ss 00:00:20 -to 00:15:30 -i tools/videos/KF2_Mountain_Pass.webm -vf fps=1 -q:v 2 tools/kf2_mountain_pass_frames/frame_%04d.jpg
```

- Frame N is the source frame at video time 20.483 + (N-1) seconds: the extraction lands 29 frames after the requested start, so `frame_0455.jpg` is 07:54.48 rather than 07:54.00. The offset was measured by MD5-matching extracted frames to the source's own frame timestamps at six points across the run, and is constant. A video time T lands in frame `round(T - 20.483) + 1`.
- The window is a single run. `frame_0001` still carries the loadout selection overlay and `frame_0910` is the VICTORY screen after the final boss, so every frame is in-level; there is no facecam, letterbox or black frame (the smallest frame is 73 KB).
- The HUD is fixed in every frame: Trader distance and wave counter top left, XP and health/armor bottom left, ammo, cash and inventory bottom right, weapon-pickup banners top center. Ignore all of it when reading geometry.
- Nothing else has been done to the frames. Which frames show which area, which are shop or pause screens, and which are the best overviews are all unresolved and left to the analysis pass.
- The footage is overcast and hazy. The KF1 level title is `KF-MountainPass_Day` and the map package ships a `GUP-MountainSky.tga`, so the KF1 sky and lighting may read brighter than this run; do not copy the KF2 mood without checking the KF1 sky and layer textures.

## Getting the game and tools

Killing Floor (Steam app 1250, 6 GB installed, 3.4 GB download) installs from a logged-in Steam client. The KF1 dedicated-server depots (app 215350) need a license, so an anonymous steamcmd download fails with `missing license for depot`. The Killing Floor SDK (app 1260, 19 MB) is a tool that installs into the game folder and adds `KFEd.exe` and `UCC.exe` to `System/`.

## Contents of the map

By export class in the package: 1,810 `StaticMeshActor` (and 1,811 `StaticMeshInstance`), 992 BSP `Model` with 992 `Polys`, 256 `TerrainSector`, 462 `Brush`, 70 local `StaticMesh`, 353 `Light`, 12 `PlayerStart`, 157 `ZombieVolume`, 198 `BlockingVolume`, 14 `KFRandomItemSpawn`, 14 `KFAmmoPickup`, 4 `ShopVolume`, 830 `PathNode`, 6,640 `ReachSpec`.

## Exporting the level with UCC

`UCC.exe` splits its own executable path at spaces, so running it from `Program Files (x86)` fails with misleading errors such as `Failed to find object 'Class Any.batchexport'`. Run it through a junction without spaces (`mklink /J C:\KF "<Steam>\steamapps\common\KillingFloor"`):

```sh
cd C:\KF\System
UCC.exe batchexport KF-MountainPass.rom Level t3d <output dir>
```

This writes `myLevel.t3d` (7.2 MB, 138,564 lines, sha256 `87acc038e2e67c6176ea2396b7ffa20ce4bc91f6f27bd99a6546013380c5b02c`); the converter expects it renamed to `.tools/kf1/export/KF-MountainPass.t3d` beside `Terrain_Main.bmp`, and the umodel output under `.tools/kf1/out/`. The file holds every actor and its properties: 1,810 `StaticMeshActor` (`StaticMesh`, `Location`, `Rotation`, `DrawScale3D`, `Skins`), 462 `Brush` actors holding 5,804 polygons, 12 `PlayerStart`, 157 `ZombieVolume`, 198 `BlockingVolume`, 14 `KFRandomItemSpawn`, 14 `KFAmmoPickup`, 4 `ShopVolume`, 24 `Teleporter` and one `TerrainInfo` whose heightmap is `Texture'KF-MountainPass.Terrain_Main'` with its layer textures. The level title is `KF-MountainPass_Day`.

The terrain heightmap is not exported by umodel (it skips the 16-bit format) but UCC writes it: `UCC.exe batchexport KF-MountainPass.rom Texture bmp <dir>` produces `Terrain_Main.bmp`, a 256 by 256, 16 bits per pixel, uncompressed BMP that holds the raw 16-bit height words (values 13,148 to 39,055, flat ground at 32,768; the bottom row comes first). UCC crashes with a general protection fault on a later texture in the same batch, after `Terrain_Main` has been written. The `TerrainInfo` actor has no `Location` and a `DrawScale3D` of 8; the T3D omits the base `TerrainScale`, so the scale was fitted against 917 path node actors, which rest on the ground: the grid is centered on the origin with 64 world units per sample in X and Y, and height is `(value - 32768) / 256 * 64` world units (trimmed regression slope 0.2493 against 0.25 expected, residual standard deviation 4.7 units over 609 nodes, which float about 46 units above the ground).

## Exporting meshes and textures with umodel

The prebuilt Linux release is a 32-bit binary that needs `libpng12` and glibc 2.27, so build umodel from the UEViewer source instead: in an `ubuntu:24.04` container install `git`, `build-essential`, `libsdl2-dev`, `libpng-dev` and `zlib1g-dev`, clone `https://github.com/gildor2/UEViewer.git`, and run `./build.sh`. Run the result in a container with `libsdl2-2.0-0` and `libpng16-16`.

umodel does not recognize the `.rom` extension, so link the map under a `.upk` name in a scratch folder next to the other packages. Copy `StaticMeshes/*.usx` and the `.utx` files named by the T3D skins from the game folder, then run `umodel -path=<scratch> -export -gltf -out=<dir> <package>` once per package. The level places 157 distinct static meshes: 561 placements from the map's own package, and the rest from `VegetationSM`, `KillingFloorStatics`, `KillingFloorLabStatics`, `KillingFloorManorStatics`, `DetailSM`, `Foundry_SM`, `IndustrySM2`, `OfficeStatics`, `PatchStatics`, `HedgehogSM`, `HemispheresSM`, `IndustrySM`, `22Patch` and `LevelSpecificSM`. Exporting those packages and their textures wrote 573 MB of glTF meshes and TGA textures under `<out>/<package>/StaticMesh/<name>.gltf` and `<out>/<package>/Texture/<name>.tga`, and every `StaticMesh='Package.Group.Name'` reference in the T3D resolves to one of those files (0 missing of 157). The map package itself yields its 70 local static meshes, 46 textures and 13 materials. umodel does not export BSP, terrain or actor placements.

## The BSP

The T3D holds the brushes that make up the BSP, not the compiled BSP. Of 462 `Brush` actors, 432 carry geometry (none rotated; vertices are brush-local, so world position is vertex minus `PrePivot` plus `Location`): 337 additive (2,053 polygons, median bounding box 144 by 56 by 32 units, 146 smaller than 256 units, mostly walls, ledges and stairs) and 94 subtractive (566 polygons; the largest span the whole world and are the void). The additive brushes use building, road and tunnel textures (`concreteroof`, `Half_Light_Hotel_Stone`, `House3_Concrete`, `LondonStreetTarmac`, `Car_Tunnel_Metal`). Their X range is -5,856 to 9,536 and Y range is -12,288 to 4,032, but they cluster in a few building complexes; one group lies far south of the terrain at Y around -10,000 to -12,000. Measured against the terrain, 68 textured additive brushes are fully above it, 117 intersect it and 117 are fully below it.

Twenty-nine additive brushes use `Engine.BlackTexture` (256 polygons, six-sided boxes) and include the largest volumes in the level (one spans 9,120 by 3,424 by 1,120 units); 26 of them intersect the terrain. What they are for, invisible collision or zone filler, is not established and needs a render or an in-editor look before deciding whether to build collision from them.

Drawing the polygons of the additive brushes (skipping `BlackTexture` and the world-size subtractive brushes) gives an approximate visible result without a boolean operation; a faithful result needs the additive and subtractive operations applied in level order.

## Layout

The terrain is a bowl about 12,000 units across. The 12 `PlayerStart` actors form a ring near the center around (0, -1,500), the 157 `ZombieVolume` actors ring the valley edge and the 4 `ShopVolume` actors sit at the sides.

## Converting the export

`uv run scripts/kf1_mountain_pass.py prepare` checks the T3D hash and writes `.tools/kf1/mesh.json` (40 MB: terrain, 1,810 placed meshes, the perimeter walls and the terrain collision) and `.tools/kf1/kf1-mountain-pass.mblevel.json`, in about five seconds. `verify-export` only checks the hash. The walkable outline, perimeter walls, floor lookup, glTF accessor reader and the `object.place` edit builder live in `scripts/level_geometry.py`, shared with `scripts/conker_colors.py`; the Conker script keeps thin wrappers that bind its own kill floor, pit floor and anchors.

- **Coordinates.** Unreal Engine 2 is left-handed with Z up, as Unity is left-handed with Y up, so `world_point()` is a cyclic permutation (Unreal X, Y, Z become Megabonk Z, X, Y) and needs no winding flip for terrain. The scale is 0.028 world units per Unreal unit, the Conker value, and has not been tuned in game.
- **Rotation.** Rotators are 65536 units per turn, applied as roll about X, then pitch about Y, then yaw about Z. The roll sign is unverified; it only matters for the few tilted props.
- **Meshes.** umodel writes glTF as Y up, meters, with Unreal Y and Z swapped (`ExportGLTF.cpp`, `TransformPosition`), so a vertex returns to Unreal units as `(x, z, y) * 100` before `DrawScale3D`, rotation and `Location` apply. That composite is a reflection, so triangle winding is reversed, as Conker does. umodel writes unsigned 16-bit indices. Its materials carry only a base color factor and no textures, so `mesh.json` materials hold the name and color until the texture mapping is built.
- **Terrain.** 256 by 256 samples, 64 units apart, centered on the origin (sample 128 at 0), height `(value - 32768) / 256 * 64`. The 12 `PlayerStart` actors rest 34 to 43 units above this surface, which confirms the fitted scale.
- **Anchors.** The first `PlayerStart` is the spawn. The `ZombieVolume` farthest from it that has a floor is the boss spawner, which is a stand-in until the boss area is chosen by hand. `ShopVolume` actors become shrine spots, `KFAmmoPickup` actors power-up spots and `KFRandomItemSpawn` actors chests. Every anchor is dropped onto the terrain within 100 units.
- **Anchors on BSP.** 17 of 157 zombie volumes, 3 of 4 shop volumes, 4 of 14 ammo pickups and 6 of 14 item spawns stand on BSP floors well off the heightmap, so there is no terrain floor within reach. The converter skips and lists them instead of failing, and the spawn alone must succeed. They return once the BSP geometry exists. Until then the level has one shrine spot, and the runtime needs more spots than shrines (see `shrineSpots` in [level-format.md](level-format.md)).
- **Level fields.** Only fields the Conker level already writes are used: no `packs` and no bundle placement until the pack exists, and the placeholder one-cell `grid` that a from-scratch level requires.

## TODO

- Establish what the `BlackTexture` brushes are (a render of terrain, meshes and brushes would settle it).
- Rebuild the BSP so the skipped anchors have a floor, and add more shrine spots.
- Map `StaticMesh`, `Skins` and material references (Shader, Combiner and TexPanner objects exported as `.mat` by umodel) onto textures for the Unity pack, and texture the terrain from its layer alpha maps.
- Tune `SCALE` against the player in game and confirm the roll sign.
