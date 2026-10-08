using System;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

public enum HarnessCommandKind
{
    LoadLevel,
    Screenshot,
    Quit,
}

// A parsed dev-harness command file; see docs/development.md for the wire format.
public readonly record struct HarnessCommand(HarnessCommandKind Kind, string Path)
{
    // Returns false with a human-readable error instead of throwing, so a bad file can never crash the game.
    public static bool TryParse(string json, out HarnessCommand command, out string error)
    {
        command = default;

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

        if (!TryGetString(root, "command", out var name))
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
            case "load-level":
                return TryParseWithPath(root, HarnessCommandKind.LoadLevel, out command, out error);
            case "screenshot":
                return TryParseWithPath(root, HarnessCommandKind.Screenshot, out command, out error);
            default:
                error = $"unknown command '{name}'";
                return false;
        }
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

    private static bool TryGetString(JsonObject root, string field, out string value)
    {
        value = null;
        return root.TryGetPropertyValue(field, out var node)
            && node is JsonValue jsonValue
            && jsonValue.TryGetValue(out value);
    }
}
