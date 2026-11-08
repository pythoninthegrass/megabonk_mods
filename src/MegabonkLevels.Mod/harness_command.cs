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
    RestartRun,
    PressDeathConfirm,
    PressSummaryRestart,
    Damage,
    Spawns,
    CharacterScreen,
    Heartbeat,
    Cells,
    Hud,
    Editor,
    SteamReady,
    State,
    Key,
    Mouse,
    Type,
    Teleport,
    DismissLevelUp,
    DismissOffers,
    Interact,
    ClickWidget,
    UiTree,
    SaveLevel,
    NewLevel,
    ListLevels,
    Palette,
    QueryObjects,
    Item,
    GrindSlide,
    FallDamage,
    MusicProbe,
    Perf,
    KillEnemies,
    Coordinates,
}

// Arguments of a new-level command: the blank from-scratch level's map, stage, tier and square grid size.
public readonly record struct NewLevelArgs(int Map, int StageIndex, int Tier, int Size);

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

    public string Variant { get; init; }

    public float? Value { get; init; }
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

// Which interactable to activate: null Type means nearest, null MaxDistance means unbounded, Force bypasses CanInteract.
public sealed class InteractArgs
{
    public string Type { get; init; }

    public float? MaxDistance { get; init; }

    public bool Force { get; init; }
}

public sealed class DamageArgs
{
    public int Amount { get; init; }

    public bool Nonlethal { get; init; } = true;
}

// The perf-sampler action and its one argument: count for spawn, value for timescale, target/enabled for toggle.
public sealed class PerfArgs
{
    public string Action { get; init; }

    public string Target { get; init; }

    public bool Enabled { get; init; } = true;

    public int Count { get; init; }

    public float? Value { get; init; }

    public int? Hp { get; init; }
}

// The type to enumerate, the public fields to read besides name, and how many levels of nested assets to expand.
public sealed class QueryArgs
{
    public string TypeName { get; init; }

    public IReadOnlyList<string> Fields { get; init; } = Array.Empty<string>();

    public int Depth { get; init; }
}

// A parsed dev-harness command file; see docs/development.md for the wire format.
public readonly record struct HarnessCommand(HarnessCommandKind Kind, string Path, CameraPose Pose = default, bool Enabled = false, string Name = null, InputArgs Input = null, TeleportArgs Teleport = null, int Choice = 0, QueryArgs Query = null, LoadOverrides Overrides = default, ItemArgs Item = null, bool? Held = null, DamageArgs Damage = null, PerfArgs Perf = null, int? Offer = null, bool Skip = false, InteractArgs Interact = null, NewLevelArgs? NewLevel = null, string KillTarget = null)
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
            case "damage":
                return TryParseDamage(root, out command, out error);
            case "kill-enemies":
                return TryParseKillEnemies(root, out command, out error);
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
            case "restart-run":
                command = new HarnessCommand(HarnessCommandKind.RestartRun, null);
                error = null;
                return true;
            case "press-death-confirm":
                command = new HarnessCommand(HarnessCommandKind.PressDeathConfirm, null);
                error = null;
                return true;
            case "press-summary-restart":
                command = new HarnessCommand(HarnessCommandKind.PressSummaryRestart, null);
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
            case "hud":
                return TryParseEnabledFlag(root, HarnessCommandKind.Hud, out command, out error);
            case "coordinates":
                return TryParseEnabledFlag(root, HarnessCommandKind.Coordinates, out command, out error);
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
            case "new-level":
                return TryParseNewLevel(root, out command, out error);
            case "list-levels":
                command = new HarnessCommand(HarnessCommandKind.ListLevels, null);
                error = null;
                return true;
            case "palette":
                command = new HarnessCommand(HarnessCommandKind.Palette, null);
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
            case "fall-damage":
                command = new HarnessCommand(HarnessCommandKind.FallDamage, null);
                error = null;
                return true;
            case "music-probe":
                return TryParseMusicProbe(root, out command, out error);
            case "perf":
                return TryParsePerf(root, out command, out error);
            case "teleport":
                return TryParseTeleport(root, out command, out error);
            case "dismiss-levelup":
                return TryParseDismissLevelUp(root, out command, out error);
            case "dismiss-offers":
                return TryParseDismissOffers(root, out command, out error);
            case "interact":
                return TryParseInteract(root, out command, out error);
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

    private static bool TryParseDamage(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;
        if (root["amount"] is not JsonValue amountValue || !amountValue.TryGetValue(out int amount) || amount is < 1 or > 99)
        {
            error = "field 'amount' must be an integer from 1 to 99";
            return false;
        }

        var nonlethal = true;
        if (root.TryGetPropertyValue("nonlethal", out var node)
            && (node is not JsonValue value || !value.TryGetValue(out nonlethal)))
        {
            error = "field 'nonlethal' must be a boolean";
            return false;
        }

        command = new HarnessCommand(HarnessCommandKind.Damage, null, Damage: new DamageArgs { Amount = amount, Nonlethal = nonlethal });
        error = null;
        return true;
    }

    private static bool TryParseKillEnemies(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;
        if (!TryGetString(root, "target", out var target) || Array.IndexOf(EnemyKillTargets.Names, target) < 0)
        {
            error = $"field 'target' must be one of {string.Join(", ", EnemyKillTargets.Names)}";
            return false;
        }

        command = new HarnessCommand(HarnessCommandKind.KillEnemies, null, KillTarget: target);
        error = null;
        return true;
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

    // The TASK-024.01 runtime-music probe; action selects the phase and path names the mp3 for decode and play.
    private static bool TryParseMusicProbe(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        if (!TryGetString(root, "action", out var action) || action.Length == 0)
        {
            error = "missing string field 'action' (decode, play, stop, status, detach)";
            return false;
        }

        var allowed = new[]
        {
            "decode", "play", "stop", "status", "restart", "duck", "unduck", "pause", "unpause",
            "mute", "unmute", "clip-null", "pitch", "lowpass", "detach", "native-info", "native-tone", "native-play",
            "radio-next", "seek", "menu-music", "stage-music",
        };
        if (Array.IndexOf(allowed, action) < 0)
        {
            error = $"unknown action '{action}'; expected {string.Join(", ", allowed)}";
            return false;
        }

        if (!TryGetOptionalFloat(root, "value", out var value, out error))
        {
            return false;
        }

        TryGetString(root, "path", out var path);
        TryGetString(root, "variant", out var variant);
        command = new HarnessCommand(
            HarnessCommandKind.MusicProbe,
            path,
            Input: new InputArgs { Action = action, Variant = variant, Value = value });
        error = null;
        return true;
    }

    // The frame-time profiler: spawn sizes an enemy population, timescale holds MyTime.timeScale, toggle switches one tick or probe.
    private static bool TryParsePerf(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        if (!TryGetString(root, "action", out var action) || action.Length == 0)
        {
            error = "missing string field 'action' (report, status, start, reset, spawn, timescale, toggle, vsync, render, physics, animation, health, census)";
            return false;
        }

        var allowed = new[] { "report", "status", "start", "reset", "spawn", "timescale", "toggle", "vsync", "render", "physics", "animation", "health", "census" };
        if (Array.IndexOf(allowed, action) < 0)
        {
            error = $"unknown action '{action}'; expected {string.Join(", ", allowed)}";
            return false;
        }

        var count = 0;
        if (action == "spawn")
        {
            if (!TryGetOptionalInt(root, "count", out var parsedCount, out error))
            {
                return false;
            }

            count = parsedCount ?? 0;
            if (!PerfLimits.ValidSpawnCount(count))
            {
                error = $"field 'count' must be an integer from 1 to {PerfSpawnPlan.MaxEnemies}";
                return false;
            }
        }

        if (!TryGetOptionalFloat(root, "value", out var value, out error))
        {
            return false;
        }

        if (action == "timescale" && value.HasValue && !PerfLimits.ValidTimeScale(value.Value))
        {
            error = $"field 'value' must be a number from {PerfLimits.MinTimeScale} to {PerfLimits.MaxTimeScale}";
            return false;
        }

        int? hp = null;
        if (action == "health")
        {
            if (!TryGetOptionalInt(root, "hp", out var parsedHp, out error))
            {
                return false;
            }

            hp = parsedHp;
            if (hp.HasValue && !PerfLimits.ValidPlayerHp(hp.Value))
            {
                error = $"field 'hp' must be an integer from 1 to {PerfLimits.MaxPlayerHp}";
                return false;
            }
        }

        TryGetString(root, "target", out var target);
        var enabled = true;
        if (action is "toggle" or "vsync" or "render" or "physics" or "animation")
        {
            if (action == "toggle" && string.IsNullOrEmpty(target))
            {
                error = "field 'target' must name a perf tick or a probe";
                return false;
            }

            if (!root.TryGetPropertyValue("enabled", out var flag) || flag is not JsonValue flagValue || !flagValue.TryGetValue(out enabled))
            {
                error = "missing boolean field 'enabled'";
                return false;
            }
        }

        command = new HarnessCommand(
            HarnessCommandKind.Perf,
            null,
            Perf: new PerfArgs { Action = action, Target = target, Enabled = enabled, Count = count, Value = value, Hp = hp });
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

    private static bool TryParseDismissOffers(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;
        int? offer = null;
        var skip = false;

        if (root.TryGetPropertyValue("choice", out var choiceNode) && choiceNode != null)
        {
            if (choiceNode is not JsonValue choiceValue || !choiceValue.TryGetValue(out int choice) || choice < 0)
            {
                error = "field 'choice' must be a non-negative integer";
                return false;
            }

            offer = choice;
        }

        if (root.TryGetPropertyValue("skip", out var skipNode) && skipNode != null)
        {
            if (skipNode is not JsonValue skipValue || !skipValue.TryGetValue(out skip))
            {
                error = "field 'skip' must be a boolean";
                return false;
            }
        }

        command = new HarnessCommand(HarnessCommandKind.DismissOffers, null, Offer: offer, Skip: skip);
        error = null;
        return true;
    }

    private static bool TryParseInteract(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;

        string type = null;
        if (root.TryGetPropertyValue("type", out var typeNode) && typeNode != null)
        {
            if (typeNode is not JsonValue typeValue || !typeValue.TryGetValue(out type) || string.IsNullOrWhiteSpace(type))
            {
                error = "field 'type' must be a non-empty string";
                return false;
            }
        }

        float? maxDistance = null;
        var parsed = 0f;
        if (root.TryGetPropertyValue("maxDistance", out var distanceNode) && distanceNode != null)
        {
            if (distanceNode is not JsonValue distanceValue || !distanceValue.TryGetValue(out parsed) || float.IsNaN(parsed) || float.IsInfinity(parsed) || parsed <= 0)
            {
                error = "field 'maxDistance' must be a positive number";
                return false;
            }

            maxDistance = parsed;
        }

        var force = false;
        if (root.TryGetPropertyValue("force", out var forceNode) && forceNode != null)
        {
            if (forceNode is not JsonValue forceValue || !forceValue.TryGetValue(out force))
            {
                error = "field 'force' must be a boolean";
                return false;
            }
        }

        command = new HarnessCommand(HarnessCommandKind.Interact, null, Interact: new InteractArgs { Type = type, MaxDistance = maxDistance, Force = force });
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

        if (!TryReadAction(root, new[] { "move", "click", "down", "up", "scroll", "clear" }, out var action, out error))
        {
            return false;
        }

        float? x = null;
        float? y = null;
        float? delta = null;
        var button = 0;
        if (action != "clear")
        {
            var coordinatesRequired = action == "move";
            if (!TryReadCoordinate(root, "x", coordinatesRequired || root.ContainsKey("y"), out x, out error)
                || !TryReadCoordinate(root, "y", coordinatesRequired || root.ContainsKey("x"), out y, out error))
            {
                return false;
            }

            if (action == "scroll")
            {
                if (!TryReadCoordinate(root, "delta", true, out delta, out error))
                {
                    return false;
                }
            }
            else if (action != "move" && !TryReadButton(root, out button, out error))
            {
                return false;
            }
        }

        command = new HarnessCommand(HarnessCommandKind.Mouse, null, Input: new InputArgs { Action = action, X = x, Y = y, Button = button, Value = delta });
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

    private static bool TryParseNewLevel(JsonObject root, out HarnessCommand command, out string error)
    {
        command = default;
        string level = null;

        if (root.TryGetPropertyValue("level", out var node) && node != null
            && (node is not JsonValue value || !value.TryGetValue(out level) || level.Trim().Length == 0))
        {
            error = "field 'level' must be a non-empty string";
            return false;
        }

        if (!TryGetOptionalInt(root, "map", out var map, out error)
            || !TryGetOptionalInt(root, "stageIndex", out var stageIndex, out error)
            || !TryGetOptionalInt(root, "tier", out var tier, out error)
            || !TryGetOptionalInt(root, "size", out var size, out error))
        {
            return false;
        }

        var mapValue = map ?? (int)EMap.Forest;
        if (!Enum.IsDefined(typeof(EMap), mapValue) || mapValue == (int)EMap.None)
        {
            error = $"field 'map' must be one of {string.Join(", ", Enum.GetValues<EMap>().Where(m => m != EMap.None).Select(m => (int)m))}, got {mapValue}";
            return false;
        }

        if (stageIndex is < 0)
        {
            error = "field 'stageIndex' must not be negative";
            return false;
        }

        if (tier is < 0)
        {
            error = "field 'tier' must not be negative";
            return false;
        }

        var sizeValue = size ?? BlankLevel.DefaultSize;
        if (sizeValue < BlankLevel.MinimumSize)
        {
            error = $"field 'size' must be at least {BlankLevel.MinimumSize}, got {sizeValue}";
            return false;
        }

        command = new HarnessCommand(HarnessCommandKind.NewLevel, level, NewLevel: new NewLevelArgs(mapValue, stageIndex ?? 0, tier ?? 0, sizeValue));
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

        var depth = 0;
        if (root.TryGetPropertyValue("depth", out var depthNode) && depthNode != null)
        {
            error = $"field 'depth' must be an integer from 0 to {AssetDump.MaxDepth}";
            if (depthNode is not JsonValue depthValue || !depthValue.TryGetValue(out depth) || depth < 0 || depth > AssetDump.MaxDepth)
            {
                return false;
            }
        }

        command = new HarnessCommand(HarnessCommandKind.QueryObjects, null, Query: new QueryArgs { TypeName = typeName, Fields = fields, Depth = depth });
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
            || !TryGetSeedField(root, out var seed, out var unseeded, out error))
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

        command = command with { Overrides = new LoadOverrides(map, stageIndex, tier, seed, TryGetString(root, "character", out var character) ? character : null, unseeded) };
        return true;
    }

    // "seed": 424242 forces that seed, "seed": null lets the game roll its own, and no seed field keeps the level file's.
    private static bool TryGetSeedField(JsonObject root, out int? seed, out bool unseeded, out string error)
    {
        seed = null;
        unseeded = false;
        error = null;

        if (!root.TryGetPropertyValue("seed", out var node))
        {
            return true;
        }

        if (node is null)
        {
            unseeded = true;
            return true;
        }

        if (node is JsonValue jsonValue && jsonValue.TryGetValue(out int parsed))
        {
            seed = parsed;
            return true;
        }

        error = "field 'seed' must be an integer or null";
        return false;
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

    private static bool TryGetOptionalFloat(JsonObject root, string field, out float? value, out string error)
    {
        value = null;
        error = null;

        if (!root.TryGetPropertyValue(field, out var node) || node == null)
        {
            return true;
        }

        if (node is JsonValue jsonValue && jsonValue.TryGetValue(out float parsed))
        {
            value = parsed;
            return true;
        }

        error = $"field '{field}' must be a number";
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
