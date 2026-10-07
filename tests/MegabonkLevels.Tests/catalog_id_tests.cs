namespace MegabonkLevels.Tests;

public class CatalogIdTests
{
    [Theory]
    [InlineData("forest/stage0/randomMapObjects/2/0")]
    [InlineData("desert/stage1/stageTilePrefabs/flat/3")]
    [InlineData("graveyard/stage2/stageTilePrefabs/specific/1")]
    [InlineData("forest/shrines/5")]
    [InlineData("interactable/chest")]
    [InlineData("interactable/chestFree")]
    [InlineData("interactable/rail/2")]
    public void Parse_ValidGameAssetId_ReturnsGameAssetNamespace(string raw)
    {
        var id = CatalogId.Parse(raw);

        Assert.Equal(CatalogNamespace.GameAsset, id.Namespace);
        Assert.Equal(raw.Split('/'), id.Segments);
    }

    [Theory]
    [InlineData("bundle:mypack/rock")]
    [InlineData("bundle:mypack/props/rock")]
    public void Parse_ValidBundleId_ReturnsBundleNamespace(string raw)
    {
        var id = CatalogId.Parse(raw);

        Assert.Equal(CatalogNamespace.Bundle, id.Namespace);
        Assert.Equal(raw.Substring("bundle:".Length).Split('/'), id.Segments);
    }

    [Fact]
    public void Serialize_RoundTripsGameAssetId()
    {
        const string raw = "forest/stage0/randomMapObjects/2/0";

        var id = CatalogId.Parse(raw);

        Assert.Equal(raw, id.Serialize());
    }

    [Fact]
    public void Serialize_RoundTripsBundleId()
    {
        const string raw = "bundle:mypack/props/rock";

        var id = CatalogId.Parse(raw);

        Assert.Equal(raw, id.Serialize());
    }

    public static readonly TheoryData<string, string> MalformedInputs = new()
    {
        { "", "empty" },
        { "   ", "whitespace" },
        { "interactable", "too few segments" },
        { "bundle:", "empty segment" },
        { "bundle:mypack", "too few segments" },
        { "foo:bar/baz", "unknown namespace prefix" },
        { "/forest/stage0", "empty segment" },
        { "forest/stage0/", "empty segment" },
        { "forest//stage0", "empty segment" },
        { "forest/stage 0", "invalid character" },
        { "forest/stage0!", "invalid character" },
        { "bundle:mypack/", "empty segment" },
    };

    [Theory]
    [MemberData(nameof(MalformedInputs))]
    public void Parse_MalformedInput_ThrowsWithReason(string raw, string expectedReasonFragment)
    {
        var ex = Assert.Throws<ArgumentException>(() => CatalogId.Parse(raw));

        Assert.Contains(expectedReasonFragment, ex.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void TryParse_MalformedInput_ReturnsFalseWithoutThrowing()
    {
        var result = CatalogId.TryParse("", out var id, out var error);

        Assert.False(result);
        Assert.Equal(default, id);
        Assert.NotNull(error);
    }

    [Fact]
    public void TryParse_ValidInput_ReturnsTrue()
    {
        var result = CatalogId.TryParse("interactable/chest", out var id, out var error);

        Assert.True(result);
        Assert.Null(error);
        Assert.Equal(CatalogNamespace.GameAsset, id.Namespace);
    }

    [Fact]
    public void Equals_SameSegments_AreEqual()
    {
        var a = CatalogId.Parse("interactable/chest");
        var b = CatalogId.Parse("interactable/chest");

        Assert.Equal(a, b);
        Assert.Equal(a.GetHashCode(), b.GetHashCode());
    }

    [Fact]
    public void Equals_DifferentSegments_AreNotEqual()
    {
        var a = CatalogId.Parse("interactable/chest");
        var b = CatalogId.Parse("interactable/chestFree");

        Assert.NotEqual(a, b);
    }
}
