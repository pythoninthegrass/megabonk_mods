namespace MegabonkLevels.Tests;

public class CustomTierCapTests
{
    [Theory]
    [InlineData(0, 0)]
    [InlineData(1, 0)]
    [InlineData(2, 0)]
    [InlineData(int.MaxValue, 0)]
    public void Clamp_NeverExceedsTheFirstTier(int tier, int expected)
    {
        Assert.Equal(expected, CustomTierCap.Clamp(tier));
    }

    [Theory]
    [InlineData(0, false)]
    [InlineData(1, true)]
    [InlineData(2, true)]
    public void IsCapped_ReportsWhetherClampChangesTheTier(int tier, bool expected)
    {
        Assert.Equal(expected, CustomTierCap.IsCapped(tier));
    }
}
