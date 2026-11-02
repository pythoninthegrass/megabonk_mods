using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

public static class LevelSettings
{
    public static readonly string[] Fields = { "playerStart", "bossSpawnPosition", "killFloorY", "maxSlopeAngle", "grindRequiresSlide", "fallDamageCharacter", "noGrass", "music", "title", "description", "mapDescription", "allowedCharacters", "map", "stageIndex", "tier", "seed" };
    private static readonly string[] TextFields = { "music", "title", "description", "mapDescription", "fallDamageCharacter" };

    public static string Read(LevelFile level, string field)
    {
        var node = JsonNode.Parse(LevelFileSerializer.Serialize(level))[field];
        return TextFields.Contains(field) && node != null ? node.GetValue<string>() : node?.ToJsonString() ?? "null";
    }

    public static LevelFile Change(LevelFile level, string field, string text)
    {
        if (!Fields.Contains(field))
        {
            throw new ArgumentException("This field is derived or not editable.");
        }
        try
        {
            var root = JsonNode.Parse(LevelFileSerializer.Serialize(level)).AsObject();
            root[field] = TextFields.Contains(field) ? (string.IsNullOrEmpty(text) ? null : JsonValue.Create(text)) : JsonNode.Parse(text);
            var changed = LevelFileSerializer.Deserialize(root.ToJsonString());
            Validate(changed);
            if ((changed.Map != level.Map || changed.StageIndex != level.StageIndex || changed.Seed != level.Seed || changed.Tier != level.Tier) && level.Edits.Count > 0)
            {
                throw new ArgumentException("Generation changes require a fresh level: existing edits target this map and seed.");
            }
            return changed;
        }
        catch (Exception ex) when (ex is JsonException || ex is InvalidOperationException || ex is FormatException)
        {
            throw new ArgumentException("Invalid value for " + field + ". Use JSON for numbers, booleans and arrays.", ex);
        }
    }

    public static void Validate(LevelFile level)
    {
        ValidatePosition(level.PlayerStart);
        ValidatePosition(level.BossSpawnPosition);
        if (level.KillFloorY is { } floor && !float.IsFinite(floor)
            || level.MaxSlopeAngle is { } slope && (!float.IsFinite(slope) || slope < 0 || slope >= 90))
        {
            throw new ArgumentException("Kill floor must be finite; slope angle must be in [0,90).");
        }
        if (!Enum.IsDefined(typeof(EMap), level.Map) || level.Map == EMap.None || level.StageIndex < 0 || level.Tier < 0)
        {
            throw new ArgumentException("Invalid generation settings.");
        }
        if (!string.IsNullOrEmpty(level.Music) && !LevelMusicReference.TryParse(level.Music, out _))
        {
            throw new ArgumentException("Music must be a bundle: or track: reference.");
        }
        if (level.AllowedCharacters != null && level.AllowedCharacters.Any(name => !new[] { "calcium", "tony", "tonymczoom" }.Contains(name, StringComparer.OrdinalIgnoreCase)))
        {
            throw new ArgumentException("Allowed characters are calcium, tony and tonymczoom.");
        }
        if (!string.IsNullOrEmpty(level.FallDamageCharacter) && FallDamagePolicy.ReferenceCharacter(level.FallDamageCharacter) == null)
        {
            throw new ArgumentException("The fall damage character must be calcium, tony or tonymczoom.");
        }
    }

    private static void ValidatePosition(IReadOnlyList<float> position)
    {
        if (position != null && (position.Count != 3 || position.Any(value => !float.IsFinite(value))))
        {
            throw new ArgumentException("A marker needs three finite coordinates, or null to use the default.");
        }
    }

    public static LevelFile CopyTo(LevelFile settings, LevelFile destination) => destination with
    {
        NoGrass = settings.NoGrass, PlayerStart = settings.PlayerStart, BossSpawnPosition = settings.BossSpawnPosition,
        KillFloorY = settings.KillFloorY, MaxSlopeAngle = settings.MaxSlopeAngle, GrindRequiresSlide = settings.GrindRequiresSlide,
        Music = settings.Music, Title = settings.Title, Description = settings.Description, MapDescription = settings.MapDescription,
        AllowedCharacters = settings.AllowedCharacters, Map = settings.Map, StageIndex = settings.StageIndex, Tier = settings.Tier, Seed = settings.Seed,
    };
}

public sealed class LevelSettingsHistory
{
    private readonly Stack<LevelFile> _undo = new();
    private readonly Stack<LevelFile> _redo = new();
    private LevelFile _saved;
    public LevelFile Current { get; private set; }
    public bool Dirty => !Current.Equals(_saved);
    public bool CanUndo => _undo.Count > 0;
    public bool CanRedo => _redo.Count > 0;

    public LevelSettingsHistory(LevelFile initial) => Current = _saved = initial with { Edits = Array.Empty<EditOp>() };

    public void Apply(string field, string value, bool hasEdits = false)
    {
        var candidate = Current with { Edits = hasEdits ? new[] { new EditOp() } : Array.Empty<EditOp>() };
        var next = LevelSettings.Change(candidate, field, value) with { Edits = Array.Empty<EditOp>() };
        if (next.Equals(Current))
        {
            return;
        }
        _undo.Push(Current);
        Current = next;
        _redo.Clear();
    }

    public bool Undo()
    {
        if (!CanUndo) return false;
        _redo.Push(Current);
        Current = _undo.Pop();
        return true;
    }

    public bool Redo()
    {
        if (!CanRedo) return false;
        _undo.Push(Current);
        Current = _redo.Pop();
        return true;
    }

    public void MarkSaved() => _saved = Current;
}
