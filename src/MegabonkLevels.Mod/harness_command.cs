using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

public enum HarnessCommandKind
{
    LoadLevel,
    LoadBundle,
    ShaderReport,
    MaterialDump,
    Screenshot,
    ApplyPendingEdits,
    Quit,
    Freeze,
    Resume,
    Camera,
    CameraClear,
    Invulnerable,
    Vulnerable,
    Kill,
    Spawns,
    CharacterScreen,
    Heartbeat,
    Cells,
    Editor,
    SteamReady,
    State,
    Key,
    Mouse,
    Type,
    Teleport,
    DismissLevelUp,
    ClickWidget,
    UiTree,
    SaveLevel,
    ListLevels,
    QueryObjects,
    Item,
    GrindSlide,
}

// World-space camera position and euler rotation in degrees.
public readonly record struct CameraPose(float X, float Y, float Z, float Rx, float Ry, float Rz);

// Arguments of a key, mouse or type command; fields a command does not use stay at their defaults.
public sealed class InputArgs
{
    public string Action { get; init; }

    public string Key { get; init; }

    public IReadOnlyList<string> Modifiers { get; init; } = Array.Empty<string>();

    public float? X { get; init; }

    public float? Y { get; init; }

    public int Button { get; init; }

    public string Text { get; init; }
}

// Exactly one of Position (world x, y, z) or Cell (grid x, z) is set.
public sealed class TeleportArgs
{
    public float[] Position { get; init; }

    public int[] Cell { get; init; }
}

// The item to read or set; a null Amount reads it.
public sealed class ItemArgs
{
    public string Name { get; init; }

    public int? Amount { get; init; }
}

// The type to enumerate and the public fields to read besides name.
public sealed class QueryArgs
{
    public string TypeName { get; init; }

    public IReadOnlyList<string> Fields { get; init; } = Array.Empty<string>();
}

// A parsed dev-harness command file; see docs/development.md for the wire format.
public readonly record struct HarnessCommand(HarnessCommandKind Kind, string Path, CameraPose Pose = default, bool Enabled = false, string Name = null, InputArgs Input = null, TeleportArgs Teleport = null, int Choice = 0, QueryArgs Query = null, LoadOverrides Overrides = default, ItemArgs Item = null, bool? Held = null)
{
    public const int MaxTypeLength = 200;

    public const int MaxItemAmount = 999;


    // Returns false with a human-readable error instead of throwing, so a bad file can never crash the game.
    public static bool TryParse(string json, out HarnessCommand command, out string error)
    {
        if (!TryParseKnown(json, out command, out error, out var name))
        {
            return false;
        }

        command = command with { Name = name };
        return true;
    }

    private static bool TryParseKnown(string json, out HarnessCommand command, out string error, out string name)
    {
        command = default;
        name = null;

        JsonObject root;
        try
        {
            root = JsonNode.Parse(json) as JsonObject;
        }
        catch (Exception ex) when (ex is JsonException or ArgumentNullException)
        {
            error = $"not valid JSON: {ex.Message}";
            return false;
        }

        if (root == null)
        {
            error = "expected a JSON object";
            return false;
        }

        if (!TryGetString(root, "command", out name))
        {
            error = "missing string field 'command'";
            return false;
        }

        switch (name)
        {
            case "quit":
                command = new HarnessCommand(HarnessCommandKind.Quit, null);
                error = null;
                return true;
            case "freeze":
                command = new HarnessCommand(HarnessCommandKind.Freeze, null);
                error = null;
                return true;
            case "resume":
                command = new HarnessCommand(HarnessCommandKind.Resume, null);
                error = null;
                return true;
            case "invulnerable":
                command = new HarnessCommand(HarnessCommandKind.Invulnerable, null);
                error = null;
                return true;
            case "vulnerable":
                command = new HarnessCommand(HarnessCommandKind.Vulnerable, null);
                error = null;
                return true;
            case "kill":
                command = new HarnessCommand(HarnessCommandKind.Kill, null);
                error = null;
                return true;
            case "steam-ready":
                command = new HarnessCommand(HarnessCommandKind.SteamReady, null);
                error = null;
                return true;
            case "state":
                command = new HarnessCommand(HarnessCommandKind.State, null);
                error = null;
                return true;
            case "camera-clear":
                command = new HarnessCommand(HarnessCommandKind.CameraClear, null);
                error = null;
                return true;
            case "spawns":
                return TryParseEnabledFlag(root, HarnessCommandKind.Spawns, out command, out error);
            case "character-screen":
                return TryParseEnabledFlag(root, HarnessCommandKind.CharacterScreen, out command, out error);
            case "heartbeat":
                return TryParseEnabledFlag(root, HarnessCommandKind.Heartbeat, out command, out error);
            case "cells":
                return TryParseEnabledFlag(root, HarnessCommandKind.Cells, out command, out error);
            case "editor":
                return TryParseEnabledFlag(root, HarnessCommandKind.Editor, out command, out error);
            case "key":
                return TryParseKey(root, out command, out error);
            case "mouse":
                return TryParseMouse(root, out command, out error);
            case "type":
                return TryParseType(root, out command, out error);
            case "click-widget":
                return TryParseClickWidget(root, out command, out error);
            case "save-level":
                return TryParseSaveLevel(root, out command, out error);
            case "list-levels":
                command = new HarnessCommand(HarnessCommandKind.ListLevels, null);
                error = null;
                return true;
            case "query-objects":
                return TryParseQueryObjects(root, out command, out error);
            case "ui-tree":
                return TryParseUiTree(root, out command, out error);
            case "item":
                return TryParseItem(root, out command, out error);
            case "grind-slide":
                return TryParseGrindSlide(root, out command, out error);
            case "teleport":
                return TryParseTeleport(root, out command, out error);
            case "dismiss-levelup":
                return TryParseDismissLevelUp(root, out command, out error);
            case "camera":
                return TryParseCamera(root, out command, out error);
            case "load-level":
                return TryParseLoadLevel(root, out command, out error);
            case "load-bundle":
                return TryParseWithPath(root, HarnessCommandKind.LoadBundle, out command, out error);
            case "material-dump":
                return TryParseMaterialDump(root, out command, out error);
            case "shader-report":
                command = new HarnessCommand(HarnessCommandKind.ShaderReport, null);
                error = null;
                return true;
            case "apply-pending-edits":
                command = new HarnessCommand(HarnessCommandKind.ApplyPendingEdits, null);
                error = null;
                return true;
            case "screenshot":
                return TryParseWithPath(root, HarnessCommandKind.Screenshot, out command, out error);
            default:
                error = $"unknown command '{name}'";
                return false;
        }
    }

    private static bool TryParseEnabledFlag(JsonObject root, HarnessCommandKind kind, out HarnessCommand command, out string error)
    {
        command = default;

        if (!root.TryGetPropertyValue("enabled", out var node) || node is not JsonValue value || !value.TryGetValue(out bool enabled))
        {
            error = "missing boolean field 'enabled'";
            return false;
        }

        command = new HarnessCommand(kind, null, Enabled: enabled);
        error = null;
        return true;
    }

    private static bool TryParseCamera(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        if (!TryGetVector3(root, "position", out var p, out error) || !TryGetVector3(root, "rotation", out var r, out error))
        {
            return false;
        }

        command = new HarnessCommand(HarnessCommandKind.Camera, null, new CameraPose(p[0], p[1], p[2], r[0], r[1], r[2]));
        return true;
    }

    private static bool TryParseItem(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        if (!TryGetString(root, "name", out var name) || name.Length == 0)
        {
            error = "missing non-empty string field 'name'";
            return false;
        }

        int? amount = null;
        if (root.TryGetPropertyValue("amount", out var node) && node != null)
        {
            if (node is not JsonValue value || !value.TryGetValue(out int parsed) || parsed < 0 || parsed > MaxItemAmount)
            {
                error = $"field 'amount' must be an integer from 0 to {MaxItemAmount}";
                return false;
            }

            amount = parsed;
        }

        command = new HarnessCommand(HarnessCommandKind.Item, null, Item: new ItemArgs { Name = name, Amount = amount });
        error = null;
        return true;
    }

    // Forces the slide button the grind gate reads; with no held field the read goes back to the real device.
    private static bool TryParseGrindSlide(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        bool? held = null;
        if (root.TryGetPropertyValue("held", out var node) && node != null)
        {
            if (node is not JsonValue value || !value.TryGetValue(out bool parsed))
            {
                error = "field 'held' must be a boolean";
                return false;
            }

            held = parsed;
        }

        command = new HarnessCommand(HarnessCommandKind.GrindSlide, null, Held: held);
        error = null;
        return true;
    }

    private static bool TryParseTeleport(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        var hasPosition = root.ContainsKey("position");
        var hasCell = root.ContainsKey("cell");
        if (hasPosition == hasCell)
        {
            error = "give exactly one of 'position' (3 numbers) or 'cell' (2 integers)";
            return false;
        }

        TeleportArgs args;
        if (hasPosition)
        {
            if (!TryGetVector3(root, "position", out var position, out error))
            {
                return false;
            }

            args = new TeleportArgs { Position = position };
        }
        else
        {
            if (!TryGetCell(root, out var cell, out error))
            {
                return false;
            }

            args = new TeleportArgs { Cell = cell };
        }

        command = new HarnessCommand(HarnessCommandKind.Teleport, null, Teleport: args);
        return true;
    }

    private static bool TryGetCell(JsonObject root, out int[] cell, out string error)
    {
        cell = new int[2];
        error = "field 'cell' must be an array of 2 integers";

        if (root["cell"] is not JsonArray { Count: 2 } array)
        {
            return false;
        }

        for (var i = 0; i < 2; i++)
        {
            if (array[i] is not JsonValue value || !value.TryGetValue(out cell[i]))
            {
                return false;
            }
        }

        error = null;
        return true;
    }

    private static bool TryParseDismissLevelUp(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;
        var choice = 0;

        if (root.TryGetPropertyValue("choice", out var node) && node != null
            && (node is not JsonValue value || !value.TryGetValue(out choice) || choice < 0))
        {
            error = "field 'choice' must be a non-negative integer";
            return false;
        }

        command = new HarnessCommand(HarnessCommandKind.DismissLevelUp, null, Choice: choice);
        error = null;
        return true;
    }

    private static bool TryParseKey(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        if (!TryReadAction(root, new[] { "tap", "down", "up" }, out var action, out error))
        {
            return false;
        }

        if (!TryGetString(root, "key", out var key))
        {
            error = "missing string field 'key'";
            return false;
        }

        if (!KeyNames.IsValid(key))
        {
            error = $"unknown key '{key}'; names are case-sensitive UnityEngine.KeyCode members from the documented list";
            return false;
        }

        if (!TryReadModifiers(root, action, out var modifiers, out error))
        {
            return false;
        }

        command = new HarnessCommand(HarnessCommandKind.Key, null, Input: new InputArgs { Action = action, Key = key, Modifiers = modifiers });
        return true;
    }

    private static bool TryReadModifiers(JsonObject root, string action, out string[] modifiers, out string error)
    {
        modifiers = Array.Empty<string>();
        error = null;

        if (!root.TryGetPropertyValue("modifiers", out var node) || node == null)
        {
            return true;
        }

        if (action != "tap")
        {
            error = "'modifiers' is only valid for action 'tap'";
            return false;
        }

        if (node is not JsonArray array)
        {
            error = "field 'modifiers' must be an array of key names";
            return false;
        }

        var names = new List<string>();
        foreach (var item in array)
        {
            if (item is not JsonValue value || !value.TryGetValue(out string name))
            {
                error = "field 'modifiers' must be an array of key names";
                return false;
            }

            if (!KeyNames.IsValid(name))
            {
                error = $"unknown modifier key '{name}'";
                return false;
            }

            names.Add(name);
        }

        modifiers = names.ToArray();
        return true;
    }

    private static bool TryParseMouse(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        if (!TryReadAction(root, new[] { "move", "click", "down", "up", "clear" }, out var action, out error))
        {
            return false;
        }

        float? x = null;
        float? y = null;
        var button = 0;
        if (action != "clear")
        {
            var coordinatesRequired = action == "move";
            if (!TryReadCoordinate(root, "x", coordinatesRequired || root.ContainsKey("y"), out x, out error)
                || !TryReadCoordinate(root, "y", coordinatesRequired || root.ContainsKey("x"), out y, out error))
            {
                return false;
            }

            if (action != "move" && !TryReadButton(root, out button, out error))
            {
                return false;
            }
        }

        command = new HarnessCommand(HarnessCommandKind.Mouse, null, Input: new InputArgs { Action = action, X = x, Y = y, Button = button });
        return true;
    }

    private static bool TryReadAction(JsonObject root, string[] allowed, out string action, out string error)
    {
        if (!TryGetString(root, "action", out action))
        {
            error = $"missing string field 'action' ({string.Join(", ", allowed)})";
            return false;
        }

        if (Array.IndexOf(allowed, action) < 0)
        {
            error = $"unknown action '{action}'; expected {string.Join(", ", allowed)}";
            return false;
        }

        error = null;
        return true;
    }

    private static bool TryReadCoordinate(JsonObject root, string field, bool required, out float? value, out string error)
    {
        value = null;
        error = null;

        if (!root.TryGetPropertyValue(field, out var node) || node == null)
        {
            if (required)
            {
                error = $"missing number field '{field}'";
            }

            return !required;
        }

        if (node is not JsonValue json || !json.TryGetValue(out float number))
        {
            error = $"field '{field}' must be a number";
            return false;
        }

        value = number;
        return true;
    }

    private static bool TryReadButton(JsonObject root, out int button, out string error)
    {
        button = 0;
        error = null;

        if (!root.TryGetPropertyValue("button", out var node) || node == null)
        {
            return true;
        }

        if (node is not JsonValue json || !json.TryGetValue(out button) || button < 0 || button > 2)
        {
            error = "field 'button' must be 0 (left), 1 (right) or 2 (middle)";
            return false;
        }

        return true;
    }

    private static bool TryParseClickWidget(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        if (!TryGetString(root, "name", out var name) || name.Length == 0)
        {
            error = "missing non-empty string field 'name'";
            return false;
        }

        command = new HarnessCommand(HarnessCommandKind.ClickWidget, null, Input: new InputArgs { Action = "click-widget", Text = name });
        error = null;
        return true;
    }

    private static bool TryParseMaterialDump(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;
        string target = null;

        if (root.TryGetPropertyValue("object", out var node) && node != null
            && (node is not JsonValue value || !value.TryGetValue(out target) || target.Trim().Length == 0))
        {
            error = "field 'object' must be a non-empty string";
            return false;
        }

        command = new HarnessCommand(HarnessCommandKind.MaterialDump, target);
        error = null;
        return true;
    }

    private static bool TryParseSaveLevel(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;
        string level = null;

        if (root.TryGetPropertyValue("level", out var node) && node != null
            && (node is not JsonValue value || !value.TryGetValue(out level) || level.Trim().Length == 0))
        {
            error = "field 'level' must be a non-empty string";
            return false;
        }

        command = new HarnessCommand(HarnessCommandKind.SaveLevel, level);
        error = null;
        return true;
    }

    private static bool TryParseQueryObjects(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        if (!TryGetString(root, "type", out var typeName) || typeName.Length == 0)
        {
            error = "missing non-empty string field 'type'";
            return false;
        }

        var fields = new List<string>();
        if (root.TryGetPropertyValue("fields", out var node) && node != null)
        {
            error = "field 'fields' must be an array of non-empty field names";
            if (node is not JsonArray array)
            {
                return false;
            }

            foreach (var item in array)
            {
                if (item is not JsonValue value || !value.TryGetValue(out string field) || field.Length == 0)
                {
                    return false;
                }

                fields.Add(field);
            }
        }

        command = new HarnessCommand(HarnessCommandKind.QueryObjects, null, Query: new QueryArgs { TypeName = typeName, Fields = fields });
        error = null;
        return true;
    }

    private static bool TryParseUiTree(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        if (!TryReadCoordinate(root, "x", root.ContainsKey("y"), out var x, out error)
            || !TryReadCoordinate(root, "y", root.ContainsKey("x"), out var y, out error))
        {
            return false;
        }

        command = new HarnessCommand(HarnessCommandKind.UiTree, null, Input: new InputArgs { Action = "ui-tree", X = x, Y = y });
        return true;
    }

    private static bool TryParseType(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        if (!TryGetString(root, "text", out var text) || text.Length == 0)
        {
            error = "missing non-empty string field 'text'";
            return false;
        }

        if (text.Length > MaxTypeLength)
        {
            error = $"field 'text' is {text.Length} characters; the maximum is {MaxTypeLength}";
            return false;
        }

        command = new HarnessCommand(HarnessCommandKind.Type, null, Input: new InputArgs { Action = "type", Text = text });
        error = null;
        return true;
    }

    private static bool TryGetVector3(JsonObject root, string field, out float[] values, out string error)
    {
        values = new float[3];
        error = $"missing field '{field}' as an array of 3 numbers";

        if (!root.TryGetPropertyValue(field, out var node) || node is not JsonArray { Count: 3 } array)
        {
            return false;
        }

        for (var i = 0; i < 3; i++)
        {
            if (array[i] is not JsonValue value || !value.TryGetValue(out values[i]))
            {
                return false;
            }
        }

        error = null;
        return true;
    }

    private static bool TryParseWithPath(JsonObject root, HarnessCommandKind kind, out HarnessCommand command, out string error)
    {
        command = default;

        if (!TryGetString(root, "path", out var path) || string.IsNullOrWhiteSpace(path))
        {
            error = "missing non-empty string field 'path'";
            return false;
        }

        command = new HarnessCommand(kind, path);
        error = null;
        return true;
    }

    private static bool TryParseLoadLevel(JsonObject root, out HarnessCommand command, out string error)
    {
        if (!TryParseWithPath(root, HarnessCommandKind.LoadLevel, out command, out error))
        {
            return false;
        }

        if (!TryGetOptionalInt(root, "map", out var map, out error)
            || !TryGetOptionalInt(root, "stageIndex", out var stageIndex, out error)
            || !TryGetOptionalInt(root, "tier", out var tier, out error)
            || !TryGetOptionalInt(root, "seed", out var seed, out error))
        {
            command = default;
            return false;
        }

        if (map is int value && !Enum.IsDefined(typeof(EMap), value))
        {
            command = default;
            error = $"field 'map' must be one of {string.Join(", ", Enum.GetValues<EMap>().Select(m => (int)m))}, got {value}";
            return false;
        }

        command = command with { Overrides = new LoadOverrides(map, stageIndex, tier, seed, TryGetString(root, "character", out var character) ? character : null) };
        return true;
    }

    private static bool TryGetOptionalInt(JsonObject root, string field, out int? value, out string error)
    {
        value = null;
        error = null;

        if (!root.TryGetPropertyValue(field, out var node))
        {
            return true;
        }

        if (node is JsonValue jsonValue && jsonValue.TryGetValue(out int parsed))
        {
            value = parsed;
            return true;
        }

        error = $"field '{field}' must be an integer";
        return false;
    }

    private static bool TryGetString(JsonObject root, string field, out string value)
    {
        value = null;
        return root.TryGetPropertyValue(field, out var node)
            && node is JsonValue jsonValue
            && jsonValue.TryGetValue(out value);
    }
}
