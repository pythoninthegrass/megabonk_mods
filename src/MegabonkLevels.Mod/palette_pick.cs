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

    // Prefers an entry of the current stage and loaded map, then the current stage, then a
    // stage-independent one of that map, then any stage-independent match. An entry with no map
    // (a pack asset) can match any loaded map.
    public static PaletteEntry? FindByPrefabName(IReadOnlyList<PaletteEntry> entries, string prefabName, int currentStage, EMap currentMap = EMap.None)
    {
        var named = entries.Where(e => e.DisplayName == prefabName).Cast<PaletteEntry?>().ToList();
        return Pick(named, e => !IsStageIndependent(e) && e.Stage == currentStage && FromMap(e, currentMap))
            ?? Pick(named, e => !IsStageIndependent(e) && e.Stage == currentStage)
            ?? Pick(named, e => IsStageIndependent(e) && FromMap(e, currentMap))
            ?? Pick(named, IsStageIndependent);
    }

    public static PaletteEntry? FindByCatalogId(IReadOnlyList<PaletteEntry> entries, CatalogId id) =>
        entries.Cast<PaletteEntry?>().FirstOrDefault(e => e.Value.Id.Equals(id));

    private static PaletteEntry? Pick(List<PaletteEntry?> named, Func<PaletteEntry, bool> matches) =>
        named.FirstOrDefault(e => matches(e.Value));

    private static bool FromMap(PaletteEntry entry, EMap currentMap) =>
        currentMap == EMap.None || entry.Map == EMap.None || entry.Map == currentMap;

    private static bool IsStageIndependent(PaletteEntry entry) => entry.Category is PaletteCategory.Shrine or PaletteCategory.Interactable or PaletteCategory.Override or PaletteCategory.Pack;
}
