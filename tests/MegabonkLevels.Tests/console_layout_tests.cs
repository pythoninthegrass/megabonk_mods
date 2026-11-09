namespace MegabonkLevels.Tests;

public class ConsoleLayoutTests
{
    [Theory]
    [InlineData(0, 10, 0, 0)]
    [InlineData(3, 10, 0, 3)]
    [InlineData(9, 10, 0, 9)]
    [InlineData(20, 10, 0, 9)]
    public void PromptRow_FollowsTheLastOutputRow_UntilThePanelIsFull(int visible, int rows, int offset, int expected)
    {
        Assert.Equal(expected, ConsoleLayout.PromptRow(visible, rows, offset));
    }

    [Fact]
    public void PromptRow_WhenScrolledBack_PinsToTheLastRow()
    {
        Assert.Equal(9, ConsoleLayout.PromptRow(5, 10, 2));
    }

    [Fact]
    public void FinderListRows_LeavesRoomForTheInfoAndQueryRows()
    {
        Assert.Equal(8, ConsoleLayout.FinderListRows(10));
        Assert.Equal(1, ConsoleLayout.FinderListRows(2));
    }

    [Fact]
    public void FinderInfoRow_SitsJustAboveTheQueryRow()
    {
        Assert.Equal(8, ConsoleLayout.FinderInfoRow(10));
    }

    [Fact]
    public void FinderIndex_PutsTheNewestMatchNextToTheInfoRow()
    {
        Assert.Equal(0, ConsoleLayout.FinderIndex(7, 10, 0));
        Assert.Equal(1, ConsoleLayout.FinderIndex(6, 10, 0));
        Assert.Equal(7, ConsoleLayout.FinderIndex(0, 10, 0));
    }

    [Fact]
    public void FinderIndex_OffsetsByTheScrollWindow()
    {
        Assert.Equal(5, ConsoleLayout.FinderIndex(7, 10, 5));
    }

    [Fact]
    public void FinderIndex_ForTheInfoAndQueryRows_IsNegative()
    {
        Assert.True(ConsoleLayout.FinderIndex(8, 10, 0) < 0);
        Assert.True(ConsoleLayout.FinderIndex(9, 10, 0) < 0);
    }
}
