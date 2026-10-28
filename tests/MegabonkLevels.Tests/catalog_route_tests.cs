namespace MegabonkLevels.Tests;

public class CatalogRouteTests
{
    [Fact]
    public void Parse_RandomMapObject_ReadsMapStageAndIndices()
    {
        var route = CatalogRoute.Parse(CatalogId.Parse("forest/stage1/randomMapObjects/2/3"));

        Assert.Equal(CatalogRouteKind.RandomMapObject, route.Kind);
        Assert.Equal(EMap.Forest, route.Map);
        Assert.Equal(1, route.Stage);
        Assert.Equal((2, 3), (route.Index, route.SubIndex));
    }

    [Fact]
    public void Parse_FlatTile_ReadsIndex()
    {
        var route = CatalogRoute.Parse(CatalogId.Parse("Graveyard/stage0/stageTilePrefabs/flat/4"));

        Assert.Equal(CatalogRouteKind.FlatTilePrefab, route.Kind);
        Assert.Equal(EMap.Graveyard, route.Map);
        Assert.Equal(4, route.Index);
    }

    [Fact]
    public void Parse_SpecificTile_ReadsIndex()
    {
        var route = CatalogRoute.Parse(CatalogId.Parse("forest/stage0/stageTilePrefabs/specific/1"));

        Assert.Equal(CatalogRouteKind.SpecificTilePrefab, route.Kind);
        Assert.Equal(1, route.Index);
    }

    [Fact]
    public void Parse_Shrine_IsMapScoped()
    {
        var route = CatalogRoute.Parse(CatalogId.Parse("forest/shrines/5"));

        Assert.Equal(CatalogRouteKind.Shrine, route.Kind);
        Assert.Equal(EMap.Forest, route.Map);
        Assert.Equal(5, route.Index);
    }

    [Fact]
    public void Parse_Chest_And_ChestFree()
    {
        Assert.Equal(CatalogRouteKind.Chest, CatalogRoute.Parse(CatalogId.Parse("interactable/chest")).Kind);
        Assert.Equal(CatalogRouteKind.ChestFree, CatalogRoute.Parse(CatalogId.Parse("interactable/chestFree")).Kind);
    }

    [Fact]
    public void Parse_Boombox()
    {
        Assert.Equal(CatalogRouteKind.Boombox, CatalogRoute.Parse(CatalogId.Parse("interactable/boombox")).Kind);
    }

    [Fact]
    public void Parse_Rail_ReadsIndex()
    {
        var route = CatalogRoute.Parse(CatalogId.Parse("interactable/rail/2"));

        Assert.Equal(CatalogRouteKind.Rail, route.Kind);
        Assert.Equal(2, route.Index);
    }

    [Theory]
    [InlineData("bundle:my/prefab")]
    [InlineData("forest/stage0/unknownCategory/1")]
    [InlineData("nomap/stage0/randomMapObjects/0/0")]
    [InlineData("forest/stageX/randomMapObjects/0/0")]
    [InlineData("forest/stage0/randomMapObjects/a/0")]
    [InlineData("forest/stage0/randomMapObjects/0")]
    [InlineData("forest/shrines/-1")]
    public void Parse_Unresolvable_ThrowsArgumentException(string raw)
    {
        Assert.Throws<ArgumentException>(() => CatalogRoute.Parse(CatalogId.Parse(raw)));
    }
}
