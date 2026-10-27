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

    [Fact]
    public void LowestPoint_NoCollider_IsThePivot()
    {
        Assert.Equal(-66f, KillFloor.LowestPoint(pivotY: -66f, colliderMinY: null));
    }

    [Fact]
    public void LowestPoint_ColliderBelowThePivot_IsTheColliderBottom()
    {
        Assert.Equal(-80f, KillFloor.LowestPoint(pivotY: -66.5f, colliderMinY: -80f));
    }

    [Fact]
    public void LowestPoint_ColliderAboveThePivot_IsThePivot()
    {
        Assert.Equal(-66f, KillFloor.LowestPoint(pivotY: -66f, colliderMinY: -10f));
    }

    [Fact]
    public void LowestPoint_TallActorStandingOnTheCatchFloor_CountsAsFallen()
    {
        var floor = KillFloor.FloorY(new[] { -2 }, tileHeight: 20f, margin: 40f, catchFloorY: -80f);

        Assert.False(KillFloor.ShouldKill(-66.5f, floor));
        Assert.True(KillFloor.ShouldKill(KillFloor.LowestPoint(-66.5f, -80f), floor));
    }

    [Fact]
    public void FloorYForTerrain_IsLowestTerrainMinusMargin()
    {
        Assert.Equal(-30f, KillFloor.FloorYForTerrain(10f, 40f, float.NegativeInfinity));
    }

    [Fact]
    public void FloorYForTerrain_IsRaisedAboveTheCatchFloor()
    {
        Assert.Equal(-12f, KillFloor.FloorYForTerrain(10f, 40f, -20f));
    }

    [Theory]
    [InlineData(float.NaN)]
    [InlineData(float.PositiveInfinity)]
    public void FloorYForTerrain_NoTerrainHeight_NeverKills(float lowest)
    {
        Assert.Equal(float.NegativeInfinity, KillFloor.FloorYForTerrain(lowest, 40f, -100f));
    }
}
