namespace MegabonkLevels.Tests;

public class KeyTextMapperTests
{
    [Theory]
    [InlineData("A", false, 'a')]
    [InlineData("A", true, 'A')]
    [InlineData("Z", false, 'z')]
    [InlineData("M", true, 'M')]
    public void CharFor_Letters_FollowShift(string key, bool shift, char expected)
    {
        Assert.Equal(expected, KeyTextMapper.CharFor(key, shift));
    }

    [Theory]
    [InlineData("Alpha0", false, '0')]
    [InlineData("Alpha1", false, '1')]
    [InlineData("Alpha9", false, '9')]
    [InlineData("Alpha1", true, '!')]
    [InlineData("Alpha2", true, '@')]
    [InlineData("Alpha9", true, '(')]
    [InlineData("Alpha0", true, ')')]
    public void CharFor_Digits_FollowShift(string key, bool shift, char expected)
    {
        Assert.Equal(expected, KeyTextMapper.CharFor(key, shift));
    }

    [Theory]
    [InlineData("Minus", false, '-')]
    [InlineData("Minus", true, '_')]
    [InlineData("Equals", false, '=')]
    [InlineData("Equals", true, '+')]
    [InlineData("LeftBracket", false, '[')]
    [InlineData("RightBracket", true, '}')]
    [InlineData("Semicolon", false, ';')]
    [InlineData("Semicolon", true, ':')]
    [InlineData("Quote", false, '\'')]
    [InlineData("Quote", true, '"')]
    [InlineData("Comma", false, ',')]
    [InlineData("Comma", true, '<')]
    [InlineData("Period", false, '.')]
    [InlineData("Period", true, '>')]
    [InlineData("Slash", false, '/')]
    [InlineData("Slash", true, '?')]
    [InlineData("Backslash", false, '\\')]
    [InlineData("Backslash", true, '|')]
    [InlineData("BackQuote", false, '`')]
    [InlineData("BackQuote", true, '~')]
    public void CharFor_Punctuation_FollowShift(string key, bool shift, char expected)
    {
        Assert.Equal(expected, KeyTextMapper.CharFor(key, shift));
    }

    [Theory]
    [InlineData("Space", false, ' ')]
    [InlineData("Space", true, ' ')]
    [InlineData("Keypad7", false, '7')]
    [InlineData("KeypadPeriod", false, '.')]
    [InlineData("KeypadMinus", false, '-')]
    [InlineData("KeypadPlus", false, '+')]
    public void CharFor_SpaceAndKeypad_IgnoreShift(string key, bool shift, char expected)
    {
        Assert.Equal(expected, KeyTextMapper.CharFor(key, shift));
    }

    [Theory]
    [InlineData("Backspace", '\b')]
    [InlineData("Return", '\n')]
    [InlineData("KeypadEnter", '\n')]
    public void CharFor_EditingKeys_ReturnControlCharacters(string key, char expected)
    {
        Assert.Equal(expected, KeyTextMapper.CharFor(key, false));
    }

    [Theory]
    [InlineData("F1")]
    [InlineData("LeftShift")]
    [InlineData("Escape")]
    [InlineData("UpArrow")]
    [InlineData("NotAKey")]
    [InlineData("")]
    public void CharFor_NonTextKeys_ReturnNull(string key)
    {
        Assert.Null(KeyTextMapper.CharFor(key, false));
    }

    [Fact]
    public void Keys_EachMapsToACharacter_WithoutDuplicates()
    {
        Assert.NotEmpty(KeyTextMapper.Keys);
        Assert.Equal(KeyTextMapper.Keys.Count, KeyTextMapper.Keys.Distinct().Count());
        Assert.All(KeyTextMapper.Keys, key => Assert.NotNull(KeyTextMapper.CharFor(key, false)));
    }

    [Fact]
    public void Keys_IncludeEveryLetterAndDigit()
    {
        foreach (var letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        {
            Assert.Contains(letter.ToString(), KeyTextMapper.Keys);
        }

        for (var digit = 0; digit <= 9; digit++)
        {
            Assert.Contains($"Alpha{digit}", KeyTextMapper.Keys);
        }
    }

    [Fact]
    public void TextFor_KeysPressedInOneFrame_ConcatenatesInOrder()
    {
        Assert.Equal("ab1", KeyTextMapper.TextFor(new[] { "A", "B", "Alpha1" }, false));
        Assert.Equal("AB!", KeyTextMapper.TextFor(new[] { "A", "B", "Alpha1" }, true));
    }

    [Fact]
    public void TextFor_SkipsNonTextKeys()
    {
        Assert.Equal("a", KeyTextMapper.TextFor(new[] { "LeftShift", "A", "F1" }, false));
    }

    [Fact]
    public void TextFor_NoKeys_ReturnsEmpty()
    {
        Assert.Equal("", KeyTextMapper.TextFor(Array.Empty<string>(), false));
    }
}
