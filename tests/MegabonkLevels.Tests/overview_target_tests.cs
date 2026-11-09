namespace MegabonkLevels.Tests;

public class OverviewTargetTests
{
    private static readonly TileState Flat = new(2, SlopeDirection.None);

    [Fact]
    public void Of_PlayerInGrid_IsThePlayer()
    {
        var (x, y, z) = OverviewTarget.Of(120f, 2f, -3f, 15, 15, 40f, 10f, Flat);

        Assert.Equal((120f, 2f, -3f), (x, y, z));
    }

    [Fact]
    public void Of_PlayerOutsideGrid_IsTheCentreTileSurface()
    {
        var (x, y, z) = OverviewTarget.Of(2000f, 2002f, 2017f, 19, 19, 40f, 10f, Flat);

        Assert.Equal((0f, 20f + TeleportTarget.PlayerBodyOffsetY, 0f), (x, y, z));
    }

    [Fact]
    public void Of_PlayerOutsideGridAndCentreEmpty_KeepsThePlayerBodyHeight()
    {
        var (x, y, z) = OverviewTarget.Of(2000f, 2002f, 2017f, 19, 19, 40f, 10f, null);

        Assert.Equal((0f, 2002f, 0f), (x, y, z));
    }

    [Theory]
    [InlineData(15, 7, 7)]
    [InlineData(19, 9, 9)]
    [InlineData(16, 8, 8)]
    public void CentreCell_IsTheMiddleOfTheGrid(int size, int expectedX, int expectedZ)
    {
        Assert.Equal((expectedX, expectedZ), OverviewTarget.CentreCell(size, size));
    }
}
