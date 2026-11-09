using MegabonkLevels;

namespace MegabonkLevels.Tests;

public class MaximinTests
{
    private static float Gap(float a, float b) => MathF.Abs(a - b);

    [Fact]
    public void PicksTheCandidateFarthestFromItsNearestTakenSpot()
    {
        Assert.True(Maximin.Pick(new[] { 1f, 9f, 6f }, new[] { 0f, 10f }, Gap, out var spot));
        Assert.Equal(6f, spot);
    }

    [Fact]
    public void TakesTheFirstCandidateWhenNothingIsTakenYet()
    {
        Assert.True(Maximin.Pick(new[] { 3f, 8f }, Array.Empty<float>(), Gap, out var spot));
        Assert.Equal(3f, spot);
    }

    [Fact]
    public void FailsWhenThereAreNoCandidates()
    {
        Assert.False(Maximin.Pick(Array.Empty<float>(), new[] { 1f }, Gap, out _));
    }
}
