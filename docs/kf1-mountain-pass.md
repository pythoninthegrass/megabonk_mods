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
- The frames have been triaged. Contact sheets of 30 frames each were read for area coverage, then every frame cited below was re-read at full resolution. No frames were deleted: the dump is still complete, and the triage produced the index in [Reading the footage](#reading-the-footage) rather than a curated subset. Frames not cited there are unverified.
- The run is a solo `Survival - Suicidal` game of four waves plus a boss, on the map the score overlay names `kf-mountainpass_zfix` (`frame_0729`, in-game clock 11:31), which is the same package as `KF-MountainPass_zfix` in [Why not the Killing Floor 2 version](#why-not-the-killing-floor-2-version). The top-left HUD box shows the wave as `n/4` and beside it either the zombies left in the wave (`frame_0027` shows 32) or the inter-wave countdown (`frame_0116` shows 0:56), so the large number is not a wave index.
- Full-screen shop, inventory, score and loadout overlays hide all geometry. Re-read at full resolution and confirmed are `f0153` and `f0340` (the `INVENTORY` / `PURCHASE GEAR` shop, whose top-center header also reads `WAVE n/4`), `f0729` (the score overlay) and `f0905` (the loadout wheel). Contact sheets show further shop and overlay screens around `f0149`-`f0158`, `f0340`-`f0347`, `f0529`-`f0538`, `f0734`, `f0756`-`f0759` and `f0771`-`f0772`, none of them re-read frame by frame.
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

## Terrain layers

`TerrainInfo1` is the level's only terrain actor. Its `TerrainMap` is `Texture'KF-MountainPass.Terrain_Main'` (the heightmap in [Exporting the level with UCC](#exporting-the-level-with-ucc)) and it holds seven terrain layers plus two decoration layers. `uv run scripts/kf1_mountain_pass.py terrain-inventory` reads the actor out of the verified T3D, resolves every package-qualified reference against the umodel export, writes `.tools/kf1/terrain_layers.json` and prints this table:

| slot | role | diffuse | mask | weight channel | diffuse size | mask size | UScale | VScale | units per tile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | ground | Landscape_T.Soil.earth_1051 | KF-MountainPass.Main_Dirt | constant | 1024x1024 | 256x256 | 2 | 2 | 128 |
| 1 | ground | Landscape_T.Grass.grass_2589 | KF-MountainPass.Main_Grass | alpha | 1024x1024 | 256x256 | 2 | 2 | 128 |
| 2 | ground | KF-MountainPass.GUP-MountainRock | KF-MountainPass.Main_Rock | alpha | 1024x1024 | 256x256 | 2 | 2 | 128 |
| 3 | ground | KF-MountainPass.GUP-GravelRocks | KF-MountainPass.Main_Gravel | alpha | 1024x1024 | 256x256 | 1.5 | 1.5 | 96 |
| 4 | ground | WyreTex.Common.MudGround | KF-MountainPass.Main_Forest | alpha | 1024x1024 | 256x256 | 2 | 2 | 128 |
| 6 | ground | KF-MountainPass.GUP-MountainGrass | KF-MountainPass.Main_DecoGrass | alpha | 1024x256 | 256x256 | 1 | 1 | 64 |
| 7 | mask-as-diffuse | KF-MountainPass.Main_DecoGrass | KF-MountainPass.Main_DecoFoliage | alpha | 256x256 | 256x256 | 1 | 1 | 64 |

`Layers(5)` is absent from the export: the actor jumps from 4 to 6. Nothing is synthesized into it and the slot numbers above are the export's own.

- **UVs.** Every layer's `TerrainMatrix` has `XPlane` and `YPlane` equal to `1 / (64 * UScale)` and `1 / (64 * VScale)`, so the diffuse tiles every `64 * UScale` world units: 128 units for the 2.0 layers, 96 for the gravel's 1.5 and 64 for the two 1.0 layers. `ZPlane` is 4 and `WPlane` is `(W=1, X=1/64, Y=1/64, Z=524272)` in all seven layers, so nothing distinguishes them but `UScale`, `VScale` and their textures.
- **Masks.** The seven `Main_*` textures are 256 by 256, `TEXF_RGBA8`, `TC_Wrap`, `Detail = None`, and their color channels are a flat `(127, 127, 127)` while the alpha channel runs the full 0 to 255. The layer weight is therefore the alpha channel, which `kf1.mask_summary` determines per texture from the exported TGA rather than assumes. Reading color instead would give every layer the same constant half weight, and the map would show no layering at all.
- **Weights are not normalized.** Summed over the seven masks the mean is 2.04 and the maximum 5.3, so a blend must renormalize; the minimum is 1.0, which is `Main_Dirt`'s constant contribution where no other layer weights. Mean weight and the share of samples above half: `Main_Dirt` 1.000 / 1.000, `Main_Grass` 0.109 / 0.106, `Main_Rock` 0.088 / 0.087, `Main_Gravel` 0.042 / 0.044, `Main_Forest` 0.089 / 0.076, `Main_DecoGrass` 0.529 / 0.535, `Main_DecoFoliage` 0.182 / 0.190. Each mask maps 1:1 onto the 256 by 256 heightmap grid. Averaging the heightmap under each mask corroborates the channel: `Main_Grass` and `Main_Forest` sit on high, gentle ground (mean height 407 and 411 units against 101 everywhere, mean slope 0.60 and 0.64 against 0.85), `Main_Gravel` on the steepest ground (1.16), and the masks draw as coherent regions, not noise. The row order of the masks against the heightmap is not established; both orientations give plausible statistics, so the blend has to confirm it.
- **Ground versus decoration.** KF1's `Texture` class carries no ground or decoration flag: every layer texture and every mask is an ordinary `Texture` with `bMasked = false`, `bAlphaTexture = false` and `Detail = None`. The semantics come from how the actor uses them. The five color diffuses (`Landscape_T.Soil.earth_1051`, `Landscape_T.Grass.grass_2589`, `GUP-MountainRock`, `GUP-GravelRocks`, `WyreTex.Common.MudGround`) are `TEXF_DXT1` 1024 by 1024 wrapping color textures used only as layer `Texture`s. The `Main_*` masks are used only as layer `AlphaMap`s and decoration `DensityMap`s, with one exception.
- **Slot 7 is a mask painted as a surface.** Its `Texture` is `KF-MountainPass.Main_DecoGrass`, the same object that is slot 6's `AlphaMap` and `DecoLayers(1)`'s `DensityMap`. That object's color is a flat 127 gray, so wherever `Main_DecoFoliage` weights it (19% of the grid) the layer paints uniform mid-gray. KF1's properties give no intent: every mask here is an ordinary `Texture`, so this is either a deliberate flat tint or a reference to the wrong object. Nothing else in the map paints a flat gray ground, so treat it as a mistake to settle in the blend, which can drop the slot or substitute a real surface.
- **Slot 6 is the decoration grass layer itself.** `KF-MountainPass.GUP-MountainGrass` is `TEXF_DXT3`, 1024 by 256, `TC_Clamp` on both axes and `bMasked = true`: a clamped masked strip rather than a tiling ground texture, which fits a grass thicket rather than soil.

### Decoration layers

| slot | mesh | density map | scale | density | fadeout | align |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | WyreStatics.Forest.WyreMiddleFoliage | KF-MountainPass.Main_DecoFoliage | 0.2-0.3 xyz | 0.04-0.09 | 3000 | yes |
| 1 | KF-MountainPass.GUP-GrassLOD | KF-MountainPass.Main_DecoGrass | 0.8-1.0 xy, 0.5-1.0 z | 0.5-0.75 | 3000 | yes |

`DecoLayerOffset` is -4. The inventory resolves both meshes and both density maps; `GUP-GrassLOD` came with the map package and `WyreMiddleFoliage` is recovered from `WyreStatics.usx`. Its two shader slots are `Static.WyreMiddleFoliage_shdr` and `Statics.FoliageB_shdr`, whose diffuse textures are `WyreTex.Static.WyreFoliageTex` and `WyreTex.Statics.FoliageBTex`, both exported. Note the two adjacent group names, `Static` and `Statics`: resolution goes through `package/group/object`, never the bare object name, which is also what keeps `Landscape_T.Soil.*` and `Landscape_T.Grass.*` apart.

### Recovering the layer textures

The map package exports with the level (see [Exporting meshes and textures with umodel](#exporting-meshes-and-textures-with-umodel)); the five third-party textures below do not, and neither does the decoration mesh from `WyreStatics`. Run these on the box that holds the KF1 install and the source-built umodel, from `.tools/kf1`, with the packages under `game/` and the export tree in `out/`:

```sh
# textures: -groups writes <package>/<Group>/<object>.tga, which the group-qualified names need
./umodel-kf1.sh -export -groups -out=/out /game/Textures/Landscape_T.utx earth_1051 Texture
./umodel-kf1.sh -export -groups -out=/out /game/Textures/Landscape_T.utx grass_2589 Texture
./umodel-kf1.sh -export -groups -out=/out /game/Textures/WyreTex.utx MudGround Texture
./umodel-kf1.sh -export -groups -out=/out /game/Textures/WyreTex.utx WyreFoliageTex Texture
./umodel-kf1.sh -export -groups -out=/out /game/Textures/WyreTex.utx FoliageBTex Texture
# the decoration mesh
./umodel-kf1.sh -export -groups -out=/out -gltf /game/StaticMeshes/WyreStatics.usx WyreMiddleFoliage StaticMesh
# umodel runs as root inside the container, so hand the new trees back to the user
docker run --rm -v "$PWD/out:/out" ubuntu:24.04 chown -R "$(id -u):$(id -g)" /out/Landscape_T /out/WyreTex /out/WyreStatics
```

The container writes outside the mounted directory unless `-out=/out` is passed, and without `-groups` it flattens every texture into `<package>/Texture/`, where `Landscape_T.Soil.earth_1051` and a same-named object in another group would overwrite each other. `umodel -dump <package> <object> Texture` prints the UE2 properties quoted above (`Format`, `USize`, `VSize`, `UClampMode`, `VClampMode`, `bMasked`, `Detail`) without needing `UCC.exe`, and `-list <package>` shows each object's index and name. Then copy the new trees to the authoring box and check them:

```sh
rsync -a <box>:git/megabonk_mods/.tools/kf1/out/{Landscape_T,WyreTex,WyreStatics} .tools/kf1/out/
uv run scripts/kf1_mountain_pass.py terrain-inventory
```

The inventory needs every object the actor names: the four third-party textures, the map-local rock, gravel, grass and the seven `Main_*` masks, and both decoration meshes. Anything missing fails with its qualified name, for example `Landscape_T.Soil.earth_1051 is not exported under .../out`, rather than substituting gray. Only the heightmap is exempt, because umodel cannot read its `TEXF_G16` format and `UCC.exe` writes it instead.

## The BSP

The T3D exports construction brushes rather than the compiled BSP mesh. Counting explicit actor-level `CsgOper` values gives 367 additive brushes (2,431 polygons), 94 subtractive brushes (566 polygons) and one brush without an operation. Vertices are brush-local: subtract `PrePivot`, add `Location`, then convert the axes and scale. The additive pass triangulates each polygon in vertex order, groups faces by their `Texture` reference and appends the same triangles to collision. It adds 4,784 triangles across 345 brushes. Rooms and doorways carved by later subtractions are still approximate.

`Engine.BlackTexture` is a surface material, not a collision flag. There are 142 mixed-material additive brushes; dropping a whole brush for one black face would remove walls and floors. The 22 entirely black additive brushes fall into two groups:

- **17 zone portals.** Each is a single sheet with actor `PolyFlags=67108873` (`0x04000009`: portal, not solid, invisible). In a top-down render of terrain, props and brush faces these appear as short cross-sections at the buildings. They belong in neither the render mesh nor collision.
- **Five solids.** These have six faces and no portal flag. `Brush173` and `Brush186` span most of the valley length; their outlines cover terrain and cross the road. `Brush245` is a building-sized box intersected by later subtractive brushes. `Brush23` and `Brush39` are smaller closed solids. The overlay establishes that these are construction volumes rather than portal sheets; it does not establish which of their faces survive in the compiled map. The additive pass omits all five instead of creating uncarved walls or floors across playable space. Reevaluate them after ordered subtraction.

UVs come from the polygon's local `Origin`, `TextureU` and `TextureV` and the dimensions of the exported TGA. When a shader exports a diffuse texture, the converter uses that texture. A missing texture leaves the material named but untextured. The standalone mesh JSON references textures relative to `.tools/kf1/`.

## Layout

The terrain is a bowl about 12,000 units across. The 12 `PlayerStart` actors form a ring near the center around (0, -1,500), the 157 `ZombieVolume` actors ring the valley edge and the 4 `ShopVolume` actors sit at the sides.

## Reading the footage

Everything from here to [Where the footage and the KF1 export disagree](#where-the-footage-and-the-kf1-export-disagree) is the KF2 rebuild, read from the playthrough frames. It records how the valley reads and what sits where; it is not a spec, and the KF1 export above is what gets built. Frame numbers are `tools/kf2_mountain_pass_frames/frame_NNNN.jpg` shortened to `f0NNNN`. A frame named individually was re-read at full resolution. A range was read at contact-sheet scale only: it means the feature recurs across that stretch, and any single frame inside it is unverified. Several claims that looked solid at contact-sheet scale did not survive full resolution, and they are called out where that happened so nobody re-adds them.

### Scale

The frames cannot give heights, so heights come from the export and the footage only gives a sense of scale.

- The one metric in the frames is the HUD's top-left `TRADER` readout: the straight-line distance to the Trader Pod in meters. Across the frames read at full resolution it runs from 5 m inside the pod (`f0736`) to 147 m deep in the brick building (`f0027`), with open ground in between (`f0525` 13, `f0168` 17, `f0744` 21, `f0486` 22, `f0357` 30, `f0519` 34, `f0132` 52, `f0378` 54, `f0322` 56, `f0331` 61, `f0060` 92, `f0891` 98, `f0628` 103, `f0003` 114).
- The HUD gives a bound on KF2 distances, not a survey of KF1: the pod relocates between waves and the two maps differ. The KF1 bowl spans about 12,000 Unreal units, or 462 Megabonk units. Megabonk units are not meters.
- The terrain grid spacing is 64 Unreal units (2.464 Megabonk units). The heightmap's raw range of 13,148 to 39,055 gives 6,477 Unreal units of relief, about 249 Megabonk units.
- Where a prop height is quoted below it is a ratio against the player, taken as 1.8 m, and the player is only visible in third person at the end of the run (`f0905`, in a `POLICE` vest), so every such number is rough.

## Terrain and the valley

The playable area is one enclosed valley bowl: a road and building complex on the valley floor, open grassy pine hillsides climbing off it, and a rocky ridge enclosing the whole thing.

- The spawn is a grassy pine clearing on a slope, with worn dirt in the grass and a tan building visible through the trees downslope (`f0003`). This is where `WAVE INCOMING` fires at the start (`f0001`-`f0006`).
- From the clearing the ground drops to the road and rises behind it to a rock ledge; descending that ledge onto the highway is the run's best single overview, with the road winding away below, a metal guardrail and a streetlamp, and the hazy lake and mountain ring beyond (`f0132`).
- The hillsides are grass over rock, with large rounded weathered boulder outcrops rather than sheer faces (`f0116`, `f0132`). Green grass on the upper slopes, dry yellow grass on the valley floor (`f0144`, `f0519`).
- One area is a burned pine stand: blackened silhouetted trees with glowing embers in the trunks, ash-white ground cover and yellow dead grass (`f0091`). This is the only bleached ground in the run.
- There is no snow. Ground that reads white at thumbnail scale is haze, ash or a transient whiteout: `f0896` is white-flooded where `f0891` a few seconds earlier shows green grass in the same place, and `f0116` is green grass under a pale hazy sky.

## The road, its tunnels and its bridges

An asphalt two-lane road is the spine of the valley floor, the only paved surface the run shows, and the built complex sits along it.

- The road's reference shot: two parallel yellow center lines and solid yellow edge lines, the rectangular tunnel portal ahead, a dark SUV with a roof rack on the verge, a green dumpster, a red hatchback, a bent-arm streetlamp, a low X-braced metal railing, and a brick perimeter wall topped with spiked anti-climb fence against the rock cliff (`f0015`).
- W-beam metal guardrail runs along the road edges (`f0132`, `f0241`), with wooden rail fencing on the verge at the lay-by (`f0628`).
- Tall tan concrete retaining walls hold the road against the cliffs, and their crests carry large boulders and panels of fence (`f0013`, `f0015`). Hay bales are only verified stacked at the road edge at the tunnel end (`f0891`); the hay-bale-topped walls logged from contact sheets do not exist, see [Unresolved](#unresolved).
- The road runs through a rectangular concrete tunnel portal set in a tan wall built into a rock cliff (`f0013`, `f0015`), and through a wider box-section underpass: square tan columns, low concrete median blocks with lit base strips, an internal ramp, and parked and wrecked cars inside (`f0357`, `f0382`). Both openings are rectangular; neither is arched.
- Large cylindrical outfall pipes are set in a tan retaining wall above a concrete drainage flume: a stepped concrete channel with metal handrails running alongside the road between rock outcrops (`f0053`-`f0065`, best `f0060`).
- Where the road crosses the drain it has a black metal bridge railing with an X-truss pattern, beside a brick boundary wall topped with spiked anti-climb fence (`f0744`).
- A tall tan concrete wall carrying the tunnel portal and a small lit doorway closes the built end of the road, with boulders above it and the rock cliff behind (`f0015`, `f0891`).
- The road's other end is a lay-by against a tan cliff: a low flat-roof building, a shipping container, a streetlamp, parked and wrecked cars and picnic tables on the verge, all in one view at 103 m (`f0628`).

## Buildings and interiors

Two built groups: a brick complex against the hillsides, and the wooden lake complex.

The brick complex, entered from the road side:

- A sunken concrete terrace or plaza with low retaining walls, steps and ramps sits at the base of the brick buildings (`f0331`).
- Interiors are brick and painted brick with bare concrete floors and ceiling fluorescent tubes: corridors, gray steel double doors, and wooden stairs with yellow nosing strips (`f0027`, `f0021`-`f0052`).
- Signage is stenciled and neon, and mixes French and English: a red neon `<SORTIE>` exit sign over a doorway (`f0027`, `f0736`), a `STOP CLONING` stencil whose `O` is a red bullseye (`f0351`), a red-and-black `DANGER HIGH VOLTAGE KEEP OUT` board and a `NO SMOKING` board reading "violators are subject to termination" on the stairwell brick (`f0031`, `f0042`). The contact-sheet reading of the second sign as `NO DISCARDING` was wrong.
- Room details: a red-and-white striped fire-equipment cabinet (`f0351`), stacked wooden pallets against a wall (`f0031`), scattered newspapers on the floor (`f0027`), red light wash on ceilings, and a small tiled room holding a red flesh mass (`f0157`, contact-sheet only).
- A cyan-glowing trader unit stands inside the brick complex, set against the brick in an open court (`f0031`), so the complex holds its own shop point as well as the pod sites outside it.
- Doors are weldable KF2 doors, which is why an `[E] TAP OPEN/CLOSE, HOLD EQUIP WELDER` prompt appears (`f0351`).

The lake complex, on the valley floor:

- A raised wooden boardwalk and observation-deck network over a hazy lake: plank walkways, post-and-rail balustrades, stairs, with mountains beyond (`f0168`); picnic tables, a lamppost and a graffiti'd shed appear across the surrounding stretch (`f0160`-`f0196`).
- The Trader's outdoor vendor spot is next to it: a rusty two-tone VW camper van, a red-and-white striped patio umbrella, bistro chairs and a cafe table on dry grass against a graffiti'd brick wall (`f0144`).

Small outbuildings sit at the base of the cliffs: a brick-and-corrugated storage shed with a lit interior and a concrete threshold ramp, a yellow hatchback beside it (`f0525`), and a dark corrugated shed nearby (`f0526`, contact-sheet only).

## Walls, fences and gates

- A brick perimeter wall runs along the highway, with chain-link and spiked anti-climb fencing above it in places (`f0013`, `f0015`, `f0744`).
- Fence panels also stand on the crest of the tan road retaining wall, and anti-climb fence caps the cliff-side wall at the lay-by (`f0015`, `f0628`).
- The only gates are the weldable steel doors in the brick complex, not gates in the fence line (`f0351`).

## Vegetation

- Conifers throughout: tall spruce or fir on the slopes and scattered specimens on the valley floor (`f0003`, `f0322`, `f0628`).
- Grass is the ground cover everywhere the road and buildings are not, green on the slopes and dry yellow on the floor (`f0116`, `f0519`).
- One burned stand of blackened pines (`f0091`).
- At least one deciduous tree among the conifers, at the cliff-base shed (`f0525`).
- Fallen logs lie on the forest floor and across the hillsides above the road (`f0502`-`f0510`, `f0701`-`f0702`, unverified at full resolution).

## Vehicles, debris and camp props

The road is dressed as a disaster scene rather than a clean highway.

- A landmark cluster on the grass beside the road: a rearing-horse equestrian statue on a tall stone pedestal, a white `SAMU de PARIS` / `MEDECIN` ambulance with a blue lightbar, a police car, and a tan-camo six-wheeled armored personnel carrier (`f0378`, `f0466`).
- Parked and abandoned vehicles: police cars with blue lights (`f0382`, `f0276`-`f0291`), a box truck or box trailer (`f0017`-`f0019`, `f0382`), sedans and hatchbacks, a pickup at the tunnel mouth (`f0891`).
- Wreck clusters: burned-out sedans and an overturned white cylindrical tanker trailer with a red stripe, among pines on a slope (`f0486`, `f0482`-`f0491`); a red hatchback on a concrete pad at the bridge (`f0744`); a green hatchback on the verge at the lay-by (`f0628`); a red car wreck at the tunnel portal (`f0013`).
- Camp props on the grass near the cliff base: a plank bonfire built inside a ring of large boulders, giving off black smoke, with two wooden picnic tables beside it and the yellow hatchback beyond (`f0519`).
- Green waste dumpsters by the road and at the built end (`f0013`, `f0015`, `f0718`-`f0750`).
- A crashed aircraft lies on the pine hillside: a dark fuselage with its tail fin among the trees, beside a worn dirt footpath (`f0322`).
- A crashed plane, a statue and an ambulance together mean the valley reads as a disaster site, not empty wilderness; the prop density along the road is what makes the map read as a pass rather than a field.

## Trader spots

KF2 drops the Trader Pod at a different site each wave, and four distinct ones appear, which is the closest the footage comes to corroborating the export's 4 `ShopVolume` actors:

- A rocky hilltop overlook above the lake: a weathered dark rock ledge with grass, hazy peaks beyond, the pod marked by a teal beacon beam (`f0116`, `f0124`). Chain-link fence is reported across this stretch (`f0116`-`f0150`) but not confirmed at full resolution.
- The outdoor vendor spot with the VW van and umbrella (`f0144`).
- An enclosed pod interior: gray block-wall corridors with glowing cyan guide lights, concrete counters and benches, red-lit doorways, a blue glowing trader door unit and a red neon `<SORTIE>` over the exit (`f0730`-`f0739`, `f0752`-`f0760`, best `f0736` and `f0729`).
- The low flat-roof building at the road's lay-by, its trader door glowing cyan (`f0628`).

Two further indoor cyan `USE TRADER` wall kiosks are reported at contact-sheet scale (`f0339`, `f0527`), alongside the verified unit at `f0031`.

## Map edges

The valley reads as closed on every side, which is what keeps a wave from running off the map:

- A hazy ring of mountains and ridgelines sits behind everything at eye level from the high ground (`f0116`, `f0132`, `f0628`).
- A lake fills one side of the valley floor, with the boardwalk complex out over it (`f0168`, `f0132`).
- Tan rock cliffs pinch the road into passes, and fencing closes those passes (`f0013`, `f0628`, `f0744`).
- Nothing in the run shows a visible wall or skybox seam; the edges read as terrain and haze rather than geometry.

## Waves, spawns and the boss

One run, four waves then the boss, with the wave counter read directly from the HUD:

- Wave 1 of 4: `f0027` (32 left, in the brick interior), `f0091` (7 left, burned stand), `f0116` (0:56 inter-wave timer at the overlook).
- Wave 2 of 4: `f0322` (0:39, plane hillside), `f0351` (0:10, `STOP CLONING` room).
- Wave 3 of 4: `f0519` (0:50, bonfire camp).
- Wave 4 of 4: `f0628` (32 left, the lay-by), `f0729` (score overlay open, `WAVE 4/4`).
- Boss wave: the intro card names `The Patriarch`, "once a brilliant scientist, until he became his own greatest creation" (`f0793`), the HUD reads `WAVE FINAL / BOSS` with his health bar top-center (`f0891`), and the `VICTORY` banner is up by `f0896` and still up at `f0905`, persisting to the last frame `f0910`.
- The boss fight is on the open highway at the tunnel-portal end, around the rectangular portal, the hay bales, the boulders and the parked vehicles (`f0796`-`f0891`, best `f0891`). It is not an enclosed arena, and no gated fight space exists anywhere in the run.
- Waves arrive across open ground from every direction rather than through fixed corridors: enemies come up the hillside to the player (`f0071`-`f0083`) and out along the road, consistent with the 157 `ZombieVolume` actors ringing the valley edge, though the footage cannot verify that count or their positions.

## KF2 look

Treat all of this as KF2's look, not KF1's, per the caveat in [Playthrough reference footage](#playthrough-reference-footage).

- Warm low sun, either dawn or dusk, with the valley filled by a strong ground haze that flattens distance and turns the far mountains into flat silhouettes.
- Pale, nearly white overcast sky on the high ground; the sky carries almost no shape and is not a reliable reference for the KF1 sky.
- Palette is muted tan and ochre rock, desaturated green grass, dry yellow grass on the floor, gray concrete, red brick, dark green conifers. The only saturated notes are the red neon and the cyan Trader beacon.
- Textures are worn and stained throughout: graffiti on brick, wood and trailers, rust on vehicles, blood and scorch on floors.
- Signage mixes French and English: `SAMU de PARIS`, `MEDECIN` and `SORTIE` sit alongside `STOP CLONING`, `NO SMOKING` and `DANGER HIGH VOLTAGE KEEP OUT`, so the valley reads as a French or Swiss alpine pass. KF1 gives no such signal and the KF1 build should not import it.

## Where the footage and the KF1 export disagree

The KF1 export is authoritative and the footage loses every argument here; the disagreements are recorded rather than resolved.

- Far-south brushes. The export has an additive-brush group at Y about -10,000 to -12,000, far south of the terrain, and brush Y reaches -12,288. Nothing in a full 16-minute run leaves the bowl, so the footage neither shows nor contradicts that group. It stays in the export as out-of-bounds or filler geometry and should not be rebuilt from a frame.
- Brush X and Y range. Brushes span X -5,856 to 9,536 and Y -12,288 to 4,032, an asymmetric extent, while the frames show one enclosed bowl with no second district off to one side. The frames cannot see underground or indoors systematically, so the export's range stands.
- Spawn. The export has 12 `PlayerStart` actors in a ring near (0, -1,500); KF2 has a single spawn point in the pine clearing (`f0003`). The footage shows one spawn because one player spawned once, so it cannot confirm or deny the ring. Build the ring from the export.
- Enemy spawns and shops. The footage corroborates the shape of the export's intent (waves from the valley rim, four trader sites) without confirming either count.
- The `BlackTexture` brushes. The footage gives no evidence about the `BlackTexture` brushes; their classification comes from the KF1 export (see [The BSP](#the-bsp)).

## Unresolved

Claims that survived only at contact-sheet scale, so they are recorded as open rather than as fact:

- Whether the road's built end is a warehouse with garage-door openings. `f0241`, `f0261`, `f0296` and `f0300`, logged from contact sheets as showing it, at full resolution show a Siren beside the guardrail, and grassy slopes with boulders. What is verified there is the tall tan retaining wall with the rectangular portal (`f0015`, `f0891`). Resolved by a full-resolution read of `f0235`-`f0300`.
- Whether the road's retaining walls are topped with stacked hay bales. The crests at `f0013` and `f0015` carry boulders and fence panels. Hay bales are verified only at the tunnel end (`f0891`). Resolved by the same full-resolution read.
- Whether chain-link fence runs up the rock cliffs to close the passes, and whether the overlook ridge is fenced. Both are contact-sheet observations only, at `f0116`-`f0150` and around `f0218`. Resolved by reading those frames at full resolution.
- Whether the brick complex is roofed or open to the sky. `f0031` lights a walled brick court with hanging fluorescent tubes under a black void, which could be a ceiling in shadow or open sky at this hour. Resolved by a frame where the sun is on that volume, or by the KF1 brushes for the same rooms.

Open questions:

- Whether the KF1 map has the burned pine stand, the lake boardwalk complex, the crashed plane, the statue-and-ambulance memorial and the armored personnel carrier, or whether those are KF2 additions. Resolving it needs the KF1 static mesh and skin lists matched to the frames, which is the texture-mapping TODO below.
- The relative arrangement of the road complex and the lake: the frames show both on the valley floor and both near the spawn, but the run never shows them in one view, so which side of the bowl each is on is not established. The export's brush and mesh positions are the only way to settle it.
- Whether the brick complex is one building or several, and how its interior levels stack. The frames show corridors, stairwells and a sunken terrace but never the building from outside as a whole. Resolved by the KF1 brush geometry, which has the wall and floor slabs, or by a second video angle.
- How many trader sites the map actually has. The pod appears at four distinct-looking places, which matches the export's 4 `ShopVolume` actors, but the cyan trader unit inside the brick complex (`f0031`) and the reported wall kiosks (`f0339`, `f0527`) may be a fifth and sixth, or may be decorations at the four. Resolved by comparing pod and kiosk positions with the `ShopVolume` locations once the level is placed.
- Whether those KF2 trader sites sit where the four `ShopVolume` actors are. Comparing them would say whether the KF2 shop spots still match the KF1 shop rooms.
- Whether the trader pod sits on the rocky overlook because that is high ground or because it is a defined shop zone; the frames cannot tell, and it matters for where to put shrine spots. The KF1 `ShopVolume` placements answer it directly.
- The height of the retaining walls and the boardwalk above the ground. No frame gives a clean side elevation against a known reference. Resolved by the heightmap plus the BSP floors once the BSP is rebuilt.
- The fallen logs at `f0502`-`f0510` and `f0701`-`f0702`, and the horizon crane at `f0376` and the overhead girder at `f0428`-`f0429`, which were reported from contact sheets and are uncertain even at that scale. Resolved by a full-resolution read of those ranges.

## Converting the export

`uv run scripts/kf1_mountain_pass.py prepare` checks the T3D hash and writes `.tools/kf1/mesh.json` (terrain, static meshes, additive brush faces, perimeter walls and combined terrain/brush collision), `.tools/kf1/kf1-mountain-pass.mblevel.json` and, derived from it, the preview level described in [Previewing the level in game](#previewing-the-level-in-game), in about five seconds. `verify-export` only checks the hash. `terrain-inventory` writes `.tools/kf1/terrain_layers.json` and prints the table in [Terrain layers](#terrain-layers). The walkable outline, perimeter walls, floor lookup, glTF accessor reader and the `object.place` edit builder live in `scripts/level_geometry.py`, shared with `scripts/conker_colors.py`; the Conker script keeps thin wrappers that bind its own kill floor, pit floor and anchors.

- **Coordinates.** `world_point()` maps Unreal X, Y, Z to Megabonk Z, X, Y without reversing winding. The [KF1 human pawn](https://github.com/InsultingPros/KillingFloor/blob/HEAD/KFMod/Classes/KFHumanPawn.uc) has a standing collision half-height of 50 Unreal units. Matching its full height to the [3.85-unit Megabonk player capsule](thps-warehouse-layout.md) gives 0.0385 Megabonk units per Unreal unit. At the center of the tarmac face on `Brush29` the road is 401 Unreal units above the heightmap, or four standing players high. This measures deck to terrain, not clear headroom under the deck.
- **Rotation.** Rotators are 65536 units per turn, applied as roll about X, then pitch about Y, then yaw about Z. The roll sign is unverified; it only matters for the few tilted props.
- **Meshes.** umodel writes glTF as Y up, meters, with Unreal Y and Z swapped (`ExportGLTF.cpp`, `TransformPosition`), so a vertex returns to Unreal units as `(x, z, y) * 100`. Multiply `DrawScale3D` by the uniform `DrawScale`, then rotate and translate. The axis swap reverses winding. Actor `Skins` override mesh material slots. The converter looks up the exported texture or follows the material's `Diffuse` reference. A texture with cutout alpha supplies its own mask; unresolved static materials carry their glTF fallback color as vertex colors so the vertex-tint shader can display it.
- **Terrain.** 256 by 256 samples, 64 units apart, centered on the origin (sample 128 at 0), height `(value - 32768) / 256 * 64`. The 12 `PlayerStart` actors rest 34 to 43 units above this surface, which confirms the fitted scale.
- **Anchors.** The first `PlayerStart` is the spawn. The `ZombieVolume` farthest from it that has a floor is the boss spawner, which is a stand-in until the boss area is chosen by hand. `ShopVolume` actors become shrine spots, `KFAmmoPickup` actors power-up spots and `KFRandomItemSpawn` actors chests. Every anchor needs a terrain or brush floor within 100 Unreal units.
- **Grounded spots.** Combined collision leaves 5 of 157 zombie volumes, 1 of 4 shop volumes, 2 of 14 ammo pickups and 3 of 14 item spawns without a floor in reach. Those anchors are reported and skipped. The three grounded shop spots are supplemented with grounded navigation nodes, selecting the most distant from the spawn, boss and already selected spots until there are eight candidates for up to seven shrines.
- **Level fields.** Only fields the Conker level already writes are used: the placeholder one-cell `grid` that a from-scratch level requires, and no `packs` entry or bundle placement, which the preview level adds instead. That is why `prepare`'s own level file cannot show the map; see [Previewing the level in game](#previewing-the-level-in-game).

## Previewing the level in game

The game never reads `mesh.json`. Its one terrain mesh, 1,810 static mesh placements and 345 brush meshes live there only until something packs them into an AssetBundle, so `.tools/kf1/kf1-mountain-pass.mblevel.json` loads as the stock map named by `map` (1 is Forest) with the chests placed and nothing wrong logged. Launch the preview level instead:

```sh
task game:editor -- .tools/kf1/bsp-preview.mblevel.json
```

`DevHarness: load-level` in `BepInEx/LogOutput.log` names the file that actually loaded. The preview level is the generated one plus exactly two things: a `"packs": {"kf1preview": "1.0.0"}` entry, and one extra `edits` entry of `opType` `object.place` whose payload places `bundle:kf1preview/MountainPass` at the origin with unit scale. Nothing else differs, so it is derived rather than hand-maintained: `prepare` writes it beside the generated level, and this rewrites it from the generated level alone:

```sh
uv run scripts/kf1_mountain_pass.py preview-level
```

`kf1.preview_level` holds those two additions. `tests/test_kf1_mountain_pass.py` pins them and compares the regenerated file with the one on disk byte for byte, so an edit made only to the preview file fails the suite and the verb puts it back.

### The kf1preview pack

`kf1preview` is a 55 MB bundle holding the whole map as the single asset `MountainPass`. `unity/pack-authoring/Assets/Editor/Kf1MountainPassPack.cs` builds it from `.tools/kf1/mesh.json`, reusing `PackBuilder.cs` and `ColorsVertexTint.shader` the way `ConkerColorsPack.cs` does, and `unity/pack-authoring/packs/kf1preview/manifest.json` is its manifest. Textures are read from their `mesh.json` paths relative to `.tools/kf1` and imported directly, so the umodel export described in [Recovering the layer textures](#recovering-the-layer-textures) has to be on the building box too.

```sh
task kf1:pack      # on a box with Unity 2023.2.22f1
task kf1:install   # the bundle for this game's runtime, plus the manifest
```

`kf1:pack` needs Unity on the machine that runs it, which is a build-time dependency only ([asset bundles](asset-bundles.md)). `UNITY_EDITOR` in `.env` overrides the default Hub path, and when no editor is there the task says so and names the path it looked for. It builds `windows` and `linux` into `.tools/bundles/<platform>/kf1preview`, and `kf1:install` picks the one the game's runtime wants: windows under CrossOver and Wine, linux for the native build. One run builds both target platforms, so the editor needs the Windows and Linux build-support modules, `windows-mono`, `linux-mono` and `linux-il2cpp` in the Hub's module ids. Every box that builds keeps its own `.tools/kf1` converter outputs current, because the build reads them off disk: `mesh.json` from `prepare` and the `out/` tree from the umodel export, both of which are produced on the box that holds the KF1 install and carried across with the finished bundle. A box that only plays receives the bundle instead.

`kf1:pack` is idempotent. Task gates it on a content checksum of the builder, `PackBuilder.cs`, the shader, the manifest, the converter, `mesh.json` and every `.tga` under `.tools/kf1/out`; a repeat run prints `task: Task "kf1:pack" is up to date` and `--force` rebuilds. The checksums live in `.task/checksum/`, and a build that fails records nothing, so a failing run happens again rather than settling for a stale bundle. `uv run scripts/kf1_mountain_pass.py verify-pack` runs first and names the offender rather than building a pack with holes in it: `material KillingFloorStatics.TruckShader needs texture out/T/TruckOneCanvasDiffuseTGA.tga, which is not under .tools/kf1`. `tests/test_kf1_pack.py` pins the manifest to the pack and asset the level places, pins the builder to the same names, keeps the build local by failing on any ssh or rsync leg, and fails if any source pattern stops matching a file, which would otherwise mean a silent rebuild on every run.

What the build does guarantee is the same result in game, not the same bytes. Two forced builds of unchanged inputs produce bundles with different hashes, because the builder recreates `Assets/Kf1MountainPass/` and Unity re-imports the generated meshes, materials and textures with fresh GUIDs each run; comparing two builds by hash will always look like a change. Compare them in game instead: the committed builder, a rebuild of it, and the original hand-built bundle at `.tools/kf1/kf1preview` (which took its textures through a PNG conversion rather than importing the umodel `.tga` files directly) render the same frame, each pair differing by a mean luma of 0.43 of 255 with under 0.06 per cent of pixels differing by more than 15, all of them the animated editor overlay. That comparison has teeth: with the bundle file removed and the manifest left in place, the same camera differs by a mean 52.94 of 255 across 72 per cent of pixels, so a pack that renders nothing is not mistaken for a match.

A missing pack does not fail the load, and neither does a pack whose bundle is absent: the placement becomes a placeholder cube either way, so the symptom is the same and only the log tells them apart. With no pack directory at all the line is `Packs: 'bundle:kf1preview/MountainPass': pack 'kf1preview' is not installed; using a placeholder`. With the manifest installed but the bundle missing, or holding no such asset, it is `Packs: manifest of 'kf1preview' lists 'MountainPass' but its bundle does not hold it; not listed in the palette.` followed by `asset not found in its pack; using a placeholder`, and the `LiveEdit: spawned` line names the prefab `Missing:bundle:kf1preview/MountainPass`. The second shape is what a bundle transfer that copied only the manifest produces. A box that only plays can be given the bundle with `rsync .tools/bundles/<platform>/kf1preview` and `task kf1:install` there, the same transfer pattern [gamepadui](gamepadui.md#transfer-thps-content-and-test-the-player-menus) uses for THPS.

What is expected to look unfinished once the map renders: the terrain is one flat untinted surface until the layer masks are blended, some static meshes carry no texture, and BSP faces fall back to their base color.

## TODO

- Fold the `packs` entry and the `bundle:kf1preview/MountainPass` placement into the generated level so the preview level is no longer a separate artifact, now that `task kf1:pack` can rebuild the bundle.
- Run the `linux` bundle against the native player build; `kf1:pack` produces it, but only the `windows` bundle has been played.
- Apply ordered brush operations and check the five black solids and remaining ungrounded placements against the resulting collision.
- Blend the terrain layer alpha maps into the terrain material: renormalize the weights, decide what to do with the slot that paints a mask as a surface, and confirm the mask row order against the heightmap.
- Confirm the roll sign on tilted props.
