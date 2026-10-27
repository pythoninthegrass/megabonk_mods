namespace MegabonkLevels;

public enum PaletteCategory
{
    RandomObject,
    FlatTile,
    SpecificTile,
    Shrine,
    Interactable,
    Pack,
}

// Stage is 0 for entries that are not stage-scoped (shrines, interactables).
public readonly record struct PaletteEntry(CatalogId Id, string DisplayName, PaletteCategory Category, int Stage);
