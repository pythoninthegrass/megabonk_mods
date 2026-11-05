namespace MegabonkLevels.Tests;

public class EditorLoadPlanTests
{
    private static LevelFile Generated(int seed = 1, int tier = 0, int stage = 0, EMap map = EMap.Forest) => new(
        SchemaVersion: 4, GameBuildId: null, Map: map, StageIndex: stage, Tier: tier, Seed: seed,
        Packs: new Dictionary<string, string>(), Edits: Array.Empty<EditOp>());

    private static LevelFile FromScratch(int seed = 0) =>
        BlankLevel.Create(EMap.Forest, 0, 0, 5, 40f, null) with { Seed = seed };

    [Fact]
    public void GeneratedToMatchingGenerated_LoadsInPlace()
    {
        Assert.Equal(EditorLoadAction.InPlace, EditorLoadPlan.Decide(Generated(), Generated()));
    }

    [Theory]
    [InlineData(2, 0, 0, EMap.Forest)]
    [InlineData(1, 1, 0, EMap.Forest)]
    [InlineData(1, 0, 1, EMap.Forest)]
    [InlineData(1, 0, 0, EMap.Hell)]
    public void GeneratedToDifferentGenerated_IsRefused(int seed, int tier, int stage, EMap map)
    {
        Assert.Equal(EditorLoadAction.Refuse, EditorLoadPlan.Decide(Generated(), Generated(seed, tier, stage, map)));
    }

    [Fact]
    public void NoCurrentLevel_LoadsInPlace()
    {
        Assert.Equal(EditorLoadAction.InPlace, EditorLoadPlan.Decide(null, Generated()));
    }

    [Fact]
    public void ALoadedFromScratchLevel_StartsAFreshRunWhateverTheSeed()
    {
        Assert.Equal(EditorLoadAction.FreshRun, EditorLoadPlan.Decide(Generated(seed: 99), FromScratch(seed: 0)));
        Assert.Equal(EditorLoadAction.FreshRun, EditorLoadPlan.Decide(FromScratch(seed: 5), FromScratch(seed: 0)));
    }

    [Fact]
    public void LeavingAFromScratchLevelForAGeneratedOne_StartsAFreshRun()
    {
        Assert.Equal(EditorLoadAction.FreshRun, EditorLoadPlan.Decide(FromScratch(), Generated()));
    }
}
