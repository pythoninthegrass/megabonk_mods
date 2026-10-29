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

        Assert.Equal(LevelFile.CurrentSchemaVersion, level.SchemaVersion);
        Assert.Empty(level.Packs);
        Assert.Null(level.Music);
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

        Assert.Equal(LevelFile.CurrentSchemaVersion, level.SchemaVersion);
        Assert.Equal(new Dictionary<string, string> { ["testpack"] = "1.2.3" }, level.Packs);
        Assert.Null(level.Music);
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
    public void RoundTrip_NoGrass_Survives()
    {
        var level = SampleLevel() with { NoGrass = true };

        var restored = LevelFileSerializer.DeserializeWithMigration(LevelFileSerializer.Serialize(level));

        Assert.True(restored.NoGrass);
        Assert.Equal(level, restored);
    }

    [Fact]
    public void Deserialize_WithoutNoGrassKey_DefaultsToFalse()
    {
        var json = """{"schemaVersion":2,"gameBuildId":"1","map":1,"stageIndex":0,"tier":0,"seed":1,"packs":{},"edits":[]}""";

        Assert.False(LevelFileSerializer.DeserializeWithMigration(json).NoGrass);
    }

    [Fact]
    public void RoundTrip_PlayerStart_Survives()
    {
        var level = SampleLevel() with { PlayerStart = new[] { 92f, 30f, -69f } };

        var restored = LevelFileSerializer.DeserializeWithMigration(LevelFileSerializer.Serialize(level));

        Assert.Equal(new[] { 92f, 30f, -69f }, restored.PlayerStart);
        Assert.Equal(level, restored);
    }

    [Fact]
    public void Deserialize_WithoutPlayerStartKey_LeavesItNull()
    {
        var json = """{"schemaVersion":2,"gameBuildId":"1","map":1,"stageIndex":0,"tier":0,"seed":1,"packs":{},"edits":[]}""";

        Assert.Null(LevelFileSerializer.DeserializeWithMigration(json).PlayerStart);
    }

    [Fact]
    public void Equals_LevelsDifferingOnlyInPlayerStart_AreNotEqual()
    {
        Assert.NotEqual(SampleLevel(), SampleLevel() with { PlayerStart = new[] { 1f, 2f, 3f } });
    }

    [Fact]
    public void RoundTrip_MaxSlopeAngle_Survives()
    {
        var level = SampleLevel() with { MaxSlopeAngle = 88f };

        var restored = LevelFileSerializer.DeserializeWithMigration(LevelFileSerializer.Serialize(level));

        Assert.Equal(88f, restored.MaxSlopeAngle);
        Assert.Equal(level, restored);
    }

    [Fact]
    public void Deserialize_WithoutMaxSlopeAngleKey_LeavesItNull()
    {
        var json = """{"schemaVersion":2,"gameBuildId":"1","map":1,"stageIndex":0,"tier":0,"seed":1,"packs":{},"edits":[]}""";

        Assert.Null(LevelFileSerializer.DeserializeWithMigration(json).MaxSlopeAngle);
    }

    [Fact]
    public void Equals_LevelsDifferingOnlyInMaxSlopeAngle_AreNotEqual()
    {
        Assert.NotEqual(SampleLevel(), SampleLevel() with { MaxSlopeAngle = 80f });
    }

    [Fact]
    public void RoundTrip_KillFloorY_Survives()
    {
        var level = SampleLevel() with { KillFloorY = -35f };

        var restored = LevelFileSerializer.DeserializeWithMigration(LevelFileSerializer.Serialize(level));

        Assert.Equal(-35f, restored.KillFloorY);
        Assert.Equal(level, restored);
    }

    [Fact]
    public void Deserialize_WithoutKillFloorYKey_LeavesItNull()
    {
        var json = """{"schemaVersion":3,"gameBuildId":"1","map":1,"stageIndex":0,"tier":0,"seed":1,"packs":{},"edits":[]}""";

        Assert.Null(LevelFileSerializer.DeserializeWithMigration(json).KillFloorY);
    }

    [Fact]
    public void Equals_LevelsDifferingOnlyInKillFloorY_AreNotEqual()
    {
        Assert.NotEqual(SampleLevel(), SampleLevel() with { KillFloorY = -35f });
    }

    [Fact]
    public void RoundTrip_BossSpawnPosition_Survives()
    {
        var level = SampleLevel() with { BossSpawnPosition = new[] { 130f, -4.933f, 65f } };

        var restored = LevelFileSerializer.DeserializeWithMigration(LevelFileSerializer.Serialize(level));

        Assert.Equal(new[] { 130f, -4.933f, 65f }, restored.BossSpawnPosition);
        Assert.Equal(level, restored);
    }

    [Fact]
    public void Deserialize_WithoutBossSpawnPositionKey_LeavesItNull()
    {
        var json = """{"schemaVersion":3,"gameBuildId":"1","map":1,"stageIndex":0,"tier":0,"seed":1,"packs":{},"edits":[]}""";

        Assert.Null(LevelFileSerializer.DeserializeWithMigration(json).BossSpawnPosition);
    }

    [Fact]
    public void Equals_LevelsDifferingOnlyInBossSpawnPosition_AreNotEqual()
    {
        Assert.NotEqual(SampleLevel(), SampleLevel() with { BossSpawnPosition = new[] { 130f, -4.933f, 65f } });
    }

    [Fact]
    public void CurrentSchemaVersion_IsThree()
    {
        Assert.Equal(3, LevelFile.CurrentSchemaVersion);
    }

    [Fact]
    public void RoundTrip_Music_Survives()
    {
        var level = SampleLevel() with { Music = "bundle:thps/Superman" };

        var restored = LevelFileSerializer.DeserializeWithMigration(LevelFileSerializer.Serialize(level));

        Assert.Equal("bundle:thps/Superman", restored.Music);
        Assert.Equal(level, restored);
    }

    [Fact]
    public void Deserialize_WithoutMusicKey_LeavesItNull()
    {
        var json = """{"schemaVersion":3,"gameBuildId":"1","map":1,"stageIndex":0,"tier":0,"seed":1,"packs":{},"edits":[]}""";

        Assert.Null(LevelFileSerializer.DeserializeWithMigration(json).Music);
    }

    [Fact]
    public void DeserializeWithMigration_V2WithoutMusic_MigratesToV3()
    {
        var json = """{"schemaVersion":2,"gameBuildId":"1","map":1,"stageIndex":0,"tier":0,"seed":1,"packs":{},"edits":[]}""";

        var level = LevelFileSerializer.DeserializeWithMigration(json);

        Assert.Equal(3, level.SchemaVersion);
        Assert.Null(level.Music);
    }

    [Fact]
    public void Equals_LevelsDifferingOnlyInMusic_AreNotEqual()
    {
        Assert.NotEqual(SampleLevel(), SampleLevel() with { Music = "bundle:thps/Superman" });
    }

    [Fact]
    public void RoundTrip_TitleAndDescription_Survive()
    {
        var level = SampleLevel() with { Title = "Warehouse", Description = "I'm trying to sleep" };

        var restored = LevelFileSerializer.DeserializeWithMigration(LevelFileSerializer.Serialize(level));

        Assert.Equal("Warehouse", restored.Title);
        Assert.Equal("I'm trying to sleep", restored.Description);
        Assert.Equal(level, restored);
    }

    [Fact]
    public void Deserialize_WithoutTitleKeys_LeavesThemNull()
    {
        var json = """{"schemaVersion":3,"gameBuildId":"1","map":1,"stageIndex":0,"tier":0,"seed":1,"packs":{},"edits":[]}""";

        var level = LevelFileSerializer.DeserializeWithMigration(json);

        Assert.Null(level.Title);
        Assert.Null(level.Description);
    }

    [Fact]
    public void RoundTrip_AllowedCharacters_Survive()
    {
        var level = SampleLevel() with { AllowedCharacters = new[] { "calcium", "tonymczoom" } };

        var restored = LevelFileSerializer.DeserializeWithMigration(LevelFileSerializer.Serialize(level));

        Assert.Equal(new[] { "calcium", "tonymczoom" }, restored.AllowedCharacters);
        Assert.Equal(level, restored);
    }

    [Fact]
    public void Deserialize_WithoutAllowedCharactersKey_LeavesItNull()
    {
        var json = """{"schemaVersion":3,"gameBuildId":"1","map":1,"stageIndex":0,"tier":0,"seed":1,"packs":{},"edits":[]}""";

        Assert.Null(LevelFileSerializer.DeserializeWithMigration(json).AllowedCharacters);
    }

    [Fact]
    public void Equals_LevelsDifferingOnlyInAllowedCharacters_AreNotEqual()
    {
        Assert.NotEqual(SampleLevel(), SampleLevel() with { AllowedCharacters = new[] { "calcium" } });
    }

    [Fact]
    public void RoundTrip_MapDescription_Survives()
    {
        var level = SampleLevel() with { MapDescription = "A warehouse built for grinding" };

        var restored = LevelFileSerializer.DeserializeWithMigration(LevelFileSerializer.Serialize(level));

        Assert.Equal("A warehouse built for grinding", restored.MapDescription);
        Assert.Equal(level, restored);
    }

    [Fact]
    public void Deserialize_WithoutMapDescriptionKey_LeavesItNull()
    {
        var json = """{"schemaVersion":3,"gameBuildId":"1","map":1,"stageIndex":0,"tier":0,"seed":1,"packs":{},"edits":[]}""";

        Assert.Null(LevelFileSerializer.DeserializeWithMigration(json).MapDescription);
    }

    [Fact]
    public void Equals_LevelsDifferingOnlyInMapDescription_AreNotEqual()
    {
        Assert.NotEqual(SampleLevel(), SampleLevel() with { MapDescription = "x" });
    }

    [Fact]
    public void Equals_LevelsDifferingOnlyInTitle_AreNotEqual()
    {
        Assert.NotEqual(SampleLevel(), SampleLevel() with { Title = "Warehouse" });
    }

    [Fact]
    public void Equals_LevelsDifferingOnlyInDescription_AreNotEqual()
    {
        Assert.NotEqual(SampleLevel(), SampleLevel() with { Description = "I'm trying to sleep" });
    }

    [Fact]
    public void Equals_LevelsDifferingOnlyInNoGrass_AreNotEqual()
    {
        Assert.NotEqual(SampleLevel(), SampleLevel() with { NoGrass = true });
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

    [Fact]
    public void EMap_HellAndDungeon_MatchLiveMapDataAssetValues()
    {
        Assert.Equal(64, (int)EMap.Hell);
        Assert.Equal(16, (int)EMap.Dungeon);
    }
}
