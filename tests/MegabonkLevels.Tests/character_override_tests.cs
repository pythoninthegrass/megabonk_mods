namespace MegabonkLevels.Tests;

public class CharacterOverrideTests
{
    [Fact]
    public void TonyMcZoomId_MatchesGameEnumValue()
    {
        Assert.Equal(13, CharacterOverride.TonyMcZoomId);
    }

    [Fact]
    public void TryApply_PassesTonyMcZoomIdToSetter_AndReturnsNull()
    {
        var applied = -1;

        var warning = CharacterOverride.TryApply(id => applied = id);

        Assert.Null(warning);
        Assert.Equal(13, applied);
    }

    [Fact]
    public void TryApply_PassesTheGivenId_ToTheSetter()
    {
        var applied = -1;

        var warning = CharacterOverride.TryApply(id => applied = id, CharacterOverride.CalciumId);

        Assert.Null(warning);
        Assert.Equal(1, applied);
    }

    [Fact]
    public void TryApply_ReturnsWarning_WhenSetterThrows()
    {
        var warning = CharacterOverride.TryApply(_ => throw new InvalidOperationException("boom"));

        Assert.NotNull(warning);
        Assert.Contains("boom", warning);
    }
}

public class CharacterAllowListTests
{
    [Fact]
    public void CalciumId_MatchesGameEnumValue()
    {
        Assert.Equal(1, CharacterOverride.CalciumId);
    }

    [Theory]
    [InlineData(1, true)]
    [InlineData(13, true)]
    [InlineData(0, false)]
    [InlineData(2, false)]
    [InlineData(-1, false)]
    public void IsAllowed_OnlyCalciumAndTony(int id, bool expected)
    {
        Assert.Equal(expected, CharacterOverride.IsAllowed(id));
    }

    [Theory]
    [InlineData("calcium", 1)]
    [InlineData("Calcium", 1)]
    [InlineData(" CALCIUM ", 1)]
    [InlineData("tony", 13)]
    [InlineData("TonyMcZoom", 13)]
    [InlineData("tonymczoom", 13)]
    public void TryParseName_KnownNames(string name, int expected)
    {
        Assert.Equal(expected, CharacterOverride.TryParseName(name));
    }

    [Theory]
    [InlineData("roberto")]
    [InlineData("")]
    [InlineData(null)]
    public void TryParseName_UnknownOrEmpty_ReturnsNull(string? name)
    {
        Assert.Null(CharacterOverride.TryParseName(name));
    }
}

public class DevCharacterTests
{
    [Fact]
    public void FlagOff_ReturnsNull_SoTheScreenIsShown()
    {
        Assert.Null(DevCharacter.Resolve(false, "calcium"));
    }

    [Fact]
    public void FlagOn_NoName_DefaultsToTony()
    {
        Assert.Equal(13, DevCharacter.Resolve(true, null));
    }

    [Fact]
    public void FlagOn_NamedCalcium()
    {
        Assert.Equal(1, DevCharacter.Resolve(true, "calcium"));
    }

    [Fact]
    public void FlagOn_UnknownName_Throws()
    {
        Assert.Throws<ArgumentException>(() => DevCharacter.Resolve(true, "roberto"));
    }
}

public class CharacterGridOrderTests
{
    [Fact]
    public void Pin_PutsCalciumThenTonyFirst_KeepsRestInStockOrder()
    {
        var stock = new[] { 5, 13, 7, 1, 9 };

        Assert.Equal(new[] { 1, 13, 5, 7, 9 }, CharacterGridOrder.Pin(stock));
    }

    [Fact]
    public void Pin_MissingPinnedCharacter_IsSkipped()
    {
        Assert.Equal(new[] { 13, 5, 7 }, CharacterGridOrder.Pin(new[] { 5, 13, 7 }));
    }

    [Fact]
    public void Pin_KeepsPlaceholderEntries_AtTheirRelativePosition()
    {
        Assert.Equal(new[] { 1, 13, 5, -1, -1 }, CharacterGridOrder.Pin(new[] { 5, 1, 13, -1, -1 }));
    }
}
