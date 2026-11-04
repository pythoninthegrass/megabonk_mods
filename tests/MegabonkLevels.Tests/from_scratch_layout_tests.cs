namespace MegabonkLevels.Tests;

public class FromScratchLayoutTests
{
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
