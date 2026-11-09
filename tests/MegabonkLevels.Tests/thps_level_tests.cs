namespace MegabonkLevels.Tests;

public class ThpsLevelTests
{
    private static string RepoFile(string relative)
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "taskfile.yml")))
        {
            dir = dir.Parent;
        }

        return Path.Combine(dir!.FullName, relative);
    }

    private static LevelFile Read() => LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(RepoFile("levels/thps.mblevel.json")));

    [Fact]
    public void Level_IsAFromScratchForestStageZeroLevel()
    {
        var level = Read();

        Assert.True(level.IsFromScratch);
        Assert.Equal(EMap.Forest, level.Map);
        Assert.Equal(0, level.StageIndex);
        Assert.All(level.Edits, op => Assert.Equal(PlaceObject.OpType, op.OpType));
    }

    [Fact]
    public void Level_DisablesGrassBecauseItWouldGrowThroughTheWarehouseFloor()
    {
        var level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(RepoFile("levels/thps.mblevel.json")));

        Assert.True(level.NoGrass);
    }

    [Fact]
    public void Level_KeepsOneHiddenFloorTileSoTheGameCanDeriveItsCatchFloor()
    {
        var floor = Assert.Single(Read().Grid!.Value.Cells);

        Assert.Equal(new AuthoredCell(10, 7, -2), floor);
    }

    [Fact]
    public void Level_AuthorsAKillFloorTheGameDoesNotRaise()
    {
        var level = Read();
        var catchFloor = (level.Grid!.Value.Cells.Min(cell => cell.Height) - 1) * 20f;

        // The game raises a kill floor to at least 8 above its catch floor, so a lower catch floor keeps the authored value.
        Assert.NotNull(level.KillFloorY);
        Assert.True(level.KillFloorY >= catchFloor + 8f, $"kill floor {level.KillFloorY} would be raised above the catch floor {catchFloor}");
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
        var spawner = Read().BossSpawner!.Value;
        var (x, y, z) = (spawner.Position[0], spawner.Position[1], spawner.Position[2]);

        // The box is a closed room above the pipe: interior floor at 15.64, roof underside at 25.42, walls at
        // x 149.4/178.9 and z 20.9/31.4. Standing on the roof would leave the portal outside it.
        Assert.True(
            y >= 15.5f && y < 25.42f,
            $"the boss portal must stand on the floor inside the hanging box, not on its roof (y={y})");
        Assert.InRange(x, 150.4f, 177.9f);
        Assert.InRange(z, 21.9f, 30.4f);
        Assert.Equal(new[] { 0.4f, 0.4f, 0.4f }, spawner.Scale);
        Assert.Contains("BottomPiece", spawner.HiddenChildren);
        Assert.Contains("Collider", spawner.HiddenChildren);
    }

    [Fact]
    public void Level_MovesTheBossOutOfTheBoxBecauseItsPortalStandsInsideOne()
    {
        Assert.True(Read().BossRedirect);
    }
}
