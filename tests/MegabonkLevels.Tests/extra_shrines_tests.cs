using MegabonkLevels;

namespace MegabonkLevels.Tests;

public class ExtraShrinesTests
{
    private static LevelFile Level() => LevelFileSerializer.Deserialize("""{"schemaVersion":3,"map":1,"seed":20261007,"packs":{},"edits":[]}""");

    [Theory]
    [InlineData(1)]
    [InlineData(2)]
    [InlineData(3)]
    public void OldLevelsSpawnNoExtraShrines(int version)
    {
        var level = LevelFileSerializer.DeserializeWithMigration($$"""{"schemaVersion":{{version}},"map":1,"seed":20261007,"packs":{},"edits":[]}""");
        Assert.Equal(0, level.ExtraShrines);
        Assert.Null(level.ExtraShrineKinds);
        Assert.False(ExtraShrines.Enabled(level));
    }

    [Fact]
    public void ExtraCountRoundTripsIndependentlyAndSurvivesSaveCopyAndHistory()
    {
        var original = Level();
        var changed = LevelSettings.Change(original, "extraShrines", "3");
        Assert.NotEqual(original, changed);
        Assert.Equal(3, changed.ExtraShrines);
        Assert.Null(changed.ExtraShrineKinds);
        Assert.Equal(changed, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(changed)));
        Assert.Equal(changed, LevelSettings.CopyTo(changed, original));
        Assert.Equal("3", LevelSettings.Read(changed, "extraShrines"));
        Assert.True(ExtraShrines.Enabled(changed));

        var history = new LevelSettingsHistory(original);
        history.Apply("extraShrines", "3", hasEdits: true);
        Assert.True(history.Dirty);
        Assert.True(history.Undo());
        Assert.Equal(original, history.Current);
        Assert.True(history.Redo());
        Assert.Equal(changed, history.Current);
        Assert.Equal(original, LevelSettings.Change(changed, "extraShrines", "0"));
        Assert.ThrowsAny<ArgumentException>(() => LevelSettings.Change(original, "extraShrines", "true"));
    }

    [Fact]
    public void ExtraKindsRoundTripIndependentlyOfTheCount()
    {
        var original = Level();
        var changed = LevelSettings.Change(original, "extraShrineKinds", """["charge","moai"]""");
        Assert.NotEqual(original, changed);
        Assert.Equal(0, changed.ExtraShrines);
        Assert.Equal(new[] { "charge", "moai" }, changed.ExtraShrineKinds);
        Assert.Equal(changed, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(changed)));
        Assert.Equal(changed, LevelSettings.CopyTo(changed, original));
        Assert.Equal("""["charge","moai"]""", LevelSettings.Read(changed, "extraShrineKinds"));

        var emptied = LevelSettings.Change(original, "extraShrineKinds", "[]");
        Assert.Empty(emptied.ExtraShrineKinds);
        Assert.True(ExtraShrines.AllowedKinds(emptied.ExtraShrineKinds) is null);
        Assert.ThrowsAny<ArgumentException>(() => LevelSettings.Change(original, "extraShrineKinds", """{"a":1}"""));
    }

    [Theory]
    [InlineData("-1")]
    [InlineData("33")]
    [InlineData("""["nope"]""")]
    [InlineData("""["charge","nope"]""")]
    public void OutOfRangeCountsAndUnknownKindsAreRejected(string value)
    {
        var field = value.StartsWith('[') ? "extraShrineKinds" : "extraShrines";
        Assert.ThrowsAny<ArgumentException>(() => LevelSettings.Change(Level(), field, value));
    }

    [Theory]
    [InlineData("InteractableShrineChallenge", ExtraShrineKind.Challenge)]
    [InlineData("InteractableShrineMagnet", ExtraShrineKind.Magnet)]
    [InlineData("InteractableShrineCursed", ExtraShrineKind.Cursed)]
    [InlineData("InteractableShrineGreed", ExtraShrineKind.Greed)]
    [InlineData("InteractableShrineBalance", ExtraShrineKind.Balance)]
    [InlineData("InteractableShrineMoai", ExtraShrineKind.Moai)]
    [InlineData("ChargeShrine", ExtraShrineKind.Charge)]
    [InlineData("InteractableChest", null)]
    [InlineData("MapGenerator", null)]
    public void KindComesFromTheShrineComponentOnThePrefab(string componentName, ExtraShrineKind? expected)
    {
        Assert.Equal(expected, ExtraShrines.KindOf(componentName));
    }

    [Fact]
    public void AllowedKindsTreatsAbsentAndEmptyAsTheFullPoolAndNamesCaseInsensitively()
    {
        Assert.Null(ExtraShrines.AllowedKinds(null));
        Assert.Null(ExtraShrines.AllowedKinds(Array.Empty<string>()));
        var allowed = ExtraShrines.AllowedKinds(new[] { "Charge", "MOAI" });
        Assert.NotNull(allowed);
        Assert.Equal(new[] { ExtraShrineKind.Moai, ExtraShrineKind.Charge }, allowed!.OrderBy(k => k));
        Assert.True(ExtraShrines.IsKnownKind("balance"));
        Assert.False(ExtraShrines.IsKnownKind("golden"));
    }

    [Theory]
    [InlineData(0, 0, 0, false)]
    [InlineData(10, 0, 0, false)]
    [InlineData(20, 0, 0, true)]
    [InlineData(0, 12, 0, false)]
    [InlineData(0, 13, 0, true)]
    public void HotPathKeepsAChargeZoneAwayFromTheAnchors(float x, float y, float z, bool expected)
    {
        var anchors = new[] { new Vector3Data(0, 0, 0) };
        Assert.Equal(expected, ExtraShrines.HotPathClear(new Vector3Data(x, y, z), anchors, Array.Empty<(Vector3Data, Vector3Data)>(), ExtraShrines.ChargeZoneReach));
    }

    [Theory]
    [InlineData(50, 0, 5, false)]
    [InlineData(50, 0, 20, true)]
    [InlineData(120, 0, 0, true)]
    [InlineData(-10, 0, 0, false)]
    public void HotPathKeepsAChargeZoneAwayFromTheRouteBetweenAnchors(float x, float y, float z, bool expected)
    {
        var routes = new[] { (new Vector3Data(0, 0, 0), new Vector3Data(100, 0, 0)) };
        Assert.Equal(expected, ExtraShrines.HotPathClear(new Vector3Data(x, y, z), Array.Empty<Vector3Data>(), routes, ExtraShrines.ChargeZoneReach));
    }

    [Fact]
    public void HotPathIsUnconstrainedWithoutAnchorsOrRoutes()
    {
        Assert.True(ExtraShrines.HotPathClear(new Vector3Data(0, 0, 0), Array.Empty<Vector3Data>(), Array.Empty<(Vector3Data, Vector3Data)>(), ExtraShrines.ChargeZoneReach));
    }

    [Theory]
    [InlineData(0, 0, 0, false)]
    [InlineData(12, 0, 0, false)]
    [InlineData(13, 0, 0, true)]
    [InlineData(0, 12, 0, false)]
    [InlineData(5, 0, 25, true)]
    public void ShrineKeepClearUsesTheFullChargeSphere(float x, float y, float z, bool expected)
    {
        var existing = new[] { new Vector3Data(0, 0, 0) };
        Assert.Equal(expected, ExtraShrines.ShrineClear(new Vector3Data(x, y, z), existing, ExtraShrines.ChargeZoneReach));
    }

    [Theory]
    [InlineData(0, false)]
    [InlineData(1, true)]
    [InlineData(32, true)]
    public void PassRunsOnlyWhenTheLevelAsksForExtraShrines(int count, bool expected)
    {
        Assert.Equal(expected, ExtraShrines.Enabled(Level() with { ExtraShrines = count }));
    }
}
