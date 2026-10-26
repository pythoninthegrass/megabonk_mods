namespace MegabonkLevels.Tests;

public class PaletteSearchInputTests
{
    [Fact]
    public void UnfocusedInput_DoesNotTypeOrCaptureKeys()
    {
        var input = new PaletteSearchInput();
        input.Step(false, false, false, "wasd 123");
        Assert.Equal("", input.Query);
        Assert.False(input.Focused);
        Assert.False(input.CapturesKeyboard);
    }

    [Fact]
    public void ClickingSearch_FocusesAndTypesPrintableCharacters()
    {
        var input = new PaletteSearchInput();
        input.Step(true, true, false, "wasd 123\t");
        Assert.Equal("wasd 123", input.Query);
        Assert.True(input.Focused);
        Assert.True(input.CapturesKeyboard);
    }

    [Theory]
    [InlineData(true, false)]
    [InlineData(false, true)]
    public void OutsideClickOrEscape_BlursButCapturesTheReleaseFrame(bool click, bool escape)
    {
        var input = new PaletteSearchInput();
        input.Step(true, true, false, "grass");
        input.Step(click, false, escape, "1");
        Assert.False(input.Focused);
        Assert.True(input.CapturesKeyboard);
        Assert.Equal("grass", input.Query);
        input.Step(false, false, false, "2");
        Assert.False(input.CapturesKeyboard);
        Assert.Equal("grass", input.Query);
    }

    [Fact]
    public void BackspaceAndReturn_AreSafeAndControlModifiedTextIsIgnored()
    {
        var input = new PaletteSearchInput();
        input.Step(true, true, false, "\b\babc\b");
        Assert.Equal("ab", input.Query);
        input.Step(false, false, false, "z", controlHeld: true);
        Assert.Equal("ab", input.Query);
        input.Step(false, false, false, "\r\n");
        Assert.Equal("ab", input.Query);
        Assert.False(input.Focused);
        Assert.True(input.CapturesKeyboard);
    }

    [Fact]
    public void ExternalBlur_PreservesQueryAndCapturesItsFrame()
    {
        var input = new PaletteSearchInput();
        input.Step(true, true, false, "rock");
        input.Blur();
        Assert.Equal("rock", input.Query);
        Assert.False(input.Focused);
        Assert.True(input.CapturesKeyboard);
        input.Step(false, false, false, "");
        Assert.False(input.CapturesKeyboard);
    }

    [Fact]
    public void Query_HasABoundedLengthAndResetClearsFocus()
    {
        var input = new PaletteSearchInput();
        input.Step(true, true, false, new string('a', 300));
        Assert.Equal(PaletteSearchInput.MaxLength, input.Query.Length);
        input.Reset();
        Assert.Equal("", input.Query);
        Assert.False(input.Focused);
        Assert.False(input.CapturesKeyboard);
    }
}
