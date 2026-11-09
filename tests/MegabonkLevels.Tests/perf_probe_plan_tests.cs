using System;
using System.Linq;
using MegabonkLevels;
using Xunit;

public class PerfProbePlanTests
{
    [Fact]
    public void CensusNode_writes_scene_live_and_any_per_component()
    {
        var node = PerfProbePlan.CensusNode(new[] { ("EnemyHpBar", 12, 3, 40) });

        var row = Assert.Single(node);
        Assert.Equal("EnemyHpBar", row["name"].GetValue<string>());
        Assert.Equal(12, row["scene"].GetValue<int>());
        Assert.Equal(3, row["live"].GetValue<int>());
        Assert.Equal(40, row["any"].GetValue<int>());
    }

    [Fact]
    public void CensusNode_keeps_the_row_order()
    {
        var node = PerfProbePlan.CensusNode(new[] { ("Enemy", 1, 1, 1), ("AnimatedMesh", 2, 2, 2) });

        Assert.Equal(new[] { "Enemy", "AnimatedMesh" }, node.Select(entry => entry["name"].GetValue<string>()));
    }

    [Fact]
    public void CensusNode_with_no_rows_is_an_empty_array()
    {
        var node = PerfProbePlan.CensusNode(Array.Empty<(string, int, int, int)>());

        Assert.Empty(node);
    }

    [Fact]
    public void AttachNode_writes_the_patched_flag_per_probe()
    {
        var node = PerfProbePlan.AttachNode(new[] { ("EnemyDissolve.Update", false), ("Enemy.MyFixedUpdate", true) });

        Assert.Equal(2, node.Count);
        Assert.Equal("EnemyDissolve.Update", node[0]["name"].GetValue<string>());
        Assert.False(node[0]["patched"].GetValue<bool>());
        Assert.True(node[1]["patched"].GetValue<bool>());
    }

    [Fact]
    public void AttachNode_with_no_probes_is_an_empty_array()
    {
        var node = PerfProbePlan.AttachNode(Enumerable.Empty<(string, bool)>());

        Assert.Empty(node);
    }
}
