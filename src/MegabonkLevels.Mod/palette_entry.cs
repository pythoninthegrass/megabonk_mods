namespace MegabonkLevels;

public enum PaletteCategory
{
    RandomObject,
    FlatTile,
    SpecificTile,
    Shrine,
    Interactable,
    Override,
    Pack,
}

// Stage is 0 for entries that are not stage-scoped (shrines, interactables). Map is the map the asset was
// walked from: EMap.None for entries that are not map-scoped, such as pack assets.
public readonly record struct PaletteEntry(CatalogId Id, string DisplayName, PaletteCategory Category, int Stage, EMap Map = EMap.None);
