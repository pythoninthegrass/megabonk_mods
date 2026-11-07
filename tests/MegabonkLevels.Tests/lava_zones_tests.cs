using MegabonkLevels;

namespace MegabonkLevels.Tests;

public class LavaZonesTests
{
    private static LevelFile Level() => LevelFileSerializer.Deserialize("""{"schemaVersion":3,"map":1,"seed":20261007,"packs":{},"edits":[]}""");

    private const string Zone = """[{"minX":12,"maxX":13,"minZ":3,"maxZ":4,"damage":4,"interval":0.5}]""";

    // Surface 20, so a standing body centre is 1.925 above it.
    [Theory]
    [InlineData(100f, 21.925f, 100f, true)]
    [InlineData(100f, 20f + LavaZones.BodyCentreAboveFeet - 0.5f, 100f, true)]
    [InlineData(100f, 20f + LavaZones.BodyCentreAboveFeet + LavaZones.Reach + 0.1f, 100f, false)]
    [InlineData(100f, 20f + LavaZones.BodyCentreAboveFeet - 3f, 100f, false)]
    [InlineData(79f, 21.925f, 100f, false)]
    [InlineData(100f, 21.925f, 161f, false)]
    public void ContainsMeansStandingInOrJustAboveTheRectangle(float x, float y, float z, bool expected) =>
        Assert.Equal(expected, LavaZones.Contains(80f, 160f, 40f, 160f, 20f, x, y, z));

    [Fact]
    public void ZonesRoundTripAndSurviveSaveCopyAndHistory()
    {
        var original = Level();
        var changed = LevelSettings.Change(original, "lavaZones", Zone);
        Assert.NotEqual(original, changed);
        Assert.Equal(new LavaZone(12, 13, 3, 4, 4f, 0.5f), changed.LavaZones[0]);
        Assert.Equal(changed, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(changed)));
        Assert.Equal(changed, LevelSettings.CopyTo(changed, original));
        Assert.Null(LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(original)).LavaZones);
        Assert.Equal(original, LevelSettings.Change(changed, "lavaZones", "null"));

        var history = new LevelSettingsHistory(original);
        history.Apply("lavaZones", Zone, hasEdits: true);
        Assert.True(history.Dirty);
        Assert.True(history.Undo());
        Assert.Equal(original, history.Current);
    }

    private static readonly LevelGrid Grid = new(15, 15, Array.Empty<AuthoredCell>());
    private static readonly LavaZone[] Pool = { new(12, 13, 3, 4, 3f, 0.5f) };

    [Theory]
    [InlineData(200f, -160f, true)]
    [InlineData(240f, -120f, true)]
    [InlineData(0f, -240f, false)]
    [InlineData(280f, -160f, false)]
    public void ASpawnInsideALavaZoneIsRefused(float x, float z, bool refused)
    {
        var message = LavaZones.SpawnRefusal(Grid, new[] { x, 20f, z }, Pool);
        Assert.Equal(refused, message != null);
        if (refused) Assert.Contains("lava", message);
    }

    [Fact]
    public void NoZonesOrNoSpawnRefusesNothing()
    {
        Assert.Null(LavaZones.SpawnRefusal(Grid, new[] { 200f, 20f, -160f }, null));
        Assert.Null(LavaZones.SpawnRefusal(Grid, null, Pool));
    }

    [Theory]
    [InlineData(0f, 0f, 7, 7)]
    [InlineData(200f, -160f, 12, 3)]
    [InlineData(-280f, -280f, 0, 0)]
    [InlineData(19.9f, 19.9f, 7, 7)]
    [InlineData(20.1f, 20.1f, 8, 8)]
    public void CellOfRoundsToTheNearestCellCentreOfACentredGrid(float x, float z, int cx, int cz) =>
        Assert.Equal((cx, cz), LavaZones.CellOf(15, 15, x, z));

    [Theory]
    [InlineData("""[{"minX":3,"maxX":1,"minZ":0,"maxZ":1,"damage":4,"interval":0.5}]""")]
    [InlineData("""[{"minX":0,"maxX":1,"minZ":4,"maxZ":1,"damage":4,"interval":0.5}]""")]
    [InlineData("""[{"minX":-1,"maxX":1,"minZ":0,"maxZ":1,"damage":4,"interval":0.5}]""")]
    [InlineData("""[{"minX":0,"maxX":1,"minZ":0,"maxZ":1,"damage":0,"interval":0.5}]""")]
    [InlineData("""[{"minX":0,"maxX":1,"minZ":0,"maxZ":1,"damage":4,"interval":0.01}]""")]
    [InlineData("""[{"minX":0,"maxX":1,"minZ":0,"maxZ":1,"damage":5000,"interval":0.5}]""")]
    public void ZonesAreValidated(string json) =>
        Assert.ThrowsAny<ArgumentException>(() => LevelSettings.Change(Level(), "lavaZones", json));
}
