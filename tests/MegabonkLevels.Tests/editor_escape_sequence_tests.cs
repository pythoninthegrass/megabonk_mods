namespace MegabonkLevels.Tests;

public class EditorEscapeSequenceTests
{
    [Theory]
    [InlineData(EditorTextField.Search)]
    [InlineData(EditorTextField.Save)]
    public void ThreeEscapes_BlurThenClearThenAllowMenu(EditorTextField field)
    {
        var sequence = new EditorEscapeSequence();
        Assert.True(sequence.BlocksMenu(field, 10));
        Assert.Equal(new EditorEscapeResult(EditorEscapeAction.Blur, field), sequence.Press(field, 10));
        Assert.True(sequence.BlocksMenu(EditorTextField.None, 10));

        Assert.True(sequence.BlocksMenu(EditorTextField.None, 12));
        Assert.Equal(new EditorEscapeResult(EditorEscapeAction.Clear, field), sequence.Press(EditorTextField.None, 12));
        Assert.True(sequence.BlocksMenu(EditorTextField.None, 12));
        Assert.True(sequence.BlocksMenu(EditorTextField.None, 12, searchHasText: false, saveHasText: false));

        Assert.False(sequence.BlocksMenu(EditorTextField.None, 14));
        Assert.Equal(new EditorEscapeResult(EditorEscapeAction.GameMenu, EditorTextField.None), sequence.Press(EditorTextField.None, 14));
        Assert.False(sequence.BlocksMenu(EditorTextField.None, 14));
    }

    [Fact]
    public void RefocusingEitherField_StartsAtBlurAgain()
    {
        var sequence = new EditorEscapeSequence();
        sequence.Press(EditorTextField.Search, 1);
        Assert.Equal(new EditorEscapeResult(EditorEscapeAction.Blur, EditorTextField.Save), sequence.Press(EditorTextField.Save, 3));
        Assert.Equal(new EditorEscapeResult(EditorEscapeAction.Clear, EditorTextField.Save), sequence.Press(EditorTextField.None, 5));
    }

    [Fact]
    public void Reset_ForgetsPendingClearAndConsumedFrame()
    {
        var sequence = new EditorEscapeSequence();
        sequence.Press(EditorTextField.Save, 1);
        sequence.Reset();
        Assert.False(sequence.BlocksMenu(EditorTextField.None, 1));
        Assert.Equal(EditorEscapeAction.GameMenu, sequence.Press(EditorTextField.None, 1).Action);
    }

    [Theory]
    [InlineData(EditorTextField.Search)]
    [InlineData(EditorTextField.Save)]
    public void EmptyFocusedForm_ImmediatelyAllowsMenu(EditorTextField field)
    {
        var sequence = new EditorEscapeSequence();
        Assert.False(sequence.BlocksMenu(field, 1, searchHasText: false, saveHasText: false));
        Assert.Equal(new EditorEscapeResult(EditorEscapeAction.GameMenu, field),
            sequence.Press(field, 1, searchHasText: false, saveHasText: false));
        Assert.False(sequence.BlocksMenu(EditorTextField.None, 1));
    }

    [Fact]
    public void EmptyPendingForm_SkipsTheClearStep()
    {
        var sequence = new EditorEscapeSequence();
        sequence.Press(EditorTextField.Save, 1);
        Assert.False(sequence.BlocksMenu(EditorTextField.None, 3, saveHasText: false));
        Assert.Equal(EditorEscapeAction.GameMenu, sequence.Press(EditorTextField.None, 3, saveHasText: false).Action);
        Assert.False(sequence.BlocksMenu(EditorTextField.None, 3));
    }

    [Fact]
    public void OnlyTheRelevantFormsContent_DeterminesWhetherToConsumeEscape()
    {
        var sequence = new EditorEscapeSequence();
        Assert.False(sequence.BlocksMenu(EditorTextField.Search, 1, searchHasText: false, saveHasText: true));
        Assert.False(sequence.BlocksMenu(EditorTextField.Save, 1, searchHasText: true, saveHasText: false));
        Assert.True(sequence.BlocksMenu(EditorTextField.Search, 1, searchHasText: true, saveHasText: false));
        Assert.True(sequence.BlocksMenu(EditorTextField.Save, 1, searchHasText: false, saveHasText: true));
    }
}
