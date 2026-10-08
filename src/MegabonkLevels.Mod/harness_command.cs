using System;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

public enum HarnessCommandKind
{
    LoadLevel,
    Screenshot,
    Quit,
    Freeze,
    Resume,
    Camera,
    CameraClear,
    Invulnerable,
    Vulnerable,
    Heartbeat,
    Cells,
}

// World-space camera position and euler rotation in degrees.
public readonly record struct CameraPose(float X, float Y, float Z, float Rx, float Ry, float Rz);

// A parsed dev-harness command file; see docs/development.md for the wire format.
public readonly record struct HarnessCommand(HarnessCommandKind Kind, string Path, CameraPose Pose = default, bool Enabled = false)
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
            case "camera-clear":
                command = new HarnessCommand(HarnessCommandKind.CameraClear, null);
                error = null;
                return true;
            case "heartbeat":
                return TryParseHeartbeat(root, out command, out error);
            case "cells":
                return TryParseCells(root, out command, out error);
            case "camera":
                return TryParseCamera(root, out command, out error);
            case "load-level":
                return TryParseWithPath(root, HarnessCommandKind.LoadLevel, out command, out error);
            case "screenshot":
                return TryParseWithPath(root, HarnessCommandKind.Screenshot, out command, out error);
            default:
                error = $"unknown command '{name}'";
                return false;
        }
    }

    private static bool TryParseHeartbeat(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        if (!root.TryGetPropertyValue("enabled", out var node) || node is not JsonValue value || !value.TryGetValue(out bool enabled))
        {
            error = "missing boolean field 'enabled'";
            return false;
        }

        command = new HarnessCommand(HarnessCommandKind.Heartbeat, null, Enabled: enabled);
        error = null;
        return true;
    }

    private static bool TryParseCells(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        if (!root.TryGetPropertyValue("enabled", out var node) || node is not JsonValue value || !value.TryGetValue(out bool enabled))
        {
            error = "missing boolean field 'enabled'";
            return false;
        }

        command = new HarnessCommand(HarnessCommandKind.Cells, null, Enabled: enabled);
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

    private static bool TryGetString(JsonObject root, string field, out string value)
    {
        value = null;
        return root.TryGetPropertyValue(field, out var node)
            && node is JsonValue jsonValue
            && jsonValue.TryGetValue(out value);
    }
}
