namespace MegabonkLevels.Tests;

public class EnemyPhysicsFreezePlanTests
{
    [Theory]
    [InlineData(true, false)]
    [InlineData(false, true)]
    public void ArmsFreeze_FollowsTheWireBoolInTheSameDirectionAsTheOtherControls(bool physicsEnabled, bool expected)
    {
        Assert.Equal(expected, EnemyPhysicsFreezePlan.ArmsFreeze(physicsEnabled));
    }

    [Fact]
    public void ToSetKinematic_TakesEveryDynamicBodyAndSkipsTheAlreadyKinematic()
    {
        var bodies = new (int, bool)[] { (1, false), (2, true), (3, false) };

        Assert.Equal(new[] { 1, 3 }, EnemyPhysicsFreezePlan.ToSetKinematic(bodies));
    }

    [Fact]
    public void ToSetKinematic_ReturnsNothingForAnEmptyCensus()
    {
        Assert.Empty(EnemyPhysicsFreezePlan.ToSetKinematic(System.Array.Empty<(int, bool)>()));
    }

    [Fact]
    public void ToSetKinematic_TakesABodyTheGameMadeDynamicAgainEvenIfWeHadFrozenIt()
    {
        Assert.Equal(new[] { 4 }, EnemyPhysicsFreezePlan.ToSetKinematic(new (int, bool)[] { (4, false) }));
    }

    [Fact]
    public void PriorValues_RemembersWhatEachFrozenBodyWasBeforeTheFreeze()
    {
        var census = new (int, bool)[] { (1, false), (2, true), (3, false) };

        var prior = EnemyPhysicsFreezePlan.PriorValues(census);

        Assert.Equal(2, prior.Count);
        Assert.False(prior[1]);
        Assert.False(prior[3]);
        Assert.False(prior.ContainsKey(2));
    }

    [Fact]
    public void PriorValues_IsEmptyWhenNothingNeedsChanging()
    {
        Assert.Empty(EnemyPhysicsFreezePlan.PriorValues(new (int, bool)[] { (1, true) }));
    }

    [Fact]
    public void Suppresses_NamesEveryThingBesidesTheSolverThatAGoneKinematicBodyLoses()
    {
        var suppresses = EnemyPhysicsFreezePlan.Suppresses;

        Assert.Contains(suppresses, line => line.Contains("solver"));
        Assert.Contains(suppresses, line => line.Contains("contact"));
        Assert.Contains(suppresses, line => line.Contains("broadphase"));
        Assert.Contains(suppresses, line => line.Contains("velocity"));
    }

    [Fact]
    public void FidelityNote_StatesWhatTheArmIsAndIsNotMeasuring()
    {
        var note = EnemyPhysicsFreezePlan.FidelityNote();

        Assert.Contains("not the solver alone", note);
        Assert.Contains("position sum", note);
    }
}
