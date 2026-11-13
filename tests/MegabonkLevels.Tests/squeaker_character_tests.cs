namespace MegabonkLevels.Tests;

public class SqueakerCharacterTests
{
    private const float StockBaseHealth = 100f;
    private const float StockColliderHeight = 3.85f;
    private const float StockColliderWidth = 0.7f;

    [Fact]
    public void Id_IsTheFirstValueAfterTheStockEnum()
    {
        Assert.Equal(21, SqueakerCharacter.Id);
    }

    [Fact]
    public void TinyTarget_LowersMaxHealth()
    {
        var total = FallDamagePolicy.StatTotal(StockBaseHealth, SqueakerCharacter.TinyTargetModifiers, FallDamagePolicy.MaxHealthStat);

        Assert.True(total < StockBaseHealth);
    }

    [Fact]
    public void TinyTarget_RaisesEvasionAboveTheZeroBase()
    {
        var total = FallDamagePolicy.StatTotal(0f, SqueakerCharacter.TinyTargetModifiers, SqueakerCharacter.EvasionStat);

        Assert.True(total > 0f);
    }

    [Fact]
    public void TinyTarget_OnlyTouchesMaxHealthAndEvasion()
    {
        var stats = SqueakerCharacter.TinyTargetModifiers.Select(row => row.Stat).OrderBy(stat => stat).ToArray();

        Assert.Equal(new[] { FallDamagePolicy.MaxHealthStat, SqueakerCharacter.EvasionStat }, stats);
    }

    [Fact]
    public void TinyTarget_AllRowsAreFlat()
    {
        Assert.All(SqueakerCharacter.TinyTargetModifiers, row => Assert.Equal(FallDamagePolicy.Flat, row.ModifyType));
    }

    [Fact]
    public void Collider_IsSmallerThanStockOnBothAxes()
    {
        Assert.True(SqueakerCharacter.ColliderHeight < StockColliderHeight);
        Assert.True(SqueakerCharacter.ColliderWidth < StockColliderWidth);
    }

    [Fact]
    public void Collider_StaysPositive()
    {
        Assert.True(SqueakerCharacter.ColliderHeight > 0f);
        Assert.True(SqueakerCharacter.ColliderWidth > 0f);
    }

    [Fact]
    public void BundleAssets_ResolveFromTheSqueakerPack()
    {
        Assert.Equal("bundle:squeaker/Squeaker", SqueakerCharacter.ModelCatalogId);
        Assert.Equal("bundle:squeaker/StaleCookie", SqueakerCharacter.CookieCatalogId);
    }
}

public class ModCharacterRegistrationTests
{
    [Fact]
    public void ShouldAppend_WhenTheIdIsNotRegistered()
    {
        Assert.True(ModCharacterRegistration.ShouldAppend(new[] { 0, 1, 13, 20 }, SqueakerCharacter.Id));
    }

    [Fact]
    public void ShouldAppend_IsFalseWhenAlreadyRegistered_SoARepeatedLoadAddsNothing()
    {
        Assert.False(ModCharacterRegistration.ShouldAppend(new[] { 0, 1, 21 }, SqueakerCharacter.Id));
    }

    [Fact]
    public void ShouldAppend_EmptyList_Appends()
    {
        Assert.True(ModCharacterRegistration.ShouldAppend(System.Array.Empty<int>(), SqueakerCharacter.Id));
    }

    [Theory]
    [InlineData(21, true)]
    [InlineData(1, false)]
    [InlineData(13, false)]
    [InlineData(20, false)]
    [InlineData(-1, false)]
    public void IsModCharacter_OnlyNamesIdsPastTheStockEnum(int id, bool expected)
    {
        Assert.Equal(expected, ModCharacterRegistration.IsModCharacter(id));
    }

    [Fact]
    public void SkinSeedIsNeeded_ForAnIdMissingFromTheSkinTable()
    {
        Assert.True(ModCharacterRegistration.NeedsSkinSeed(new[] { 0, 1, 20 }, SqueakerCharacter.Id));
        Assert.False(ModCharacterRegistration.NeedsSkinSeed(new[] { 0, 21 }, SqueakerCharacter.Id));
    }
}

public class SelectedCharacterGuardTests
{
    [Fact]
    public void RestoreTarget_IsNullForAStockSelection()
    {
        Assert.Null(SelectedCharacterGuard.RestoreTarget(13, 1));
    }

    [Fact]
    public void RestoreTarget_ReplacesAModCharacterWithTheSavedStockOne()
    {
        Assert.Equal(13, SelectedCharacterGuard.RestoreTarget(21, 13));
    }

    [Fact]
    public void RestoreTarget_FallsBackToCalcium_WhenNothingStockWasSaved()
    {
        Assert.Equal(CharacterOverride.CalciumId, SelectedCharacterGuard.RestoreTarget(21, null));
    }

    [Fact]
    public void RestoreTarget_IgnoresASavedModCharacter_SoItNeverRestoresTheSameValue()
    {
        Assert.Equal(CharacterOverride.CalciumId, SelectedCharacterGuard.RestoreTarget(21, 21));
    }
}

public class SqueakerNameTests
{
    [Theory]
    [InlineData("squeaker")]
    [InlineData("Squeaker")]
    [InlineData(" SQUEAKER ")]
    public void TryParseName_AcceptsSqueaker(string name)
    {
        Assert.Equal(21, CharacterOverride.TryParseName(name));
    }

    [Fact]
    public void DisplayName_NamesSqueaker()
    {
        Assert.Equal("Squeaker", CharacterOverride.DisplayName(21));
    }

    [Fact]
    public void IsAllowed_KeepsTheStockHarnessSetOnly()
    {
        Assert.False(CharacterOverride.IsAllowed(21));
    }

    [Fact]
    public void DevCharacter_ResolvesSqueakerWhenTheFlagIsOn()
    {
        Assert.Equal(21, DevCharacter.Resolve(true, "squeaker"));
    }

    [Fact]
    public void Restriction_ToCalciumAndTony_RefusesSqueaker()
    {
        var allowed = CharacterPolicy.AllowedIds(new[] { "calcium", "tonymczoom" });

        Assert.False(CharacterPolicy.Permits(allowed, 21));
        Assert.True(CharacterPolicy.Permits(allowed, 1));
        Assert.True(CharacterPolicy.Permits(allowed, 13));
    }

    [Fact]
    public void Restriction_NamingSqueaker_Permits()
    {
        var allowed = CharacterPolicy.AllowedIds(new[] { "squeaker" });

        Assert.True(CharacterPolicy.Permits(allowed, 21));
        Assert.False(CharacterPolicy.Permits(allowed, 1));
    }
}

public class SqueakerTextTests
{
    [Fact]
    public void EvasionPercent_AppliesTheGameTransform()
    {
        Assert.Equal(20, SqueakerCharacter.EvasionPercent(0.25f));
    }

    [Fact]
    public void PassiveDescription_StatesTheTradeFromTheConstants()
    {
        var text = SqueakerCharacter.PassiveDescription;

        Assert.Contains("20% evasion", text);
        Assert.Contains("30 max HP", text);
        Assert.Contains("hitbox", text);
    }

    [Fact]
    public void Names_AreFixed()
    {
        Assert.Equal("Squeaker", SqueakerCharacter.DisplayName);
        Assert.Equal("Tiny Target", SqueakerCharacter.PassiveName);
        Assert.Equal("Stale Cookie", SqueakerCharacter.WeaponName);
    }
}

public class CookieProjectileSwapTests
{
    [Theory]
    [InlineData(21, true)]
    [InlineData(1, false)]
    [InlineData(13, false)]
    [InlineData(-1, false)]
    public void UsesCookie_OnlyForSqueaker(int characterId, bool expected)
    {
        Assert.Equal(expected, SqueakerCharacter.UsesCookieProjectile(characterId));
    }
}

public class ModCharacterStatKeysTests
{
    [Theory]
    [InlineData("21Kills")]
    [InlineData("21Rank")]
    [InlineData("22Kills")]
    public void IsModCharacterKey_MatchesTheKeysAnUnnamedCharacterGetsWritten(string key)
    {
        Assert.True(ModCharacterStatKeys.IsModCharacterKey(key));
    }

    [Theory]
    [InlineData("calciumKills")]
    [InlineData("calciumRank")]
    [InlineData("ent1Kills")]
    [InlineData("ghostGrave4Kills")]
    [InlineData("kills")]
    [InlineData("")]
    public void IsModCharacterKey_LeavesStockKeysAlone(string key)
    {
        Assert.False(ModCharacterStatKeys.IsModCharacterKey(key));
    }

    [Theory]
    [InlineData("20Kills")]
    [InlineData("0Rank")]
    [InlineData("21Gold")]
    [InlineData("21")]
    [InlineData("Kills21")]
    public void IsModCharacterKey_IgnoresStockIdsAndOtherSuffixes(string key)
    {
        Assert.False(ModCharacterStatKeys.IsModCharacterKey(key));
    }
}
