namespace MegabonkLevels.Tests;

public class GrindAssistTests
{
    [Theory]
    // A level without the key, or a run the mod did not load, keeps the game's catch and nothing else.
    [InlineData(true, false, true, false)]
    [InlineData(false, true, true, false)]
    [InlineData(false, false, true, false)]
    // Released there is no intent to help, and on a rail already the game is doing it itself.
    [InlineData(true, true, false, false)]
    [InlineData(true, true, true, true)]
    public void Assists_IsTrueOnlyForAGatedLevelWithTheButtonHeldOffARail(
        bool customLevel, bool optIn, bool slideHeld, bool grinding)
    {
        Assert.False(GrindAssist.Assists(customLevel, optIn, slideHeld, grinding));
    }

    [Fact]
    public void Assists_IsTrueOnAnOptedInCustomLevelWithTheButtonHeldOffARail()
    {
        Assert.True(GrindAssist.Assists(true, true, true, false));
    }

    [Theory]
    // The bar sits at the player's feet when they are stood on a coping, and just under them on a lip.
    [InlineData(0f)]
    [InlineData(-0.6f)]
    [InlineData(-3f)]
    [InlineData(GrindAssist.CatchRiseAboveFeet)]
    public void WithinBand_AcceptsABarAtOrBelowTheFeet(float railHeightOverFeet)
    {
        Assert.True(GrindAssist.WithinBand(railHeightOverFeet, 0f));
    }

    [Theory]
    // A bar well above the feet is a rail the player is passing under, not one to be pulled onto.
    [InlineData(1.5f)]
    [InlineData(4f)]
    public void WithinBand_RefusesABarHighAboveTheFeet(float railHeightOverFeet)
    {
        Assert.False(GrindAssist.WithinBand(railHeightOverFeet, 0f));
    }

    [Fact]
    public void TheCatchReachesFurtherThanTheGamesContactButNoFurtherThanAHandoff()
    {
        Assert.InRange(GrindAssist.CatchRadius, 0.5f, RailHandoff.SearchRadius);
    }

    [Fact]
    public void PickNearest_UsesTheRadiusItIsGiven()
    {
        var distances = new[] { 1.2f, 2.4f };
        var onCooldown = new[] { false, false };

        Assert.Equal(0, RailHandoff.PickNearest(distances, onCooldown, 1.5f));
        Assert.Equal(1, RailHandoff.PickNearest(new[] { 1.2f, 2.4f }, new[] { true, false }, 3.5f));
        Assert.Equal(-1, RailHandoff.PickNearest(distances, onCooldown, 1f));
        Assert.Equal(-1, RailHandoff.PickNearest(distances, onCooldown, 0.5f));
    }

    [Fact]
    public void PickNearest_WithARadiusStillSkipsRailsOnCooldown()
    {
        Assert.Equal(1, RailHandoff.PickNearest(new[] { 0.2f, 1.8f }, new[] { true, false }, 3.5f));
    }

    [Theory]
    // Caught near the far end, the grind would stop at once, so it is started back the way it came.
    [InlineData(0.92f, -1f)]
    [InlineData(0.05f, 1f)]
    public void DirectionForFreshCatch_RunsAwayFromAnEndItLandsNear(float progress, float expected)
    {
        Assert.Equal(expected, RailHandoff.DirectionForFreshCatch(progress) ?? 0f);
    }

    [Theory]
    // Caught in the middle of a rail the game's own direction is kept.
    [InlineData(0.3f)]
    [InlineData(0.5f)]
    [InlineData(0.7f)]
    public void DirectionForFreshCatch_LeavesTheGameToItselfAwayFromTheEnds(float progress)
    {
        Assert.Null(RailHandoff.DirectionForFreshCatch(progress));
    }
}
