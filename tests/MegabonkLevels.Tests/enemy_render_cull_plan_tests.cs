namespace MegabonkLevels.Tests;

public class EnemyRenderCullPlanTests
{
    [Fact]
    public void ShouldRescan_KeepsTheLastSweepWhilePopulationAndIntervalAreUnchanged()
    {
        Assert.False(EnemyRenderCullPlan.ShouldRescan(liveEnemies: 240, lastSeenEnemies: 240, nowSeconds: 10.0, lastScanSeconds: 9.5, intervalSeconds: 1.0));
    }

    [Fact]
    public void ShouldRescan_FiresWhenThePopulationMoved()
    {
        Assert.True(EnemyRenderCullPlan.ShouldRescan(liveEnemies: 241, lastSeenEnemies: 240, nowSeconds: 10.0, lastScanSeconds: 9.5, intervalSeconds: 1.0));
    }

    [Fact]
    public void ShouldRescan_FiresWhenTheIntervalElapsesEvenToTheExactSecond()
    {
        Assert.True(EnemyRenderCullPlan.ShouldRescan(liveEnemies: 240, lastSeenEnemies: 240, nowSeconds: 10.5, lastScanSeconds: 9.5, intervalSeconds: 1.0));
        Assert.True(EnemyRenderCullPlan.ShouldRescan(liveEnemies: 240, lastSeenEnemies: 240, nowSeconds: 10.0, lastScanSeconds: 9.0, intervalSeconds: 1.0));
    }

    [Fact]
    public void ToDisable_TakesEveryEnabledRendererAndSkipsTheAlreadyDisabled()
    {
        var renderers = new (int, bool)[] { (1, true), (2, false), (3, true) };

        var toDisable = EnemyRenderCullPlan.ToDisable(renderers);

        Assert.Equal(new[] { 1, 3 }, toDisable);
    }

    [Fact]
    public void ToDisable_ReturnsNothingForAnEmptyCensus()
    {
        Assert.Empty(EnemyRenderCullPlan.ToDisable(System.Array.Empty<(int, bool)>()));
    }

    [Fact]
    public void ToDisable_TakesARendererTheGameReEnabledEvenIfWeHadDisabledIt()
    {
        // The tracked/disabled distinction lives in the caller; anything enabled in this snapshot must go back off.
        var toDisable = EnemyRenderCullPlan.ToDisable(new (int, bool)[] { (1, true) });

        Assert.Equal(new[] { 1 }, toDisable);
    }

    [Fact]
    public void PositionSum_AddsEveryComponentOfEveryPosition()
    {
        var positions = new (float, float, float)[] { (1f, 2f, 3f), (4f, 5f, 6f) };

        Assert.Equal(21.0, EnemyRenderCullPlan.PositionSum(positions), 3);
    }

    [Fact]
    public void PositionSum_OfNoEnemiesIsZero()
    {
        Assert.Equal(0.0, EnemyRenderCullPlan.PositionSum(System.Array.Empty<(float, float, float)>()), 3);
    }
}
