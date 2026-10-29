namespace MegabonkLevels.Tests;

public class ThpsLevelTests
{
    private static string RepoFile(string relative)
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "Taskfile.yml")))
        {
            dir = dir.Parent;
        }

        return Path.Combine(dir!.FullName, relative);
    }

    private static LevelState Replay()
    {
        var level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(RepoFile("levels/thps.mblevel.json")));
        var stack = new EditStack(new LevelState());
        foreach (var op in level.Edits)
        {
            stack.Apply(op);
        }

        return stack.State;
    }

    [Fact]
    public void Level_LoadsAsForestStageZeroOnTheKnownSeed()
    {
        var level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(RepoFile("levels/thps.mblevel.json")));

        Assert.Equal(EMap.Forest, level.Map);
        Assert.Equal(0, level.StageIndex);
        Assert.Equal(20261007, level.Seed);
    }

    [Fact]
    public void Level_DisablesGrassBecauseItWouldGrowThroughTheWarehouseFloor()
    {
        var level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(RepoFile("levels/thps.mblevel.json")));

        Assert.True(level.NoGrass);
    }

    [Fact]
    public void Level_KeepsOnlyTheGeneratedSpawnCellTile()
    {
        var state = Replay();

        Assert.Single(state.Tiles);
        var kept = state.GetTile(10, 7);
        Assert.NotNull(kept);
        Assert.Equal(-1, kept!.Value.Height);
    }

    [Fact]
    public void Level_TheKeptTileIsReachableFromTheGeneratedSpawnCell()
    {
        var state = Replay();

        var result = ReachabilityValidator.Validate(state, (10, 7));

        Assert.True(result.IsReachable((10, 7)));
    }

    [Fact]
    public void Level_ArmsTheKillFloorBelowItsOnlyTile()
    {
        var level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(RepoFile("levels/thps.mblevel.json")));
        var keptLevel = Replay().GetTile(10, 7)!.Value.Height;

        Assert.NotNull(level.KillFloorY);
        Assert.True(level.KillFloorY < keptLevel * 20f, $"kill floor {level.KillFloorY} must sit below the kept tile at {keptLevel * 20f}");
    }

    [Fact]
    public void Level_StandsTheBossSpawnerOnTheWarehouseFloorNotInTheHangingBox()
    {
        var level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(RepoFile("levels/thps.mblevel.json")));
        var move = level.Edits.Single(e => e.OpType == MoveObject.OpType && e.Target == "gen:object:BossSpawner:0000");

        var placed = MoveObject.FromEditOp(move);
        Assert.True(
            placed.NewTransform.Position.Y is > -10f and < 10f,
            $"the boss spawner must stand on the arena floor, not in the box above the pipe (y={placed.NewTransform.Position.Y})");
        Assert.Contains("BottomPiece", placed.HiddenChildren);
        Assert.Contains("Collider", placed.HiddenChildren);
    }
}
