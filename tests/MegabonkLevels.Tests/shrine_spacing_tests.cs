using MegabonkLevels;

namespace MegabonkLevels.Tests;

public class ShrineSpacingTests
{
    private static LevelFile Level() => LevelFileSerializer.Deserialize("""{"schemaVersion":3,"map":1,"packs":{},"edits":[]}""");
    private static readonly IReadOnlyDictionary<string, float> Spacing = new Dictionary<string, float> { ["mOaI"] = 120 };

    [Theory]
    [InlineData(119.99f, 500, false)]
    [InlineData(120, 0, true)]
    [InlineData(121, -500, true)]
    public void SameKindGapIsHorizontalAndIncludesTheBoundary(float x, float y, bool clear)
    {
        var placed = new[] { (ExtraShrineKind.Moai, new Vector3Data(0, 0, 0)) };
        Assert.Equal(clear, ExtraShrines.SpotClear(ExtraShrineKind.Moai, new Vector3Data(x, y, 0), placed, Spacing));
    }

    [Fact]
    public void DifferentKindsKeepTheNormalGapAndMissingRulesPreserveExistingLevels()
    {
        var placed = new[] { (ExtraShrineKind.Moai, new Vector3Data(0, 0, 0)) };
        Assert.True(ExtraShrines.SpotClear(ExtraShrineKind.Charge, new Vector3Data(13, 0, 0), placed, Spacing));
        Assert.False(ExtraShrines.SpotClear(ExtraShrineKind.Charge, new Vector3Data(12, 0, 0), placed, Spacing));
        Assert.True(ExtraShrines.SpotClear(ExtraShrineKind.Moai, new Vector3Data(13, 0, 0), placed, null));
        Assert.False(ExtraShrines.SpotClear(ExtraShrineKind.Moai, new Vector3Data(0, 0, 0), placed, null));
    }

    [Fact]
    public void AValidAnchorDoesNotAuthorizeANudgeInsideTheGap()
    {
        var placed = new[] { (ExtraShrineKind.Moai, new Vector3Data(8, 0, 0)) };
        Assert.True(ExtraShrines.SpotClear(ExtraShrineKind.Moai, new Vector3Data(128, 0, 0), placed, Spacing));
        Assert.False(ExtraShrines.SpotClear(ExtraShrineKind.Moai, new Vector3Data(126, 0, 0), placed, Spacing));
    }

    [Fact]
    public void SpacingRoundTripsCopiesAndParticipatesInHistory()
    {
        var original = Level();
        var changed = LevelSettings.Change(original, "shrineKindSpacing", """{"moai":120}""");
        Assert.NotEqual(original, changed);
        Assert.Equal(120, changed.ShrineKindSpacing["moai"]);
        Assert.Equal(changed, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(changed)));
        Assert.Equal(changed, LevelSettings.CopyTo(changed, original));
        Assert.Null(original.ShrineKindSpacing);
        Assert.Equal(original, LevelSettings.Change(changed, "shrineKindSpacing", "null"));
        var history = new LevelSettingsHistory(original);
        history.Apply("shrineKindSpacing", """{"moai":120}""");
        Assert.True(history.Dirty);
        Assert.True(history.Undo());
        Assert.Equal(original, history.Current);
        Assert.True(history.Redo());
        Assert.Equal(changed, history.Current);
    }

    [Theory]
    [InlineData("""{"nope":120}""")]
    [InlineData("""{"moai":-1}""")]
    [InlineData("""{"moai":1e100}""")]
    [InlineData("""{"moai":120,"Moai":130}""")]
    public void InvalidSpacingIsRejected(string json) =>
        Assert.Throws<ArgumentException>(() => LevelSettings.Change(Level(), "shrineKindSpacing", json));
}
