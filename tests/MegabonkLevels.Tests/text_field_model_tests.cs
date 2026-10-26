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
}
