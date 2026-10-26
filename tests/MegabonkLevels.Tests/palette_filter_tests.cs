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
    public void GroupAndSearch_AreCombinedWithoutMixingStages()
    {
        var result = PaletteFilter.Apply(Entries, "grass", new PaletteGroup(1, PaletteCategory.FlatTile));

        Assert.Equal(Entries[2], Assert.Single(result));
        Assert.Empty(PaletteFilter.Apply(Entries, "shrine", new PaletteGroup(1, PaletteCategory.FlatTile)));
    }

    [Fact]
    public void Groups_AreDistinctInCatalogOrder()
    {
        Assert.Equal(
            new[] { new PaletteGroup(0, PaletteCategory.Shrine), new(0, PaletteCategory.FlatTile), new(1, PaletteCategory.FlatTile) },
            PaletteFilter.Groups(Entries.Concat(Entries).ToArray()));
        Assert.Empty(PaletteFilter.Groups([]));
    }

    [Fact]
    public void FilteredSelection_RemainsInFullCatalogWhenHidden()
    {
        var selection = new PaletteSelection();
        selection.Replace(Entries);
        var visible = PaletteFilter.Apply(selection.Entries, "grass", new PaletteGroup(1, PaletteCategory.FlatTile));
        selection.Select(Assert.Single(visible).Id);

        Assert.Empty(PaletteFilter.Apply(selection.Entries, "missing", null));
        Assert.Equal(Entries[2].Id, selection.Current);
        Assert.Equal(3, selection.Entries.Count);
    }
}
