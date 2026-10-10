using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// Finds the palette entry for an object already in the level, for the editor's pick-block click.
public static class PalettePick
{
    private const string ObjectCategoryPrefix = "object:";

    // The prefab name inside an "object:{prefabName}:{index}" genId; null for other categories such as tileObject.
    public static string PrefabNameOf(string genId)
    {
        if (!genId.StartsWith(ObjectCategoryPrefix, StringComparison.Ordinal))
        {
            return null;
        }

        var start = ObjectCategoryPrefix.Length;
        return genId.Substring(start, genId.LastIndexOf(':') - start);
    }

    // Prefers an entry of the current stage, then a stage-independent one (shrines, interactables).
    public static PaletteEntry? FindByPrefabName(IReadOnlyList<PaletteEntry> entries, string prefabName, int currentStage)
    {
        var named = entries.Where(e => e.DisplayName == prefabName).Cast<PaletteEntry?>().ToList();
        return named.FirstOrDefault(e => !IsStageIndependent(e.Value) && e.Value.Stage == currentStage)
            ?? named.FirstOrDefault(e => IsStageIndependent(e.Value));
    }

    public static PaletteEntry? FindByCatalogId(IReadOnlyList<PaletteEntry> entries, CatalogId id) =>
        entries.Cast<PaletteEntry?>().FirstOrDefault(e => e.Value.Id.Equals(id));

    private static bool IsStageIndependent(PaletteEntry entry) => entry.Category is PaletteCategory.Shrine or PaletteCategory.Interactable;
}
