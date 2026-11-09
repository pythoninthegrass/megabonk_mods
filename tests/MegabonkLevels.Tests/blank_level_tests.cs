namespace MegabonkLevels.Tests;

public class BlankLevelTests
{
    private static LevelFile Blank(int size = 7, float spacing = 40f) =>
        BlankLevel.Create(EMap.Forest, stageIndex: 1, tier: 2, size, spacing, "build-1");

    [Fact]
    public void Create_IsAFromScratchLevelForTheGivenMapStageAndTier()
    {
        var level = Blank();

        Assert.True(level.IsFromScratch);
        Assert.Equal(EMap.Forest, level.Map);
        Assert.Equal(1, level.StageIndex);
        Assert.Equal(2, level.Tier);
        Assert.Equal("build-1", level.GameBuildId);
        Assert.Equal(LevelFile.CurrentSchemaVersion, level.SchemaVersion);
        Assert.Empty(level.Edits);
    }

    [Fact]
    public void Create_BuildsAFlatSquareGridOfEveryCell()
    {
        var grid = Blank(5).Grid!.Value;

        Assert.Equal(5, grid.Width);
        Assert.Equal(5, grid.Depth);
        Assert.Equal(25, grid.Cells.Count);
        Assert.All(grid.Cells, cell => Assert.Equal(new AuthoredCell(cell.X, cell.Z, 0), cell));
    }

    [Fact]
    public void Create_PutsTheSpawnAtTheCentreCellAndTheBossSpawnerTwoCellsEast()
    {
        var level = Blank(7, 40f);

        Assert.Equal(new[] { 0f, 2f, 0f }, level.Spawn!.Value.Position);
        Assert.Equal(new[] { 80f, 0f, 0f }, level.BossSpawner!.Value.Position);
    }

    [Fact]
    public void Create_KeepsTheBossSpawnerOnTheGridForASmallGrid()
    {
        var level = Blank(3, 40f);

        var boss = PositionReadout.CellOf(level.BossSpawner!.Value.Position[0], level.BossSpawner!.Value.Position[2], 3, 3, 40f);
        Assert.True(boss.InGrid);
        Assert.NotEqual((1, 1), (boss.X, boss.Z));
    }

    [Fact]
    public void Create_ProducesAFileThatPassesValidation()
    {
        var level = Blank();

        LevelFileValidator.Validate(level);
    }

    [Theory]
    [InlineData(2)]
    [InlineData(0)]
    [InlineData(-4)]
    public void Create_RefusesAGridTooSmallForASpawnAndABossSpawner(int size)
    {
        Assert.Throws<ArgumentException>(() => Blank(size));
    }
}
