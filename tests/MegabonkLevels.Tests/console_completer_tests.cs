namespace MegabonkLevels.Tests;

public class ConsoleCompleterTests
{
    private static ConsoleCompleter NewCompleter() => new(ConsoleCommandRegistry.Default);

    [Fact]
    public void Tab_OnAmbiguousPrefix_CompletesTheFirstMatchThenCyclesAndWraps()
    {
        var completer = NewCompleter();
        var line = "music.p";

        line = completer.Tab(line, line.Length, null);
        Assert.Equal("music.pause ", line);

        line = completer.Tab(line, line.Length, null);
        Assert.Equal("music.play ", line);

        line = completer.Tab(line, line.Length, null);
        Assert.Equal("music.prev ", line);

        line = completer.Tab(line, line.Length, null);
        Assert.Equal("music.pause ", line);
    }

    [Fact]
    public void Tab_AfterTheLineIsEdited_CompletesAfresh()
    {
        var completer = NewCompleter();
        var line = completer.Tab("music.p", 7, null);

        var edited = "music.pl";
        Assert.Equal("music.play ", completer.Tab(edited, edited.Length, null));
        Assert.Equal("music.pause ", line);
    }

    [Fact]
    public void Tab_CyclesLevelTitlesOfTheLevelLoadArgument()
    {
        var completer = NewCompleter();
        var levels = new[] { "alpha.mblevel.json", "alps.mblevel.json" };
        var line = "level.load al";

        line = completer.Tab(line, line.Length, levels);
        Assert.Equal("level.load alpha ", line);

        line = completer.Tab(line, line.Length, levels);
        Assert.Equal("level.load alps ", line);
    }

    [Fact]
    public void Tab_WithNothingToComplete_ReturnsNull()
    {
        Assert.Null(NewCompleter().Tab("zzz", 3, null));
    }

    [Fact]
    public void Tab_AfterAMiss_StillCompletesTheNextLine()
    {
        var completer = NewCompleter();
        completer.Tab("zzz", 3, null);

        Assert.Equal("music.pause ", completer.Tab("music.p", 7, null));
    }

    [Fact]
    public void Tab_CompletesTheTextBeforeTheCaret()
    {
        Assert.Equal("music.pause ", NewCompleter().Tab("music.p tail", 7, null));
    }
}
