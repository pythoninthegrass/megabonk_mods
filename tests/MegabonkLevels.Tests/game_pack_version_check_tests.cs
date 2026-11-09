namespace MegabonkLevels.Tests;

public class GamePackVersionCheckTests
{
    [Fact]
    public void MismatchWarning_ReturnsNull_WhenVersionsMatch()
    {
        Assert.Null(GamePackVersionCheck.MismatchWarning("testpack", "1.2.3", "1.2.3"));
    }

    [Fact]
    public void MismatchWarning_ReturnsWarning_WhenVersionsDiffer()
    {
        var warning = GamePackVersionCheck.MismatchWarning("testpack", "1.2.3", "1.3.0");

        Assert.NotNull(warning);
        Assert.Contains("testpack", warning);
        Assert.Contains("1.2.3", warning);
        Assert.Contains("1.3.0", warning);
    }

    [Fact]
    public void MismatchWarning_ReturnsNull_WhenRecordedVersionIsMissing()
    {
        Assert.Null(GamePackVersionCheck.MismatchWarning("testpack", null, "1.3.0"));
    }

    [Fact]
    public void MismatchWarning_ReturnsNull_WhenInstalledVersionIsMissing()
    {
        Assert.Null(GamePackVersionCheck.MismatchWarning("testpack", "1.2.3", null));
    }

    [Fact]
    public void MismatchWarning_ReportsPackName()
    {
        var warning = GamePackVersionCheck.MismatchWarning("mypack", "0.1", "0.2");

        Assert.NotNull(warning);
        Assert.Contains("mypack", warning);
    }
}
