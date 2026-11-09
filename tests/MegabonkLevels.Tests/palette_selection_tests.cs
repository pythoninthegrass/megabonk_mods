namespace MegabonkLevels.Tests;

public class PaletteSelectionTests
{
    private static PaletteEntry Entry(string id) =>
        new(CatalogId.Parse(id), id, PaletteCategory.Shrine, 0);

    [Fact]
    public void Select_SetsCurrentAndRaisesChanged()
    {
        var selection = new PaletteSelection();
        selection.Replace([Entry("forest/shrines/0")]);
        CatalogId? seen = null;
        selection.Changed += id => seen = id;

        selection.Select(CatalogId.Parse("forest/shrines/0"));

        Assert.Equal("forest/shrines/0", selection.Current?.Serialize());
        Assert.Equal("forest/shrines/0", seen?.Serialize());
    }

    [Fact]
    public void Select_IdNotInPalette_Throws()
    {
        var selection = new PaletteSelection();
        selection.Replace([Entry("forest/shrines/0")]);

        Assert.Throws<ArgumentException>(() => selection.Select(CatalogId.Parse("forest/shrines/9")));
    }

    [Fact]
    public void Replace_SelectionStillListed_KeepsIt()
    {
        var selection = new PaletteSelection();
        selection.Replace([Entry("forest/shrines/0")]);
        selection.Select(CatalogId.Parse("forest/shrines/0"));

        selection.Replace([Entry("forest/shrines/0"), Entry("forest/shrines/1")]);

        Assert.Equal("forest/shrines/0", selection.Current?.Serialize());
    }

    [Fact]
    public void Replace_SelectionNoLongerListed_ClearsAndRaisesChanged()
    {
        var selection = new PaletteSelection();
        selection.Replace([Entry("forest/shrines/0")]);
        selection.Select(CatalogId.Parse("forest/shrines/0"));
        var raised = new List<CatalogId?>();
        selection.Changed += raised.Add;

        selection.Replace([Entry("desert/shrines/0")]);

        Assert.Null(selection.Current);
        Assert.Equal([null], raised);
    }

    [Fact]
    public void Replace_ExposesEntries()
    {
        var selection = new PaletteSelection();

        selection.Replace([Entry("forest/shrines/0")]);

        Assert.Single(selection.Entries);
    }

    [Fact]
    public void Clear_NoSelection_DoesNotRaiseChanged()
    {
        var selection = new PaletteSelection();
        var count = 0;
        selection.Changed += _ => count++;

        selection.Clear();

        Assert.Equal(0, count);
    }
}
