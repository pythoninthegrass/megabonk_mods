namespace MegabonkLevels.Tests;

public class FallDamagePolicyTests
{
    private static readonly StatModifierRow[] TonyRows =
    {
        new(FallDamagePolicy.MaxHealthStat, FallDamagePolicy.Flat, -30f),
        new(FallDamagePolicy.FallDamageReductionStat, FallDamagePolicy.Flat, 1f),
    };

    private static readonly StatModifierRow[] CalciumRows =
    {
        new(FallDamagePolicy.MoveSpeedStat, FallDamagePolicy.Addition, 0.15f),
    };

    [Theory]
    [InlineData("tony", CharacterOverride.TonyMcZoomId)]
    [InlineData("TonyMcZoom", CharacterOverride.TonyMcZoomId)]
    [InlineData("CALCIUM", CharacterOverride.CalciumId)]
    [InlineData("  calcium  ", CharacterOverride.CalciumId)]
    public void ReferenceCharacter_ParsesTheNamesALevelMayName(string name, int expectedId)
    {
        Assert.Equal(expectedId, FallDamagePolicy.ReferenceCharacter(name));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("randy")]
    public void ReferenceCharacter_IsNullForAnythingElse(string name)
    {
        Assert.Null(FallDamagePolicy.ReferenceCharacter(name));
    }

    [Fact]
    public void Applies_FalseOnARunTheModDidNotLoad_SoStockLevelsKeepStockFallDamage()
    {
        Assert.False(FallDamagePolicy.Applies(false, CharacterOverride.TonyMcZoomId, CharacterOverride.CalciumId));
    }

    [Fact]
    public void Applies_FalseWhenTheLevelNamesNoReferenceCharacter()
    {
        Assert.False(FallDamagePolicy.Applies(true, null, CharacterOverride.CalciumId));
    }

    [Fact]
    // The reference character's own landings run untouched, which is what keeps Tony stock everywhere.
    public void Applies_FalseWhenThePlayerIsTheReferenceCharacter()
    {
        Assert.False(FallDamagePolicy.Applies(true, CharacterOverride.TonyMcZoomId, CharacterOverride.TonyMcZoomId));
    }

    [Fact]
    public void Applies_TrueForAnotherCharacterOnAnOptedInCustomLevel()
    {
        Assert.True(FallDamagePolicy.Applies(true, CharacterOverride.TonyMcZoomId, CharacterOverride.CalciumId));
    }

    [Fact]
    // Tony's flat +1 over a zero base is the 100% reduction that makes his landings free.
    public void StatTotal_IsTheReferenceCharactersOwnReduction()
    {
        Assert.Equal(1f, FallDamagePolicy.StatTotal(0f, TonyRows, FallDamagePolicy.FallDamageReductionStat));
    }

    [Fact]
    // With nothing carrying the stat, the total is the base, which is why Calcium's landings hurt.
    public void StatTotal_IsTheBaseWhenTheCharacterCarriesNoModifierForTheStat()
    {
        Assert.Equal(0f, FallDamagePolicy.StatTotal(0f, CalciumRows, FallDamagePolicy.FallDamageReductionStat));
    }

    [Fact]
    // The same rule reads any stat, so the numbers come from the character asset rather than a hardcoded pair.
    public void StatTotal_ReadsOnlyTheStatAskedFor()
    {
        Assert.Equal(70f, FallDamagePolicy.StatTotal(100f, TonyRows, FallDamagePolicy.MaxHealthStat));
    }

    [Theory]
    [InlineData(FallDamagePolicy.Addition)]
    [InlineData(FallDamagePolicy.Flat)]
    public void StatTotal_SumsBothAdditiveModifyTypes(byte modifyType)
    {
        var rows = new[] { new StatModifierRow(FallDamagePolicy.FallDamageReductionStat, modifyType, 0.5f) };
        Assert.Equal(0.5f, FallDamagePolicy.StatTotal(0f, rows, FallDamagePolicy.FallDamageReductionStat));
    }

    [Fact]
    public void StatTotal_ScalesTheAdditiveSumByMultiplication()
    {
        var rows = new[]
        {
            new StatModifierRow(FallDamagePolicy.FallDamageReductionStat, FallDamagePolicy.Flat, 1f),
            new StatModifierRow(FallDamagePolicy.FallDamageReductionStat, FallDamagePolicy.Multiplication, -0.25f),
        };
        Assert.Equal(0.75f, FallDamagePolicy.StatTotal(0f, rows, FallDamagePolicy.FallDamageReductionStat));
    }
}
