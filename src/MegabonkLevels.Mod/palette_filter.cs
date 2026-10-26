using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

public readonly record struct PaletteGroup(int Stage, PaletteCategory Category)
{
    public static PaletteGroup Of(PaletteEntry entry) => new(entry.Stage, entry.Category);

    public string Label => Category switch
    {
        PaletteCategory.RandomObject => $"Stage {Stage} random objects",
        PaletteCategory.FlatTile => $"Stage {Stage} flat tiles",
        PaletteCategory.SpecificTile => $"Stage {Stage} specific tiles",
        PaletteCategory.Shrine => "Shrines",
        _ => "Interactables",
    };
}

public static class PaletteFilter
{
    public static IReadOnlyList<PaletteGroup> Groups(IReadOnlyList<PaletteEntry> entries) =>
        entries.Select(PaletteGroup.Of).Distinct().ToArray();

    public static IReadOnlyList<PaletteEntry> Apply(IReadOnlyList<PaletteEntry> entries, string query, PaletteGroup? group) =>
        entries.Where(entry => (!group.HasValue || PaletteGroup.Of(entry) == group.Value)
            && (entry.DisplayName.Contains(query, StringComparison.OrdinalIgnoreCase)
                || entry.Id.Serialize().Contains(query, StringComparison.OrdinalIgnoreCase))).ToArray();
}
