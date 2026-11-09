# AssetBundle authoring

The THPS construction kit has a separate manifest `kitVersion` alongside its
preserved legacy version. Levels using `piece-` or `added-` assets record this
revision so an older pack warns even while `version` remains `2.0.21`. See
[level compatibility](level-format.md#pack-versions) and the
[editable reference assembly](thps-warehouse-layout.md#editable-construction-assembly).

Megabonk runs Unity 2023.2.22f1 on the built-in render pipeline (the game references Post Processing v2 and MK.Toon, not URP; confirm the engine version from `Megabonk_Data/globalgamemanagers` or the first lines of `Player.log`). A bundle for the game has to be built by that exact editor version for the game's platform.

## Authoring project

`unity/pack-authoring/` is a fresh minimal project created with `Unity -createProject`. It holds only `Packages/manifest.json` (the `assetbundle` and `physics` modules), `ProjectSettings/`, and `Assets/Editor/PackBuilder.cs`. `GraphicsSettings` has no render pipeline asset, which is the built-in pipeline. Unity's generated state (`Library/`, `Temp/`, `Logs/`, `UserSettings/`, the generated `TestProp` assets) is gitignored.

A fresh project was chosen over upgrading `.tools/mb_terrain_generator`. That project is Unity 2022.3 on URP, and converting it to 2023.2.22f1 and the built-in pipeline is work with no payoff for a first bundle. It is also paid third-party content that must never be redistributed or committed.

## Building

Install Unity 2023.2.22f1 through Unity Hub (it is an archived version; install it from the Hub's archive page) with the **Windows Build Support (Mono)** and **Linux Build Support (Mono)** modules. The scripting backend does not affect a bundle, because a bundle holds serialized data and no compiled code. Sign in to Hub and keep a Personal licence active: a batch-mode build exits with `No valid Unity Editor license found` otherwise. Opening any project once from Hub after signing in writes the licence file the command line needs.

```sh
task pack:build
```

The task runs `PackBuilder.BuildTestPack` in batch mode. It creates two prefabs, assigns each to its own bundle, and calls `BuildPipeline.BuildAssetBundles` with `ChunkBasedCompression` (LZ4) once per target, writing `testprop` and `testmodel` under `.tools/bundles/windows/` and `.tools/bundles/linux/`. `TestProp` is a cube with a Standard-shader material. `TestModel` is a four-part composite: a body with a textured Standard material (a generated brick PNG), a cylinder with a `Legacy Shaders/Diffuse` material, a sphere with an emissive Standard material and a roof with a plain Standard material. It exercises the shader remap below. Type trees are kept (the default). Set `UNITY_EDITOR` in `.env` to use another editor path. The licensing client prints `Code 10 while verifying Licensing Client signature` errors during the build; they are harmless.

A bundle is built per platform. The Windows build (used under CrossOver and Wine on macOS) needs the Windows bundle and the native Linux build needs the Linux one.

## Loading in the game

`run.py bundle <path>` sends the `load-bundle` harness command, which loads the bundle, lists its assets, resolves the first `GameObject`, and unloads the bundle. Against `.tools/bundles/windows/testprop` in the Wine-hosted game it returns `{"assets": ["TestProp:GameObject"], "prefab": "TestProp"}`, so a bundle built by Unity 2023.2.22f1 for Windows deserializes in the game without errors in `Player.log`.

### Interop limits

The MelonLoader interop assemblies cannot call the synchronous loaders, and the game's own `AssetBundle` class has had them stripped:

- `AssetBundle.LoadFromFile` throws `MissingMethodException` for `Il2CppSystem.ReadOnlySpan<T>.GetPinnableReference`, thrown from the interop's `LoadFromFile_Internal`.
- `AssetBundle.LoadFromMemory` throws `ObjectCollectedException` from `Il2CppSystem.Span<T>..ctor`, even when the managed array is kept alive.
- `LoadAssetAsync`, `LoadFromFileAsync`, `LoadAllAssetsAsync(Type)` and `Unload` have native bodies in `GameAssembly` and work. The parameterless `LoadAllAssetsAsync()` has none and fails with `Invalid call to method`, so use the `Type` overload with `Il2CppType.Of<UnityEngine.Object>()`.
- Reading `AssetBundleCreateRequest.assetBundle` and `AssetBundleRequest.allAssets` blocks until the load completes, which makes the async API usable from a synchronous command handler.

## Packs and `bundle:` catalogIds

A pack is a directory `UserData/LevelPacks/<pack>/` in the game folder. Every file in it with no extension or a `.bundle` extension is loaded as an AssetBundle; other files are ignored. A bundle is platform-specific, so a bundle built for the wrong platform fails to load and is logged as a warning for that file only.

A catalogId `bundle:<pack>/<asset>` resolves to the `GameObject` named `<asset>` in any bundle of pack `<pack>`. The pack is loaded the first time an ID references it and stays loaded for the session, because instantiated prefabs depend on the bundle's data. `Applier.ResolvePrefab` is the single resolver: game-asset IDs go through `CatalogRoute`, and `bundle:` IDs go through `PackPrefabs`, so placing, undoing and saving a pack object use the same edit pipeline as a game prefab. Game-asset IDs find their `MapData` through `CatalogPrefabs.TryFindMap`, which scans the loaded `MapData` assets because `DataManager.maps` omits Hell and Dungeon; `bundle:` IDs never touch it, so packs are not affected by which map is loaded. Pack placement itself has not been run on Hell. The pure lookup and caching live in `PackCatalog`, which is unit tested without Unity.

### Shader remap

Materials in a bundle keep the shader they were authored with, and the game's build only holds the shaders and shader variants its own materials use. `PackShaderRemap.Apply` therefore runs on each prefab as its bundle loads (`PackPrefabs.LoadBundleInto`). It replaces the material on every renderer with a new material on the game's toon shader and copies the properties the rules map. The pure rules are in `shader_remap.cs` (`ShaderRemap.PlanFor`) and are unit tested.

The target is `MK/Toon/Built-in/Standard/Simple + Outline`. In the forest level 1362 of the scene's materials use it, including every textured prop, and it is the only MK.Toon Standard variant with textured, opaque materials. Plain `MK/Toon/Built-in/Standard/Simple` was tried first and rendered an albedo texture as flat white: the keyword combination it needs was not in the build.

| authoring shader | result |
| --- | --- |
| `Standard`, `Standard (Specular setup)`, `Legacy Shaders/*`, `Unlit/*`, `HDRP/*` | remapped, copying the Built-in properties below |
| `Universal Render Pipeline/*` | remapped, copying the URP properties below |
| `MK/Toon/*`, `Toon/*`, `Sprites/*`, `UI/*` | kept as authored |
| missing, `Hidden/*` (the pink error shader) or any other name | remapped with the Built-in copies and one warning per prefab and shader |

| from (authoring) | to (`Simple + Outline`) | note |
| --- | --- | --- |
| `_MainTex`, or `_BaseMap` for URP | `_AlbedoMap` | texture, scale and offset; enables `_MK_ALBEDO_MAP` when set |
| `_Color`, or `_BaseColor` for URP | `_AlbedoColor` | |
| `_BumpMap` | `_NormalMap` | copied only; the game has no material with a normal map, so its keyword is unverified |
| `_EmissionMap`, `_EmissionColor` | `_EmissionMap`, `_EmissionColor` | enables `_MK_EMISSION` when the map is set or the color is not black |

Every remapped material also gets the keywords every textured game material carries: `_MK_LIGHT_CEL`, `_MK_WRAPPED_DIFFUSE`, `_WRAPPEDLIGHTING_ON`, `_MK_RECEIVE_SHADOWS`, `_RECEIVESHADOWS_ON`, `_MK_ENVIRONMENT_REFLECTIONS_AMBIENT` and `_MK_ARTISTIC_ANIMATION_STUTTER`. Without them the shader runs a keyword combination the build stripped and ignores the albedo map. Smoothness, metallic, specular and every other property are not copied; the result is flat toon shading with cel bands, shadows and the level's fog.

An author who wants full control can assign an MK.Toon material in the authoring project, but the project has no MK.Toon package, so a pack normally ships Standard materials and relies on the remap. Author in plain colors and one albedo texture per material; per-material tuning is not carried over.

`run.py shader-report` (harness command `shader-report`) prints which candidate shaders `Shader.Find` resolves in the running game, the shaders and properties of the scene's materials, and the keyword sets of the MK.Toon materials. Use it to re-check the target after a game update. In the forest level `Unlit/Color`, `UnlitVertexColor` and `Standard (Specular setup)` do not resolve, while `Standard`, `Unlit/Texture`, `Legacy Shaders/Diffuse` and the MK.Toon and `Toon/Lit Tri Planar *` shaders do.

### Missing packs and assets

If the pack directory does not exist, or the asset is not in it, `PackPrefabs.Resolve` returns a placeholder cube named `Missing:<catalogId>`, logs one warning per catalogId and shows an editor toast. Nothing throws. The placeholder is spawned like any object, so the original catalogId stays in the level and is saved unchanged.

### Palette entries

The editor palette lists installed pack assets in one `Packs` tab on every map, as `bundle:<pack>/<asset>` entries named after the asset and ordered by pack id, then asset name; the pack id is searchable and shown in the tooltip's `catalogId`. A pack with a valid manifest lists the assets that the manifest names and the bundle holds. A manifest asset the bundle lacks is logged as a warning and not listed, and a bundle asset the manifest omits is not listed. A pack with no manifest, or an invalid one, lists every prefab in its bundle. Packs load once per session, so a pack installed while the game runs appears in the palette only after a relaunch.

### Manifests and pack versions

Every pack directory holds a `manifest.json` (`UserData/LevelPacks/<packId>/manifest.json`) describing the pack. `PackManifest.Parse` reads and validates it in Unity-free code (`pack_manifest.cs`), unit tested for malformed JSON, missing fields, a non-string field, a non-list `assets`, and an `id` that differs from the folder name. The fields are:

| field | type | meaning |
| --- | --- | --- |
| `id` | string | Must equal the pack folder name and the `<pack>` segment of the `bundle:<pack>/<asset>` catalogIds this pack serves. `PackManifest.Parse` takes the folder name and rejects a manifest whose `id` differs from it. |
| `name` | string | Human-readable pack name. |
| `author` | string | Pack author. |
| `version` | string | Pack version, compared against the level's recorded version (see below). |
| `assets` | string[] | The asset (prefab) names the pack provides, matching the `<asset>` segment of its catalogIds. |

`PackCatalog.Resolve` (in `pack_catalog.cs`) reads a pack's manifest once, when it first loads the pack, through the manifest loader `PackPrefabs` supplies. For a pack with a manifest, an asset absent from the manifest `assets` list resolves as `AssetMissing` even when the bundle holds it, so it produces the `Missing:<catalogId>` placeholder, warning, and toast. This keeps the manifest authoritative: a pack that ships a bundle but forgets to list an asset surfaces the placeholder instead of silently loading it. A pack with no `manifest.json` is not filtered. A `manifest.json` that fails validation (including an `id` that differs from the folder) is logged once as a warning and leaves the pack unfiltered, the same as having none.

`PackPrefabs.ManifestVersion` returns a pack's manifest `version` for the level-side check, or null when the pack has no valid manifest.

### Level-side pack versions

The level schema carries an optional top-level `packs` map (`{"<packId>": "<version>"}`), added at schema version 2. `LevelFileSerializer` migrates a version 1 level (no `packs`) to version 2 with an empty `packs` map; a version 2 level keeps its `packs` as-is. The editor save fills `packs` from the installed manifests of the packs the level references: `LiveEditPatch.SnapshotLevelFile` collects the `bundle:` catalogIds in the edit list and records each referenced pack's manifest version (`LiveEditPatch.BuildPacks`). A level with no `bundle:` edits has an empty `packs` map.

`GamePackVersionCheck.MismatchWarning` (in `game_pack_version_check.cs`, mirroring `GameBuildIdCheck`) compares the level's `packs[<packId>]` to the installed manifest version by exact string match and returns a warning string, or null when they match, or when either side is absent. A level with no `packs` entry for a pack, or a pack with no recorded version, produces no warning. The check runs in both load paths — `LevelLoaderPatch.Start` (disk load) and `EditorTileTools.LoadSelected` (editor load) — logs a warning, and the run still starts; it never blocks or crashes. A missing pack version just means there is nothing to compare, so no warning.

## THPS Warehouse pack

`Assets/Editor/ThpsPack.cs` builds the `thps` pack: the merged `Warehouse`, a
[canonical construction library](#warehouse-pieces), and one clip per mp3 in
`tools/ost`. Geometry comes from `.tools/thps1/warehouse` (`warehouse.obj`,
`warehouse.mtl`, PNGs; override with `-warehouseSource`). Soundtrack filenames
become clip names with non-word runs replaced by underscores (`04 Superman.mp3`
becomes `04_Superman`); `-musicSource` overrides the source directory. Missing
music is logged and skipped. Generated `Assets/Thps/` and extraction files are
gitignored; the builder/helpers, manifest, instance sidecar and attachment
metadata are committed. The build rewrites the manifest and sidecars.

```sh
task pack:thps
```

The task builds the bundle (`task pack:build PACK_METHOD=ThpsPack.Build`) and runs `task pack:install`, which copies `.tools/bundles/<platform>/thps` and the manifest into `<game dir>/UserData/LevelPacks/thps/` (the `windows` bundle everywhere except Linux). `task pack:install PACK=<id>` installs any other pack the same way. Relaunch the game afterwards, because packs load once per session.

| asset | shape | collider |
| --- | --- | --- |
| `Warehouse` | the extracted level at OBJ scale, centred on its footprint with y = 0 at the floor and y up, one submesh per material; the level placement applies the scale (79.2 puts the 1.8 m skater at about 4.4 units per metre) | non-convex `MeshCollider` on a separate collision mesh |

### Warehouse pieces

The [piece inventory](thps-warehouse-pieces.md) describes source instances, not a requirement for one palette asset per instance. Alongside the untouched merged `Warehouse`, the builder emits a canonical asset library. Repeated posters/banners, boards, kicker parts, posts and props share assets when their normalized geometry, artwork/UVs, winding and collision agree. Their placements carry the differences in position, rotation and size. Names for these reusable assets contain a deterministic geometry signature, not a location in the Warehouse. Distinct artwork and genuinely different shapes remain separate. Ramp modules keep their mating conventions and local grind paths. Window panes remain render-only; solid frames keep their collision.

The generated roof is consolidated only for the kit: adjoining coplanar quads first merge into larger rectangles/trapezoids, then faces are clipped into 40-by-40-world-unit roof sections. A section includes its ceiling, steps and edge skirts, not one prefab per tiny face. Steps, openings, edge profiles and inward/downward facing are retained. Equal normalized sections share a scalable `added-roof-panel-*` asset. This does not change the legacy roof grid, spill computation, merged mesh or collision mesh. The former quad-per-prefab kit is discarded, without aliases or hidden old palette entries.

Plain rectangular ceiling sections all use `added-roof-panel-flat`, a stock
40-by-40 panel; partial edge sections scale it to fit. Internal triangulation is
removed only when the whole rectangle is covered, so holes are not filled.
Other roof sections retain their distinct step/skirt profiles.

Disconnected copies inside a source sign row become independent placements;
opposite faces at the same location stay together. Loose planks use shared
artwork/crop variants, fitted to each source instance's size and pose. Minor
source skew, missing edge slivers and triangulation differences are standardized
instead of becoming new products. This is a deliberate kit simplification,
not a rewrite of the preserved mesh. Other geometry uses strict matching. Riding
kickers remain rigid-sized and different top artwork stays a separate variant.

The build rewrites `packs/thps/pieces.json` (`thps-pieces/1`). Each row is an instance: `asset` is its inventory/assembly identity, `catalogAsset` names the reusable prefab, and `position`, full Euler `rotation` and absolute `scale` reproduce its world pose. Source rows retain their group/face coverage; archival suppressed-post rows have an empty `catalogAsset` and are not built. `pivot` remains in mesh coordinates, and `yaw` is a convenience value, not a substitute for the full rotation. Prefab roots carry scale 79.2; canonical geometry uses the first matching instance's dimensions so fresh palette placements have a useful size. `manifest.json` lists unique built prefabs only, with `Warehouse` first. Legacy version remains pinned while `kitVersion` identifies the incompatible kit revision. Tests cross-check source coverage, canonical references, positive transforms and prefab scales; `WarehouseKit.cs` tests normalization/reconstruction and roof unions outside Unity.

#### Piece attachments

`task pack:thps` also runs `scripts/build_thps_attachments.py`, which writes
`packs/thps/attachments.json`; `task pack:install` copies it beside the bundle.
Its `pack-attachments/1` schema maps each owner asset name under `assets` to an
ordered list of `{name, catalogId, localTransform, hidden}` attachments. Positions,
rotations and scales use the owner's prefab-local frame, including its 79.2 root
scale. Extra `start`/`end` fields record the original world-space grind endpoints
for auditing, not runtime world-position tests. The merged `Warehouse` has no
entry and gains no extra rails or supports.

An `instances` map records the original assembly's per-instance attachment
transforms. It is consumed by the editable-level generator, while the palette
uses canonical `assets` defaults. A support's `sourceInstance` identifies which
assembly row it replaces; its `catalogId` names the shared prefab. The generator
does not emit a second root copy. Full owner rotation and scale are included in
the world-to-local conversion; kicker owners stay rigid-sized so supports do
not acquire shear under a nonuniform parent.

The palette copies this list into the placed object's serialized edit. Each
attachment receives its own placement ID and is parented to the owner at runtime:
move/rotate/scale and removal follow the owner; independent edits change only the
attachment's local transform or active state. Undoing an owner removal does not
revive an independently removed support. Removing a rail or its owner also stops
an active grind on that rail. Clicking a hidden grind collider selects
its visible owner by default; **Ctrl-click** selects the hidden path itself. Visible
supports are selected normally. Replacing a pack's defaults does not rewrite
attachments already saved in a level.

The four mesh rails retain their tuned game `interactable/rail/0` transforms with
renderers disabled. Coping paths spanning ramp strips are split at source module
boundaries, never duplicated onto adjoining decks. Every segment exceeds the
3.5-unit handoff radius, including the original two-chord pocket tip. Rail posts
belong to their straight/bent/deck bars; kicker frames belong to their boards;
the room's underside box follows its floor, and suspension chains/braces follow
its roof. The support assets remain separately available in the palette. A level
assembled from the kit must omit separate copies of these attached supports and
must not also place the legacy hidden rails.

Window pass-through is baked into each pane's own collision result, not a live
cutout in neighbouring walls. Moving a pane never removes triangles from a wall
it is moved against; use a window frame with an authored opening rather than
expecting a solid wall to be carved automatically.

#### Authoring rules

- Set every GameObject of the prefab, children included, to layer 8. The generated tile ground (`TileGround`, `TileSlope`, `TileWall` and the combined collision mesh) is layer 8 and the player is layer 7. A placed object keeps the layer its prefab was saved with, because the mod does not touch the layer of what it spawns.
- Textures are the extracted PS1 PNGs, point-filtered with no mipmaps and repeat wrap, on materials the pack's shader remap turns into the toon shader. The PS1 transparency key (magenta) is baked to a dark glass colour (`TransparencyKey`, `KeyReplacement`) because the shader is opaque, except for the textures in `SeeThroughTextures` (every keyed texture: chains, crane hooks, posters, graffiti, the fence, the lamp and the windows): their keyed pixels get alpha 0 and their materials use `Sprites/Default`, because the game build has no usable alpha-clip variant of the toon shader (with `_MK_ALPHA_CLIPPING` on, the albedo map is ignored and the chains render white or black). The 41 faces with no texture share a flat concrete material.
- The build is reproducible: two builds on one machine, and builds on two machines with the same inputs, give byte-identical bundles. Unity otherwise picks a random GUID per asset per machine and random file IDs for a new prefab's objects, and the bundle derives its object identities from both. `ThpsPack` writes each asset's `.meta` before Unity imports it, with a GUID that is the MD5 of the asset path, serializes meshes and materials to their path and imports them (`AssetDatabase.CreateAsset` ignores a pre-written `.meta`), renumbers the prefab's file IDs after each save, and deletes `Assets/Thps` at the start of every build. A `.meta` that holds only a GUID carries no importer settings, so an importer that defaults badly has to be set explicitly: a PNG imports as a cubemap, `LoadAssetAtPath<Texture2D>` returns null, the materials get no texture and the Warehouse renders flat white, so the texture import sets `textureShape` to `Texture2D`. A bundle with textures lists `Class: 28` (Texture2D) in its `.manifest`.
- To check a built pack in the game, `run.py material-dump` lists each Warehouse material's shader, keywords and texture. A textured material shows the `_MK_ALBEDO_MAP` keyword and a named `_AlbedoMap`; `withoutTexture` should be 2 (the flat concrete and roof materials), and a count near 81 means the textures did not reach the bundle.
- Build through the explicit `AssetBundleBuild[]` overload of `BuildAssetBundles`, so a build of the pack does not rebuild the test bundles in the same project.
- The authoring project enables the `com.unity.modules.audio` package module. Without it the build logs `'AudioClip' is not supported because the module Audio is disabled in the build` and leaves the clip out of the bundle.
- Unity's bundle build is incremental and keeps an output whose inputs it considers unchanged, so delete `.tools/bundles/<platform>/thps` and its `.manifest` to force a rebuild after changing project settings.
- List every prefab in `manifest.json`; an omitted prefab resolves as `Missing:` even when the bundle holds it. Audio clips are not filtered by the manifest. Keep the legacy manifest `version` and generator `PACK_VERSION` pinned while the preserved level's dependencies remain unchanged; use `kitVersion` for kit additions, consolidation or removals. Changing a protected dependency requires a deliberate legacy version/baseline update, not a kit revision.

### Warehouse collision

The `MeshCollider` is built from a separate `WarehouseCollision` mesh (`SaveCollisionMesh`) so the render and the collision can differ:

- The windows of the secret room and the top of the starting slope render but do not collide, so the player and enemies pass through them. Faces of material `FA88F30D` are dropped everywhere; faces of `F2184063`, which solid windows elsewhere share, are dropped only inside the `OpenedWindowBounds` boxes. See "Windows opened to the player" in [thps-warehouse-layout.md](thps-warehouse-layout.md).

### Floor patch

The extraction left a gap in the floor against the west wall. The pack adds a patch over it on the floor material `F051E515`, with UVs fitted to the extracted floor (`FloorUvScaleU` and the related constants) so the texture continues, placed just under the floor plane so the grime decals around it stay on top.

### Rail posts

The mesh's rail bars were extracted floating, with small plates of the original posts left well below them. The rail-material faces inside `RailLeftoverBounds` are dropped from the mesh, and `ThpsPack.AddRailPosts` adds dark box posts under the bars (`RailPosts`), which are part of the mesh and its collision. The grind comes from hidden game rails placed along the bars by the level, described in thps-warehouse-layout.md under "Mesh rail near (75, 3, 28)".

### Warehouse mesh import

`ThpsPack.ParseWarehouseObj` reads `.tools/thps1/warehouse/warehouse.obj` and turns every face into its own corners, so no vertex is shared between faces. The extraction leaves faces that lie exactly in the same plane as another face and overlap it: posters over walls, and the stacked planks of the wood piles. With equal depth the depth buffer picks a winner per pixel and the result flickers as the camera moves.

`CoplanarLayering.Separate` (`Assets/Editor/CoplanarLayering.cs`, plain C# with no Unity types so `tests/MegabonkLevels.Tests` compiles it directly) removes the tie. For every pair of faces that face the same way, lie within `0.00001` mesh units of one plane and overlap with positive area, the smaller face goes on top, and the later OBJ face goes on top when the areas are equal. A face is lifted along its front normal by `LiftStep` (`0.0005` mesh units, about 0.04 world units at the placed scale) for each face it has to sit above, so stacks of three or more separate too. Faces that only touch along an edge, back-to-back faces and faces in parallel planes beyond the tolerance are left alone. Positions move by under 0.2 world units at most, and UVs, textures and filtering are untouched.

On the current mesh the pass lifts 195 of 1345 faces, at most 3 levels deep. The floor grime decals are not part of this pass: they sit 0.174 world units above the floor faces, and the floor patch sits under the floor plane on purpose.

### Warehouse roof

The extracted PS1 level has no roof, truss ceiling or tall walls: the highest visible face is 0.81 OBJ units (about 64.7 world units), and the 297 faces the converter skips with base flag `0x80` are collision-only vertical quads, none of them horizontal. `ThpsPack.AddRoof` therefore adds one flat dark roof, so a player with two Feathers cannot jump out of the shell. A player who jumps into it just bumps the roof.

`WarehouseRoof` (`Assets/Editor/WarehouseRoof.cs`, plain C# with no Unity types so `tests/MegabonkLevels.Tests` compiles it directly) builds a roof that rides the tops of the walls, in four parts. `ColumnTops` rasterises the mesh onto a grid of `RoofCell` (1.5 world unit) cells and keeps the highest surface over each: faces that are not steep are sampled across the cells they cover, and a steep face (a wall) is traced along its base line so its top reaches every cell it passes through. `SpillLevels` turns those heights into a ceiling by filling from the footprint edge inwards, like water poured over the rim: a cell's ceiling is the lowest height at which a player in it could clear every wall around it, never below its own surface. Boundary cells at or below `RoofOpenBelow` (15 units) have nothing built there and start at the seal height, 2 units above the tallest vertex, so an open edge cannot pull the whole hall down to the floor. On the current mesh nearly the whole hall fills to y 48, the lowest slab, the roof sits on each wall top and slab at its own height, and the taller walls and the south rooms (55 to 65) poke through it. `Quads` emits the down-facing roof quads (equal-height cells in a row merged), a vertical step face between cells of different height facing the taller side, and an inward-facing skirt per `EdgeWallProfile` segment and cell along each outer edge. `EdgeWallProfile` returns, per footprint edge, the wall-top line as `(along, y)` points: between consecutive vertices of the steep faces (normal within 60 degrees of horizontal) lying within 1.5 units of the edge plane, it takes the covering face's top at both ends, and the floor where no wall stands there; it never rises above the wall beneath it and steps where heights jump. The edges sit `RoofInset` (0.003 mesh units) inside the footprint so they do not overlap the original outer faces. The quads use a dark flat material (`Warehouse_Roof`) and are part of the collision mesh. `ThpsPack.AddRoof` fails the build above 65,000 vertices, the limit of a Unity mesh with 16-bit indices.

The roof is solid from inside; from above a falling player passes through it, because ground checks ignore back faces, so the roof has to leave no air above a wall for a player to reach. The tallest standable surface is a slab at y 55 over the start room (z about -124 to -93); most of the south half has a slab at y 48. A flat roof above the 64.8 gable left 10 to 17 units of air over those slabs, and per-cell lids or curtains left slits and stair-stepped edges; the spill-level ceiling replaces them.

Measured in the game with the pack: a player teleported 4 units above a flat top settles at the top plus 1.925 (the capsule centre height), so every `Block` top, the taxi cabin and the corridor floor hold the player. On a ramp the player lands on the surface and slides down it when the slope is steep, and rests on shallow slopes; nothing fell through. A teleport to only 1 unit above a surface leaves the player hovering at that height with no gravity, so test support with a drop of several units.

Ground coverage of the collision mesh: `warehouse_surface.unity_mesh_triangles` reads `Assets/Thps/WarehouseCollision.asset` (a text mesh asset) and `warehouse_surface.ground_gaps` lists the grid points that no upward-facing triangle covers, so a body above one falls to the kill floor. The mesh is centred, so a vertex maps to world as `vertex * 79.2 + (100, 0.5, 0)` (`WAREHOUSE_SCALE`, the placement x and `WAREHOUSE_LIFT`). Over the arena footprint (x 21 to 179, z -124 to 124) at 1 unit spacing the uncovered points form two regions: x 22 to 39 with z -123 to 2, and x 22 to 79 with z 106 to 123. Every one of those points is also uncovered in the unpacked `warehouse.obj` mesh, and the pack covers 563 more points than the OBJ does. Nothing is uncovered over the main half pipe and the boss box (x 130 to 170, z -30 to 45), where six enemies were once logged reaching the kill floor together. That fall is not explained by the mesh, and about 4 minutes of game time with 173 kills (boss killed 3 seconds after the summon, player in the box and on the pipe) did not reproduce it, so it is treated as not reproducible. Open: whether enemies can reach the two uncovered regions; the kill floor kills anything that does.

## Not yet established

- The Linux bundle builds but has not been loaded. MelonLoader segfaults the native Linux build, so there is no mod-side harness there to run it.
- A bundle built by a different editor version (Unity 6.6 was installed but has no Windows build module) has not been tried. Treat the exact 2023.2.22f1 match as required until a test says otherwise.
- Custom `MonoBehaviour` scripts cannot ship in a bundle for an IL2CPP game; any behaviour has to live in the mod.
