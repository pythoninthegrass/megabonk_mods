namespace MegabonkLevels.Tests;

public class ScreenshotPathTests
{
    private static readonly string Evidence = Path.Combine(Path.GetTempPath(), "evidence-root");

    private static bool Missing(string path) => false;

    [Fact]
    public void Resolve_RelativePathLandsUnderTheEvidenceDirectory()
    {
        var result = ScreenshotPath.Resolve("shot.png", Evidence, Missing);

        Assert.Null(result.Error);
        Assert.Equal(Path.Combine(Evidence, "shot.png"), result.Path);
    }

    [Fact]
    public void Resolve_RelativeSubfolderIsKept()
    {
        var result = ScreenshotPath.Resolve(Path.Combine("sub", "shot.png"), Evidence, Missing);

        Assert.Equal(Path.Combine(Evidence, "sub", "shot.png"), result.Path);
    }

    [Fact]
    public void Resolve_AbsolutePathIsLeftAlone()
    {
        var absolute = Path.Combine(Path.GetTempPath(), "elsewhere", "shot.png");

        var result = ScreenshotPath.Resolve(absolute, Evidence, _ => true);

        Assert.Null(result.Error);
        Assert.Equal(absolute, result.Path);
    }

    [Fact]
    public void Resolve_ExistingRelativeTargetIsRefused()
    {
        var result = ScreenshotPath.Resolve("shot.png", Evidence, path => path == Path.Combine(Evidence, "shot.png"));

        Assert.Null(result.Path);
        Assert.Contains("already exists", result.Error);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    public void Resolve_WithoutAnEvidenceDirectoryRelativePathIsUnchanged(string evidence)
    {
        var result = ScreenshotPath.Resolve("shot.png", evidence, _ => true);

        Assert.Null(result.Error);
        Assert.Equal("shot.png", result.Path);
    }
}
