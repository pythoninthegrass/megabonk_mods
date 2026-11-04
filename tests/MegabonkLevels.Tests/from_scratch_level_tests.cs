using System.Text.Json.Nodes;

namespace MegabonkLevels.Tests;

public class FromScratchLevelTests
{
    private static string RepoFile(string relative)
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "taskfile.yml")))
        {
            dir = dir.Parent;
        }

        return Path.Combine(dir!.FullName, relative);
    }

    private static JsonObject FromScratchDocument() => JsonNode.Parse("""
        {
          "schemaVersion": 4,
          "baseline": "none",
          "map": 1,
          "stageIndex": 0,
          "tier": 0,
          "packs": {},
          "grid": {
            "width": 4,
            "depth": 3,
            "cells": [
              { "x": 0, "z": 0, "height": 0 },
              { "x": 1, "z": 0, "height": 0 },
              { "x": 1, "z": 1, "height": 0, "slope": "north" },
              { "x": 1, "z": 2, "height": 1 }
            ]
          },
          "spawn": { "position": [0.5, 2, 0.5], "rotation": [0, 90, 0] },
          "bossSpawner": { "position": [2.5, 3, 1.5], "rotation": [0, 180, 0] },
          "edits": [
            { "opType": "object.place", "target": "placement:0", "payload": "{\"catalogId\":\"game:Rock\",\"position\":{\"x\":1,\"y\":0,\"z\":1},\"rotation\":{\"x\":0,\"y\":0,\"z\":0},\"scale\":{\"x\":1,\"y\":1,\"z\":1}}" }
          ]
        }
        """)!.AsObject();

    private static string Without(string key)
    {
        var document = FromScratchDocument();
        document.Remove(key);
        return document.ToJsonString();
    }

    private static string WithEdit(string opType, string target)
    {
        var document = FromScratchDocument();
        document["edits"]!.AsArray().Add(new JsonObject { ["opType"] = opType, ["target"] = target, ["payload"] = "{}" });
        return document.ToJsonString();
    }

    private static string WithCells(params (int X, int Z)[] cells)
    {
        var document = FromScratchDocument();
        var array = new JsonArray();
        foreach (var (x, z) in cells)
        {
            array.Add(new JsonObject { ["x"] = x, ["z"] = z, ["height"] = 0 });
        }

        document["grid"]!["cells"] = array;
        return document.ToJsonString();
    }

    [Fact]
    public void CurrentSchemaVersion_IsFour()
    {
        Assert.Equal(4, LevelFile.CurrentSchemaVersion);
    }

    [Fact]
    public void FromScratchFile_ParsesGridSpawnAndBossSpawner()
    {
        var level = LevelFileSerializer.Deserialize(FromScratchDocument().ToJsonString());

        Assert.Equal("none", level.Baseline);
        Assert.Equal(4, level.Grid!.Value.Width);
        Assert.Equal(3, level.Grid.Value.Depth);
        Assert.Equal(4, level.Grid.Value.Cells.Count);
        Assert.Equal(SlopeDirection.None, level.Grid.Value.Cells[0].Slope);
        Assert.Equal(SlopeDirection.North, level.Grid.Value.Cells[2].Slope);
        Assert.Equal([0.5f, 2f, 0.5f], level.Spawn!.Value.Position);
        Assert.Equal([0f, 90f, 0f], level.Spawn.Value.Rotation);
        Assert.Equal([2.5f, 3f, 1.5f], level.BossSpawner!.Value.Position);
    }

    [Fact]
    public void FromScratchFile_RoundTripsUnchanged()
    {
        var level = LevelFileSerializer.Deserialize(FromScratchDocument().ToJsonString());

        var roundTripped = LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(level));

        Assert.Equal(level, roundTripped);
        Assert.Single(roundTripped.Edits);
    }

    [Fact]
    public void FromScratchFile_SerializesSlopeByNameAndOmitsNone()
    {
        var level = LevelFileSerializer.Deserialize(FromScratchDocument().ToJsonString());

        var cells = JsonNode.Parse(LevelFileSerializer.Serialize(level))!["grid"]!["cells"]!.AsArray();

        Assert.Null(cells[0]!["slope"]);
        Assert.Equal("north", (string?)cells[2]!["slope"]);
    }

    [Fact]
    public void FromScratchFile_WithoutSeed_Loads()
    {
        var level = LevelFileSerializer.DeserializeWithMigration(FromScratchDocument().ToJsonString());

        Assert.Equal(0, level.Seed);
    }

    [Theory]
    [InlineData("grid")]
    [InlineData("spawn")]
    [InlineData("bossSpawner")]
    public void FromScratchFile_MissingRequiredField_IsRejectedNamingTheField(string field)
    {
        var json = Without(field);

        var plain = Assert.Throws<ArgumentException>(() => LevelFileSerializer.Deserialize(json));
        var migrating = Assert.Throws<ArgumentException>(() => LevelFileSerializer.DeserializeWithMigration(json));

        Assert.Contains(field, plain.Message);
        Assert.Contains(field, migrating.Message);
    }

    [Theory]
    [InlineData("tile.setHeight", "tile:0001")]
    [InlineData("tile.setSlope", "tile:0001")]
    [InlineData("tile.add", "tile:0001")]
    [InlineData("tile.remove", "tile:0001")]
    public void FromScratchFile_WithTileEditOp_IsRejected(string opType, string target)
    {
        Assert.Throws<ArgumentException>(() => LevelFileSerializer.Deserialize(WithEdit(opType, target)));
    }

    [Theory]
    [InlineData("object.move")]
    [InlineData("object.remove")]
    public void FromScratchFile_WithGeneratedObjectTarget_IsRejected(string opType)
    {
        var ex = Assert.Throws<ArgumentException>(() => LevelFileSerializer.Deserialize(WithEdit(opType, "gen:0042")));

        Assert.Contains("gen:", ex.Message);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("generated")]
    public void GeneratedBaselineFile_WithGrid_IsRejected(string? baseline)
    {
        var document = FromScratchDocument();
        if (baseline is null)
        {
            document.Remove("baseline");
        }
        else
        {
            document["baseline"] = baseline;
        }

        var ex = Assert.Throws<ArgumentException>(() => LevelFileSerializer.Deserialize(document.ToJsonString()));

        Assert.Contains("grid", ex.Message);
    }

    [Fact]
    public void UnknownBaseline_IsRejected()
    {
        var document = FromScratchDocument();
        document["baseline"] = "blank";

        var ex = Assert.Throws<ArgumentException>(() => LevelFileSerializer.Deserialize(document.ToJsonString()));

        Assert.Contains("baseline", ex.Message);
    }

    [Theory]
    [InlineData(4, 0)]
    [InlineData(0, 3)]
    [InlineData(-1, 0)]
    [InlineData(0, -1)]
    public void FromScratchFile_WithCellOutsideGrid_IsRejected(int x, int z)
    {
        var ex = Assert.Throws<ArgumentException>(() => LevelFileSerializer.Deserialize(WithCells((0, 0), (x, z))));

        Assert.Contains($"({x}, {z})", ex.Message);
    }

    [Fact]
    public void FromScratchFile_WithDuplicateCell_IsRejected()
    {
        var ex = Assert.Throws<ArgumentException>(() => LevelFileSerializer.Deserialize(WithCells((1, 1), (2, 2), (1, 1))));

        Assert.Contains("(1, 1)", ex.Message);
    }

    [Fact]
    public void FromScratchFile_WithNonPositiveGridSize_IsRejected()
    {
        var document = FromScratchDocument();
        document["grid"]!["width"] = 0;

        Assert.Throws<ArgumentException>(() => LevelFileSerializer.Deserialize(document.ToJsonString()));
    }

    [Fact]
    public void Migration_FromVersionThree_BumpsVersionAndLeavesGeneratedBaseline()
    {
        var json = """{"schemaVersion":3,"gameBuildId":"1","map":1,"stageIndex":0,"tier":0,"seed":1,"packs":{},"edits":[{"opType":"tile.setHeight","target":"tile:0001","payload":"{\"height\":2}"}]}""";

        var level = LevelFileSerializer.DeserializeWithMigration(json);

        Assert.Equal(4, level.SchemaVersion);
        Assert.Null(level.Baseline);
        Assert.Null(level.Grid);
        Assert.Null(level.Spawn);
        Assert.Null(level.BossSpawner);
        Assert.Single(level.Edits);
    }

    [Fact]
    public void GeneratedBaselineFile_SerializesWithoutTheNewKeys()
    {
        var json = """{"schemaVersion":3,"gameBuildId":"1","map":1,"stageIndex":0,"tier":0,"seed":1,"packs":{},"edits":[]}""";

        var written = JsonNode.Parse(LevelFileSerializer.Serialize(LevelFileSerializer.DeserializeWithMigration(json)))!.AsObject();

        Assert.False(written.ContainsKey("baseline"));
        Assert.False(written.ContainsKey("grid"));
        Assert.False(written.ContainsKey("spawn"));
        Assert.False(written.ContainsKey("bossSpawner"));
    }

    public static IEnumerable<object[]> ShippedLevelFiles() =>
        Directory.GetFiles(RepoFile("levels"), "*.mblevel.json")
            .Where(path => (string?)JsonNode.Parse(File.ReadAllText(path))!["baseline"] != "none")
            .Select(path => new object[] { Path.GetFileName(path) });

    [Theory]
    [MemberData(nameof(ShippedLevelFiles))]
    public void ShippedLevelFile_LoadsWithItsEditsUnchanged(string fileName)
    {
        var text = File.ReadAllText(RepoFile(Path.Combine("levels", fileName)));
        var rawEdits = JsonNode.Parse(text)!["edits"]!.AsArray();

        var level = LevelFileSerializer.DeserializeWithMigration(text);

        Assert.Null(level.Grid);
        Assert.Null(level.Spawn);
        Assert.Null(level.BossSpawner);
        Assert.Equal(rawEdits.Count, level.Edits.Count);
        for (var i = 0; i < rawEdits.Count; i++)
        {
            Assert.Equal((string?)rawEdits[i]!["opType"], level.Edits[i].OpType);
            Assert.Equal((string?)rawEdits[i]!["target"], level.Edits[i].Target);
            Assert.Equal((string?)rawEdits[i]!["payload"], level.Edits[i].Payload);
        }
    }

    [Fact]
    public void Grid_ConvertsToLevelStateTheReachabilityValidatorAccepts()
    {
        var level = LevelFileSerializer.Deserialize(FromScratchDocument().ToJsonString());

        var state = level.Grid!.Value.ToLevelState();
        var result = ReachabilityValidator.Validate(state, (0, 0));

        Assert.Equal(4, state.Tiles.Count);
        Assert.Equal(new TileState(0, SlopeDirection.North), state.GetTile(1, 1));
        Assert.Null(state.GetTile(3, 2));
        Assert.Empty(result.Unreachable);
        Assert.True(result.IsReachable((1, 2)));
    }

    [Fact]
    public void Grid_WithDisconnectedCell_ReportsItUnreachable()
    {
        var level = LevelFileSerializer.Deserialize(WithCells((0, 0), (1, 0), (3, 2)));

        var result = ReachabilityValidator.Validate(level.Grid!.Value.ToLevelState(), (0, 0));

        Assert.Equal([(3, 2)], result.Unreachable);
    }
}
