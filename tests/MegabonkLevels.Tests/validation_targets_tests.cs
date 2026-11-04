namespace MegabonkLevels.Tests;

public class ValidationTargetsTests
{
    private const int Width = 4;
    private const int Depth = 3;
    private const float Spacing = 1f;

    private static LevelFile Level(string baseline, SpawnPoint? spawn = null, SpawnPoint? boss = null) => new(
        SchemaVersion: 4, GameBuildId: null, Map: default, StageIndex: 0, Tier: 0, Seed: 0,
        Packs: new Dictionary<string, string>(), Edits: Array.Empty<EditOp>(),
        Baseline: baseline, Spawn: spawn, BossSpawner: boss);

    private static SpawnPoint At(float x, float y, float z) => new(new[] { x, y, z }, new[] { 0f, 0f, 0f });

    private static LevelState Tiles(params (int X, int Z)[] cells) =>
        LevelState.FromTiles(cells.Select(c => KeyValuePair.Create(c, new TileState(0, SlopeDirection.None))));

    private static LevelState WithObject(LevelState state, float x, float z)
    {
        new EditStack(state).Apply(new PlaceObject("bundle:thps/rail", new Vector3Data(x, 0, z), default, new Vector3Data(1, 1, 1)).ToEditOp());
        return state;
    }

    [Fact]
    public void FromScratch_StartsFromTheAuthoredSpawnCell()
    {
        var level = Level(LevelFile.NoBaseline, spawn: At(-2f, 2f, -1f), boss: At(0f, 2f, 0f));

        var targets = ValidationTargetSelector.Select(level, Tiles((0, 0), (2, 1)), Width, Depth, Spacing);

        Assert.Equal(ValidationTargetSource.AuthoredLevel, targets.Source);
        Assert.Equal((0, 0), targets.Start);
        Assert.Equal((2, 1), targets.Boss);
    }

    [Fact]
    public void FromScratch_SpawnOutsideTheGridHasNoStart()
    {
        var level = Level(LevelFile.NoBaseline, spawn: At(50f, 2f, 0f), boss: At(0f, 2f, 0f));

        var targets = ValidationTargetSelector.Select(level, Tiles((2, 1)), Width, Depth, Spacing);

        Assert.Null(targets.Start);
    }

    [Fact]
    public void GeneratedBaseline_DefersToTheNameSearch()
    {
        var level = Level(LevelFile.GeneratedBaseline, spawn: At(0f, 0f, 0f), boss: At(1f, 0f, 0f));

        var targets = ValidationTargetSelector.Select(level, Tiles((0, 0)), Width, Depth, Spacing);

        Assert.Equal(ValidationTargetSource.NameSearch, targets.Source);
        Assert.Null(targets.Start);
        Assert.Null(targets.Boss);
        Assert.Null(targets.Warning);
    }

    [Fact]
    public void LevelWithoutABaselineField_DefersToTheNameSearch()
    {
        var targets = ValidationTargetSelector.Select(Level(null), Tiles((0, 0)), Width, Depth, Spacing);

        Assert.Equal(ValidationTargetSource.NameSearch, targets.Source);
    }

    [Fact]
    public void BossSpawnerOverATile_HasNoWarning()
    {
        var level = Level(LevelFile.NoBaseline, spawn: At(-2f, 2f, -1f), boss: At(0f, 2f, 0f));

        var targets = ValidationTargetSelector.Select(level, Tiles((0, 0), (2, 1)), Width, Depth, Spacing);

        Assert.Null(targets.Warning);
    }

    [Fact]
    public void BossSpawnerOverAnEmptyCell_WarnsWhenNothingIsPlacedThere()
    {
        var level = Level(LevelFile.NoBaseline, spawn: At(-2f, 2f, -1f), boss: At(0f, 2f, 0f));

        var targets = ValidationTargetSelector.Select(level, Tiles((0, 0)), Width, Depth, Spacing);

        Assert.Equal((2, 1), targets.Boss);
        Assert.Contains("boss spawner", targets.Warning);
    }

    [Fact]
    public void BossSpawnerOverAnEmptyCell_NoWarningWhenAPlacedObjectSitsInThatCell()
    {
        var level = Level(LevelFile.NoBaseline, spawn: At(-2f, 2f, -1f), boss: At(0f, 2f, 0f));
        var state = WithObject(Tiles((0, 0)), 0.2f, 0.1f);

        var targets = ValidationTargetSelector.Select(level, state, Width, Depth, Spacing);

        Assert.Null(targets.Warning);
    }

    [Fact]
    public void BossSpawnerOverAnEmptyCell_WarnsWhenTheOnlyPlacedObjectIsInAnotherCell()
    {
        var level = Level(LevelFile.NoBaseline, spawn: At(-2f, 2f, -1f), boss: At(0f, 2f, 0f));
        var state = WithObject(Tiles((0, 0)), -2f, -1f);

        var targets = ValidationTargetSelector.Select(level, state, Width, Depth, Spacing);

        Assert.NotNull(targets.Warning);
    }
}
