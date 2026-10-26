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
