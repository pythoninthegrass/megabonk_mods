using System.Text.Json.Nodes;

namespace MegabonkLevels.Tests;

public class LevelFileTests
{
    private static LevelFile SampleLevel() => new(
        SchemaVersion: LevelFile.CurrentSchemaVersion,
        GameBuildId: "1.0.69",
        Map: EMap.Forest,
        StageIndex: 0,
        Tier: 1,
        Seed: 20261007,
        Packs: new Dictionary<string, string>(),
        Edits:
        [
            new EditOp("tile.setHeight", "tile:0042", "{\"height\":2}"),
            new EditOp("object.place", "catalogId:rock_small", "{\"x\":1,\"y\":0,\"z\":3}"),
        ]);

    [Fact]
    public void RoundTrip_SerializeThenDeserialize_ProducesEqualLevel()
    {
        var level = SampleLevel();

        var json = LevelFileSerializer.Serialize(level);
        var deserialized = LevelFileSerializer.Deserialize(json);

        Assert.Equal(level, deserialized);
    }

    [Fact]
    public void DeserializeWithMigration_AtCurrentVersion_MatchesPlainDeserialize()
    {
        var level = SampleLevel();
        var json = LevelFileSerializer.Serialize(level);

        var migrated = LevelFileSerializer.DeserializeWithMigration(json);

        Assert.Equal(level, migrated);
    }

    [Fact]
    public void DeserializeWithMigration_V1WithoutPacks_MigratesToEmptyPacks()
    {
        var json = @"{
            ""schemaVersion"": 1,
            ""gameBuildId"": ""1.0.69"",
            ""map"": 1,
            ""stageIndex"": 0,
            ""tier"": 1,
            ""seed"": 20261007,
            ""edits"": []
        }";

        var level = LevelFileSerializer.DeserializeWithMigration(json);

        Assert.Equal(2, level.SchemaVersion);
        Assert.Empty(level.Packs);
    }

    [Fact]
    public void DeserializeWithMigration_V2WithPacks_PreservesPacks()
    {
        var json = @"{
            ""schemaVersion"": 2,
            ""gameBuildId"": ""1.0.69"",
            ""map"": 1,
            ""stageIndex"": 0,
            ""tier"": 1,
            ""seed"": 20261007,
            ""edits"": [],
            ""packs"": { ""testpack"": ""1.2.3"" }
        }";

        var level = LevelFileSerializer.DeserializeWithMigration(json);

        Assert.Equal(2, level.SchemaVersion);
        Assert.Equal(new Dictionary<string, string> { ["testpack"] = "1.2.3" }, level.Packs);
    }

    [Fact]
    public void RoundTrip_WithPacks_SurvivesMigration()
    {
        var level = new LevelFile(
            SchemaVersion: LevelFile.CurrentSchemaVersion,
            GameBuildId: "1.0.69",
            Map: EMap.Forest,
            StageIndex: 0,
            Tier: 1,
            Seed: 20261007,
            Packs: new Dictionary<string, string> { ["testpack"] = "1.2.3" },
            Edits: Array.Empty<EditOp>());

        var migrated = LevelFileSerializer.DeserializeWithMigration(LevelFileSerializer.Serialize(level));

        Assert.Equal(level, migrated);
    }

    [Fact]
    public void GetHashCode_LevelsWithEqualPacks_AreEqual()
    {
        var a = SampleLevel() with { Packs = new Dictionary<string, string> { ["testpack"] = "1.2.3" } };
        var b = SampleLevel() with { Packs = new Dictionary<string, string> { ["testpack"] = "1.2.3" } };

        Assert.Equal(a, b);
        Assert.Equal(a.GetHashCode(), b.GetHashCode());
    }

    [Fact]
    public void DeserializeWithMigration_V2WithoutPacksKey_YieldsEmptyPacks()
    {
        const string json = @"{ ""schemaVersion"": 2, ""gameBuildId"": ""1.0.69"", ""map"": 0, ""stageIndex"": 0, ""tier"": 1, ""seed"": 1, ""edits"": [] }";

        var level = LevelFileSerializer.DeserializeWithMigration(json);

        Assert.NotNull(level.Packs);
        Assert.Empty(level.Packs);
    }

    [Fact]
    public void Deserialize_WithoutPacksKey_YieldsEmptyPacks()
    {
        const string json = @"{ ""schemaVersion"": 2, ""gameBuildId"": ""1.0.69"", ""map"": 0, ""stageIndex"": 0, ""tier"": 1, ""seed"": 1, ""edits"": [] }";

        var level = LevelFileSerializer.Deserialize(json);

        Assert.NotNull(level.Packs);
        Assert.Empty(level.Packs);
    }

    // Synthetic test-only step proving SchemaMigrator's loop/registry mechanism; it is local to the test and never registered in production.
    [Fact]
    public void SchemaMigrator_AppliesRegisteredStepUntilTargetVersionReached()
    {
        var v1Document = new JsonObject
        {
            ["schemaVersion"] = 1,
            ["value"] = "foo",
        };

        var steps = new Dictionary<int, MigrationStep>
        {
            [1] = document =>
            {
                var migrated = new JsonObject
                {
                    ["schemaVersion"] = 2,
                    ["renamedValue"] = document["value"]!.DeepClone(),
                };
                return migrated;
            },
        };

        var migrated = SchemaMigrator.Migrate(v1Document, targetVersion: 2, steps);

        Assert.Equal(2, (int)migrated["schemaVersion"]!);
        Assert.Equal("foo", (string)migrated["renamedValue"]!);
    }

    [Fact]
    public void SchemaMigrator_MissingStepForOlderVersion_Throws()
    {
        var document = new JsonObject { ["schemaVersion"] = 0 };

        Assert.Throws<InvalidOperationException>(
            () => SchemaMigrator.Migrate(document, targetVersion: 1, new Dictionary<int, MigrationStep>()));
    }
}
