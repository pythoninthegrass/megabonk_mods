namespace MegabonkLevels.Tests;

public class KillFloorTests
{
    [Fact]
    public void FloorY_IsLowestLevelTimesHeightMinusMargin()
    {
        var floor = KillFloor.FloorY(new[] { 2, -1, 0 }, tileHeight: 20f, margin: 40f, catchFloorY: float.NegativeInfinity);

        Assert.Equal(-60f, floor);
    }

    [Fact]
    public void FloorY_NoTiles_NeverKills()
    {
        var floor = KillFloor.FloorY(Array.Empty<int>(), tileHeight: 20f, margin: 40f, catchFloorY: float.NegativeInfinity);

        Assert.Equal(float.NegativeInfinity, floor);
        Assert.False(KillFloor.ShouldKill(-1_000_000f, floor));
    }

    [Fact]
    public void FloorY_IsRaisedAboveTheCatchFloorSoAPlayerRestingOnItStillTriggers()
    {
        var floor = KillFloor.FloorY(new[] { -5 }, tileHeight: 20f, margin: 40f, catchFloorY: -80f);

        Assert.True(floor > -80f);
        Assert.True(KillFloor.ShouldKill(-80f, floor));
    }

    [Fact]
    public void FloorY_CatchFloorBelowTheDerivedFloorChangesNothing()
    {
        var floor = KillFloor.FloorY(new[] { -1 }, tileHeight: 20f, margin: 40f, catchFloorY: -80f);

        Assert.Equal(-60f, floor);
    }

    [Theory]
    [InlineData(-61f, -60f, true)]
    [InlineData(-60f, -60f, false)]
    [InlineData(10f, -60f, false)]
    public void ShouldKill_IsTrueOnlyStrictlyBelowTheFloor(float y, float floorY, bool expected)
    {
        Assert.Equal(expected, KillFloor.ShouldKill(y, floorY));
    }
}
