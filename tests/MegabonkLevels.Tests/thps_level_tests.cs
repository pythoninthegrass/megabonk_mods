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
    public void Level_EveryArenaTileIsReachableFromTheGeneratedSpawnCell()
    {
        var state = Replay();

        var result = ReachabilityValidator.Validate(state, (10, 7));

        for (var x = 8; x <= 10; x++)
        {
            for (var z = 4; z <= 7; z++)
            {
                Assert.True(result.IsReachable((x, z)), $"arena tile ({x},{z}) is unreachable");
            }
        }
    }

    [Fact]
    public void Level_OnlyTheArenaAndItsWallRingRemain()
    {
        var state = Replay();

        Assert.Equal(5 * 6, state.Tiles.Count);
    }
}
