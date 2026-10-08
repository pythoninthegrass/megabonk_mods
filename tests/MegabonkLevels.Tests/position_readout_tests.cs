namespace MegabonkLevels.Tests;

public class PositionReadoutTests
{
    private const int Width = 15;
    private const int Depth = 15;
    private const float Spacing = 40f;

    [Theory]
    [InlineData(-280f, -280f, 0, 0)]
    [InlineData(280f, 280f, 14, 14)]
    [InlineData(0f, 0f, 7, 7)]
    [InlineData(240f, 0f, 13, 7)]
    public void CellOf_CellCentre_ReturnsThatCell(float x, float z, int cellX, int cellZ)
    {
        var cell = PositionReadout.CellOf(x, z, Width, Depth, Spacing);

        Assert.Equal(new GridCell(cellX, cellZ, true), cell);
    }

    [Fact]
    public void CellOf_TileEdge_BelongsToTheTileAwayFromTheOrigin()
    {
        Assert.Equal(new GridCell(8, 7, true), PositionReadout.CellOf(20f, 0f, Width, Depth, Spacing));
        Assert.Equal(new GridCell(7, 7, true), PositionReadout.CellOf(19.9f, 0f, Width, Depth, Spacing));
        Assert.Equal(new GridCell(7, 7, true), PositionReadout.CellOf(-20f, 0f, Width, Depth, Spacing));
        Assert.Equal(new GridCell(6, 7, true), PositionReadout.CellOf(-20.1f, 0f, Width, Depth, Spacing));
    }

    [Fact]
    public void CellOf_OuterEdgeOfTheLastTile_IsStillInTheGrid()
    {
        Assert.Equal(new GridCell(14, 0, true), PositionReadout.CellOf(299.9f, -299.9f, Width, Depth, Spacing));
        Assert.Equal(new GridCell(0, 14, true), PositionReadout.CellOf(-299.9f, 299.9f, Width, Depth, Spacing));
    }

    [Theory]
    [InlineData(300f, 0f, 15, 7)]
    [InlineData(-300.1f, 0f, -1, 7)]
    [InlineData(0f, 340f, 7, 16)]
    [InlineData(0f, -1000f, 7, -18)]
    public void CellOf_OutsideTheGrid_ReturnsTheUnclampedCellAndFlagsIt(float x, float z, int cellX, int cellZ)
    {
        var cell = PositionReadout.CellOf(x, z, Width, Depth, Spacing);

        Assert.Equal(new GridCell(cellX, cellZ, false), cell);
    }

    [Fact]
    public void CellOf_EvenSizedGrid_CentresTheOriginBetweenTwoCells()
    {
        Assert.Equal(new GridCell(0, 0, true), PositionReadout.CellOf(-20f, -20f, 2, 2, Spacing));
        Assert.Equal(new GridCell(1, 1, true), PositionReadout.CellOf(20f, 20f, 2, 2, Spacing));
    }

    [Fact]
    public void LevelOf_RoundsToTheNearestHeightStep()
    {
        Assert.Equal(1, PositionReadout.LevelOf(22f, 20f));
        Assert.Equal(0, PositionReadout.LevelOf(9.9f, 20f));
        Assert.Equal(-2, PositionReadout.LevelOf(-41f, 20f));
    }

    [Fact]
    public void Format_InsideTheGridAboveTheFloor_ShowsCellLevelPositionAndFloor()
    {
        var text = PositionReadout.Format(240f, 22f, 0f, new GridCell(13, 7, true), 1, -72f);

        Assert.Equal("cell (13,7) h1  pos (240, 22, 0)  floor -72", text);
    }

    [Fact]
    public void Format_BelowTheFloor_AppendsTheFlag()
    {
        var text = PositionReadout.Format(0f, -80f, 0f, new GridCell(7, 7, true), -4, -72f);

        Assert.EndsWith("  BELOW FLOOR", text);
    }

    [Fact]
    public void Format_AtTheFloor_IsNotBelow()
    {
        var text = PositionReadout.Format(0f, -72f, 0f, new GridCell(7, 7, true), -4, -72f);

        Assert.DoesNotContain("BELOW", text);
    }

    [Fact]
    public void Format_OutsideTheGrid_MarksTheCell()
    {
        var text = PositionReadout.Format(-320f, 22f, 0f, new GridCell(-1, 7, false), 1, -72f);

        Assert.StartsWith("cell (-1,7) outside h1", text);
    }

    [Fact]
    public void Format_NoFloor_OmitsTheFloorAndNeverFlags()
    {
        var text = PositionReadout.Format(0f, -5000f, 0f, new GridCell(7, 7, true), -250, float.NegativeInfinity);

        Assert.DoesNotContain("floor", text);
        Assert.DoesNotContain("BELOW", text);
    }

    [Fact]
    public void Format_RoundsAndNeverPrintsNegativeZero()
    {
        var text = PositionReadout.Format(-0.2f, 1.5f, -0.4f, new GridCell(7, 7, true), 0, -72f);

        Assert.Contains("pos (0, 2, 0)", text);
    }
}
