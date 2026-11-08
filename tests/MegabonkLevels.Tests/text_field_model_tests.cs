namespace MegabonkLevels.Tests;

public class TextFieldModelTests
{
    private static TextFieldModel Field(string text, int maxLength = 20)
    {
        var field = new TextFieldModel(maxLength);
        field.Set(text);
        return field;
    }

    [Fact]
    public void Set_PutsTheCaretAtTheEndAndTruncatesToTheLimit()
    {
        var field = Field("abcdef", 4);

        Assert.Equal("abcd", field.Text);
        Assert.Equal(4, field.Caret);
    }

    [Fact]
    public void Type_InsertsAtTheCaretAndAdvancesIt()
    {
        var field = Field("ac");
        field.Navigate(new CaretKeys(Left: 1));
        field.Type("b");

        Assert.Equal("abc", field.Text);
        Assert.Equal(2, field.Caret);
    }

    [Fact]
    public void Type_BackspaceRemovesTheCharacterBeforeTheCaret()
    {
        var field = Field("abc");
        field.Navigate(new CaretKeys(Left: 1));
        field.Type("\b");

        Assert.Equal("ac", field.Text);
        Assert.Equal(1, field.Caret);
        field.Navigate(new CaretKeys(Home: true));
        field.Type("\b");
        Assert.Equal("ac", field.Text);
        Assert.Equal(0, field.Caret);
    }

    [Fact]
    public void Type_IgnoresControlCharactersAndStopsAtTheLimit()
    {
        var field = Field("ab", 3);
        field.Type("c\td");

        Assert.Equal("abc", field.Text);
        Assert.Equal(3, field.Caret);
    }

    [Theory]
    [InlineData("x\r", true)]
    [InlineData("x\n", true)]
    [InlineData("x", false)]
    public void Type_ReportsEnterAndIgnoresTextAfterIt(string input, bool submitted)
    {
        var field = new TextFieldModel(20);

        Assert.Equal(submitted, field.Type(input));
        Assert.Equal("x", field.Text);
    }

    [Fact]
    public void Type_TextAfterEnterIsDropped()
    {
        var field = new TextFieldModel(20);

        Assert.True(field.Type("a\rb"));
        Assert.Equal("a", field.Text);
    }

    [Fact]
    public void Navigate_LeftAndRightClampAtTheEnds()
    {
        var field = Field("abc");
        field.Navigate(new CaretKeys(Left: 9));
        Assert.Equal(0, field.Caret);
        field.Navigate(new CaretKeys(Right: 2));
        Assert.Equal(2, field.Caret);
        field.Navigate(new CaretKeys(Right: 9));
        Assert.Equal(3, field.Caret);
    }

    [Fact]
    public void Navigate_HomeEndAndDelete()
    {
        var field = Field("abc");
        field.Navigate(new CaretKeys(Home: true));
        Assert.Equal(0, field.Caret);
        field.Navigate(new CaretKeys(Delete: 1));
        Assert.Equal("bc", field.Text);
        Assert.Equal(0, field.Caret);
        field.Navigate(new CaretKeys(End: true));
        Assert.Equal(2, field.Caret);
        field.Navigate(new CaretKeys(Delete: 1));
        Assert.Equal("bc", field.Text);
    }

    [Fact]
    public void Clear_EmptiesTheTextAndCaret()
    {
        var field = Field("abc");
        field.Clear();

        Assert.Equal("", field.Text);
        Assert.Equal(0, field.Caret);
    }

    [Fact]
    public void Set_WithACaretPlacesItThere()
    {
        var field = new TextFieldModel(20);

        field.Set("player.teleport", 6);

        Assert.Equal("player.teleport", field.Text);
        Assert.Equal(6, field.Caret);
    }

    [Fact]
    public void Set_WithACaretClampsItToTheText()
    {
        var field = new TextFieldModel(20);

        field.Set("abc", 99);

        Assert.Equal(3, field.Caret);
    }

    [Theory]
    [InlineData("music.play 3", 12, "music.play ", 11)]
    [InlineData("music.play 3  ", 14, "music.play ", 11)]
    [InlineData("music.play", 10, "", 0)]
    [InlineData("a bc def", 4, "a  def", 2)]
    [InlineData("a bc def", 5, "a def", 2)]
    [InlineData("  abc", 5, "  ", 2)]
    [InlineData("abc", 0, "abc", 0)]
    [InlineData("", 0, "", 0)]
    public void DeleteWordLeft_RemovesTheWhitespaceDelimitedWordBeforeTheCaret(string text, int caret, string expected, int expectedCaret)
    {
        var field = new TextFieldModel(40);
        field.Set(text, caret);

        field.DeleteWordLeft();

        Assert.Equal(expected, field.Text);
        Assert.Equal(expectedCaret, field.Caret);
    }

    [Theory]
    [InlineData("music.play 3", 12, "", 0)]
    [InlineData("music.play 3", 6, "play 3", 0)]
    [InlineData("abc", 0, "abc", 0)]
    [InlineData("", 0, "", 0)]
    public void DeleteToStart_RemovesEverythingBeforeTheCaret(string text, int caret, string expected, int expectedCaret)
    {
        var field = new TextFieldModel(40);
        field.Set(text, caret);

        field.DeleteToStart();

        Assert.Equal(expected, field.Text);
        Assert.Equal(expectedCaret, field.Caret);
    }

    [Theory]
    [InlineData("a bc def", 8, 5)]
    [InlineData("a bc def", 5, 2)]
    [InlineData("a bc def", 2, 0)]
    [InlineData("a bc def", 0, 0)]
    [InlineData("ab  ", 4, 0)]
    [InlineData("a  bc", 5, 3)]
    public void NavigateWordLeft_JumpsToTheStartOfTheWhitespaceDelimitedWord(string text, int caret, int expected)
    {
        var field = new TextFieldModel(40);
        field.Set(text, caret);

        field.Navigate(new CaretKeys(WordLeft: 1));

        Assert.Equal(expected, field.Caret);
        Assert.Equal(text, field.Text);
    }

    [Theory]
    [InlineData("a bc def", 0, 1)]
    [InlineData("a bc def", 1, 4)]
    [InlineData("a bc def", 4, 8)]
    [InlineData("a bc def", 8, 8)]
    [InlineData("  ab", 0, 4)]
    [InlineData("ab  ", 2, 4)]
    public void NavigateWordRight_JumpsToTheEndOfTheWhitespaceDelimitedWord(string text, int caret, int expected)
    {
        var field = new TextFieldModel(40);
        field.Set(text, caret);

        field.Navigate(new CaretKeys(WordRight: 1));

        Assert.Equal(expected, field.Caret);
    }

    [Fact]
    public void NavigateWordLeft_RepeatCountMovesThatManyWords()
    {
        var field = Field("a bc def");

        field.Navigate(new CaretKeys(WordLeft: 2));

        Assert.Equal(2, field.Caret);
    }

    [Theory]
    [InlineData("music.play 3", 6, "music.", 6)]
    [InlineData("music.play 3", 0, "", 0)]
    [InlineData("music.play 3", 12, "music.play 3", 12)]
    [InlineData("", 0, "", 0)]
    public void DeleteToEnd_RemovesEverythingAfterTheCaretAndKeepsTheCaret(string text, int caret, string expected, int expectedCaret)
    {
        var field = new TextFieldModel(40);
        field.Set(text, caret);

        field.DeleteToEnd();

        Assert.Equal(expected, field.Text);
        Assert.Equal(expectedCaret, field.Caret);
    }
}
