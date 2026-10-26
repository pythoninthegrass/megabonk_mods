namespace MegabonkLevels.Tests;

public class ThumbnailCacheTests
{
    private static readonly CatalogId Id = CatalogId.Parse("forest/shrines/0");

    [Fact]
    public void Unrendered_IsNotCached()
    {
        var cache = new ThumbnailCache<string>();

        Assert.False(cache.TryGet(Id, out _));
    }

    [Fact]
    public void Render_RunsOncePerId()
    {
        var cache = new ThumbnailCache<string>();
        var calls = 0;

        Assert.Equal("img", cache.GetOrRender(Id, _ => { calls++; return "img"; }));
        Assert.Equal("img", cache.GetOrRender(Id, _ => { calls++; return "other"; }));
        Assert.Equal(1, calls);
    }

    [Fact]
    public void FailedRender_IsCachedAsNullAndNotRetried()
    {
        var cache = new ThumbnailCache<string>();
        var calls = 0;

        Assert.Null(cache.GetOrRender(Id, _ => { calls++; return null; }));
        Assert.Null(cache.GetOrRender(Id, _ => { calls++; return "img"; }));
        Assert.True(cache.TryGet(Id, out var cached));
        Assert.Null(cached);
        Assert.Equal(1, calls);
    }

    [Fact]
    public void Clear_ForgetsEverything()
    {
        var cache = new ThumbnailCache<string>();
        cache.GetOrRender(Id, _ => "img");
        cache.Clear();

        Assert.False(cache.TryGet(Id, out _));
        Assert.Equal(0, cache.Count);
    }
}
