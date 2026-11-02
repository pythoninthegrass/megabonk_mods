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
    public void Level_RequiresTheSlideButtonToStartAGrind()
    {
        var level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(RepoFile("levels/thps.mblevel.json")));

        // The coping is a rail along every lip, so a grind that starts on contact takes over each ride over a lip.
        Assert.True(level.GrindRequiresSlide);
    }

    [Fact]
    public void Level_ScoresFallDamageWithTonyMcZoom()
    {
        var level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(RepoFile("levels/thps.mblevel.json")));

        // Calcium carries no FallDamageReduction, so the drop off a half pipe lip would otherwise empty his health bar.
        Assert.Equal(CharacterOverride.TonyMcZoomId, FallDamagePolicy.ReferenceCharacter(level.FallDamageCharacter));
        Assert.True(FallDamagePolicy.Applies(true, FallDamagePolicy.ReferenceCharacter(level.FallDamageCharacter), CharacterOverride.CalciumId));
    }

    [Fact]
    public void Level_StandsTheBossPortalOnTheFloorInsideTheGlassBox()
    {
        var level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(RepoFile("levels/thps.mblevel.json")));
        var move = level.Edits.Single(e => e.OpType == MoveObject.OpType && e.Target == "gen:object:BossSpawner:0000");
        var placed = MoveObject.FromEditOp(move);
        var (x, y, z) = (placed.NewTransform.Position.X, placed.NewTransform.Position.Y, placed.NewTransform.Position.Z);

        // The box is a closed room above the pipe: interior floor at 15.64, roof underside at 25.42, walls at
        // x 149.4/178.9 and z 20.9/31.4. Standing on the roof would leave the portal outside it.
        Assert.True(
            y >= 15.5f && y < 25.42f,
            $"the boss portal must stand on the floor inside the hanging box, not on its roof (y={y})");
        Assert.InRange(x, 150.4f, 177.9f);
        Assert.InRange(z, 21.9f, 30.4f);
        Assert.Contains("BottomPiece", placed.HiddenChildren);
        Assert.Contains("Collider", placed.HiddenChildren);
    }

    [Fact]
    public void Level_SendsTheBossToTheGroundOutsideTheBox()
    {
        var level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(RepoFile("levels/thps.mblevel.json")));

        Assert.NotNull(level.BossSpawnPosition);
        var (x, y, z) = (level.BossSpawnPosition[0], level.BossSpawnPosition[1], level.BossSpawnPosition[2]);
        Assert.True(y < 15.31f, $"the boss must spawn below the hanging box's floor slab, not inside it (y={y})");
        Assert.True(y > level.KillFloorY, $"the boss must spawn above the kill floor at {level.KillFloorY}");
        // In the open on the pipe floor: same x column as the portal, south of the box's near wall.
        Assert.InRange(x, 149.4f, 178.9f);
        Assert.True(z is > 14f and < 20.9f, $"the boss must come out clear of the box, on the pipe floor (z={z})");
    }
}
