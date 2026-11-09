namespace MegabonkLevels.Tests;

public class EnemyControlPlanTests
{
    [Theory]
    [InlineData(true, false)]
    [InlineData(false, true)]
    public void ArmsControl_ArmsOnTheOppositeSenseOfTheWireBool(bool enabledWanted, bool expected)
    {
        Assert.Equal(expected, EnemyControlPlan.ArmsControl(enabledWanted));
    }

    [Fact]
    public void ShouldRescan_KeepsTheLastSweepWhilePopulationAndIntervalAreUnchanged()
    {
        Assert.False(EnemyControlPlan.ShouldRescan(240, 240, 10.0, 9.5, 1.0));
    }

    [Fact]
    public void ShouldRescan_FiresWhenThePopulationMoved()
    {
        Assert.True(EnemyControlPlan.ShouldRescan(241, 240, 10.0, 9.5, 1.0));
    }

    [Fact]
    public void ShouldRescan_FiresWhenTheIntervalElapsesEvenToTheExactSecond()
    {
        Assert.True(EnemyControlPlan.ShouldRescan(240, 240, 10.5, 9.5, 1.0));
        Assert.True(EnemyControlPlan.ShouldRescan(240, 240, 10.0, 9.0, 1.0));
    }

    [Fact]
    public void ShouldRescan_FiresTheFirstTimeAnythingIsSeen()
    {
        Assert.True(EnemyControlPlan.ShouldRescan(0, -1, 0.0, double.NegativeInfinity, 0.5));
    }

    [Fact]
    public void TheRescanIntervalIsTheOneTheRenderCullSweepsOn()
    {
        Assert.Equal(0.5, EnemyControlPlan.RescanIntervalSeconds);
    }
}
