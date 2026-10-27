# AssetBundle authoring

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

A catalogId `bundle:<pack>/<asset>` resolves to the `GameObject` named `<asset>` in any bundle of pack `<pack>`. The pack is loaded the first time an ID references it and stays loaded for the session, because instantiated prefabs depend on the bundle's data. `Applier.ResolvePrefab` is the single resolver: game-asset IDs go through `CatalogRoute`, and `bundle:` IDs go through `PackPrefabs`, so placing, undoing and saving a pack object use the same edit pipeline as a game prefab. The pure lookup and caching live in `PackCatalog`, which is unit tested without Unity.

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

Assets in a pack are not listed in the editor palette yet; place them through a level file or the harness.

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

## Not yet established

- The Linux bundle builds but has not been loaded. MelonLoader segfaults the native Linux build, so there is no mod-side harness there to run it.
- A bundle built by a different editor version (Unity 6.6 was installed but has no Windows build module) has not been tried. Treat the exact 2023.2.22f1 match as required until a test says otherwise.
- Custom `MonoBehaviour` scripts cannot ship in a bundle for an IL2CPP game; any behaviour has to live in the mod.
