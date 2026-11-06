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
    [Fact]
    public void CountRangeAndShrineSpotsRoundTripAndSurviveSaveCopyAndHistory()
    {
        var original = Level();
        var changed = LevelSettings.Change(LevelSettings.Change(LevelSettings.Change(original,
            "extraShrines", "2"), "extraShrinesMax", "3"), "shrineSpots", "[[30,2,71],[81,30,-98]]");
        Assert.Equal(3, changed.ExtraShrinesMax);
        Assert.Equal(2, changed.ShrineSpots!.Count);
        Assert.Equal(new float[] { 81, 30, -98 }, changed.ShrineSpots[1]);
        Assert.Equal(changed, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(changed)));
        Assert.Equal(changed, LevelSettings.CopyTo(changed, original with { ExtraShrines = 2 }));
        Assert.Equal("3", LevelSettings.Read(changed, "extraShrinesMax"));
        Assert.NotEqual(changed, changed with { ShrineSpots = new[] { new float[] { 30, 2, 71 } } });
        Assert.NotEqual(changed, changed with { ShrineSpots = new[] { new float[] { 30, 2, 71 }, new float[] { 81, 30, -99 } } });

        var history = new LevelSettingsHistory(original);
        history.Apply("shrineSpots", "[[1,2,3]]");
        Assert.True(history.Dirty);
        Assert.True(history.Undo());
        Assert.Null(history.Current.ShrineSpots);
    }

    [Theory]
    [InlineData("extraShrinesMax", "1")]
    [InlineData("extraShrinesMax", "33")]
    [InlineData("shrineSpots", "[[0,0]]")]
    [InlineData("shrineSpots", "[[0,0,0,0]]")]
    [InlineData("shrineSpots", "[1,2,3]")]
    public void InvalidCountRangeAndShrineSpotsAreRejected(string field, string value)
    {
        var level = Level() with { ExtraShrines = 2 };
        Assert.ThrowsAny<ArgumentException>(() => LevelSettings.Change(level, field, value));
    }

    [Fact]
    public void ShrineCountStaysInsideTheRangeAndUsesBothEnds()
    {
        var random = new Random(7);
        var counts = Enumerable.Range(0, 200).Select(_ => ExtraShrines.ShrineCount(2, 3, random)).ToHashSet();
        Assert.Equal(new[] { 2, 3 }, counts.OrderBy(c => c));
        Assert.Equal(4, ExtraShrines.ShrineCount(4, null, random));
    }

    [Fact]
    public void ARangeEnablesThePassEvenWithAZeroMinimum()
    {
        Assert.True(ExtraShrines.Enabled(Level() with { ExtraShrines = 0, ExtraShrinesMax = 3 }));
        Assert.False(ExtraShrines.Enabled(Level() with { ExtraShrines = 0, ExtraShrinesMax = 0 }));
    }

    [Fact]
    public void WithNothingPlacedYetEverySpotCanBePicked()
    {
        var spots = new[] { new Vector3Data(0, 0, 0), new Vector3Data(50, 0, 0), new Vector3Data(100, 0, 0) };
        var random = new Random(4);
        var picks = Enumerable.Range(0, 300).Select(_ => ExtraShrines.PickSpread(spots, Array.Empty<Vector3Data>(), random)).ToHashSet();
        Assert.Equal(new[] { 0, 1, 2 }, picks.OrderBy(i => i));
    }

    [Fact]
    public void ASpotCloserThanTheMinimumGapToAPlacedShrineIsNeverPicked()
    {
        var taken = new[] { new Vector3Data(0, 0, 0) };
        var spots = new[] { new Vector3Data(ExtraShrines.MinSpotGap - 1, 0, 0), new Vector3Data(60, 0, 0) };
        var random = new Random(4);
        Assert.All(Enumerable.Range(0, 100), _ => Assert.Equal(1, ExtraShrines.PickSpread(spots, taken, random)));
        Assert.Equal(-1, ExtraShrines.PickSpread(new[] { spots[0] }, taken, random));
        Assert.Equal(-1, ExtraShrines.PickSpread(Array.Empty<Vector3Data>(), taken, random));
    }

    [Fact]
    public void FartherSpotsAreLikelierButCloserOnesStillComeUp()
    {
        var taken = new[] { new Vector3Data(0, 0, 0) };
        var spots = new[] { new Vector3Data(30, 0, 0), new Vector3Data(90, 0, 0) };
        var random = new Random(11);
        var picks = Enumerable.Range(0, 1000).Select(_ => ExtraShrines.PickSpread(spots, taken, random)).ToList();
        Assert.True(picks.Count(i => i == 1) > 3 * picks.Count(i => i == 0));
        Assert.Contains(0, picks);
    }

    [Fact]
    public void SpreadUsesTheNearestPlacedShrineNotTheFirst()
    {
        var taken = new[] { new Vector3Data(0, 0, 0), new Vector3Data(100, 0, 0) };
        var spots = new[] { new Vector3Data(50, 0, 0), new Vector3Data(5, 0, 0) };
        var random = new Random(2);
        Assert.All(Enumerable.Range(0, 50), _ => Assert.Equal(0, ExtraShrines.PickSpread(spots, taken, random)));
    }

    [Fact]
    public void SpotFloorWindowReachesAboveAndBelowTheAuthoredHeight()
    {
        var (top, bottom) = ExtraShrines.SpotFloorWindow(10f);
        Assert.True(top > 10f && bottom < 10f);
    }

    [Fact]
    public void NudgeOffsetsStartAtTheSpotAndWidenRingByRing()
    {
        var offsets = ExtraShrines.NudgeOffsets(2f, 3, 8);
        Assert.Equal((0f, 0f), offsets[0]);
        Assert.Equal(1 + 3 * 8, offsets.Count);
        var distances = offsets.Select(o => MathF.Round(MathF.Sqrt(o.X * o.X + o.Z * o.Z), 2)).ToList();
        Assert.Equal(distances.OrderBy(d => d), distances);
        Assert.Equal(6f, distances.Max(), 3);
        Assert.Equal(offsets.Count, offsets.Distinct().Count());
    }

    [Fact]
    public void GoldenRollFollowsItsChance()
    {
        var random = new Random(9);
        Assert.All(Enumerable.Range(0, 50), _ => Assert.False(ExtraShrines.RollGolden(random, 0f)));
        Assert.All(Enumerable.Range(0, 50), _ => Assert.True(ExtraShrines.RollGolden(random, 1f)));
        var mixed = Enumerable.Range(0, 200).Select(_ => ExtraShrines.RollGolden(random, ExtraShrines.GoldenChance)).ToList();
        Assert.Contains(true, mixed);
        Assert.Contains(false, mixed);
    }

    [Fact]
    public void GuaranteedKindsRoundTripAndKeepDuplicatesAsMinimumCounts()
    {
        var original = Level();
        var changed = LevelSettings.Change(original, "guaranteedShrineKinds", """["magnet","cursed","moai","magnet"]""");
        Assert.Equal(new[] { "magnet", "cursed", "moai", "magnet" }, changed.GuaranteedShrineKinds);
        Assert.Equal(changed, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(changed)));
        Assert.Equal(changed, LevelSettings.CopyTo(changed, original));
        Assert.Equal("""["magnet","cursed","moai","magnet"]""", LevelSettings.Read(changed, "guaranteedShrineKinds"));
        Assert.NotEqual(changed, changed with { GuaranteedShrineKinds = new[] { "magnet", "cursed", "moai" } });
        Assert.True(ExtraShrines.Enabled(changed));
        Assert.False(ExtraShrines.Enabled(changed with { GuaranteedShrineKinds = Array.Empty<string>() }));
    }

    [Theory]
    [InlineData("""["nope"]""")]
    [InlineData("""["magnet","golden"]""")]
    [InlineData("""{"a":1}""")]
    public void UnknownGuaranteedKindsAreRejected(string value)
    {
        Assert.ThrowsAny<ArgumentException>(() => LevelSettings.Change(Level(), "guaranteedShrineKinds", value));
    }

    [Fact]
    public void ParseKindsKeepsOrderAndDuplicatesAndIgnoresCase()
    {
        Assert.Equal(new[] { ExtraShrineKind.Moai, ExtraShrineKind.Charge, ExtraShrineKind.Moai }, ExtraShrines.ParseKinds(new[] { "MOAI", "charge", "moai" }));
        Assert.Empty(ExtraShrines.ParseKinds(null));
        Assert.Throws<ArgumentException>(() => ExtraShrines.ParseKinds(new[] { "nope" }));
    }

    [Fact]
    public void ShuffledIsAPermutationThatRepeatsPerSeedAndVariesAcrossSeeds()
    {
        var items = Enumerable.Range(0, 8).ToList();
        var first = ExtraShrines.Shuffled(items, new Random(3));
        Assert.Equal(items, first.OrderBy(i => i));
        Assert.Equal(first, ExtraShrines.Shuffled(items, new Random(3)));
        Assert.Contains(Enumerable.Range(4, 20), seed => !ExtraShrines.Shuffled(items, new Random(seed)).SequenceEqual(first));
        Assert.Equal(Enumerable.Range(0, 8), items);
    }

    [Fact]
    public void ChestLuckRangeRoundTripsAndIsValidated()
    {
        var original = Level();
        var changed = LevelSettings.Change(original, "chestLuckRange", "[-0.5,1.5]");
        Assert.Equal(new float[] { -0.5f, 1.5f }, changed.ChestLuckRange);
        Assert.Equal(changed, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(changed)));
        Assert.Equal(changed, LevelSettings.CopyTo(changed, original));
        Assert.Equal("[-0.5,1.5]", LevelSettings.Read(changed, "chestLuckRange"));
        Assert.Null(LevelSettings.Change(changed, "chestLuckRange", "null").ChestLuckRange);
        Assert.ThrowsAny<ArgumentException>(() => LevelSettings.Change(original, "chestLuckRange", "[1,2,3]"));
        Assert.ThrowsAny<ArgumentException>(() => LevelSettings.Change(original, "chestLuckRange", "[2,1]"));
    }

    [Fact]
    public void ChestLuckShiftIsDrawnInsideTheRangeAndReachesBothSides()
    {
        var range = new float[] { -0.5f, 1.5f };
        var random = new Random(8);
        var shifts = Enumerable.Range(0, 400).Select(_ => ChestLuck.Roll(range, random)).ToList();
        Assert.All(shifts, shift => Assert.InRange(shift, -0.5f, 1.5f));
        Assert.Contains(shifts, shift => shift < 0f);
        Assert.Contains(shifts, shift => shift > 1f);
        Assert.Equal(0f, ChestLuck.Roll(null, random));
        Assert.Equal(2f, ChestLuck.Apply(0.5f, 1.5f), 3);
    }
}
