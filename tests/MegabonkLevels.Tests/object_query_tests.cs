using System.Text.Json;
using System.Text.Json.Nodes;

namespace MegabonkLevels.Tests;

public class ObjectQueryTests
{
    private enum Kind
    {
        Forest = 1,
        Hell = 64,
    }

    private sealed class Asset
    {
        public string name { get; init; } = "";

        public Kind eMap { get; init; }

        public int Order { get; init; }

        public bool Flag;

        public Asset Linked { get; init; }
    }

    private sealed class Other
    {
    }

    private static class Nested
    {
        public sealed class Asset
        {
        }
    }

    [Fact]
    public void Read_ReturnsNameAndRequestedFieldsPerObject()
    {
        var items = new[] { new Asset { name = "MapHell", eMap = Kind.Hell, Order = 3 }, new Asset { name = "MapForest", eMap = Kind.Forest, Order = 1 } };

        var result = ObjectQuery.Read(typeof(Asset), items, new[] { "Order" });

        Assert.Equal("Asset", (string)result["type"]!);
        Assert.Equal(2, (int)result["count"]!);
        var rows = (JsonArray)result["objects"]!;
        Assert.Equal("MapHell", (string)rows[0]!["name"]!);
        Assert.Equal(3L, (long)rows[0]!["Order"]!);
        Assert.Equal("MapForest", (string)rows[1]!["name"]!);
    }

    [Fact]
    public void Read_ReturnsEnumFieldsAsTheirIntegerValue()
    {
        var result = ObjectQuery.Read(typeof(Asset), new[] { new Asset { name = "MapHell", eMap = Kind.Hell } }, new[] { "eMap" });

        var value = ((JsonArray)result["objects"]!)[0]!["eMap"]!;
        Assert.Equal(JsonValueKind.Number, value.GetValueKind());
        Assert.Equal(64L, (long)value);
    }

    [Fact]
    public void Read_ReadsPublicFieldsAsWellAsProperties()
    {
        var result = ObjectQuery.Read(typeof(Asset), new[] { new Asset { name = "a", Flag = true } }, new[] { "Flag" });

        Assert.True((bool)((JsonArray)result["objects"]!)[0]!["Flag"]!);
    }

    [Fact]
    public void Read_ReturnsNullForANullFieldAndTextForAnObjectField()
    {
        var linked = new Asset { name = "inner" };

        var result = ObjectQuery.Read(typeof(Asset), new[] { new Asset { name = "a", Linked = linked }, new Asset { name = "b" } }, new[] { "Linked" });

        var rows = (JsonArray)result["objects"]!;
        Assert.Equal(linked.ToString(), (string)rows[0]!["Linked"]!);
        Assert.Null(rows[1]!["Linked"]);
    }

    [Fact]
    public void Read_WithNameRequestedTwice_ReturnsItOnce()
    {
        var result = ObjectQuery.Read(typeof(Asset), new[] { new Asset { name = "a" } }, new[] { "name", "name" });

        Assert.Single(((JsonArray)result["objects"]!)[0]!.AsObject());
    }

    [Fact]
    public void Read_UnknownField_ThrowsNamingTheFieldAndTypeEvenWithNoInstances()
    {
        var ex = Assert.Throws<InvalidOperationException>(() => ObjectQuery.Read(typeof(Asset), Array.Empty<Asset>(), new[] { "Missing" }));

        Assert.Contains("Missing", ex.Message);
        Assert.Contains("Asset", ex.Message);
    }

    [Fact]
    public void ResolveType_MatchesByShortOrFullName()
    {
        var candidates = new[] { typeof(Asset), typeof(Other) };

        Assert.Equal(typeof(Other), ObjectQuery.ResolveType(candidates, "Other"));
        Assert.Equal(typeof(Other), ObjectQuery.ResolveType(candidates, typeof(Other).FullName!));
    }

    [Fact]
    public void ResolveType_UnknownName_ThrowsNamingIt()
    {
        var ex = Assert.Throws<InvalidOperationException>(() => ObjectQuery.ResolveType(new[] { typeof(Asset) }, "Nope"));

        Assert.Contains("Nope", ex.Message);
    }

    [Fact]
    public void ResolveType_AmbiguousShortName_ListsTheFullNames()
    {
        var ex = Assert.Throws<InvalidOperationException>(() => ObjectQuery.ResolveType(new[] { typeof(Asset), typeof(Nested.Asset) }, "Asset"));

        Assert.Contains("Nested+Asset", ex.Message);
    }
}
