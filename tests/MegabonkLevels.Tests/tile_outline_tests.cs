namespace MegabonkLevels.Tests;

public class TileOutlineTests
{
    private const int Width = 15;
    private const int Depth = 15;
    private const float Spacing = 40f;
    private const float TileHeight = 20f;
    private const float Lift = 0.5f;

    private static IReadOnlyList<Vector3Data> Corners(int x, int z, TileState state) =>
        TileOutline.Corners(x, z, state, Width, Depth, Spacing, TileHeight, Lift);

    [Fact]
    public void Corners_FlatTile_SquareAroundTheCellCentreAtItsTopSurface()
    {
        Assert.Equal(new[]
        {
            new Vector3Data(60f, 20.5f, -20f),
            new Vector3Data(100f, 20.5f, -20f),
            new Vector3Data(100f, 20.5f, 20f),
            new Vector3Data(60f, 20.5f, 20f),
        }, Corners(9, 7, new TileState(1, SlopeDirection.None)));
    }

    [Fact]
    public void Corners_CentreMapsBackToTheSameCell()
    {
        var corners = Corners(3, 11, new TileState(0, SlopeDirection.None));

        var cell = PositionReadout.CellOf(corners.Average(c => c.X), corners.Average(c => c.Z), Width, Depth, Spacing);

        Assert.Equal(new GridCell(3, 11, true), cell);
    }

    [Theory]
    [InlineData(SlopeDirection.North, new[] { 0f, 0f, 1f, 1f })]
    [InlineData(SlopeDirection.South, new[] { 1f, 1f, 0f, 0f })]
    [InlineData(SlopeDirection.East, new[] { 0f, 1f, 1f, 0f })]
    [InlineData(SlopeDirection.West, new[] { 1f, 0f, 0f, 1f })]
    public void Corners_Slope_RaisesTheUphillEdgeOneLevel(SlopeDirection direction, float[] levelsAboveBase)
    {
        var corners = Corners(7, 7, new TileState(2, direction));

        Assert.Equal(levelsAboveBase.Select(l => 40f + l * TileHeight + Lift), corners.Select(c => c.Y));
    }
}
