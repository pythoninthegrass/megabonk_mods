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
    public void TryApply_ReturnsWarning_WhenSetterThrows()
    {
        var warning = CharacterOverride.TryApply(_ => throw new InvalidOperationException("boom"));

        Assert.NotNull(warning);
        Assert.Contains("boom", warning);
    }
}
