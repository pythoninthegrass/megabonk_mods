namespace MegabonkLevels.Tests;

public class TerrainGridLayoutTests
{
    [Fact]
    public void BothIl2CppArrayHeadersAreOfferedWithTheirCellStart()
    {
        var multi = Assert.Single(TerrainGridLayout.CandidateLayouts, layout => layout.Name == "multi");
        var single = Assert.Single(TerrainGridLayout.CandidateLayouts, layout => layout.Name == "sz");

        Assert.Equal(24, multi.LengthOffset);
        Assert.Equal(32, multi.DataOffset);
        Assert.Equal(16, single.LengthOffset);
        Assert.Equal(24, single.DataOffset);
        Assert.All(TerrainGridLayout.CandidateLayouts, layout => Assert.True(layout.DataOffset > layout.LengthOffset));
    }

    [Theory]
    [InlineData(0, false)]
    [InlineData(-1, false)]
    [InlineData(256, true)]
    [InlineData(TerrainGridLayout.MaxCells, true)]
    [InlineData(TerrainGridLayout.MaxCells + 1, false)]
    public void OnlyAnArrayWithACredibleCellCountIsReadable(int length, bool readable)
    {
        Assert.Equal(readable, TerrainGridLayout.IsReadable(length));
    }

    [Fact]
    public void ACountThatDisagreesWithTheExpectedGridIsRefused()
    {
        Assert.True(TerrainGridLayout.LengthMatches(58_081, 58_081));
        Assert.False(TerrainGridLayout.LengthMatches(58_081, 65_025));
        Assert.True(TerrainGridLayout.LengthMatches(58_081, 0));
    }

    [Fact]
    public void AnAbsurdGridIsNotReadableAgainstAnExpectedSize()
    {
        Assert.False(TerrainGridLayout.LengthMatches(TerrainGridLayout.MaxCells + 1, 256));
    }

    [Fact]
    public void HeightsThatVaryWithinAPlausibleRangeLookLikeAGrid()
    {
        Assert.True(TerrainGridLayout.IsPlausible(new[] { 0.1f, 4.5f, 2.25f }));
    }

    [Fact]
    public void TheGridSummarySpansAndAveragesTheCells()
    {
        var stats = TerrainGridLayout.Of(new[] { -2f, 0f, 4f, 6f });

        Assert.NotNull(stats);
        Assert.Equal(4, stats!.Value.Cells);
        Assert.Equal(-2f, stats.Value.Min);
        Assert.Equal(6f, stats.Value.Max);
        Assert.Equal(2f, stats.Value.Mean);
    }

    [Fact]
    public void NoCellsOrUnusableCellsHaveNoSummary()
    {
        Assert.Null(TerrainGridLayout.Of(Array.Empty<float>()));
        Assert.Null(TerrainGridLayout.Of(null!));
        Assert.Null(TerrainGridLayout.Of(new[] { 1f, float.NaN, 2f }));
        Assert.Null(TerrainGridLayout.Of(new[] { 1f, float.PositiveInfinity, 2f }));
    }

    [Fact]
    public void AFlatOrBrokenBufferDoesNotLookLikeAGrid()
    {
        Assert.False(TerrainGridLayout.IsPlausible(new[] { 1.5f, 1.5f, 1.5f }));
        Assert.False(TerrainGridLayout.IsPlausible(new[] { 1.5f, float.NaN, 2f }));
        Assert.False(TerrainGridLayout.IsPlausible(new[] { 1.5f, TerrainGridLayout.MaxMagnitude * 2, 2f }));
        Assert.False(TerrainGridLayout.IsPlausible(Array.Empty<float>()));
        Assert.False(TerrainGridLayout.IsPlausible(null));
    }

    [Fact]
    public void ChecksSpanTheWholeGrid()
    {
        var indices = TerrainGridLayout.CheckIndices(1000, 4);
        Assert.Equal(new[] { 0, 333, 666, 999 }, indices);
    }

    [Fact]
    public void AGridShorterThanTheChecksIsStillChecked()
    {
        var indices = TerrainGridLayout.CheckIndices(2, 4);
        Assert.Equal(new[] { 0, 1 }, indices);
    }

    [Fact]
    public void NoCellsMeansNoChecks()
    {
        Assert.Empty(TerrainGridLayout.CheckIndices(0, 4));
    }

    [Fact]
    public void ABufferMatchingItsSamplesIsTrusted()
    {
        var copied = new[] { 0.25f, 0.5f, 0.75f, 1f };
        var indices = new[] { 0, 3 };
        Assert.True(TerrainGridLayout.Agrees(copied, new float?[] { 0.25f, 1f }, indices));
    }

    [Fact]
    public void ABufferReadingTheWrongBytesIsRefused()
    {
        var copied = new[] { 0.25f, 0.5f, 0.75f, 1f };
        var indices = new[] { 0, 3 };
        Assert.False(TerrainGridLayout.Agrees(copied, new float?[] { 0.25f, 1.5f }, indices));
    }

    [Fact]
    public void ASampleThatCannotBeReadProvesNothing()
    {
        var copied = new[] { 0.25f, 0.5f };
        Assert.False(TerrainGridLayout.Agrees(copied, new float?[] { null }, new[] { 1 }));
    }

    [Fact]
    public void ASampleOutsideTheBufferIsRefused()
    {
        var copied = new[] { 0.25f };
        Assert.False(TerrainGridLayout.Agrees(copied, new float?[] { 0.25f }, new[] { 7 }));
    }

    [Fact]
    public void MismatchedIndicesAndSamplesAreRefused()
    {
        var copied = new[] { 0.25f, 0.5f };
        Assert.False(TerrainGridLayout.Agrees(copied, new float?[] { 0.25f }, new[] { 0, 1 }));
    }

    [Fact]
    public void NoChecksMeansNoTrust()
    {
        Assert.False(TerrainGridLayout.Agrees(new[] { 0.25f }, Array.Empty<float?>(), Array.Empty<int>()));
    }
}
