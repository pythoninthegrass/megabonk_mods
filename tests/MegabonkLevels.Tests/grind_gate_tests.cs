namespace MegabonkLevels.Tests;

public class GrindGateTests
{
    [Theory]
    // A level without the key grinds on touch, held or not, which is the game's own behaviour.
    [InlineData(true, false, false)]
    [InlineData(true, false, true)]
    // A run the mod did not load keeps the game's behaviour whatever the level file says.
    [InlineData(false, true, false)]
    [InlineData(false, false, false)]
    public void AllowsGrind_IsTrueWhereverTheGateIsNotInForce(bool customLevel, bool optIn, bool slideHeld)
    {
        Assert.True(GrindGate.AllowsGrind(customLevel, optIn, slideHeld));
    }

    [Fact]
    // The same answer covers the touch that starts a grind, the joint that would carry it on, and staying on the rail at
    // all, so a released button comes the player off the rail instead of leaving them riding to the next junction.
    public void AllowsGrind_IsFalseOnAnOptedInCustomLevelWithSlideReleased()
    {
        Assert.False(GrindGate.AllowsGrind(true, true, false));
    }

    [Fact]
    // Held, the grind runs and chains through junctions for as long as the button is down.
    public void AllowsGrind_IsTrueOnAnOptedInCustomLevelWithSlideHeld()
    {
        Assert.True(GrindGate.AllowsGrind(true, true, true));
    }

    [Theory]
    [InlineData(true, true, true)]
    [InlineData(true, false, false)]
    [InlineData(false, true, false)]
    [InlineData(false, false, false)]
    public void UsesGate_IsTrueOnlyForAnOptedInCustomLevel(bool customLevel, bool optIn, bool expected)
    {
        Assert.Equal(expected, GrindGate.UsesGate(customLevel, optIn));
    }

    [Fact]
    public void FailedSlideRead_LeavesTheGameToItself()
    {
        // An unreachable Rewired must not make grinding impossible, and must not throw the player off a running grind,
        // so a failed read reports the button held.
        Assert.True(GrindGate.SlideHeldWhenReadFails);
        Assert.True(GrindGate.AllowsGrind(true, true, GrindGate.SlideHeldWhenReadFails));
    }

    [Fact]
    public void SlideAction_IsTheGamesOwnSlideActionName()
    {
        Assert.Equal("Slide", GrindGate.SlideAction);
    }
}
