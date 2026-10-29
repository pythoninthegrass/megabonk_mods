namespace MegabonkLevels.Tests;

public class CharacterPolicyTests
{
    [Fact]
    public void AllowedIds_NullOrEmpty_IsUnrestricted()
    {
        Assert.Null(CharacterPolicy.AllowedIds(null));
        Assert.Null(CharacterPolicy.AllowedIds(Array.Empty<string>()));
    }

    [Fact]
    public void AllowedIds_ParsesKnownNames_IgnoringCaseAndAliases()
    {
        var ids = CharacterPolicy.AllowedIds(new[] { "Calcium", "tony" });

        Assert.Equal(new[] { CharacterOverride.CalciumId, CharacterOverride.TonyMcZoomId }, ids);
    }

    [Fact]
    public void AllowedIds_SkipsUnknownNames()
    {
        var ids = CharacterPolicy.AllowedIds(new[] { "calcium", "nobody" });

        Assert.Equal(new[] { CharacterOverride.CalciumId }, ids);
    }

    [Fact]
    public void AllowedIds_AllNamesUnknown_IsUnrestricted()
    {
        Assert.Null(CharacterPolicy.AllowedIds(new[] { "nobody" }));
    }

    [Fact]
    public void UnknownNames_ListsTheUnparsedOnes()
    {
        Assert.Equal(new[] { "nobody" }, CharacterPolicy.UnknownNames(new[] { "calcium", "nobody" }));
        Assert.Empty(CharacterPolicy.UnknownNames(null));
    }

    [Theory]
    [InlineData(1, true)]
    [InlineData(13, true)]
    [InlineData(2, false)]
    public void Permits_ChecksTheAllowedIds(int id, bool expected)
    {
        Assert.Equal(expected, CharacterPolicy.Permits(new[] { 1, 13 }, id));
    }

    [Fact]
    public void Permits_NullAllowedIds_PermitsAnyone()
    {
        Assert.True(CharacterPolicy.Permits(null, 2));
    }

    [Fact]
    public void Refusal_NamesTheAllowedCharactersAndTheLevel()
    {
        var message = CharacterPolicy.Refusal(new[] { CharacterOverride.CalciumId, CharacterOverride.TonyMcZoomId }, "Warehouse");

        Assert.Equal("Pick Calcium or Tony McZoom for Warehouse", message);
    }

    [Fact]
    public void Refusal_SingleCharacter_AndNoTitle()
    {
        Assert.Equal("Pick Calcium for this level", CharacterPolicy.Refusal(new[] { CharacterOverride.CalciumId }, null));
    }
}
