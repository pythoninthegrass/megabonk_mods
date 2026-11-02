using MegabonkLevels;

namespace MegabonkLevels.Tests;

public class InteractableRandomizationTests
{
    private static LevelFile Level() => LevelFileSerializer.Deserialize("""{"schemaVersion":3,"map":1,"seed":20261007,"packs":{},"edits":[]}""");

    [Theory]
    [InlineData(RandomizedInteractableKind.ShadyGuy, 0, 1, 0)]
    [InlineData(RandomizedInteractableKind.Chest, 0, 0, 1)]
    [InlineData(RandomizedInteractableKind.Moai, 0, 0, 1)]
    public void UprightAxisComesFromTheNativeModelNotTheSourceGround(RandomizedInteractableKind kind, float x, float y, float z)
    {
        Assert.Equal(new Vector3Data(x, y, z), InteractableRandomization.LocalUp(kind));
    }

    [Theory]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    public void OldLevelsDefaultToUnchangedPlacement(int version)
    {
        var level = LevelFileSerializer.DeserializeWithMigration($$"""{"schemaVersion":{{version}},"map":1,"seed":20261007,"packs":{},"edits":[]}""");
        Assert.False(level.RandomizeShadyGuy);
        Assert.False(level.RandomizeChests);
        Assert.False(level.RandomizeMoai);
        foreach (var kind in Enum.GetValues<RandomizedInteractableKind>())
            Assert.False(InteractableRandomization.ShouldMove(level, kind, "chest:0000", level.Edits));
    }

    [Theory]
    [InlineData("randomizeShadyGuy", RandomizedInteractableKind.ShadyGuy)]
    [InlineData("randomizeChests", RandomizedInteractableKind.Chest)]
    [InlineData("randomizeMoai", RandomizedInteractableKind.Moai)]
    public void SettingsRoundTripIndependentlyAndSurviveSaveCopy(string field, RandomizedInteractableKind selected)
    {
        var original = Level();
        var changed = LevelSettings.Change(original, field, "true");
        Assert.NotEqual(original, changed);
        Assert.Equal(changed, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(changed)));
        Assert.Equal(changed, LevelSettings.CopyTo(changed, original));
        Assert.Equal("true", LevelSettings.Read(changed, field));
        foreach (var kind in Enum.GetValues<RandomizedInteractableKind>())
            Assert.Equal(kind == selected, InteractableRandomization.ShouldMove(changed, kind, "chest:0000", changed.Edits));

        var history = new LevelSettingsHistory(original);
        history.Apply(field, "true", hasEdits: true);
        Assert.True(history.Dirty);
        Assert.True(history.Undo());
        Assert.Equal(original, history.Current);
        Assert.True(history.Redo());
        Assert.Equal(changed, history.Current);
        Assert.Equal(original, LevelSettings.Change(changed, field, "false"));
        Assert.ThrowsAny<ArgumentException>(() => LevelSettings.Change(original, field, "1"));
    }

    [Fact]
    public void AuthoredMovesAndRemovalsPinOnlyTheirOwnGeneratedTargets()
    {
        var level = Level() with { RandomizeChests = true };
        var edits = new[]
        {
            new EditOp(MoveObject.OpType, "gen:chest:0000", "{}"),
            new EditOp(RemoveObject.OpType, "gen:chest:0001", "{}"),
            new EditOp(PlaceObject.OpType, "", "{}"),
            new EditOp(MoveObject.OpType, "placement:0", "{}"),
        };
        Assert.False(InteractableRandomization.ShouldMove(level, RandomizedInteractableKind.Chest, "chest:0000", edits));
        Assert.False(InteractableRandomization.ShouldMove(level, RandomizedInteractableKind.Chest, "chest:0001", edits));
        Assert.True(InteractableRandomization.ShouldMove(level, RandomizedInteractableKind.Chest, "chest:0002", edits));
    }

    [Fact]
    public void CandidateSearchRejectsOccupiedSpotsWithoutRepeatingAndStopsAtBudget()
    {
        var visited = new List<int>();
        Assert.True(InteractableRandomization.TryChoose(new[] { 1, 2, 3 }, _ => 0,
            item => { visited.Add(item); return item == 3; }, 3, out var result));
        Assert.Equal(3, result);
        Assert.Equal(new[] { 1, 2, 3 }, visited);
        visited.Clear();
        Assert.False(InteractableRandomization.TryChoose(new[] { 1, 2, 3 }, _ => 0,
            item => { visited.Add(item); return false; }, 2, out _));
        Assert.Equal(new[] { 1, 2 }, visited);
    }

    [Fact]
    public void EmptyOrZeroBudgetSearchNeverCallsRandomOrValidation()
    {
        int Next(int _) => throw new Exception("Unexpected random draw");
        bool Valid(int _) => throw new Exception("Unexpected validation");
        Assert.False(InteractableRandomization.TryChoose(Array.Empty<int>(), Next, Valid, 10, out _));
        Assert.False(InteractableRandomization.TryChoose(new[] { 1 }, Next, Valid, 0, out _));
    }

    [Fact]
    public void WalkableSamplesCanRouteAroundBlockedTileCentersButNotThroughWallsOrHoles()
    {
        var samples = new Dictionary<(int X, int Z), int>
        {
            [(0, 0)] = 0, [(0, 1)] = 1, [(1, 1)] = 2, [(2, 1)] = 3, [(2, 0)] = 4,
            [(3, 0)] = 5, [(5, 0)] = 6,
        };
        var reachable = InteractableRandomization.ReachableSamples(samples, (0, 0), (a, b) => a != 5 && b != 5);
        Assert.Equal(5, reachable.Count);
        Assert.Contains((2, 0), reachable);
        Assert.DoesNotContain((3, 0), reachable);
        Assert.DoesNotContain((5, 0), reachable);
        Assert.Empty(InteractableRandomization.ReachableSamples(samples, (4, 0), (_, _) => true));
    }
}
