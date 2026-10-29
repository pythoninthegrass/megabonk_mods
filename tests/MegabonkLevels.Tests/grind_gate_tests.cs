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
    public void AllowsStart_IsTrueWhereverTheGateIsNotInForce(bool customLevel, bool optIn, bool slideHeld)
    {
        Assert.True(GrindGate.AllowsStart(customLevel, optIn, slideHeld));
    }

    [Fact]
    public void AllowsStart_IsFalseOnAnOptedInCustomLevelWithSlideReleased()
    {
        Assert.False(GrindGate.AllowsStart(true, true, false));
    }

    [Fact]
    public void AllowsStart_IsTrueOnAnOptedInCustomLevelWithSlideHeld()
    {
        Assert.True(GrindGate.AllowsStart(true, true, true));
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
        // An unreachable Rewired must not make grinding impossible, so a failed read reports the button held.
        Assert.True(GrindGate.SlideHeldWhenReadFails);
        Assert.True(GrindGate.AllowsStart(true, true, GrindGate.SlideHeldWhenReadFails));
    }

    [Fact]
    public void SlideAction_IsTheGamesOwnSlideActionName()
    {
        Assert.Equal("Slide", GrindGate.SlideAction);
    }
}
