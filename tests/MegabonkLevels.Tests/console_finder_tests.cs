namespace MegabonkLevels.Tests;

public class ConsoleFinderTests
{
    private static readonly string[] Entries = { "state", "ui.hud off", "help", "ui.hud on", "player.teleport 1 2 3" };

    [Fact]
    public void Rows_ListTheNewestEntryFirst()
    {
        var finder = new ConsoleFinder(Entries);

        Assert.Equal(new[] { 4, 3, 2, 1, 0 }, finder.Rows.Select(row => row.Index));
        Assert.Equal(5, finder.Total);
    }

    [Fact]
    public void SetQuery_FiltersRowsAndKeepsNewestFirst()
    {
        var finder = new ConsoleFinder(Entries);

        finder.SetQuery("hud");

        Assert.Equal(new[] { 3, 1 }, finder.Rows.Select(row => row.Index));
    }

    [Fact]
    public void Selection_StartsOnTheNewestEntry()
    {
        var finder = new ConsoleFinder(Entries);

        Assert.Equal("player.teleport 1 2 3", finder.SelectedEntry);
    }

    [Fact]
    public void Move_ClampsAtBothEnds()
    {
        var finder = new ConsoleFinder(Entries);

        finder.Move(-3);
        Assert.Equal(0, finder.Selected);

        finder.Move(99);
        Assert.Equal(4, finder.Selected);
        Assert.Equal("state", finder.SelectedEntry);
    }

    [Fact]
    public void SetQuery_ReturnsTheSelectionToTheNewestMatch()
    {
        var finder = new ConsoleFinder(Entries);
        finder.Move(3);

        finder.SetQuery("hud");

        Assert.Equal(0, finder.Selected);
        Assert.Equal("ui.hud on", finder.SelectedEntry);
    }

    [Fact]
    public void SetQuery_WithTheSameQueryKeepsTheSelection()
    {
        var finder = new ConsoleFinder(Entries);
        finder.SetQuery("hud");
        finder.Move(1);

        finder.SetQuery("hud");

        Assert.Equal(1, finder.Selected);
    }

    [Fact]
    public void NoMatches_LeavesNothingSelected()
    {
        var finder = new ConsoleFinder(Entries);

        finder.SetQuery("zzzz");

        Assert.Empty(finder.Rows);
        Assert.Null(finder.SelectedEntry);
        Assert.Equal(0, finder.Selected);
        finder.Move(1);
        Assert.Equal(0, finder.Selected);
    }

    [Fact]
    public void Info_ReportsMatchedOverTotal()
    {
        var finder = new ConsoleFinder(Entries);
        finder.SetQuery("hud");

        Assert.Equal("2/5", finder.Info);
    }

    [Fact]
    public void Window_ScrollsOnlyWhenTheSelectionLeavesTheViewport()
    {
        var finder = new ConsoleFinder(Entries);

        Assert.Equal(0, finder.Window(3));

        finder.Move(2);
        Assert.Equal(0, finder.Window(3));

        finder.Move(1);
        Assert.Equal(1, finder.Window(3));

        finder.Move(1);
        Assert.Equal(2, finder.Window(3));

        finder.Move(-4);
        Assert.Equal(0, finder.Window(3));
    }

    [Fact]
    public void Window_ShrinksBackWhenAFilterLeavesFewerRowsThanTheOffset()
    {
        var finder = new ConsoleFinder(Entries);
        finder.Move(4);
        finder.Window(2);

        finder.SetQuery("hud");

        Assert.Equal(0, finder.Window(2));
    }

    [Fact]
    public void RowMarkup_MarksTheSelectedRowInTheGutter()
    {
        Assert.StartsWith("> ", ConsoleFinder.RowMarkup("state", new int[0], true));
        Assert.StartsWith("  ", ConsoleFinder.RowMarkup("state", new int[0], false));
    }

    [Fact]
    public void RowMarkup_HighlightsOnlyTheMatchedCharacters()
    {
        var markup = ConsoleFinder.RowMarkup("state", new[] { 0, 4 }, false);

        Assert.Contains("<color=#FFD24A>s</color>tat<color=#FFD24A>e</color>", markup);
    }

    [Fact]
    public void RowMarkup_EscapesRichTextOpeners()
    {
        var markup = ConsoleFinder.RowMarkup("a<b", new int[0], false);

        Assert.Contains("a<noparse><</noparse>b", markup);
    }

    [Fact]
    public void RowMarkup_EscapesAHighlightedOpener()
    {
        var markup = ConsoleFinder.RowMarkup("a<b", new[] { 1 }, false);

        Assert.Contains("<color=#FFD24A><noparse><</noparse></color>", markup);
    }
}
