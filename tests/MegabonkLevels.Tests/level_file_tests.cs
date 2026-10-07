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

    // Synthetic test-only step proving SchemaMigrator's loop/registry mechanism.
    // No real schemaVersion 2 exists yet; this step is local to the test and never registered in production.
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
