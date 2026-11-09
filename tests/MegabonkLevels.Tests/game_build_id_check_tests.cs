namespace MegabonkLevels.Tests;

public class GameBuildIdCheckTests
{
    [Fact]
    public void MismatchWarning_ReturnsNull_WhenBuildIdsMatch()
    {
        Assert.Null(GameBuildIdCheck.MismatchWarning("21750826", "21750826"));
    }

    [Fact]
    public void MismatchWarning_ReturnsWarning_WhenBuildIdsDiffer()
    {
        var warning = GameBuildIdCheck.MismatchWarning("21750826", "21800000");

        Assert.NotNull(warning);
        Assert.Contains("21750826", warning);
        Assert.Contains("21800000", warning);
    }

    [Fact]
    public void MismatchWarning_ReturnsNull_WhenRecordedBuildIdIsMissing()
    {
        Assert.Null(GameBuildIdCheck.MismatchWarning("", "21750826"));
    }
}
