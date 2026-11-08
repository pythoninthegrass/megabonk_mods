namespace MegabonkLevels.Tests;

public sealed class ConsoleLogStoreTests : IDisposable
{
    private readonly DirectoryInfo _dir = Directory.CreateTempSubdirectory("console-log-store-");

    private string PathFor(string name = "console.jsonl") => System.IO.Path.Combine(_dir.FullName, name);

    public void Dispose() => _dir.Delete(true);

    [Fact]
    public void Load_MissingFile_IsEmpty()
    {
        var snapshot = new ConsoleLogStore(PathFor()).Load(50, 400);

        Assert.Empty(snapshot.History);
        Assert.Empty(snapshot.Scrollback);
    }

    [Fact]
    public void Load_ReturnsAppendedInputsAndOutputsInOrder()
    {
        var store = new ConsoleLogStore(PathFor());
        store.AppendInput("state");
        store.AppendOutput("> state");
        store.AppendOutput("ok");
        store.AppendInput("editor");

        var snapshot = new ConsoleLogStore(PathFor()).Load(50, 400);

        Assert.Equal(new[] { "state", "editor" }, snapshot.History);
        Assert.Equal(new[] { "> state", "ok" }, snapshot.Scrollback);
    }

    [Fact]
    public void Load_RoundTripsQuotesAndUnicode()
    {
        var store = new ConsoleLogStore(PathFor());
        store.AppendInput("level.load \"Bramblecrown Hill\"");
        store.AppendOutput("{\"ok\":true} ✓ café");

        var snapshot = store.Load(50, 400);

        Assert.Equal("level.load \"Bramblecrown Hill\"", Assert.Single(snapshot.History));
        Assert.Equal("{\"ok\":true} ✓ café", Assert.Single(snapshot.Scrollback));
    }

    [Fact]
    public void Load_ClearMarkerDropsEarlierScrollbackButKeepsHistory()
    {
        var store = new ConsoleLogStore(PathFor());
        store.AppendInput("state");
        store.AppendOutput("before");
        store.AppendClear();
        store.AppendOutput("after");

        var snapshot = store.Load(50, 400);

        Assert.Equal(new[] { "state" }, snapshot.History);
        Assert.Equal(new[] { "after" }, snapshot.Scrollback);
    }

    [Fact]
    public void Load_KeepsOnlyTheNewestEntriesWithinTheCaps()
    {
        var store = new ConsoleLogStore(PathFor());
        for (var i = 1; i <= 5; i++)
        {
            store.AppendInput($"in{i}");
            store.AppendOutput($"out{i}");
        }

        var snapshot = store.Load(2, 3);

        Assert.Equal(new[] { "in4", "in5" }, snapshot.History);
        Assert.Equal(new[] { "out3", "out4", "out5" }, snapshot.Scrollback);
    }

    [Fact]
    public void Load_SkipsBlankCorruptAndUnknownLines()
    {
        File.WriteAllLines(PathFor(), new[]
        {
            "{\"k\":\"in\",\"v\":\"state\"}",
            "",
            "not json at all",
            "{\"k\":\"mystery\",\"v\":\"x\"}",
            "{\"k\":\"out\"}",
            "{\"k\":\"out\",\"v\":\"kept\"}",
            "{\"k\":\"out\",\"v\":\"trunc",
        });

        var snapshot = new ConsoleLogStore(PathFor()).Load(50, 400);

        Assert.Equal(new[] { "state" }, snapshot.History);
        Assert.Equal(new[] { "kept" }, snapshot.Scrollback);
    }

    [Fact]
    public void Compact_RewritesTheFileWithOnlyTheEntriesLoadWouldKeep()
    {
        var store = new ConsoleLogStore(PathFor());
        for (var i = 1; i <= 20; i++)
        {
            store.AppendInput($"in{i}");
            store.AppendOutput($"out{i}");
        }

        store.AppendClear();
        store.AppendOutput("kept");
        var before = File.ReadAllLines(PathFor()).Length;

        store.Compact(5, 10);

        var after = File.ReadAllLines(PathFor());
        Assert.True(after.Length < before);
        var snapshot = new ConsoleLogStore(PathFor()).Load(5, 10);
        Assert.Equal(new[] { "in16", "in17", "in18", "in19", "in20" }, snapshot.History);
        Assert.Equal(new[] { "kept" }, snapshot.Scrollback);
        Assert.DoesNotContain(after, line => line.Contains("\"clear\""));
    }

    [Fact]
    public void Compact_MissingFileIsANoOp()
    {
        new ConsoleLogStore(PathFor()).Compact(5, 10);

        Assert.False(File.Exists(PathFor()));
    }

    [Fact]
    public void Append_UnwritablePathDoesNotThrow()
    {
        var blocker = PathFor("blocker");
        File.WriteAllText(blocker, "");
        var store = new ConsoleLogStore(System.IO.Path.Combine(blocker, "console.jsonl"));

        var thrown = Record.Exception(() =>
        {
            store.AppendInput("state");
            store.AppendOutput("ok");
            store.AppendClear();
            store.Compact(5, 10);
        });

        Assert.Null(thrown);
        Assert.Empty(store.Load(5, 10).History);
    }
}
