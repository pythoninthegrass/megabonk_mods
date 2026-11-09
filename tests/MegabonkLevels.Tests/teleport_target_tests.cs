namespace MegabonkLevels.Tests;

public class TeleportTargetTests
{
    [Fact]
    public void CellStandingPoint_FlatTile_IsTheCentreAtTheTileSurface()
    {
        var (x, y, z) = TeleportTarget.CellStandingPoint(9, 7, new TileState(2, SlopeDirection.None), 15, 15, 40f, 10f, 99f);

        Assert.Equal((80f, 20f, 0f), (x, y, z));
    }

    [Fact]
    public void CellStandingPoint_EmptyCell_KeepsTheCurrentHeight()
    {
        var (x, y, z) = TeleportTarget.CellStandingPoint(9, 7, null, 15, 15, 40f, 10f, 99f);

        Assert.Equal((80f, 99f, 0f), (x, y, z));
    }

    [Fact]
    public void CellStandingPoint_RampTile_IsHalfALevelUpAtTheCentre()
    {
        var (_, y, _) = TeleportTarget.CellStandingPoint(7, 7, new TileState(1, SlopeDirection.North), 15, 15, 40f, 10f, 0f);

        Assert.Equal(15f, y);
    }
}
