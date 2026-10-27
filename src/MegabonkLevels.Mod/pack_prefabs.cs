using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Il2CppInterop.Runtime;
using MelonLoader;
using MelonLoader.Utils;
using UnityEngine;

namespace MegabonkLevels;

// Loads asset packs from UserData/LevelPacks/<pack>/ and resolves bundle: catalogIds to their prefabs; see docs/asset-bundles.md.
public static class PackPrefabs
{
    private const string PacksDirectoryName = "LevelPacks";

    private static readonly PackCatalog<GameObject> Catalog = new(LoadPack, ReadManifest);
    private static readonly Dictionary<string, GameObject> Placeholders = new();
    private static readonly HashSet<string> Warned = new();
    private static GameObject _hiddenRoot;
    private static MelonLogger.Instance _logger;

    public static void Initialize(MelonLogger.Instance logger) => _logger = logger;

    // Returns the pack prefab, or a placeholder cube with a warning when the pack or asset is absent.
    public static GameObject Resolve(CatalogId id)
    {
        var lookup = Catalog.Resolve(id);
        if (lookup.Result == PackResolution.Found)
        {
            return lookup.Prefab;
        }

        var key = id.Serialize();
        if (Warned.Add(key))
        {
            var reason = lookup.Result == PackResolution.PackMissing ? $"pack '{id.Segments[0]}' is not installed" : "asset not found in its pack";
            _logger.Warning($"Packs: '{key}': {reason}; using a placeholder.");
            EditorTileTools.Warn($"missing asset {key}");
        }

        return PlaceholderFor(key);
    }

    private static IReadOnlyDictionary<string, GameObject> LoadPack(string pack)
    {
        var directory = PackDirectory(pack);
        if (!Directory.Exists(directory))
        {
            return null;
        }

        var assets = new Dictionary<string, GameObject>();
        foreach (var file in Directory.GetFiles(directory).Where(f => PackFiles.IsBundleFile(Path.GetFileName(f))).OrderBy(f => f, StringComparer.Ordinal))
        {
            try
            {
                LoadBundleInto(file, assets);
            }
            catch (Exception e)
            {
                _logger.Warning($"Packs: could not load bundle '{file}': {e.Message}");
            }
        }

        _logger.Msg($"Packs: loaded pack '{pack}' with {assets.Count} prefab(s).");
        return assets;
    }

    // The version recorded in the pack's manifest, or null when it has no valid manifest. Editor save writes it into the level so a later load can warn if the pack changed.
    public static string ManifestVersion(string pack) => ReadManifest(pack)?.Version;

    // The pack's parsed manifest.json, or null when the file is absent or invalid; an invalid one is warned about once and leaves the pack unfiltered.
    private static PackManifest? ReadManifest(string pack)
    {
        var manifestPath = Path.Combine(PackDirectory(pack), PackManifest.FileName);
        if (!File.Exists(manifestPath))
        {
            return null;
        }

        try
        {
            return PackManifest.Parse(File.ReadAllText(manifestPath), pack);
        }
        catch (Exception e)
        {
            if (Warned.Add($"manifest:{pack}"))
            {
                _logger.Warning($"Packs: ignoring manifest for '{pack}': {e.Message}");
            }

            return null;
        }
    }

    private static string PackDirectory(string pack) =>
        Path.Combine(MelonEnvironment.GameRootDirectory, "UserData", PacksDirectoryName, pack);

    // Bundles stay loaded for the session because instantiated prefabs depend on their data. The async API is used because the synchronous loaders fail in the Il2Cpp interop.
    private static void LoadBundleInto(string path, Dictionary<string, GameObject> assets)
    {
        var bundle = AssetBundle.LoadFromFileAsync(path).assetBundle;
        if (bundle == null)
        {
            throw new InvalidOperationException("not a loadable AssetBundle for this platform");
        }

        foreach (var asset in bundle.LoadAllAssetsAsync(Il2CppType.Of<UnityEngine.Object>()).allAssets)
        {
            if (asset.TryCast<GameObject>() is { } prefab)
            {
                PackShaderRemap.Apply(prefab, _logger);
                assets[prefab.name] = prefab;
            }
        }
    }

    // Placeholders sit under an inactive root so the template itself is never rendered, while a clone spawned at the scene root is active.
    private static GameObject PlaceholderFor(string key)
    {
        if (Placeholders.TryGetValue(key, out var existing) && existing != null)
        {
            return existing;
        }

        if (_hiddenRoot == null)
        {
            _hiddenRoot = new GameObject("MegabonkLevels.Placeholders");
            _hiddenRoot.SetActive(false);
            UnityEngine.Object.DontDestroyOnLoad(_hiddenRoot);
        }

        var placeholder = GameObject.CreatePrimitive(PrimitiveType.Cube);
        placeholder.name = $"Missing:{key}";
        placeholder.transform.SetParent(_hiddenRoot.transform, false);
        Placeholders[key] = placeholder;
        return placeholder;
    }
}
