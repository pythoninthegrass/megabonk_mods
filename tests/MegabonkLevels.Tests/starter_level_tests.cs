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
        var pool = new JsonArray(200f, 0f, -160f);
        if (field == "spawn") json["spawn"]!["position"] = pool;
        else json["playerStart"] = pool;
        var ex = Assert.ThrowsAny<ArgumentException>(() => LevelFileSerializer.DeserializeWithMigration(json.ToJsonString()));
        Assert.Contains("lava", ex.Message);
    }

    [Fact]
    public void StarterPlansHaveRoomForFiveMoaiAcrossSampledSeeds()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "../../../../../"));
        var level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(Path.Combine(root, "levels/bramblecrown-hill.mblevel.json")));
        for (var seed = 0; seed < 256; seed++)
        {
            var streams = new CustomRunRandom(seed);
            var plan = ExtraShrines.Plan(level, new[] { ExtraShrineKind.Charge, ExtraShrineKind.Magnet, ExtraShrineKind.Greed }, streams.ShrinePlan);
            var remaining = level.ShrineSpots.Select(p => new Vector3Data(p[0], p[1], p[2])).ToList();
            var placed = new List<(ExtraShrineKind Kind, Vector3Data Position)>();
            foreach (var kind in plan)
            {
                var guaranteed = ShrineGuarantees.CandidateIndexes(level.ShrineGuarantees, kind, remaining, placed);
                var allowed = (guaranteed ?? Enumerable.Range(0, remaining.Count).ToList())
                    .Where(i => ExtraShrines.SpotClear(kind, remaining[i], placed, level.ShrineKindSpacing)).ToList();
                var pick = ExtraShrines.PickSpread(allowed.Select(i => remaining[i]).ToList(), placed.Select(p => p.Position).ToList(), streams.ShrinePlacement);
                Assert.True(pick >= 0, $"No spot for {kind} in seed {seed}");
                var spot = remaining[allowed[pick]];
                placed.Add((kind, spot));
                remaining.RemoveAt(allowed[pick]);
            }
            Assert.Empty(ShrineGuarantees.Unmet(level.ShrineGuarantees, placed));
        }
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
        Assert.Equal(13, grid.Width);
        Assert.Equal(12, grid.Depth);
        var reachable = ReachabilityValidator.Validate(grid.ToLevelState(), (6, 1));
        Assert.Empty(reachable.Unreachable);
        Assert.Equal(156, reachable.Reachable.Count);
        foreach (var edit in level.Edits)
        {
            var placement = PlaceObject.FromEditOp(edit);
            var id = CatalogId.Parse(placement.CatalogId);
            Assert.Equal(CatalogNamespace.GameAsset, id.Namespace);
            CatalogRoute.Parse(id);
        }
    }
}
