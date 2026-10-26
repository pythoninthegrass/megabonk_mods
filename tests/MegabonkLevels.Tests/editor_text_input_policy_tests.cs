namespace MegabonkLevels.Tests;

public class EditorTextInputPolicyTests
{
    [Theory]
    [InlineData(false, false, false)]
    [InlineData(false, true, false)]
    [InlineData(true, false, false)]
    [InlineData(true, true, true)]
    public void GameMenu_IsBlockedOnlyWhenTheEditorOwnsTextInput(bool editorActive, bool captured, bool blocked) =>
        Assert.Equal(blocked, EditorTextInputPolicy.BlockGameMenu(editorActive, captured));

    [Fact]
    public void EscapeReleaseFrame_StillBlocksTheGameMenu()
    {
        var search = new PaletteSearchInput();
        search.Step(true, true, false, "roc");
        Assert.True(EditorTextInputPolicy.BlockGameMenu(true, search.CapturesKeyboard));

        search.Step(false, false, true, "");
        Assert.False(search.Focused);
        Assert.True(EditorTextInputPolicy.BlockGameMenu(true, search.CapturesKeyboard));

        search.Step(false, false, false, "");
        Assert.False(EditorTextInputPolicy.BlockGameMenu(true, search.CapturesKeyboard));
    }
}
