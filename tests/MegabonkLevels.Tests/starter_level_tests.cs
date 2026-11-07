using System.Text.Json.Nodes;

namespace MegabonkLevels.Tests;

public class StarterLevelTests
{
    [Theory]
    [InlineData("spawn")]
    [InlineData("playerStart")]
    public void MovingTheSpawnOntoTheLavaPoolIsRefusedOnLoad(string field)
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "../../../../../"));
        var json = JsonNode.Parse(File.ReadAllText(Path.Combine(root, "levels/bramblecrown-hill.mblevel.json")))!;
        var pool = new JsonArray(200f, 20f, -160f);
        if (field == "spawn") json["spawn"]!["position"] = pool;
        else json["playerStart"] = pool;
        var ex = Assert.ThrowsAny<ArgumentException>(() => LevelFileSerializer.DeserializeWithMigration(json.ToJsonString()));
        Assert.Contains("lava", ex.Message);
    }

    [Fact]
    public void ShippedStarter_ParsesEveryPlacementAndHasAConnectedGrid()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "../../../../../"));
        var level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(Path.Combine(root, "levels/bramblecrown-hill.mblevel.json")));
        var grid = level.Grid!.Value;

        Assert.Equal("Bramblecrown Hill", level.Title);
        Assert.Null(FromScratchLayout.SizeRefusal(grid, 15));
        Assert.Empty(level.Packs);
        var reachable = ReachabilityValidator.Validate(grid.ToLevelState(), (7, 1));
        Assert.Empty(reachable.Unreachable);
        Assert.Equal(225, reachable.Reachable.Count);
        foreach (var edit in level.Edits)
        {
            var placement = PlaceObject.FromEditOp(edit);
            var id = CatalogId.Parse(placement.CatalogId);
            Assert.Equal(CatalogNamespace.GameAsset, id.Namespace);
            CatalogRoute.Parse(id);
        }
    }
}
