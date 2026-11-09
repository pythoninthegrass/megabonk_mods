namespace MegabonkLevels.Tests;

public class LevelMusicReferenceTests
{
    [Theory]
    [InlineData("14 Strobe")]
    [InlineData("06.01 Screamer")]
    [InlineData("13 Le Hot '99")]
    public void TryParse_RuntimeTrack_PreservesExtensionlessName(string name)
    {
        Assert.True(LevelMusicReference.TryParse("track:" + name, out var reference));
        Assert.Null(reference.Pack);
        Assert.Equal(name, reference.Asset);
        Assert.True(reference.IsRuntime);
    }

    [Theory]
    [InlineData("track:")]
    [InlineData("track: ")]
    [InlineData("track:../song")]
    [InlineData("track:a\\song")]
    [InlineData("track:C:song")]
    [InlineData("track:song\n")]
    public void TryParse_UnsafeRuntimeReference_ReturnsFalse(string value)
    {
        Assert.False(LevelMusicReference.TryParse(value, out _));
    }

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
