namespace MegabonkLevels.Tests;

public class ConsoleHistoryTests
{
    [Fact]
    public void Add_RecordsEntriesOldestFirst()
    {
        var history = new ConsoleHistory();
        history.Add("state");
        history.Add("ui.hud off");

        Assert.Equal(new[] { "state", "ui.hud off" }, history.Entries);
    }

    [Fact]
    public void Add_SkipsARepeatOfTheNewestEntry()
    {
        var history = new ConsoleHistory();
        history.Add("state");
        history.Add("state");
        history.Add("state");

        Assert.Single(history.Entries);
    }

    [Fact]
    public void Add_AllowsARepeatAfterADifferentEntry()
    {
        var history = new ConsoleHistory();
        history.Add("state");
        history.Add("help");
        history.Add("state");

        Assert.Equal(new[] { "state", "help", "state" }, history.Entries);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void Add_SkipsBlankLines(string line)
    {
        var history = new ConsoleHistory();
        history.Add(line);

        Assert.Empty(history.Entries);
    }

    [Fact]
    public void Add_PastTheCap_DropsTheOldestEntry()
    {
        var history = new ConsoleHistory(2);
        history.Add("a");
        history.Add("b");
        history.Add("c");

        Assert.Equal(new[] { "b", "c" }, history.Entries);
    }

    [Fact]
    public void Add_DuplicateOfTheNewest_WhenFull_KeepsTheOrder()
    {
        var history = new ConsoleHistory(2);
        history.Add("a");
        history.Add("b");
        history.Add("b");

        Assert.Equal(new[] { "a", "b" }, history.Entries);
    }

    [Fact]
    public void Previous_WalksBackwardsFromTheEnd()
    {
        var history = new ConsoleHistory();
        history.Add("state");
        history.Add("help");

        Assert.Equal("help", history.Previous());
        Assert.Equal("state", history.Previous());
    }

    [Fact]
    public void Previous_AtTheOldestEntry_StaysThere()
    {
        var history = new ConsoleHistory();
        history.Add("state");
        history.Add("help");

        history.Previous();
        history.Previous();

        Assert.Equal("state", history.Previous());
    }

    [Fact]
    public void Next_WalksForwardsBackToAnEmptyLine()
    {
        var history = new ConsoleHistory();
        history.Add("state");
        history.Add("help");

        history.Previous();
        history.Previous();

        Assert.Equal("help", history.Next());
        Assert.Equal("", history.Next());
    }

    [Fact]
    public void Next_AtTheEnd_StaysEmpty()
    {
        var history = new ConsoleHistory();
        history.Add("state");

        Assert.Equal("", history.Next());
        Assert.Equal("", history.Next());
    }

    [Fact]
    public void Previous_AfterAnEmptyHistory_IsEmpty()
    {
        Assert.Equal("", new ConsoleHistory().Previous());
    }

    [Fact]
    public void Add_ResetsTheCursorToTheEnd()
    {
        var history = new ConsoleHistory();
        history.Add("state");
        history.Add("help");
        history.Previous();
        history.Add("clear");

        Assert.Equal("clear", history.Previous());
    }

    [Fact]
    public void Reset_PutsTheCursorBackAtTheEnd()
    {
        var history = new ConsoleHistory();
        history.Add("state");
        history.Previous();
        history.Reset();

        Assert.Equal("", history.Next());
        Assert.Equal("state", history.Previous());
    }
}
