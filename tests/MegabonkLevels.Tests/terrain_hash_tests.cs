namespace MegabonkLevels.Tests;

public class TerrainHashTests
{
    [Fact]
    public void AMissingGridHashesToNothing()
    {
        Assert.Null(TerrainHash.Of(null!, out var cellCount));
        Assert.Equal(0, cellCount);
    }

    [Fact]
    public void CountsAndFingerprintsEveryCell()
    {
        var hash = TerrainHash.Of(Build(17, 13), out var cellCount);
        Assert.Equal(221, cellCount);
        Assert.Matches("^[0-9A-F]{64}$", hash!);
    }

    [Fact]
    public void EqualGridsHashAlikeWhateverTheirIdentity()
    {
        var first = TerrainHash.Of(Build(9, 7), out _);
        var second = TerrainHash.Of(Build(9, 7), out _);
        Assert.Equal(first, second);
    }

    [Fact]
    public void AChangedCellChangesTheHash()
    {
        var grid = Build(9, 7);
        var before = TerrainHash.Of(grid, out _);
        grid[4, 3] += 0.25f;
        Assert.NotEqual(before, TerrainHash.Of(grid, out _));
    }

    [Fact]
    public void CellOrderChangesTheHash()
    {
        var forward = TerrainHash.Of(new object[] { 1.5f, 2.5f }, out _);
        var backward = TerrainHash.Of(new object[] { 2.5f, 1.5f }, out _);
        Assert.NotEqual(forward, backward);
    }

    [Fact]
    public void AMissingCellDiffersFromGroundLevel()
    {
        var missing = TerrainHash.Of(new object?[] { null, 1.5f }!, out _);
        var level = TerrainHash.Of(new object[] { 0f, 1.5f }, out _);
        Assert.NotEqual(missing, level);
    }

    [Fact]
    public void JitterBelowTheReportedPrecisionStillChangesNothing()
    {
        var grid = Build(6, 6);
        var before = TerrainHash.Of(grid, out _);
        grid[1, 1] += 0.000001f;
        Assert.Equal(before, TerrainHash.Of(grid, out _));
    }

    private static float[,] Build(int width, int height)
    {
        var grid = new float[width, height];
        for (var x = 0; x < width; x++)
        {
            for (var y = 0; y < height; y++)
            {
                grid[x, y] = x * 0.125f - y * 0.05f;
            }
        }

        return grid;
    }
}
