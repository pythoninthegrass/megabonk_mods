namespace MegabonkLevels.Tests;

public class ConsoleFuzzyTests
{
    private static int[] Positions(string query, string text) =>
        ConsoleFuzzy.Parse(query).Match(text)?.ToArray();

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("'")]
    [InlineData("!")]
    [InlineData("^")]
    public void BlankQuery_MatchesEverythingWithNoPositions(string query)
    {
        Assert.Empty(Positions(query, "state"));
    }

    [Fact]
    public void Fuzzy_MatchesASubsequenceAndReportsPositions()
    {
        Assert.Equal(new[] { 0, 2, 4 }, Positions("sae", "state"));
    }

    [Fact]
    public void Fuzzy_RejectsOutOfOrderCharacters()
    {
        Assert.Null(Positions("ets", "state"));
    }

    [Fact]
    public void Fuzzy_PrefersTheTightestSpan()
    {
        Assert.Equal(new[] { 8, 9 }, Positions("ab", "a xxx  xab"));
    }

    [Fact]
    public void Exact_MatchesASubstring()
    {
        Assert.Equal(new[] { 3, 4, 5, 6 }, Positions("'wild", "ab.wild off"));
    }

    [Fact]
    public void Exact_RejectsAScatteredMatch()
    {
        Assert.Null(Positions("'sae", "state"));
    }

    [Fact]
    public void Prefix_AnchorsAtTheStart()
    {
        Assert.Equal(new[] { 0, 1, 2 }, Positions("^ui.", "ui.hud off"));
        Assert.Null(Positions("^hud", "ui.hud off"));
    }

    [Fact]
    public void Suffix_AnchorsAtTheEnd()
    {
        Assert.Equal(new[] { 7, 8, 9 }, Positions("off$", "ui.hud off"));
        Assert.Null(Positions("hud$", "ui.hud off"));
    }

    [Fact]
    public void PrefixAndSuffix_RequireTheWholeLine()
    {
        Assert.Equal(new[] { 0, 1, 2, 3, 4 }, Positions("^state$", "state"));
        Assert.Null(Positions("^state$", "state now"));
    }

    [Fact]
    public void Inverse_ExcludesLinesContainingTheTerm()
    {
        Assert.Null(Positions("!hud", "ui.hud off"));
        Assert.Empty(Positions("!hud", "state"));
    }

    [Fact]
    public void InversePrefix_ExcludesOnlyLinesStartingWithTheTerm()
    {
        Assert.Null(Positions("!^ui", "ui.hud off"));
        Assert.Empty(Positions("!^ui", "player ui"));
    }

    [Fact]
    public void InverseSuffix_ExcludesOnlyLinesEndingWithTheTerm()
    {
        Assert.Null(Positions("!off$", "ui.hud off"));
        Assert.Empty(Positions("!off$", "off now"));
    }

    [Fact]
    public void Terms_AreAnded()
    {
        Assert.Equal(new[] { 0, 1, 7, 8, 9 }, Positions("^ui off$", "ui.hud off"));
        Assert.Null(Positions("^ui on$", "ui.hud off"));
    }

    [Fact]
    public void Pipe_OrsTheTermsAroundItWithinAnAndedQuery()
    {
        var query = ConsoleFuzzy.Parse("^core go$ | rb$ | py$");

        Assert.NotNull(query.Match("core.go"));
        Assert.NotNull(query.Match("core.rb"));
        Assert.NotNull(query.Match("core.py"));
        Assert.Null(query.Match("core.js"));
        Assert.Null(query.Match("util.go"));
    }

    [Fact]
    public void Pipe_BindsTighterThanSpace()
    {
        var query = ConsoleFuzzy.Parse("^a b$ | ^c");

        Assert.NotNull(query.Match("a b"));
        Assert.Null(query.Match("c d"));
        Assert.Null(query.Match("a x"));
    }

    [Fact]
    public void Pipe_WithNothingBeforeItIsIgnored()
    {
        Assert.NotNull(ConsoleFuzzy.Parse("| state").Match("state"));
    }

    [Fact]
    public void Positions_AreTheSortedUnionAcrossTerms()
    {
        Assert.Equal(new[] { 0, 1, 3, 4, 5 }, Positions("^ui hud", "ui.hud"));
    }

    [Fact]
    public void SmartCase_IsInsensitiveForALowercaseQuery()
    {
        Assert.NotNull(Positions("teleport", "Player.Teleport 1 2 3"));
    }

    [Fact]
    public void SmartCase_IsSensitiveOnceTheQueryHasAnUppercaseLetter()
    {
        Assert.NotNull(Positions("Teleport", "Player.Teleport 1 2 3"));
        Assert.Null(Positions("Teleport", "player.teleport 1 2 3"));
    }

    [Fact]
    public void Filter_KeepsChronologicalOrderAndReportsOriginalIndexes()
    {
        var entries = new[] { "state", "ui.hud off", "help", "ui.hud on" };

        var hits = ConsoleFuzzy.Filter(entries, "hud");

        Assert.Equal(new[] { 1, 3 }, hits.Select(hit => hit.Index));
    }

    [Fact]
    public void Filter_ReturnsEveryEntryForABlankQuery()
    {
        var hits = ConsoleFuzzy.Filter(new[] { "a", "b" }, "");

        Assert.Equal(new[] { 0, 1 }, hits.Select(hit => hit.Index));
    }
}
