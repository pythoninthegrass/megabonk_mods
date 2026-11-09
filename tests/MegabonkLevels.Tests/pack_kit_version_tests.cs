using MegabonkLevels;

namespace MegabonkLevels.Tests;

public class PackKitVersionTests
{
    private const string Manifest = """{"id":"thps","name":"THPS","author":"test","version":"2.0.21","assets":["Warehouse","piece-flat"],"kitVersion":"1","kitAssetPrefixes":["piece-","added-"]}""";

    [Fact]
    public void OnlyKitAssetsRequireTheSeparateRevision()
    {
        var manifest = PackManifest.Parse(Manifest, "thps");
        Assert.Equal("1", manifest.KitVersion);
        Assert.True(manifest.IsKitAsset("piece-flat"));
        Assert.False(manifest.IsKitAsset("Warehouse"));
        Assert.False(manifest.IsKitAsset("piece-missing"));
        Assert.Null(PackManifest.Parse(Manifest.Replace(",\"kitVersion\":\"1\",\"kitAssetPrefixes\":[\"piece-\",\"added-\"]", ""), "thps").KitVersion);
    }

    [Theory]
    [InlineData("1", "1", false)]
    [InlineData("1", "0", true)]
    [InlineData("1", null, true)]
    [InlineData(null, "1", false)]
    public void OldOrMissingKitRevisionsWarnWithoutChangingLegacyChecks(string? recorded, string? installed, bool warns)
    {
        Assert.Equal(warns, GamePackVersionCheck.KitMismatchWarning("thps", recorded!, installed!) != null);
    }

    [Fact]
    public void LevelRoundTripPreservesKitVersionsAndLegacyFilesOmitThem()
    {
        var level = LevelFileSerializer.Deserialize("""{"schemaVersion":3,"packs":{},"edits":[],"packKitVersions":{"thps":"1"}}""");
        Assert.Equal("1", level.PackKitVersions["thps"]);
        Assert.Equal(level, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(level)));
        Assert.NotEqual(level, level with { PackKitVersions = new Dictionary<string, string>() });
        var legacy = LevelFileSerializer.Deserialize("""{"schemaVersion":3,"packs":{},"edits":[]}""");
        Assert.DoesNotContain("packKitVersions", LevelFileSerializer.Serialize(legacy));
    }
}
