using System.Text.Json.Nodes;

namespace MegabonkLevels;

// The outcome of one harness command, written to harness/results/<command file name>; see docs/development.md for the shapes.
public readonly record struct HarnessResult(string Command, bool Ok, JsonObject Result, string Error)
{
    public static HarnessResult Success(string command, JsonObject result) => new(command, true, result, null);

    public static HarnessResult Failure(string command, string error) => new(command, false, null, error);

    public string ToJson()
    {
        var root = new JsonObject { ["command"] = Command, ["ok"] = Ok };
        if (Ok)
        {
            root["result"] = Result == null ? null : JsonNode.Parse(Result.ToJsonString());
        }
        else
        {
            root["error"] = Error;
        }

        return root.ToJsonString();
    }
}

public readonly record struct PlayerSnapshot(float X, float Y, float Z, GridCell? Cell);

// The editor's edit count, whether it differs from the last save, and the outcome of the last save attempt ("none", "saved" or "failed").
public readonly record struct EditsSnapshot(int Count, bool Dirty, string LastSavedName, string SaveStatus)
{
    public JsonObject ToJson() => new()
    {
        ["count"] = Count,
        ["dirty"] = Dirty,
        ["lastSavedName"] = LastSavedName,
        ["saveStatus"] = SaveStatus,
    };
}

// A null field is one the mod cannot source at that moment.
public readonly record struct GameStateSnapshot(
    bool LevelLoaded,
    bool KillFloorArmed,
    bool Editor,
    bool Frozen,
    bool Invulnerable,
    bool SpawnsOff,
    PlayerSnapshot? Player,
    string EditorTool,
    string Selected,
    int? PaletteEntries,
    EditsSnapshot? Edits,
    int ScreenWidth,
    int ScreenHeight)
{
    public JsonObject ToJson() => new()
    {
        ["levelLoaded"] = LevelLoaded,
        ["killFloorArmed"] = KillFloorArmed,
        ["editor"] = Editor,
        ["frozen"] = Frozen,
        ["invulnerable"] = Invulnerable,
        ["spawnsOff"] = SpawnsOff,
        ["player"] = Player is { } p ? PlayerJson(p) : null,
        ["editorTool"] = EditorTool,
        ["selected"] = Selected,
        ["paletteEntries"] = PaletteEntries,
        ["edits"] = Edits?.ToJson(),
        ["screen"] = new JsonArray(ScreenWidth, ScreenHeight),
    };

    private static JsonObject PlayerJson(PlayerSnapshot player) => new()
    {
        ["position"] = new JsonArray(player.X, player.Y, player.Z),
        ["cell"] = player.Cell is { } c ? new JsonArray(c.X, c.Z) : null,
    };
}
