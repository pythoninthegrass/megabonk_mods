namespace MegabonkLevels.Tests;

public class RailHandoffTests
{
    [Theory]
    [InlineData(1f)]
    [InlineData(0f)]
    public void ReachedEnd_IsTrueAtEitherEndOfTheSpline(float progress)
    {
        Assert.True(RailHandoff.ReachedEnd(progress));
    }

    [Theory]
    [InlineData(0.01f)]
    [InlineData(0.5f)]
    [InlineData(0.99f)]
    public void ReachedEnd_IsFalseInsideTheSpline(float progress)
    {
        Assert.False(RailHandoff.ReachedEnd(progress));
    }

    [Fact]
    public void PickNearest_ReturnsTheClosestRailInRange()
    {
        var pick = RailHandoff.PickNearest(new[] { 1.5f, 0.4f, 0.9f }, new[] { false, false, false });

        Assert.Equal(1, pick);
    }

    [Fact]
    public void PickNearest_SkipsRailsOnCooldown()
    {
        var pick = RailHandoff.PickNearest(new[] { 0.1f, 0.9f }, new[] { true, false });

        Assert.Equal(1, pick);
    }

    [Fact]
    public void PickNearest_IgnoresRailsBeyondTheSearchRadius()
    {
        var pick = RailHandoff.PickNearest(new[] { RailHandoff.SearchRadius + 0.1f }, new[] { false });

        Assert.Equal(-1, pick);
    }

    [Fact]
    public void PickNearest_NothingNearby_ReturnsMinusOne()
    {
        Assert.Equal(-1, RailHandoff.PickNearest(Array.Empty<float>(), Array.Empty<bool>()));
    }
}
