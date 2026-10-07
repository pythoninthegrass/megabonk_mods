namespace MegabonkLevels.Tests;

public class GenerationReportTests
{
    [Fact]
    public void Format_IncludesSeedAndAllTileCounts()
    {
        var line = GenerationReport.Format(new GenerationSnapshot(105, 999, "Forest", 0, 1200, 700, 40, 1940, "ABCD"));

        Assert.Equal(
            "A_GenerationComplete: map=Forest mapType=0 mapSeed=105 debugSeed=999 tiles=1200 flatTiles=700 fillTiles=40 nodes=1940 hash=ABCD",
            line);
    }

    [Fact]
    public void Format_HandlesNegativeAndZeroValues()
    {
        var line = GenerationReport.Format(new GenerationSnapshot(-1, -1, "", -1, 0, 0, 0, 0, ""));

        Assert.Equal(
            "A_GenerationComplete: map= mapType=-1 mapSeed=-1 debugSeed=-1 tiles=0 flatTiles=0 fillTiles=0 nodes=0 hash=",
            line);
    }
}
