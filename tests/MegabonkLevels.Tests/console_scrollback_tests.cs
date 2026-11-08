namespace MegabonkLevels.Tests;

public class ConsoleScrollbackTests
{
    [Fact]
    public void Append_AddsLinesAtTheBottom()
    {
        var scrollback = new ConsoleScrollback(10, 5);
        scrollback.Append("one");
        scrollback.Append("two");

        Assert.Equal(new[] { "one", "two" }, scrollback.VisibleLines);
    }

    [Fact]
    public void Append_SplitsAReplyWithNewlines()
    {
        var scrollback = new ConsoleScrollback(10, 5);
        scrollback.Append("one\ntwo\n");

        Assert.Equal(new[] { "one", "two" }, scrollback.VisibleLines);
    }

    [Fact]
    public void Split_SplitsAReplyWithNewlines()
    {
        Assert.Equal(new[] { "one", "two" }, ConsoleScrollback.Split("one\ntwo\n"));
        Assert.Empty(ConsoleScrollback.Split(""));
    }

    [Fact]
    public void Split_NormalisesCarriageReturns()
    {
        Assert.Equal(new[] { "one", "two" }, ConsoleScrollback.Split("one\r\ntwo\r"));
    }

    [Fact]
    public void Append_PastTheBufferCap_DropsTheOldestLines()
    {
        var scrollback = new ConsoleScrollback(3, 5);
        scrollback.Append("1\n2\n3\n4");

        Assert.Equal(new[] { "2", "3", "4" }, scrollback.Lines);
    }

    [Fact]
    public void VisibleLines_CapsAtTheViewportSize()
    {
        var scrollback = new ConsoleScrollback(10, 3);
        scrollback.Append("1\n2\n3\n4\n5");

        Assert.Equal(new[] { "3", "4", "5" }, scrollback.VisibleLines);
    }

    [Fact]
    public void PageUp_MovesOneViewportUp()
    {
        var scrollback = new ConsoleScrollback(10, 3);
        scrollback.Append("1\n2\n3\n4\n5\n6");

        scrollback.PageUp();

        Assert.Equal(new[] { "1", "2", "3" }, scrollback.VisibleLines);
    }

    [Fact]
    public void PageUp_AtTheTop_StopsThere()
    {
        var scrollback = new ConsoleScrollback(3, 3);
        scrollback.Append("1\n2\n3");

        scrollback.PageUp();
        scrollback.PageUp();

        Assert.Equal(new[] { "1", "2", "3" }, scrollback.VisibleLines);
    }

    [Fact]
    public void PageDown_MovesOneViewportDown()
    {
        var scrollback = new ConsoleScrollback(10, 3);
        scrollback.Append("1\n2\n3\n4\n5\n6");
        scrollback.PageUp();

        scrollback.PageDown();

        Assert.Equal(new[] { "4", "5", "6" }, scrollback.VisibleLines);
    }

    [Fact]
    public void PageDown_PastTheEnd_ClampsToTheLatestLines()
    {
        var scrollback = new ConsoleScrollback(10, 3);
        scrollback.Append("1\n2\n3\n4\n5\n6");
        scrollback.PageUp();
        scrollback.PageUp();

        scrollback.PageDown();
        scrollback.PageDown();
        scrollback.PageDown();

        Assert.Equal(new[] { "4", "5", "6" }, scrollback.VisibleLines);
    }

    [Fact]
    public void Append_WhileScrolledUp_StaysOnTheSameLines()
    {
        var scrollback = new ConsoleScrollback(10, 3);
        scrollback.Append("1\n2\n3\n4");
        scrollback.PageUp();

        scrollback.Append("5");

        Assert.Equal(new[] { "2", "3", "4" }, scrollback.VisibleLines);
    }

    [Fact]
    public void Append_WhileScrolledUp_KeepsTheViewWhenTheBufferTrims()
    {
        var scrollback = new ConsoleScrollback(5, 2);
        scrollback.Append("1\n2\n3\n4");
        scrollback.PageUp();

        scrollback.Append("5");

        Assert.Equal(new[] { "2", "3" }, scrollback.VisibleLines);
    }

    [Fact]
    public void Append_WhileScrolledUp_FallsBackToTheBottomWhenTheViewIsTrimmedAway()
    {
        var scrollback = new ConsoleScrollback(3, 2);
        scrollback.Append("1\n2\n3");
        scrollback.PageUp();

        scrollback.Append("4\n5");

        Assert.Equal(new[] { "3", "4" }, scrollback.VisibleLines);
    }

    [Fact]
    public void Follow_LetsNewLinesScrollBackToTheBottom()
    {
        var scrollback = new ConsoleScrollback(10, 3);
        scrollback.Append("1\n2\n3\n4");
        scrollback.PageUp();
        scrollback.Follow();

        scrollback.Append("5");

        Assert.Equal(new[] { "3", "4", "5" }, scrollback.VisibleLines);
    }

    [Fact]
    public void ScrollToBottom_JumpsToTheLatestLines()
    {
        var scrollback = new ConsoleScrollback(10, 2);
        scrollback.Append("1\n2\n3\n4");
        scrollback.PageUp();
        scrollback.PageUp();

        scrollback.ScrollToBottom();

        Assert.Equal(new[] { "3", "4" }, scrollback.VisibleLines);
    }

    [Fact]
    public void ScrollToEnd_WithNoLines_IsEmpty()
    {
        var scrollback = new ConsoleScrollback(10, 3);

        Assert.Empty(scrollback.Lines);
        Assert.Empty(scrollback.VisibleLines);

        scrollback.PageUp();
        scrollback.PageDown();

        Assert.Empty(scrollback.VisibleLines);
    }

    [Fact]
    public void ScrollBy_PositiveMovesTowardOlderLines()
    {
        var scrollback = new ConsoleScrollback(100, 5);
        for (var i = 0; i < 20; i++)
        {
            scrollback.Append($"line{i}");
        }

        scrollback.ScrollBy(3);

        Assert.Equal(3, scrollback.Offset);
        Assert.Equal("line16", scrollback.VisibleLines[^1]);
    }

    [Fact]
    public void ScrollBy_ClampsAtTheTopAndBottom()
    {
        var scrollback = new ConsoleScrollback(100, 5);
        for (var i = 0; i < 20; i++)
        {
            scrollback.Append($"line{i}");
        }

        scrollback.ScrollBy(500);
        Assert.Equal(15, scrollback.Offset);

        scrollback.ScrollBy(-500);
        Assert.Equal(0, scrollback.Offset);
    }

    [Fact]
    public void Viewport_ReportsTheConfiguredLineCount()
    {
        Assert.Equal(7, new ConsoleScrollback(100, 7).Viewport);
    }

    [Fact]
    public void Wrap_BreaksALongLineIntoRowsOfAtMostTheColumnCount()
    {
        Assert.Equal(new[] { "abcd", "efgh", "ij" }, ConsoleScrollback.Wrap("abcdefghij", 4));
    }

    [Fact]
    public void Wrap_LeavesAShortLineAlone()
    {
        Assert.Equal(new[] { "abc" }, ConsoleScrollback.Wrap("abc", 4));
        Assert.Equal(new[] { "abcd" }, ConsoleScrollback.Wrap("abcd", 4));
    }

    [Fact]
    public void Append_WrapsALongLineAcrossRows()
    {
        var scrollback = new ConsoleScrollback(10, 5, 4);
        scrollback.Append("abcdefghij\nxy");

        Assert.Equal(new[] { "abcd", "efgh", "ij", "xy" }, scrollback.Lines);
    }

    [Fact]
    public void Append_WithoutAWrapWidth_KeepsLongLinesWhole()
    {
        var scrollback = new ConsoleScrollback(10, 5);
        scrollback.Append(new string('a', 500));

        Assert.Single(scrollback.Lines);
    }
}
