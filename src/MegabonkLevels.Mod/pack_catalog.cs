using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

public enum PackResolution
{
    Found,
    PackMissing,
    AssetMissing,
}

public readonly record struct PackLookup<T>(PackResolution Result, T Prefab) where T : class;

public static class PackFiles
{
    // Bundles built by task pack:build have no extension; .bundle is the explicit form.
    public static bool IsBundleFile(string fileName)
    {
        var extension = System.IO.Path.GetExtension(fileName);
        return fileName.Length > 0 && (extension.Length == 0 || extension.Equals(".bundle", StringComparison.OrdinalIgnoreCase));
    }
}

// Resolves bundle:<pack>/<asset> catalogIds. The loader returns a pack's assets by name, or null when the pack is not installed; each pack is loaded once, including a miss.
// The optional manifest loader returns the pack's manifest, or null when it has none; a pack with a manifest only resolves the assets that manifest lists.
public sealed class PackCatalog<T> where T : class
{
    private readonly Func<string, IReadOnlyDictionary<string, T>> _loadPack;
    private readonly Func<string, PackManifest?> _loadManifest;
    private readonly Dictionary<string, (IReadOnlyDictionary<string, T> Assets, PackManifest? Manifest)> _packs = new();

    public PackCatalog(Func<string, IReadOnlyDictionary<string, T>> loadPack, Func<string, PackManifest?> loadManifest = null)
    {
        _loadPack = loadPack;
        _loadManifest = loadManifest ?? (_ => null);
    }

    public PackLookup<T> Resolve(CatalogId id)
    {
        if (id.Namespace != CatalogNamespace.Bundle)
        {
            throw new ArgumentException($"'{id.Serialize()}' is not a bundle catalogId.", nameof(id));
        }

        var pack = id.Segments[0];
        if (!_packs.TryGetValue(pack, out var loaded))
        {
            var assets = _loadPack(pack);
            loaded = (assets, assets is null ? null : _loadManifest(pack));
            _packs[pack] = loaded;
        }

        if (loaded.Assets is null)
        {
            return new PackLookup<T>(PackResolution.PackMissing, null);
        }

        if (id.Segments.Count != 2)
        {
            return new PackLookup<T>(PackResolution.AssetMissing, null);
        }

        var asset = id.Segments[1];
        if (loaded.Manifest is { } manifest && !manifest.Assets.Contains(asset))
        {
            return new PackLookup<T>(PackResolution.AssetMissing, null);
        }

        return loaded.Assets.TryGetValue(asset, out var prefab)
            ? new PackLookup<T>(PackResolution.Found, prefab)
            : new PackLookup<T>(PackResolution.AssetMissing, null);
    }
}
