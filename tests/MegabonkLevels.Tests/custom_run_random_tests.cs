using MegabonkLevels;

namespace MegabonkLevels.Tests;

public class CustomRunRandomTests
{
    private static readonly string[] Pool = { "Ent1", "Ent2", "Pharaoh1", "Pharaoh2" };

    [Theory]
    [InlineData(0)]
    [InlineData(481)]
    [InlineData(-1)]
    public void SameSeedReproducesEachStream(int seed)
    {
        var a = new CustomRunRandom(seed);
        var b = new CustomRunRandom(seed);
        for (var i = 0; i < 50; i++)
        {
            Assert.Equal(a.ShrinePlan.Next(), b.ShrinePlan.Next());
            Assert.Equal(a.ShrinePlacement.Next(), b.ShrinePlacement.Next());
            Assert.Equal(a.PickBoss(Pool), b.PickBoss(Pool));
        }
    }

    [Fact]
    public void ConsumersDoNotPerturbOtherStreams()
    {
        var a = new CustomRunRandom(0);
        var b = new CustomRunRandom(0);
        for (var i = 0; i < 100; i++)
        {
            a.ShrinePlan.Next();
            a.ShrinePlacement.Next();
        }
        Assert.Equal(a.PickBoss(Pool), b.PickBoss(Pool));
        a.Reset(0);
        b.Reset(0);
        for (var i = 0; i < 100; i++) a.PickBoss(Pool);
        Assert.Equal(a.ShrinePlan.Next(), b.ShrinePlan.Next());
        Assert.Equal(a.ShrinePlacement.Next(), b.ShrinePlacement.Next());
        a.Reset(0);
        b.Reset(0);
        for (var i = 0; i < 100; i++) a.ShrinePlacement.Next();
        Assert.Equal(a.ShrinePlan.Next(), b.ShrinePlan.Next());
    }

    [Fact]
    public void ResetRewindsStreamsAndSharedUsedNames()
    {
        var run = new CustomRunRandom(0);
        var firstPlan = run.ShrinePlan.Next();
        var firstPlacement = run.ShrinePlacement.Next();
        var firstBoss = run.PickBoss(Pool);
        while (run.PickBoss(Pool) != null) { }
        run.Reset(0);
        Assert.Equal(firstPlan, run.ShrinePlan.Next());
        Assert.Equal(firstPlacement, run.ShrinePlacement.Next());
        Assert.Equal(firstBoss, run.PickBoss(Pool));
        run.Reset(481);
        var fresh = new CustomRunRandom(481);
        Assert.Equal(fresh.PickBoss(Pool), run.PickBoss(Pool));
    }

    [Fact]
    public void BossMinibossAndCurseCopyCallsShareCaseInsensitiveExhaustion()
    {
        var run = new CustomRunRandom(0);
        Assert.Equal("Ent1", run.PickBoss(new[] { "Ent1" }));
        Assert.Equal("MinibossPig", run.PickBoss(new[] { "ent1", "MinibossPig" }));
        Assert.Null(run.PickBoss(new[] { "ENT1" }));
        Assert.Null(run.PickBoss(new[] { "MinibossPig" }));
        Assert.Null(run.PickBoss(null));
    }

    [Fact]
    public void PhaseStreamsDiffer()
    {
        var run = new CustomRunRandom(0);
        Assert.NotEqual(run.ShrinePlan.Next(), run.ShrinePlacement.Next());
    }

    [Theory]
    [InlineData(0)]
    [InlineData(481)]
    public void ShrinePlanReproducesCountsKindsAndOrderBeforePlacement(int seed)
    {
        var settings = LevelFileSerializer.Deserialize("""
            {"schemaVersion":3,"map":1,"seed":0,"packs":{},"edits":[],
             "guaranteedShrineKinds":["charge","charge"],"extraShrines":2,"extraShrinesMax":3,
             "shrineKindRanges":{"moai":[3,4],"shadyGuy":[2,3]}}
            """);
        var a = new CustomRunRandom(seed);
        var b = new CustomRunRandom(seed);
        var kinds = new[] { ExtraShrineKind.Charge, ExtraShrineKind.Greed };
        var plan = ExtraShrines.Plan(settings, kinds, a.ShrinePlan);
        for (var i = 0; i < 200; i++) b.ShrinePlacement.Next();
        b.PickBoss(Pool);
        Assert.Equal(plan, ExtraShrines.Plan(settings, kinds, b.ShrinePlan));
        Assert.InRange(plan.Count, 9, 12);
        Assert.InRange(plan.Count(k => k == ExtraShrineKind.Moai), 3, 4);
        Assert.InRange(plan.Count(k => k == ExtraShrineKind.ShadyGuy), 2, 3);
        Assert.True(plan.Count(k => k == ExtraShrineKind.Charge) >= 2);
    }
}
