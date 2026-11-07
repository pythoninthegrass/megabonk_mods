using MegabonkLevels;

namespace MegabonkLevels.Tests;

public class GroundZonesTests
{
    private static LevelFile Level() => LevelFileSerializer.Deserialize("""{"schemaVersion":3,"map":1,"seed":20261007,"packs":{},"edits":[]}""");

    private const string Zones = """[{"material":"m_1_TerrainDesert","minX":11,"maxX":14,"minZ":9,"maxZ":14},{"material":"m_TerrainHell","minX":12,"maxX":14,"minZ":0,"maxZ":8}]""";

    [Fact]
    public void MaterialAtIsInclusiveAndNullOutsideEveryZone()
    {
        var zones = LevelSettings.Change(Level(), "groundZones", Zones).GroundZones;
        Assert.Equal("m_1_TerrainDesert", GroundZones.MaterialAt(zones, 11, 9));
        Assert.Equal("m_1_TerrainDesert", GroundZones.MaterialAt(zones, 14, 14));
        Assert.Equal("m_TerrainHell", GroundZones.MaterialAt(zones, 13, 4));
        Assert.Null(GroundZones.MaterialAt(zones, 10, 9));
        Assert.Null(GroundZones.MaterialAt(zones, 11, 8));
        Assert.Null(GroundZones.MaterialAt(null, 1, 1));
        Assert.Null(GroundZones.MaterialAt(Array.Empty<GroundZone>(), 1, 1));
    }

    [Fact]
    public void ALaterZoneWinsWhereZonesOverlap()
    {
        var zones = new[] { new GroundZone("a", 0, 5, 0, 5), new GroundZone("b", 2, 3, 2, 3) };
        Assert.Equal("a", GroundZones.MaterialAt(zones, 1, 1));
        Assert.Equal("b", GroundZones.MaterialAt(zones, 2, 2));
    }

    [Fact]
    public void ZonesRoundTripAndSurviveSaveCopyAndHistory()
    {
        var original = Level();
        var changed = LevelSettings.Change(original, "groundZones", Zones);
        Assert.NotEqual(original, changed);
        Assert.Equal(2, changed.GroundZones.Count);
        Assert.Equal(changed, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(changed)));
        Assert.Equal(changed, LevelSettings.CopyTo(changed, original));
        Assert.Null(LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(original)).GroundZones);
        Assert.Equal(original, LevelSettings.Change(changed, "groundZones", "null"));

        var history = new LevelSettingsHistory(original);
        history.Apply("groundZones", Zones, hasEdits: true);
        Assert.True(history.Dirty);
        Assert.True(history.Undo());
        Assert.Equal(original, history.Current);
    }

    [Theory]
    [InlineData("""[{"material":"","minX":0,"maxX":1,"minZ":0,"maxZ":1}]""")]
    [InlineData("""[{"material":"m","minX":3,"maxX":1,"minZ":0,"maxZ":1}]""")]
    [InlineData("""[{"material":"m","minX":0,"maxX":1,"minZ":4,"maxZ":1}]""")]
    [InlineData("""[{"material":"m","minX":-1,"maxX":1,"minZ":0,"maxZ":1}]""")]
    [InlineData("""[{"minX":0,"maxX":1,"minZ":0,"maxZ":1}]""")]
    public void ZonesAreValidated(string json) =>
        Assert.ThrowsAny<ArgumentException>(() => LevelSettings.Change(Level(), "groundZones", json));
}
