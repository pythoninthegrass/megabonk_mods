using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

public readonly record struct PackPaletteListing(
    IReadOnlyList<PaletteEntry> Entries,
    IReadOnlyList<(string Pack, string Asset)> MissingFromBundle);

// Builds the Packs palette entries from installed packs, applying the same manifest filter as PackCatalog.Resolve.
public static class PackPaletteEntries
{
    // loadAssetNames returns a pack's bundle prefab names, or null when the pack cannot be loaded; loadManifest returns its valid manifest, or null.
    public static PackPaletteListing Build(
        IEnumerable<string> packIds,
        Func<string, IReadOnlyCollection<string>> loadAssetNames,
        Func<string, PackManifest?> loadManifest)
    {
        var entries = new List<PaletteEntry>();
        var missing = new List<(string, string)>();

        foreach (var pack in packIds.OrderBy(p => p, StringComparer.Ordinal))
        {
            if (loadAssetNames(pack) is not { } bundleNames)
            {
                continue;
            }

            var listed = bundleNames.AsEnumerable();
            if (loadManifest(pack) is { } manifest)
            {
                var inBundle = bundleNames.ToHashSet(StringComparer.Ordinal);
                missing.AddRange(manifest.Assets.Where(a => !inBundle.Contains(a)).Select(a => (pack, a)));
                listed = bundleNames.Where(manifest.Assets.Contains);
            }

            entries.AddRange(listed.OrderBy(a => a, StringComparer.Ordinal)
                .Select(asset => new PaletteEntry(CatalogId.Parse($"bundle:{pack}/{asset}"), asset, PaletteCategory.Pack, 0)));
        }

        return new PackPaletteListing(entries, missing);
    }
}
