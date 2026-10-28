namespace MegabonkLevels.Tests;

public class LevelMusicReferenceTests
{
    [Fact]
    public void TryParse_BundleId_SplitsPackAndAsset()
    {
        Assert.True(LevelMusicReference.TryParse("bundle:thps/Superman", out var reference));

        Assert.Equal("thps", reference.Pack);
        Assert.Equal("Superman", reference.Asset);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("Superman")]
    [InlineData("thps/Superman")]
    [InlineData("pack:thps/Superman")]
    [InlineData("bundle:")]
    [InlineData("bundle:thps")]
    [InlineData("bundle:thps/")]
    [InlineData("bundle:thps/a/b")]
    [InlineData("bundle:thps/../Superman")]
    [InlineData("bundle:thps/Super man")]
    [InlineData("forest/shrines/1")]
    public void TryParse_NotAPackAsset_ReturnsFalse(string value)
    {
        Assert.False(LevelMusicReference.TryParse(value, out _));
    }
}
