using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

public readonly record struct PaletteGroup(int Stage, PaletteCategory Category, EMap Map = EMap.None)
{
    public static PaletteGroup Of(PaletteEntry entry) => new(entry.Stage, entry.Category, entry.Map);

    public string Label => Category switch
    {
        PaletteCategory.RandomObject => $"Stage {Stage} random objects",
        PaletteCategory.FlatTile => $"Stage {Stage} flat tiles",
        PaletteCategory.SpecificTile => $"Stage {Stage} specific tiles",
        PaletteCategory.Shrine => "Shrines",
        PaletteCategory.Override => "Overrides",
        PaletteCategory.Pack => "Packs",
        _ => "Interactables",
    };

    // Names the map an asset came from when the palette is showing another map's level.
    public string LabelFor(EMap loadedMap) =>
        Map is not EMap.None && Map != loadedMap ? $"{Map} · {Label}" : Label;
}

public static class PaletteFilter
{
    public static IReadOnlyList<PaletteCategory> Categories(IReadOnlyList<PaletteEntry> entries) =>
        entries.Select(entry => entry.Category).Distinct().ToArray();

    public static IReadOnlyList<PaletteEntry> Apply(IReadOnlyList<PaletteEntry> entries, string query, PaletteCategory? category) =>
        entries.Where(entry => (!category.HasValue || entry.Category == category.Value)
            && (entry.DisplayName.Contains(query, StringComparison.OrdinalIgnoreCase)
                || entry.Id.Serialize().Contains(query, StringComparison.OrdinalIgnoreCase))).ToArray();
}

public static class PaletteCategoryNames
{
    public static string Label(this PaletteCategory category) => category switch
    {
        PaletteCategory.RandomObject => "Random objects",
        PaletteCategory.FlatTile => "Flat tiles",
        PaletteCategory.SpecificTile => "Specific tiles",
        PaletteCategory.Shrine => "Shrines",
        PaletteCategory.Override => "Overrides",
        PaletteCategory.Pack => "Packs",
        _ => "Interactables",
    };

    public static string ShortLabel(this PaletteCategory category) => category switch
    {
        PaletteCategory.RandomObject => "Obj",
        PaletteCategory.FlatTile => "Flat",
        PaletteCategory.SpecificTile => "Spec",
        PaletteCategory.Shrine => "Shrn",
        PaletteCategory.Override => "Ovr",
        PaletteCategory.Pack => "Pack",
        _ => "Item",
    };
}
