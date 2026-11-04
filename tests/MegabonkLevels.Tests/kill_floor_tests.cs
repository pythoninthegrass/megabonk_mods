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

    [Fact]
    public void FloorYExplicit_UsesTheAuthoredHeight()
    {
        Assert.Equal(-35f, KillFloor.FloorYExplicit(-35f, float.NegativeInfinity));
    }

    [Fact]
    public void FloorYExplicit_IsRaisedAboveTheCatchFloorSoABodyRestingOnItStillTriggers()
    {
        var floor = KillFloor.FloorYExplicit(-90f, -80f);

        Assert.Equal(-72f, floor);
        Assert.True(KillFloor.ShouldKill(-80f, floor));
    }

    [Fact]
    public void FloorYExplicit_NoAuthoredHeight_NeverKills()
    {
        var floor = KillFloor.FloorYExplicit(null, -80f);

        Assert.Equal(float.NegativeInfinity, floor);
        Assert.False(KillFloor.ShouldKill(-1_000_000f, floor));
    }

    [Fact]
    public void ShouldProbeCollider_ActorWithinReachingDistance_IsProbed()
    {
        Assert.True(KillFloor.ShouldProbeCollider(-80f, -80f));
        Assert.True(KillFloor.ShouldProbeCollider(-60f, -80f));
        Assert.True(KillFloor.ShouldProbeCollider(-200f, -80f));
    }

    [Fact]
    public void ShouldProbeCollider_ActorFarAboveTheFloor_IsSkipped()
    {
        Assert.False(KillFloor.ShouldProbeCollider(-40f, -80f));
        Assert.False(KillFloor.ShouldProbeCollider(40f, -80f));
    }

    [Fact]
    public void ShouldProbeCollider_AtAndPastTheMargin()
    {
        Assert.True(KillFloor.ShouldProbeCollider(-80f + KillFloor.ColliderProbeMargin, -80f));
        Assert.False(KillFloor.ShouldProbeCollider(-80f + KillFloor.ColliderProbeMargin + 0.01f, -80f));
    }

    [Fact]
    public void FloorY_FromAnAuthoredGridUsesItsLowestCell()
    {
        var grid = new LevelGrid(2, 1, new[] { new AuthoredCell(0, 0, 2), new AuthoredCell(1, 0, -1) });

        var floor = KillFloor.FloorY(grid.ToLevelState().Tiles.Values.Select(tile => tile.Height), tileHeight: 20f, margin: 40f, catchFloorY: float.NegativeInfinity);

        Assert.Equal(-60f, floor);
    }

    [Fact]
    public void FloorY_FromAnAuthoredGridStaysAboveTheCatchFloor()
    {
        var grid = new LevelGrid(1, 1, new[] { new AuthoredCell(0, 0, -5) });

        var floor = KillFloor.FloorY(grid.ToLevelState().Tiles.Values.Select(tile => tile.Height), tileHeight: 20f, margin: 40f, catchFloorY: -80f);

        Assert.True(floor > -80f);
    }

    [Fact]
    public void FloorY_FromAnEmptyAuthoredGridNeverKills()
    {
        var floor = KillFloor.FloorY(new LevelGrid(1, 1, Array.Empty<AuthoredCell>()).ToLevelState().Tiles.Values.Select(tile => tile.Height), 20f, 40f, -80f);

        Assert.Equal(float.NegativeInfinity, floor);
    }
}
