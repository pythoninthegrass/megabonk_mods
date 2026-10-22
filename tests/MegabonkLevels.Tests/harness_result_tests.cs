using System.Text.Json.Nodes;

namespace MegabonkLevels.Tests;

public class HarnessResultTests
{
    [Fact]
    public void Success_WithObject_SerializesCommandOkAndResult()
    {
        var json = HarnessResult.Success("state", new JsonObject { ["levelLoaded"] = true }).ToJson();

        var root = JsonNode.Parse(json)!.AsObject();
        Assert.Equal("state", (string?)root["command"]);
        Assert.True((bool?)root["ok"]);
        Assert.True((bool?)root["result"]!["levelLoaded"]);
        Assert.False(root.ContainsKey("error"));
    }

    [Fact]
    public void Success_WithNullResult_SerializesJsonNull()
    {
        var json = HarnessResult.Success("freeze", null).ToJson();

        var root = JsonNode.Parse(json)!.AsObject();
        Assert.True(root.ContainsKey("result"));
        Assert.Null(root["result"]);
        Assert.True((bool?)root["ok"]);
    }

    [Fact]
    public void Failure_SerializesCommandOkFalseAndError()
    {
        var json = HarnessResult.Failure("load-level", "no such file").ToJson();

        var root = JsonNode.Parse(json)!.AsObject();
        Assert.Equal("load-level", (string?)root["command"]);
        Assert.False((bool?)root["ok"]);
        Assert.Equal("no such file", (string?)root["error"]);
        Assert.False(root.ContainsKey("result"));
    }

    [Fact]
    public void Failure_WithNullCommand_WritesJsonNullCommand()
    {
        var json = HarnessResult.Failure(null, "not valid JSON").ToJson();

        var root = JsonNode.Parse(json)!.AsObject();
        Assert.True(root.ContainsKey("command"));
        Assert.Null(root["command"]);
    }

    [Fact]
    public void Failure_WithSpecialCharacters_RoundTripsTheError()
    {
        var error = "bad \"path\" C:\\shots\\one.png\nline two\ttab é";

        var json = HarnessResult.Failure("screenshot", error).ToJson();

        Assert.Equal(error, (string?)JsonNode.Parse(json)!["error"]);
    }

    [Fact]
    public void ToJson_CalledTwice_ReturnsTheSameText()
    {
        var result = HarnessResult.Success("state", new JsonObject { ["editor"] = false });

        Assert.Equal(result.ToJson(), result.ToJson());
    }

    [Fact]
    public void GameStateSnapshot_WithEveryFieldSourced_SerializesAllFields()
    {
        var snapshot = new GameStateSnapshot(
            LevelLoaded: true,
            KillFloorArmed: true,
            Editor: true,
            Frozen: true,
            Invulnerable: false,
            Player: new PlayerSnapshot(1.5f, 2f, -3f, new GridCell(4, 5, true)),
            EditorTool: "Select",
            Selected: "object:tree-1",
            PaletteEntries: 12,
            ScreenWidth: 1920,
            ScreenHeight: 1080);

        var root = snapshot.ToJson();

        Assert.True((bool?)root["levelLoaded"]);
        Assert.True((bool?)root["killFloorArmed"]);
        Assert.True((bool?)root["editor"]);
        Assert.True((bool?)root["frozen"]);
        Assert.False((bool?)root["invulnerable"]);
        Assert.Equal(new[] { 1.5f, 2f, -3f }, root["player"]!["position"]!.AsArray().Select(n => (float)n!).ToArray());
        Assert.Equal(new[] { 4, 5 }, root["player"]!["cell"]!.AsArray().Select(n => (int)n!).ToArray());
        Assert.Equal("Select", (string?)root["editorTool"]);
        Assert.Equal("object:tree-1", (string?)root["selected"]);
        Assert.Equal(12, (int?)root["paletteEntries"]);
        Assert.Equal(new[] { 1920, 1080 }, root["screen"]!.AsArray().Select(n => (int)n!).ToArray());
    }

    [Fact]
    public void GameStateSnapshot_WithUnsourcedFields_SerializesJsonNulls()
    {
        var snapshot = new GameStateSnapshot(false, false, false, false, false, null, null, null, null, 800, 600);

        var root = snapshot.ToJson();

        foreach (var field in new[] { "player", "editorTool", "selected", "paletteEntries" })
        {
            Assert.True(root.ContainsKey(field), field);
            Assert.Null(root[field]);
        }
    }

    [Fact]
    public void GameStateSnapshot_PlayerOutsideTheGrid_SerializesNullCell()
    {
        var snapshot = new GameStateSnapshot(true, false, false, false, false, new PlayerSnapshot(0f, 0f, 0f, null), null, null, null, 800, 600);

        var player = snapshot.ToJson()["player"]!.AsObject();

        Assert.True(player.ContainsKey("cell"));
        Assert.Null(player["cell"]);
    }
}
