namespace MegabonkLevels.Tests;

public class EnemyAnimationCullPlanTests
{
    [Theory]
    [InlineData(true, false)]
    [InlineData(false, true)]
    public void ArmsCull_FollowsTheWireBoolInTheSameDirectionAsTheOtherControls(bool animationEnabled, bool expected)
    {
        Assert.Equal(expected, EnemyAnimationCullPlan.ArmsCull(animationEnabled));
    }

    [Fact]
    public void ToDisable_TakesEveryEnabledBehaviourAndSkipsTheAlreadyDisabled()
    {
        var behaviours = new (int, bool)[] { (1, true), (2, false), (3, true) };

        Assert.Equal(new[] { 1, 3 }, EnemyAnimationCullPlan.ToDisable(behaviours));
    }

    [Fact]
    public void ToDisable_ReturnsNothingForAnEmptyCensus()
    {
        Assert.Empty(EnemyAnimationCullPlan.ToDisable(System.Array.Empty<(int, bool)>()));
    }

    [Fact]
    public void ToDisable_TakesAComponentTheGameReEnabledEvenIfWeHadStoppedIt()
    {
        Assert.Equal(new[] { 7 }, EnemyAnimationCullPlan.ToDisable(new (int, bool)[] { (7, true) }));
    }

    [Fact]
    public void CountsByType_CountsOnlyWhatTheCullActuallyStopped()
    {
        var census = new (string, bool)[]
        {
            ("AnimatedMesh", true),
            ("AnimatedMesh", false),
            ("Animator", true),
            ("AnimatedMesh", true),
        };

        var counts = EnemyAnimationCullPlan.CountsByType(census);

        Assert.Equal(2, counts.Count);
        Assert.Equal(2, counts["AnimatedMesh"]);
        Assert.Equal(1, counts["Animator"]);
    }

    [Fact]
    public void CountsByType_IsEmptyWhenTheCullStoppedNothing()
    {
        Assert.Empty(EnemyAnimationCullPlan.CountsByType(new (string, bool)[] { ("Animator", false) }));
    }

    [Fact]
    public void Suppresses_NamesTheAnimationUpdatesAndWhatTheyDrive()
    {
        var suppresses = EnemyAnimationCullPlan.Suppresses;

        Assert.Contains(suppresses, line => line.Contains("AnimatedMesh"));
        Assert.Contains(suppresses, line => line.Contains("Animator"));
        Assert.Contains(suppresses, line => line.Contains("reach"));
    }

    [Fact]
    public void FidelityNote_SaysRenderersAndPhysicsKeepRunningAndWhereToCheckTheConfound()
    {
        var note = EnemyAnimationCullPlan.FidelityNote();

        Assert.Contains("renderers", note);
        Assert.Contains("position sum", note);
    }
}
