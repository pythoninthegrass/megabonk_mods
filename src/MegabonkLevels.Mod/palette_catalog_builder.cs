using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// Prefab counts of one StageData: prefabs per RandomMapObject entry, then the two StageTilePrefabs arrays.
public readonly record struct PaletteStageCatalog(IReadOnlyList<int> RandomObjectPrefabCounts, int FlatTileCount, int SpecificTileCount);

public readonly record struct PaletteMapCatalog(
    EMap Map,
    IReadOnlyList<PaletteStageCatalog> Stages,
    int ShrineCount,
    bool HasChest,
    bool HasChestFree,
    int RailCount);

// Builds the catalogId shapes that CatalogRoute decodes, from counts read off the game's catalog.
public static class PaletteCatalogBuilder
{
    public static IReadOnlyList<PaletteEntry> Build(PaletteMapCatalog catalog, Func<CatalogId, string> prefabName)
    {
        var entries = new List<PaletteEntry>();
        var map = catalog.Map.ToString().ToLowerInvariant();

        void Add(string id, PaletteCategory category, int stage, string fallbackLabel)
        {
            var catalogId = CatalogId.Parse(id);
            var name = prefabName(catalogId);
            entries.Add(new PaletteEntry(catalogId, string.IsNullOrWhiteSpace(name) ? fallbackLabel : name, category, stage));
        }

        for (var stage = 0; stage < catalog.Stages.Count; stage++)
        {
            var data = catalog.Stages[stage];
            var prefix = $"{map}/stage{stage}";
            for (var obj = 0; obj < data.RandomObjectPrefabCounts.Count; obj++)
            {
                for (var prefab = 0; prefab < data.RandomObjectPrefabCounts[obj]; prefab++)
                {
                    Add($"{prefix}/randomMapObjects/{obj}/{prefab}", PaletteCategory.RandomObject, stage, $"Random object {obj}/{prefab}");
                }
            }

            for (var i = 0; i < data.FlatTileCount; i++)
            {
                Add($"{prefix}/stageTilePrefabs/flat/{i}", PaletteCategory.FlatTile, stage, $"Flat tile {i}");
            }

            for (var i = 0; i < data.SpecificTileCount; i++)
            {
                Add($"{prefix}/stageTilePrefabs/specific/{i}", PaletteCategory.SpecificTile, stage, $"Specific tile {i}");
            }
        }

        for (var i = 0; i < catalog.ShrineCount; i++)
        {
            Add($"{map}/shrines/{i}", PaletteCategory.Shrine, 0, $"Shrine {i}");
        }

        if (catalog.HasChest)
        {
            Add("interactable/chest", PaletteCategory.Interactable, 0, "Chest");
        }

        if (catalog.HasChestFree)
        {
            Add("interactable/chestFree", PaletteCategory.Interactable, 0, "Chest (free)");
        }

        for (var i = 0; i < catalog.RailCount; i++)
        {
            Add($"interactable/rail/{i}", PaletteCategory.Interactable, 0, $"Rail {i}");
        }

        return entries;
    }
}
