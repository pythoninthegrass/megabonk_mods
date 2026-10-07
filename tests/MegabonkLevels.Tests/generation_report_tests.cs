namespace MegabonkLevels.Tests;

public class GenerationReportTests
{
    [Fact]
    public void Format_IncludesSeedAndAllTileCounts()
    {
        var line = GenerationReport.Format(new GenerationSnapshot(105, 1200, 700, 40));

        Assert.Equal("A_GenerationComplete: mapSeed=105 tiles=1200 flatTiles=700 fillTiles=40", line);
    }

    [Fact]
    public void Format_HandlesNegativeAndZeroValues()
    {
        var line = GenerationReport.Format(new GenerationSnapshot(-1, 0, 0, 0));

        Assert.Equal("A_GenerationComplete: mapSeed=-1 tiles=0 flatTiles=0 fillTiles=0", line);
    }
}
