namespace MegabonkLevels.Tests;

public class PaletteLayoutTests
{
    [Fact]
    public void StartsExpandedWithAFourColumnGrid()
    {
        var layout = new PaletteLayout();

        Assert.False(layout.Compact);
        Assert.Equal(4, layout.Columns);
        Assert.Equal(24, layout.PerPage);
    }

    [Fact]
    public void Compact_ShowsASingleColumnOfTheSameRows()
    {
        var layout = new PaletteLayout();

        layout.SetCompact(true, 0);

        Assert.True(layout.Compact);
        Assert.Equal(1, layout.Columns);
        Assert.Equal(6, layout.PerPage);
    }

    [Theory]
    [InlineData(0, 0)]
    [InlineData(1, 4)]
    [InlineData(2, 8)]
    [InlineData(3, 12)]
    public void Collapsing_KeepsTheFirstVisibleEntryOnPage(int expandedPage, int compactPage) =>
        Assert.Equal(compactPage, CollapsedPage(expandedPage));

    [Theory]
    [InlineData(0, 0)]
    [InlineData(5, 1)]
    [InlineData(6, 1)]
    [InlineData(12, 3)]
    public void Expanding_KeepsTheFirstVisibleEntryOnPage(int compactPage, int expandedPage)
    {
        var layout = new PaletteLayout();
        layout.SetCompact(true, 0);

        Assert.Equal(expandedPage, layout.SetCompact(false, compactPage));
    }

    [Fact]
    public void SettingTheCurrentStateKeepsThePage()
    {
        var layout = new PaletteLayout();

        Assert.Equal(3, layout.SetCompact(false, 3));
    }

    [Fact]
    public void Reset_ReturnsToExpanded()
    {
        var layout = new PaletteLayout();
        layout.SetCompact(true, 0);

        layout.Reset();

        Assert.False(layout.Compact);
    }

    private static int CollapsedPage(int expandedPage) => new PaletteLayout().SetCompact(true, expandedPage);
}
