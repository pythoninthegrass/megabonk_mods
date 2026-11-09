namespace MegabonkLevels.Tests;

public class MenuBackoutTests
{
    [Theory]
    [InlineData(false, false, false, false)]
    [InlineData(true, false, false, true)]
    [InlineData(false, true, false, true)]
    [InlineData(true, true, false, true)]
    [InlineData(false, false, true, false)]
    [InlineData(true, false, true, false)]
    [InlineData(false, true, true, false)]
    [InlineData(true, true, true, false)]
    public void CancelOnlyPendingSetupUnlessMovingForwardToMaps(
        bool held, bool restricted, bool movingToMaps, bool expected)
    {
        Assert.Equal(expected, MenuBackout.ShouldCancel(held, restricted, movingToMaps));
    }

    [Fact]
    public void ConfirmCharacterPreservesHoldButBackingOutOfMapsCancelsIt()
    {
        Assert.False(MenuBackout.ShouldCancel(true, true, movingToMaps: true));
        Assert.True(MenuBackout.ShouldCancel(true, true, movingToMaps: false));
    }

    [Fact]
    public void SuccessfulStartLeavesNothingForDisableToCancel()
    {
        Assert.False(MenuBackout.ShouldCancel(false, false, movingToMaps: false));
    }
}
