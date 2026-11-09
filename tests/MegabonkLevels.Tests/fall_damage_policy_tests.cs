namespace MegabonkLevels.Tests;

public class FallDamagePolicyTests
{
    [Theory]
    [InlineData(40, true)]
    [InlineData(40.25f, true)]
    [InlineData(40.3f, false)]
    [InlineData(60, false)]
    public void TwoStepAllowanceIncludesReportedSummitDropButNotLargerFalls(float drop, bool expected) =>
        Assert.Equal(expected, FallDamagePolicy.FreeDropApplies(true, 40, drop));

    [Theory]
    [InlineData(0, true)]
    [InlineData(20, true)]
    [InlineData(20.2f, true)]
    [InlineData(21, false)]
    [InlineData(40, false)]
    [InlineData(float.NaN, false)]
    public void FreeDropExemptsOneHeightStepButNotLargerFalls(float drop, bool expected) =>
        Assert.Equal(expected, FallDamagePolicy.FreeDropApplies(true, 20, drop));

    [Fact]
    public void FreeDropIsOptInAndNeedsAKnownTakeoffHeight()
    {
        Assert.False(FallDamagePolicy.FreeDropApplies(false, 20, 20));
        Assert.False(FallDamagePolicy.FreeDropApplies(true, null, 20));
        Assert.False(FallDamagePolicy.FreeDropApplies(true, 20, null));
    }

    [Fact]
    public void DropTrackerMeasuresFromGroundNotTheJumpApexAndResetsBetweenRuns()
    {
        var tracker = new LandingHeightTracker();
        Assert.Null(tracker.DropTo(2));
        tracker.Observe(true, 42);
        tracker.Observe(false, 50);
        tracker.Observe(false, 30);
        Assert.Equal(20, tracker.DropTo(22));
        Assert.Equal(40, tracker.DropTo(2));
        tracker.Observe(true, 22);
        Assert.Equal(20, tracker.DropTo(2));
        tracker.Reset();
        Assert.Null(tracker.DropTo(2));
    }

    [Fact]
    public void GroundedFlagLingeringDuringJumpDoesNotInflateAOneLevelDropToTwentyTwoUnits()
    {
        var tracker = new LandingHeightTracker();
        tracker.ObserveContact(true, 42, 40, 1.925f);
        tracker.ObserveContact(true, 44.073524f, 40, 1.925f);
        tracker.ObserveContact(false, 50, 40, 1.925f);
        Assert.Equal(20, tracker.DropTo(20));
        Assert.True(FallDamagePolicy.FreeDropApplies(true, 20, tracker.DropTo(20)));
        Assert.False(FallDamagePolicy.FreeDropApplies(true, 20, tracker.DropTo(0)));
    }

    [Fact]
    public void GroundContactSamplingFollowsRampsButRejectsUnknownOrDistantFloor()
    {
        var tracker = new LandingHeightTracker();
        tracker.ObserveContact(true, 2, null, 1.925f);
        Assert.Null(tracker.DropTo(0));
        tracker.ObserveContact(true, 12, 10, 1.925f);
        tracker.ObserveContact(true, 22, 20, 1.925f);
        tracker.ObserveContact(true, 44, 0, 1.925f);
        Assert.Equal(20, tracker.DropTo(0));
    }

    [Fact]
    public void FreeHeightSettingRoundTripsCopiesAndParticipatesInHistory()
    {
        var original = LevelFileSerializer.Deserialize("""{"schemaVersion":3,"map":1,"packs":{},"edits":[]}""");
        var changed = LevelSettings.Change(original, "fallDamageFreeHeight", "20");
        Assert.NotEqual(original, changed);
        Assert.Equal(20, changed.FallDamageFreeHeight);
        Assert.Equal(changed, LevelSettings.CopyTo(changed, original));
        Assert.Equal(changed, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(changed)));
        Assert.Null(original.FallDamageFreeHeight);
        Assert.Equal(original, LevelSettings.Change(changed, "fallDamageFreeHeight", "null"));
        var history = new LevelSettingsHistory(original);
        history.Apply("fallDamageFreeHeight", "20");
        Assert.True(history.Undo());
        Assert.Equal(original, history.Current);
        Assert.True(history.Redo());
        Assert.Equal(changed, history.Current);
    }

    [Theory]
    [InlineData("-1")]
    [InlineData("1e100")]
    public void FreeHeightMustBeFiniteAndNonNegative(string value)
    {
        var level = LevelFileSerializer.Deserialize("""{"schemaVersion":3,"map":1,"packs":{},"edits":[]}""");
        Assert.Throws<ArgumentException>(() => LevelSettings.Change(level, "fallDamageFreeHeight", value));
    }

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
