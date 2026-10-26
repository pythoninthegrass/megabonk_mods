namespace MegabonkLevels.Tests;

public class TextWindowTests
{
    [Theory]
    [InlineData(0, 5, 10, 0, 0)]
    [InlineData(5, 5, 10, 0, 0)]
    [InlineData(10, 10, 10, 0, 0)]
    [InlineData(11, 11, 10, 0, 1)]
    [InlineData(30, 30, 10, 0, 20)]
    public void Start_ScrollsRightOnlyWhenTheCaretPassesTheEdge(int caret, int length, int capacity, int start, int expected) =>
        Assert.Equal(expected, TextWindow.Start(caret, length, capacity, start));

    [Fact]
    public void Start_ScrollsBackLeftToKeepTheCaretVisible() =>
        Assert.Equal(12, TextWindow.Start(12, 30, 10, 20));

    [Fact]
    public void Start_KeepsTheViewStillWhileTheCaretMovesInsideIt() =>
        Assert.Equal(5, TextWindow.Start(8, 30, 10, 5));

    [Fact]
    public void Start_PullsBackWhenTextShrinks() =>
        Assert.Equal(0, TextWindow.Start(4, 4, 10, 15));

    [Fact]
    public void Visible_ReturnsTheWindowedSubstring()
    {
        Assert.Equal("cdefg", TextWindow.Visible("abcdefghij", 2, 5));
        Assert.Equal("hij", TextWindow.Visible("abcdefghij", 7, 5));
        Assert.Equal("", TextWindow.Visible("", 0, 5));
    }
}
