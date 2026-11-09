using System.Text.Json;
using System.Text.Json.Nodes;

namespace MegabonkLevels.Tests;

public class AssetDumpTests
{
    private enum Kind
    {
        Forest = 1,
        Hell = 64,
    }

    private sealed class Leaf
    {
        public string name { get; init; } = "";

        public int Size { get; init; }

        public float Volatility { get; init; }

        public bool Flag { get; init; }

        public Kind EMap { get; init; }
    }

    private sealed class Asset
    {
        public string name { get; init; } = "";

        public Leaf? Parameters { get; init; }

        public Leaf[]? Stages { get; init; }

        public int Count { get; init; }
    }

    private sealed class Thrower
    {
        public string name { get; } = "thrower";

        public int Good { get; } = 7;

        public int Bad => throw new InvalidOperationException("field not readable");
    }

    private sealed class Self
    {
        public string name { get; init; } = "";

        public Self? Next { get; set; }
    }

    [Fact]
    public void Describe_Primitives_KeepsTheirJsonKinds()
    {
        Assert.Equal("MapForest", (string)AssetDump.Describe("MapForest", 0)!);
        Assert.True((bool)AssetDump.Describe(true, 0)!);
        Assert.Equal(7L, (long)AssetDump.Describe(7, 0)!);
        Assert.Equal(64L, (long)AssetDump.Describe(Kind.Hell, 0)!);
        Assert.Equal(0.5f, (float)AssetDump.Describe(0.5f, 0)!);
        Assert.Null(AssetDump.Describe(null, 0));
    }

    [Fact]
    public void Describe_ZeroDepth_LeavesAnObjectAsItsText()
    {
        var leaf = new Leaf { name = "MapForestParams", Size = 15 };

        var node = AssetDump.Describe(leaf, 0);

        Assert.Equal(JsonValueKind.String, node!.GetValueKind());
        Assert.Equal(leaf.ToString(), (string)node);
    }

    [Fact]
    public void Describe_ExpandsAnObjectWithItsTypeItsNameAndPublicMembers()
    {
        var asset = new Asset { name = "MapForest", Count = 3, Parameters = new Leaf { name = "Params", Size = 15, Volatility = 0.5f, Flag = true, EMap = Kind.Forest } };

        var node = AssetDump.Describe(asset, 2)!.AsObject();

        Assert.Equal("Asset", (string)node["$type"]!);
        Assert.Equal("MapForest", (string)node["name"]!);
        Assert.Equal(3L, (long)node["Count"]!);
        var parameters = node["Parameters"]!.AsObject();
        Assert.Equal("Leaf", (string)parameters["$type"]!);
        Assert.Equal("Params", (string)parameters["name"]!);
        Assert.Equal(15L, (long)parameters["Size"]!);
        Assert.Equal(0.5f, (float)parameters["Volatility"]!);
        Assert.True((bool)parameters["Flag"]!);
        Assert.Equal(1L, (long)parameters["EMap"]!);
    }

    [Fact]
    public void Describe_NullMember_StaysNull()
    {
        var node = AssetDump.Describe(new Asset { name = "MapDesert" }, 2)!.AsObject();

        Assert.Null(node["Parameters"]);
    }

    [Fact]
    public void Describe_ExpandsAnArrayAsJsonItems()
    {
        var asset = new Asset
        {
            name = "MapForest",
            Stages = new[] { new Leaf { name = "Stage0", Size = 15 }, new Leaf { name = "Stage1", Size = 19 } },
        };

        var stages = AssetDump.Describe(asset, 2)!.AsObject()["Stages"]!.AsArray();

        Assert.Equal(2, stages.Count);
        Assert.Equal("Stage0", (string)stages[0]!["name"]!);
        Assert.Equal(19L, (long)stages[1]!["Size"]!);
    }

    [Fact]
    public void Describe_ArrayLongerThanTheItemCap_ReportsTheFullCountAndTruncates()
    {
        var asset = new Asset
        {
            name = "MapForest",
            Stages = Enumerable.Range(0, 5).Select(index => new Leaf { name = $"Stage{index}" }).ToArray(),
        };

        var node = AssetDump.Describe(asset, 2, maxItems: 2)!.AsObject()["Stages"]!.AsObject();

        Assert.Equal(5L, (long)node["count"]!);
        Assert.True((bool)node["truncated"]!);
        Assert.Equal(2, node["items"]!.AsArray().Count);
        Assert.Equal("Stage1", (string)node["items"]!.AsArray()[1]!["name"]!);
    }

    [Fact]
    public void Describe_AWalkOverBudget_StopsInsteadOfExpandingEverything()
    {
        var asset = new Asset
        {
            name = "MapForest",
            Stages = Enumerable.Range(0, 200).Select(index => new Leaf { name = $"Stage{index}", Size = index }).ToArray(),
        };

        var node = AssetDump.Describe(asset, 3, maxNodes: 60)!.AsObject();

        Assert.Contains("truncated", node.ToJsonString());
        Assert.True(node.ToJsonString().Length < 20000, $"the walk ignored its budget: {node.ToJsonString().Length} characters");
    }

    [Fact]
    public void Describe_ZeroDepth_LeavesMembersAsText()
    {
        var asset = new Asset { name = "MapForest", Parameters = new Leaf { name = "Params", Size = 15 } };

        var node = AssetDump.Describe(asset, 1)!.AsObject();

        Assert.Equal(asset.Parameters!.ToString(), (string)node["Parameters"]!);
    }

    [Fact]
    public void Describe_AMemberThatThrows_RecordsTheFailureAndKeepsTheRest()
    {
        var node = AssetDump.Describe(new Thrower(), 1)!.AsObject();

        Assert.Equal(7L, (long)node["Good"]!);
        Assert.Contains("field not readable", (string)node["Bad"]!);
    }

    [Fact]
    public void Describe_AReferenceToAnObjectAlreadyOnThePath_IsMarkedWithoutRecursing()
    {
        var inner = new Self { name = "inner" };
        var outer = new Self { name = "outer", Next = inner };
        inner.Next = outer;

        var node = AssetDump.Describe(outer, 4)!.AsObject();
        var back = node["Next"]!.AsObject()["Next"]!.AsObject();

        Assert.Equal("outer", (string)back["name"]!);
        Assert.True((bool)back["$cycle"]!);
        Assert.Null(back["Next"]);
    }

    [Fact]
    public void Describe_DepthBeyondTheCap_IsClamped()
    {
        var node = AssetDump.Describe(new Asset { name = "a", Parameters = new Leaf { name = "b", Size = 1 } }, AssetDump.MaxDepth + 10)!.AsObject();

        Assert.Equal(1L, (long)node["Parameters"]!["Size"]!);
    }

    [Fact]
    public void Describe_AnEngineObject_ReadsItsFieldsButNeverItsProperties()
    {
        var node = AssetDump.Describe(new Holder { Prefab = new FakeGameObject { name = "Tree", Amount = 3 } }, 3)!.AsObject();
        var prefab = node["Prefab"]!.AsObject();

        Assert.Equal("Tree", (string)prefab["name"]!);
        Assert.Equal(3L, (long)prefab["Amount"]!);
        Assert.True((bool)prefab["$fieldsOnly"]!);
        Assert.False(prefab.ContainsKey("Dangerous"));
    }

    [Fact]
    public void Describe_ADataAssetBelowScriptableObject_ExpandsItsMembers()
    {
        var node = AssetDump.Describe(new FakeData { name = "ParamForest1", Parameters = new Leaf { name = "inner", Size = 19 } }, 3)!.AsObject();

        Assert.Equal(19L, (long)node["Parameters"]!["Size"]!);
        Assert.False(node.ContainsKey("$fieldsOnly"));
    }

    private sealed class Holder
    {
        public FakeGameObject? Prefab { get; init; }
    }

    private sealed class FakeGameObject : UnityEngine.GameObject
    {
        public int Amount;

        public int Dangerous => throw new InvalidOperationException("component lookup");
    }

    private sealed class FakeData : UnityEngine.ScriptableObject
    {
        public string name { get; set; } = "";

        public Leaf? Parameters { get; set; }
    }
}
