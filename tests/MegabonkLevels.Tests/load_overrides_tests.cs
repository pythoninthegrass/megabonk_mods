using System.Collections.Generic;

namespace MegabonkLevels.Tests;

public class LoadOverridesTests
{
    private static readonly LevelFile Level = new(
        LevelFile.CurrentSchemaVersion,
        "1",
        EMap.Forest,
        0,
        1,
        20261007,
        new Dictionary<string, string>(),
        new List<EditOp>());

    [Fact]
    public void Apply_WithNoOverrides_ReturnsTheLevelUnchanged()
    {
        Assert.Equal(Level, default(LoadOverrides).Apply(Level));
    }

    [Fact]
    public void Apply_ReplacesOnlyTheSuppliedFields()
    {
        var result = new LoadOverrides(Map: 64, Seed: 7).Apply(Level);

        Assert.Equal(Level with { Map = EMap.Hell, Seed = 7 }, result);
    }

    [Fact]
    public void Apply_ReplacesStageAndTier()
    {
        var result = new LoadOverrides(StageIndex: 2, Tier: 0).Apply(Level);

        Assert.Equal(2, result.StageIndex);
        Assert.Equal(0, result.Tier);
        Assert.Equal(Level.Map, result.Map);
    }

    [Fact]
    public void Apply_Unseeded_KeepsTheLevelsSeedInTheRecord()
    {
        var result = new LoadOverrides(Unseeded: true).Apply(Level);

        Assert.Equal(Level.Seed, result.Seed);
        Assert.True(new LoadOverrides(Unseeded: true).Unseeded);
    }

    [Fact]
    public void Apply_KeepsEdits()
    {
        var edited = Level with { Edits = new List<EditOp> { new("op", "t", "p") } };

        Assert.Equal(edited.Edits, new LoadOverrides(Map: 2).Apply(edited).Edits);
    }

    [Fact]
    public void TryParse_ReadsEachOptionalField()
    {
        var ok = HarnessCommand.TryParse("""{"command":"load-level","path":"a","map":64,"stageIndex":1,"tier":2,"seed":5}""", out var command, out var error);

        Assert.True(ok, error);
        Assert.Equal(new LoadOverrides(64, 1, 2, 5), command.Overrides);
    }

    [Fact]
    public void TryParse_WithoutOverrides_LeavesThemEmpty()
    {
        Assert.True(HarnessCommand.TryParse("""{"command":"load-level","path":"a"}""", out var command, out _));
        Assert.Equal(default, command.Overrides);
    }

    [Theory]
    [InlineData("""{"command":"load-level","path":"a","map":"forest"}""", "map")]
    [InlineData("""{"command":"load-level","path":"a","stageIndex":1.5}""", "stageIndex")]
    [InlineData("""{"command":"load-level","path":"a","tier":true}""", "tier")]
    [InlineData("""{"command":"load-level","path":"a","seed":"42"}""", "seed")]
    [InlineData("""{"command":"load-level","path":"a","map":3}""", "map")]
    public void TryParse_RejectsAnOverrideThatIsNotAnIntegerOrAKnownMap_NamingTheField(string json, string field)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains(field, error);
    }
}
