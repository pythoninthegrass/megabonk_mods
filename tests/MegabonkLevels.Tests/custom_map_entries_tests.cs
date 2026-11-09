namespace MegabonkLevels.Tests;

public class CustomMapEntriesTests
{
    private static LevelFile Level(string title, string description = null) => new(
        LevelFile.CurrentSchemaVersion, "1", EMap.Forest, 0, 0, 0,
        new Dictionary<string, string>(), new List<EditOp>(), Title: title, Description: description);

    [Fact]
    public void From_SkipsLevelsWithoutATitle()
    {
        var entries = CustomMapEntries.From(new[] { ("a.mblevel.json", Level(null)), ("b.mblevel.json", Level("  ")) });

        Assert.Empty(entries);
    }

    [Fact]
    public void From_KeepsPathTitleAndDescription()
    {
        var entries = CustomMapEntries.From(new[] { ("thps.mblevel.json", Level("Warehouse", "I'm trying to sleep")) });

        var entry = Assert.Single(entries);
        Assert.Equal("thps.mblevel.json", entry.Path);
        Assert.Equal("Warehouse", entry.Title);
        Assert.Equal("I'm trying to sleep", entry.Description);
        Assert.Equal(EMap.Forest, entry.Map);
        Assert.Null(entry.AllowedCharacters);
    }

    [Fact]
    public void From_KeepsAllowedCharacters()
    {
        var level = Level("Warehouse") with { AllowedCharacters = new[] { "calcium" } };

        var entry = Assert.Single(CustomMapEntries.From(new[] { ("a.mblevel.json", level) }));

        Assert.Equal(new[] { "calcium" }, entry.AllowedCharacters);
    }

    [Fact]
    public void From_PrefersMapDescriptionOverTheBannerDescription()
    {
        var level = Level("Warehouse", "I'm trying to sleep") with { MapDescription = "A warehouse built for grinding" };

        var entry = Assert.Single(CustomMapEntries.From(new[] { ("a.mblevel.json", level) }));

        Assert.Equal("A warehouse built for grinding", entry.Description);
    }

    [Fact]
    public void From_UsesEmptyDescription_WhenLevelHasNone()
    {
        var entry = Assert.Single(CustomMapEntries.From(new[] { ("a.mblevel.json", Level("Arena")) }));

        Assert.Equal("", entry.Description);
    }

    [Fact]
    public void From_SortsByTitleIgnoringCase()
    {
        var entries = CustomMapEntries.From(new[]
        {
            ("1.mblevel.json", Level("warehouse")),
            ("2.mblevel.json", Level("Arena")),
        });

        Assert.Equal(new[] { "Arena", "warehouse" }, entries.Select(e => e.Title));
    }
}
