namespace MegabonkLevels.Tests;

public class PalettePagerTests
{
    [Theory]
    [InlineData(0, 20, 1)]
    [InlineData(20, 20, 1)]
    [InlineData(21, 20, 2)]
    [InlineData(75, 20, 4)]
    public void PageCount_RoundsUpWithAMinimumOfOne(int count, int perPage, int expected) =>
        Assert.Equal(expected, PalettePager.PageCount(count, perPage));

    [Theory]
    [InlineData(-3, 75, 0)]
    [InlineData(2, 75, 2)]
    [InlineData(9, 75, 3)]
    public void Clamp_KeepsThePageInRange(int page, int count, int expected) =>
        Assert.Equal(expected, PalettePager.Clamp(page, count, 20));

    [Fact]
    public void Slice_ReturnsThePageAndTheShortLastPage()
    {
        var items = Enumerable.Range(0, 45).ToArray();

        Assert.Equal(Enumerable.Range(20, 20), PalettePager.Slice(items, 1, 20));
        Assert.Equal(Enumerable.Range(40, 5), PalettePager.Slice(items, 2, 20));
        Assert.Equal(Enumerable.Range(40, 5), PalettePager.Slice(items, 9, 20));
        Assert.Empty(PalettePager.Slice(Array.Empty<int>(), 0, 20));
    }

    [Theory]
    [InlineData(0, 0)]
    [InlineData(19, 0)]
    [InlineData(20, 1)]
    [InlineData(-1, 0)]
    public void PageOf_FindsThePageHoldingAnIndex(int index, int expected) =>
        Assert.Equal(expected, PalettePager.PageOf(index, 20));

    [Theory]
    [InlineData(0, 1f, 4, 1)]
    [InlineData(1, -1f, 4, 0)]
    [InlineData(0, -1f, 4, 0)]
    [InlineData(3, 1f, 4, 3)]
    [InlineData(1, 2f, 4, 3)]
    [InlineData(2, 0f, 4, 2)]
    public void Step_MovesOnePagePerNotchWithoutWrapping(int page, float notches, int pageCount, int expected) =>
        Assert.Equal(expected, PalettePager.Step(page, notches, pageCount));
}
