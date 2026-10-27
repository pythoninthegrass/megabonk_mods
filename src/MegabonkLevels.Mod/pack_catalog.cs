using System;
using System.Collections.Generic;

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
public sealed class PackCatalog<T> where T : class
{
    private readonly Func<string, IReadOnlyDictionary<string, T>> _loadPack;
    private readonly Dictionary<string, IReadOnlyDictionary<string, T>> _packs = new();

    public PackCatalog(Func<string, IReadOnlyDictionary<string, T>> loadPack)
    {
        _loadPack = loadPack;
    }

    public PackLookup<T> Resolve(CatalogId id)
    {
        if (id.Namespace != CatalogNamespace.Bundle)
        {
            throw new ArgumentException($"'{id.Serialize()}' is not a bundle catalogId.", nameof(id));
        }

        var pack = id.Segments[0];
        if (!_packs.TryGetValue(pack, out var assets))
        {
            assets = _loadPack(pack);
            _packs[pack] = assets;
        }

        if (assets is null)
        {
            return new PackLookup<T>(PackResolution.PackMissing, null);
        }

        return id.Segments.Count == 2 && assets.TryGetValue(id.Segments[1], out var prefab)
            ? new PackLookup<T>(PackResolution.Found, prefab)
            : new PackLookup<T>(PackResolution.AssetMissing, null);
    }
}
