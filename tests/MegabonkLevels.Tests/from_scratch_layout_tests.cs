namespace MegabonkLevels.Tests;

public class FromScratchLayoutTests
{
    [Fact]
    public void ExposedEdges_IncludeTheExteriorAndSparseHolesButNotSharedFaces()
    {
        var cells = new HashSet<(int X, int Z)> { (0, 0), (1, 0), (1, 1) };
        var edges = FillEdgePlan.ExposedEdges(cells, (x, z) => cells.Contains((x, z)));

        Assert.Equal(8, edges.Count);
        Assert.Contains(new CellEdge(-1, 0, 0, 0), edges);
        Assert.Contains(new CellEdge(0, 0, 0, 1), edges);
        Assert.DoesNotContain(new CellEdge(0, 0, 1, 0), edges);
        Assert.Equal(edges.Count, edges.Distinct().Count());
        Assert.All(edges, edge => Assert.NotEqual(cells.Contains((edge.Ax, edge.Az)), cells.Contains((edge.Bx, edge.Bz))));
    }

    private static LevelGrid Grid(int width, int depth) => new(width, depth, Array.Empty<AuthoredCell>());

    [Fact]
    public void SizeRefusal_AcceptsAGridUpToTheStockSize()
    {
        Assert.Null(FromScratchLayout.SizeRefusal(Grid(15, 15), 15));
        Assert.Null(FromScratchLayout.SizeRefusal(Grid(4, 3), 15));
    }

    [Theory]
    [InlineData(16, 15)]
    [InlineData(15, 16)]
    [InlineData(40, 2)]
    public void SizeRefusal_NamesTheGridAndTheCapWhenEitherSideIsTooLarge(int width, int depth)
    {
        var reason = FromScratchLayout.SizeRefusal(Grid(width, depth), 15);

        Assert.NotNull(reason);
        Assert.Contains($"{width}x{depth}", reason);
        Assert.Contains("15x15", reason);
    }

    [Theory]
    [InlineData(4, 3, 4)]
    [InlineData(3, 4, 4)]
    [InlineData(5, 5, 5)]
    public void GeneratorSize_IsTheLongerSideBecauseTheGameGridIsSquare(int width, int depth, int expected) =>
        Assert.Equal(expected, FromScratchLayout.GeneratorSize(Grid(width, depth)));

    [Theory]
    [InlineData(13, 12, -240, -240, 0, -20, 520, 480)]
    [InlineData(12, 13, -240, -240, -20, 0, 480, 520)]
    [InlineData(15, 15, -280, -280, 0, 0, 600, 600)]
    [InlineData(4, 3, 100, -70, 160, -30, 160, 120)]
    public void WorldBoundsFollowTheAuthoredRectangleNotTheSquareBackingArray(
        int width, int depth, float originX, float originZ, float centerX, float centerZ, float sizeX, float sizeZ)
    {
        var grid = Grid(width, depth);
        var size = FromScratchLayout.WorldSize(grid, 40, new Vector3Data(600, 100, 600));
        var center = FromScratchLayout.WorldCenter(grid, 40, new Vector3Data(originX, 0, originZ), new Vector3Data(0, 30, 0));

        Assert.Equal(new Vector3Data(sizeX, 100, sizeZ), size);
        Assert.Equal(new Vector3Data(centerX, 30, centerZ), center);
        Assert.Equal(originX - 20, center.X - size.X / 2);
        Assert.Equal(originZ - 20, center.Z - size.Z / 2);
        Assert.Equal(originX + (width - 1) * 40 + 20, center.X + size.X / 2);
        Assert.Equal(originZ + (depth - 1) * 40 + 20, center.Z + size.Z / 2);
    }

    [Fact]
    public void CompactNorthernBarrierMeetsTheGroundAtTheReportedGap()
    {
        var grid = Grid(13, 12);
        var size = FromScratchLayout.WorldSize(grid, 40, new Vector3Data(520, 100, 520));
        var center = FromScratchLayout.WorldCenter(grid, 40, new Vector3Data(-240, 0, -240), new Vector3Data(0, 30, 0));

        Assert.Equal(220, center.Z + size.Z / 2);
        Assert.True(217 < center.Z + size.Z / 2);
        Assert.True(240 > center.Z + size.Z / 2);
    }

    [Fact]
    public void WorldBoundsUseTheLiveCellSpacingAndLeaveVerticalValuesAlone()
    {
        var grid = Grid(7, 5);
        Assert.Equal(new Vector3Data(140, 73, 100), FromScratchLayout.WorldSize(grid, 20, new Vector3Data(140, 73, 140)));
        Assert.Equal(new Vector3Data(0, -13, -20), FromScratchLayout.WorldCenter(grid, 20, new Vector3Data(-60, 99, -60), new Vector3Data(0, -13, 0)));
    }

    [Fact]
    public void TileArguments_FlatCellFacesNorthAtItsHeight()
    {
        var args = FromScratchLayout.TileArguments(new AuthoredCell(2, 3, 4));

        Assert.False(args.IsSlope);
        Assert.Equal((2, 3, 4), (args.X, args.Z, args.Height));
        Assert.Equal((0, 1), (args.DirectionX, args.DirectionZ));
    }

    [Theory]
    [InlineData(SlopeDirection.North, 0, 1)]
    [InlineData(SlopeDirection.East, 1, 0)]
    [InlineData(SlopeDirection.South, 0, -1)]
    [InlineData(SlopeDirection.West, -1, 0)]
    public void TileArguments_SlopeFacesItsUphillSide(SlopeDirection slope, int dx, int dz)
    {
        var args = FromScratchLayout.TileArguments(new AuthoredCell(0, 0, 1, slope));

        Assert.True(args.IsSlope);
        Assert.Equal((dx, dz), (args.DirectionX, args.DirectionZ));
        Assert.Equal(TilePlacement.UphillVector(slope), (args.DirectionX, args.DirectionZ));
    }

    [Fact]
    public void IsInPlace_IsTrueWithinTheToleranceOnEveryAxis()
    {
        var target = new[] { 10f, 2f, -4f };

        Assert.True(FromScratchLayout.IsInPlace(new[] { 10f, 2f, -4f }, target, 0.5f));
        Assert.True(FromScratchLayout.IsInPlace(new[] { 10.4f, 1.6f, -4.4f }, target, 0.5f));
        Assert.False(FromScratchLayout.IsInPlace(new[] { 10.6f, 2f, -4f }, target, 0.5f));
        Assert.False(FromScratchLayout.IsInPlace(new[] { 10f, 2f, -3.4f }, target, 0.5f));
    }

    [Fact]
    public void IsInPlace_IsFalseWhenEitherPositionIsMissing()
    {
        Assert.False(FromScratchLayout.IsInPlace(null, new[] { 0f, 0f, 0f }, 0.5f));
        Assert.False(FromScratchLayout.IsInPlace(new[] { 0f, 0f, 0f }, null, 0.5f));
        Assert.False(FromScratchLayout.IsInPlace(new[] { 0f, 0f }, new[] { 0f, 0f, 0f }, 0.5f));
    }
}
