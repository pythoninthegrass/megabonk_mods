namespace MegabonkLevels.Tests;

public class PaletteCatalogBuilderTests
{
    private static PaletteMapCatalog Forest(int shrines = 0, bool chest = false, bool chestFree = false, int rails = 0, params PaletteStageCatalog[] stages) =>
        new(EMap.Forest, stages, shrines, chest, chestFree, rails);

    private static string Id(PaletteEntry entry) => entry.Id.Serialize();

    [Fact]
    public void Build_RandomMapObjects_ListsEveryPrefabWithObjectAndPrefabIndex()
    {
        var catalog = Forest(stages: new PaletteStageCatalog([2, 1], 0, 0));

        var ids = PaletteCatalogBuilder.Build(catalog, _ => null).Select(Id).ToArray();

        Assert.Equal(
            ["forest/stage0/randomMapObjects/0/0", "forest/stage0/randomMapObjects/0/1", "forest/stage0/randomMapObjects/1/0"],
            ids);
    }

    [Fact]
    public void Build_TilePrefabs_ListsFlatAndSpecificPerStage()
    {
        var catalog = Forest(stages: [new PaletteStageCatalog([], 0, 0), new PaletteStageCatalog([], 2, 1)]);

        var ids = PaletteCatalogBuilder.Build(catalog, _ => null).Select(Id).ToArray();

        Assert.Equal(
            ["forest/stage1/stageTilePrefabs/flat/0", "forest/stage1/stageTilePrefabs/flat/1", "forest/stage1/stageTilePrefabs/specific/0"],
            ids);
    }

    [Fact]
    public void Build_ShrinesAndInteractables_UseMapScopedAndGlobalIds()
    {
        var catalog = Forest(shrines: 2, chest: true, chestFree: true, rails: 2);

        var ids = PaletteCatalogBuilder.Build(catalog, _ => null).Select(Id).ToArray();

        Assert.Equal(
            ["forest/shrines/0", "forest/shrines/1", "interactable/chest", "interactable/chestFree", "interactable/rail/0", "interactable/rail/1"],
            ids);
    }

    [Fact]
    public void Build_Boombox_IsAnInteractableEntry()
    {
        var catalog = Forest() with { HasBoombox = true };

        var entry = Assert.Single(PaletteCatalogBuilder.Build(catalog, _ => null));

        Assert.Equal("interactable/boombox", entry.Id.Serialize());
        Assert.Equal(PaletteCategory.Interactable, entry.Category);
    }

    [Fact]
    public void Build_MissingChestsAndNoRails_OmitsThem()
    {
        var entries = PaletteCatalogBuilder.Build(Forest(), _ => null);

        Assert.Empty(entries);
    }

    [Fact]
    public void Build_EveryIdRoundTripsThroughCatalogRoute()
    {
        var catalog = new PaletteMapCatalog(
            EMap.Graveyard,
            [new PaletteStageCatalog([2, 3], 2, 2), new PaletteStageCatalog([1], 1, 0)],
            ShrineCount: 3, HasChest: true, HasChestFree: true, RailCount: 2);

        foreach (var entry in PaletteCatalogBuilder.Build(catalog, _ => null))
        {
            var route = CatalogRoute.Parse(CatalogId.Parse(entry.Id.Serialize()));
            Assert.NotEqual(default, route);
        }
    }

    [Fact]
    public void Build_RoutesDecodeToTheSourceIndices()
    {
        var catalog = Forest(stages: [new PaletteStageCatalog([1, 2], 0, 0)]);

        var entry = PaletteCatalogBuilder.Build(catalog, _ => null).Last();
        var route = CatalogRoute.Parse(entry.Id);

        Assert.Equal(new CatalogRoute(CatalogRouteKind.RandomMapObject, EMap.Forest, 0, 1, 1), route);
    }

    [Fact]
    public void Build_EntriesCarryCategoryAndStage()
    {
        var catalog = Forest(shrines: 1, stages: [new PaletteStageCatalog([], 0, 0), new PaletteStageCatalog([1], 1, 1)]);

        var entries = PaletteCatalogBuilder.Build(catalog, _ => null);

        Assert.Equal(
            [(PaletteCategory.RandomObject, 1), (PaletteCategory.FlatTile, 1), (PaletteCategory.SpecificTile, 1), (PaletteCategory.Shrine, 0)],
            entries.Select(e => (e.Category, e.Stage)).ToArray());
    }

    [Fact]
    public void Build_UsesSuppliedPrefabName()
    {
        var catalog = Forest(shrines: 1);

        var entry = Assert.Single(PaletteCatalogBuilder.Build(catalog, id => id.Serialize() == "forest/shrines/0" ? "ShrineGreed" : null));

        Assert.Equal("ShrineGreed", entry.DisplayName);
    }

    [Fact]
    public void Build_MissingName_FallsBackToCategoryLabelWithIndexPath()
    {
        var catalog = Forest(stages: [new PaletteStageCatalog([1, 2], 0, 0)]);

        var entry = PaletteCatalogBuilder.Build(catalog, _ => null).Last();

        Assert.Equal("Random object 1/1", entry.DisplayName);
    }

    [Fact]
    public void Build_BlankName_FallsBackToLabel()
    {
        var entry = Assert.Single(PaletteCatalogBuilder.Build(Forest(chest: true), _ => "  "));

        Assert.Equal("Chest", entry.DisplayName);
    }
}
