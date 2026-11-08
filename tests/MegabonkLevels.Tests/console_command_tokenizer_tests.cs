namespace MegabonkLevels.Tests;

public class ConsoleCommandTokenizerTests
{
    [Fact]
    public void Tokenize_SplitsOnWhitespace()
    {
        var tokens = ConsoleCommandTokenizer.Tokenize("player.teleport 10 5 3");

        Assert.Equal(new[] { "player.teleport", "10", "5", "3" }, tokens.Tokens);
        Assert.Null(tokens.Error);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("\t \r\n ")]
    public void Tokenize_BlankInput_HasNoTokens(string line)
    {
        var tokens = ConsoleCommandTokenizer.Tokenize(line);

        Assert.Empty(tokens.Tokens);
        Assert.True(tokens.IsBlank);
        Assert.Null(tokens.Error);
    }

    [Fact]
    public void Tokenize_KeepsQuotedArgumentWhole()
    {
        var tokens = ConsoleCommandTokenizer.Tokenize("coc \"Bramblecrown Hill\"");

        Assert.Equal(new[] { "coc", "Bramblecrown Hill" }, tokens.Tokens);
    }

    [Fact]
    public void Tokenize_QuotedArgumentKeepsInnerWhitespaceAndQuotes()
    {
        var tokens = ConsoleCommandTokenizer.Tokenize("type  \"  two   words  \" trailing");

        Assert.Equal(new[] { "type", "  two   words  ", "trailing" }, tokens.Tokens);
    }

    [Fact]
    public void Tokenize_EmptyQuotedArgumentIsAToken()
    {
        var tokens = ConsoleCommandTokenizer.Tokenize("debug.material_dump \"\"");

        Assert.Equal(new[] { "debug.material_dump", "" }, tokens.Tokens);
    }

    [Fact]
    public void Tokenize_TextAfterAClosingQuoteContinuesTheWord()
    {
        var tokens = ConsoleCommandTokenizer.Tokenize("level.load \"my level\"--force");

        Assert.Equal(new[] { "level.load", "my level--force" }, tokens.Tokens);
    }

    [Fact]
    public void Tokenize_APostropheInAWordIsLiteral()
    {
        var tokens = ConsoleCommandTokenizer.Tokenize("player.add_item don't");

        Assert.Equal(new[] { "player.add_item", "don't" }, tokens.Tokens);
    }

    [Theory]
    [InlineData("level.load \"Warehouse")]
    [InlineData("\"")]
    [InlineData("level.load Warehouse\"")]
    public void Tokenize_UnterminatedQuote_IsAnError(string line)
    {
        var tokens = ConsoleCommandTokenizer.Tokenize(line);

        Assert.Null(tokens.Tokens);
        Assert.Contains("quote", tokens.Error);
    }

    [Fact]
    public void Tokenize_QuoteOpensAWhitespaceRunInsideAWord()
    {
        var tokens = ConsoleCommandTokenizer.Tokenize("level.load bramblecrown\" hill\"");

        Assert.Equal(new[] { "level.load", "bramblecrown hill" }, tokens.Tokens);
    }

    [Theory]
    [InlineData("  state  ", new[] { "state" })]
    [InlineData("state\t\tvalue", new[] { "state", "value" })]
    [InlineData(" ui.hud   on ", new[] { "ui.hud", "on" })]
    public void Tokenize_ExtraWhitespace_Collapses(string line, string[] expected)
    {
        Assert.Equal(expected, ConsoleCommandTokenizer.Tokenize(line).Tokens);
    }

    [Fact]
    public void Tokenize_RejectsAControlCharacter()
    {
        var tokens = ConsoleCommandTokenizer.Tokenize("ui.hud on\0");

        Assert.Null(tokens.Tokens);
        Assert.Contains("control character", tokens.Error);
    }
}
