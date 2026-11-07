namespace MegabonkLevels.Tests;

public class StarterLevelTests
{
    [Fact]
    public void ShippedStarter_ParsesEveryPlacementAndHasAConnectedGrid()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "../../../../../"));
        var level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(Path.Combine(root, "levels/mosswatch-hollow.mblevel.json")));
        var grid = level.Grid!.Value;

        Assert.Equal("Mosswatch Hollow", level.Title);
        Assert.Null(FromScratchLayout.SizeRefusal(grid, 15));
        Assert.Empty(level.Packs);
        var reachable = ReachabilityValidator.Validate(grid.ToLevelState(), (5, 1));
        Assert.Empty(reachable.Unreachable);
        Assert.Equal(121, reachable.Reachable.Count);
        foreach (var edit in level.Edits)
        {
            var placement = PlaceObject.FromEditOp(edit);
            var id = CatalogId.Parse(placement.CatalogId);
            Assert.Equal(CatalogNamespace.GameAsset, id.Namespace);
            CatalogRoute.Parse(id);
        }
    }
}
