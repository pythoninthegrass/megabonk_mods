namespace MegabonkLevels.Tests;

public class PaletteFilterTests
{
    private static readonly PaletteEntry[] Entries =
    [
        new(CatalogId.Parse("forest/shrines/0"), "Ancient Shrine", PaletteCategory.Shrine, 0),
        new(CatalogId.Parse("forest/stage0/stageTilePrefabs/flat/0"), "Grass", PaletteCategory.FlatTile, 0),
        new(CatalogId.Parse("forest/stage1/stageTilePrefabs/flat/0"), "Grass", PaletteCategory.FlatTile, 1),
    ];

    [Theory]
    [InlineData("", 3)]
    [InlineData("gRaSs", 2)]
    [InlineData("FOREST/SHRINES", 1)]
    [InlineData("missing", 0)]
    public void Search_MatchesNameOrIdIgnoringCase(string query, int count) =>
        Assert.Equal(count, PaletteFilter.Apply(Entries, query, null).Count);

    [Fact]
    public void CategoryAndSearch_AreCombinedAcrossStages()
    {
        var result = PaletteFilter.Apply(Entries, "grass", PaletteCategory.FlatTile);

        Assert.Equal(new[] { Entries[1], Entries[2] }, result);
        Assert.Empty(PaletteFilter.Apply(Entries, "shrine", PaletteCategory.FlatTile));
    }

    [Fact]
    public void Categories_AreDistinctInCatalogOrder()
    {
        Assert.Equal(
            new[] { PaletteCategory.Shrine, PaletteCategory.FlatTile },
            PaletteFilter.Categories(Entries.Concat(Entries).ToArray()));
        Assert.Empty(PaletteFilter.Categories([]));
    }

    [Fact]
    public void FilteredSelection_RemainsInFullCatalogWhenHidden()
    {
        var selection = new PaletteSelection();
        selection.Replace(Entries);
        var visible = PaletteFilter.Apply(selection.Entries, "shrine", PaletteCategory.Shrine);
        selection.Select(Assert.Single(visible).Id);

        Assert.Empty(PaletteFilter.Apply(selection.Entries, "missing", null));
        Assert.Equal(Entries[0].Id, selection.Current);
        Assert.Equal(3, selection.Entries.Count);
    }

    [Fact]
    public void Search_MatchesAcrossMapsById()
    {
        var entries = Entries.Append(new PaletteEntry(CatalogId.Parse("desert/shrines/0"), "Ancient Shrine", PaletteCategory.Shrine, 0, EMap.Desert)).ToArray();

        Assert.Equal(2, PaletteFilter.Apply(entries, "shrines", PaletteCategory.Shrine).Count);
        Assert.Single(PaletteFilter.Apply(entries, "desert/shrines", null));
    }
}

public class PaletteGroupTests
{
    private static PaletteGroup Group(string id, PaletteCategory category, int stage, EMap map) =>
        PaletteGroup.Of(new PaletteEntry(CatalogId.Parse(id), "Asset", category, stage, map));

    [Theory]
    [InlineData("forest/shrines/0", PaletteCategory.Shrine, 0, EMap.Forest, "Shrines")]
    [InlineData("forest/stage1/stageTilePrefabs/flat/0", PaletteCategory.FlatTile, 1, EMap.Forest, "Stage 1 flat tiles")]
    [InlineData("forest/randomObjectsOverride/0/0", PaletteCategory.Override, 0, EMap.Forest, "Overrides")]
    public void Label_NamesTheGroupWhenTheAssetIsFromTheLoadedMap(string id, PaletteCategory category, int stage, EMap map, string expected) =>
        Assert.Equal(expected, Group(id, category, stage, map).LabelFor(EMap.Forest));

    [Theory]
    [InlineData("desert/shrines/0", PaletteCategory.Shrine, 0, EMap.Desert, "Desert · Shrines")]
    [InlineData("graveyard/stage1/stageTilePrefabs/flat/0", PaletteCategory.FlatTile, 1, EMap.Graveyard, "Graveyard · Stage 1 flat tiles")]
    public void Label_NamesTheOriginMapOfACrossMapAsset(string id, PaletteCategory category, int stage, EMap map, string expected) =>
        Assert.Equal(expected, Group(id, category, stage, map).LabelFor(EMap.Forest));

    [Fact]
    public void Label_LeavesMaplessEntriesAlone() =>
        Assert.Equal("Packs", PaletteGroup.Of(new PaletteEntry(CatalogId.Parse("bundle:thps/warehouse-skateable-0"), "Rail", PaletteCategory.Pack, 0)).LabelFor(EMap.Forest));
}

public class PaletteCategoryNamesTests
{
    [Theory]
    [InlineData(PaletteCategory.RandomObject, "Random objects")]
    [InlineData(PaletteCategory.FlatTile, "Flat tiles")]
    [InlineData(PaletteCategory.SpecificTile, "Specific tiles")]
    [InlineData(PaletteCategory.Shrine, "Shrines")]
    [InlineData(PaletteCategory.Interactable, "Interactables")]
    public void Label_NamesTheCategory(PaletteCategory category, string expected) =>
        Assert.Equal(expected, category.Label());

    [Fact]
    public void ShortLabel_FitsATab() =>
        Assert.All(Enum.GetValues<PaletteCategory>(), category => Assert.InRange(category.ShortLabel().Length, 1, 5));
}
