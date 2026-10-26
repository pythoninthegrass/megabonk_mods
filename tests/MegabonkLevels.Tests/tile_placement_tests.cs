namespace MegabonkLevels.Tests;

public class TilePlacementTests
{
    [Theory]
    [InlineData(SlopeDirection.None, TilePlacementKind.ReplaceWithFlat)]
    [InlineData(SlopeDirection.North, TilePlacementKind.ReplaceWithSlope)]
    [InlineData(SlopeDirection.East, TilePlacementKind.ReplaceWithSlope)]
    [InlineData(SlopeDirection.South, TilePlacementKind.ReplaceWithSlope)]
    [InlineData(SlopeDirection.West, TilePlacementKind.ReplaceWithSlope)]
    public void Decide_StaticBatch_ReplacesInsteadOfMovingInvisibleSurface(SlopeDirection slope, TilePlacementKind expected)
    {
        foreach (var height in new[] { -1, 0, 1, 3 })
        {
            Assert.Equal(expected, TilePlacement.Decide(true, slope, new TileState(height, slope), liveIsStaticBatch: true));
        }
    }

    [Theory]
    [InlineData(SlopeDirection.North, 0, 1)]
    [InlineData(SlopeDirection.South, 0, -1)]
    [InlineData(SlopeDirection.East, 1, 0)]
    [InlineData(SlopeDirection.West, -1, 0)]
    public void UphillVector_MapsCardinalDirectionToGridStep(SlopeDirection direction, int dx, int dz)
    {
        Assert.Equal((dx, dz), TilePlacement.UphillVector(direction));
    }

    [Fact]
    public void UphillVector_None_Throws()
    {
        Assert.Throws<ArgumentException>(() => TilePlacement.UphillVector(SlopeDirection.None));
    }

    [Theory]
    [InlineData(0, 1, SlopeDirection.North)]
    [InlineData(0, -1, SlopeDirection.South)]
    [InlineData(1, 0, SlopeDirection.East)]
    [InlineData(-1, 0, SlopeDirection.West)]
    public void SlopeFromVector_IsInverseOfUphillVector(int dx, int dz, SlopeDirection expected)
    {
        Assert.Equal(expected, TilePlacement.SlopeFromVector(dx, dz));
    }

    [Fact]
    public void SlopeFromVector_NonCardinal_ReturnsNone()
    {
        Assert.Equal(SlopeDirection.None, TilePlacement.SlopeFromVector(0, 0));
        Assert.Equal(SlopeDirection.None, TilePlacement.SlopeFromVector(1, 1));
    }

    [Fact]
    public void Decide_NoLiveTile_AddsFlatOrSlopeByTarget()
    {
        Assert.Equal(TilePlacementKind.AddFlat, TilePlacement.Decide(false, SlopeDirection.None, new TileState(2, SlopeDirection.None)));
        Assert.Equal(TilePlacementKind.AddSlope, TilePlacement.Decide(false, SlopeDirection.None, new TileState(2, SlopeDirection.East)));
    }

    [Fact]
    public void Decide_LiveFlatTargetFlat_OnlyMoves()
    {
        Assert.Equal(TilePlacementKind.MoveOnly, TilePlacement.Decide(true, SlopeDirection.None, new TileState(3, SlopeDirection.None)));
    }

    [Fact]
    public void Decide_LiveSlopeSameDirection_OnlyMoves()
    {
        Assert.Equal(TilePlacementKind.MoveOnly, TilePlacement.Decide(true, SlopeDirection.North, new TileState(3, SlopeDirection.North)));
    }

    [Fact]
    public void Decide_LiveFlatTargetSlope_ReplacesWithSlope()
    {
        Assert.Equal(TilePlacementKind.ReplaceWithSlope, TilePlacement.Decide(true, SlopeDirection.None, new TileState(1, SlopeDirection.West)));
    }

    [Fact]
    public void Decide_LiveSlopeDifferentDirection_ReplacesWithSlope()
    {
        Assert.Equal(TilePlacementKind.ReplaceWithSlope, TilePlacement.Decide(true, SlopeDirection.North, new TileState(1, SlopeDirection.South)));
    }

    [Fact]
    public void Decide_LiveSlopeTargetFlat_ReplacesWithFlat()
    {
        Assert.Equal(TilePlacementKind.ReplaceWithFlat, TilePlacement.Decide(true, SlopeDirection.East, new TileState(1, SlopeDirection.None)));
    }

    [Fact]
    public void WorldPosition_ScalesGridCellAndHeightFromMapParameters()
    {
        var position = TilePlacement.WorldPosition(x: 3, z: 4, height: 2, originX: -280, originZ: -280, scaledTileWidth: 40, scaledTileHeight: 20);

        Assert.Equal((-160f, 40f, -120f), position);
    }
}
