using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace MegabonkLevels;

public sealed class CamelCaseSlopeConverter : JsonStringEnumConverter
{
    public CamelCaseSlopeConverter() : base(JsonNamingPolicy.CamelCase)
    {
    }
}

public readonly record struct AuthoredCell(
    int X,
    int Z,
    int Height,
    [property: JsonConverter(typeof(CamelCaseSlopeConverter))]
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    SlopeDirection Slope = SlopeDirection.None);

// The tile grid of a from-scratch level: a missing cell is empty.
public readonly record struct LevelGrid(int Width, int Depth, IReadOnlyList<AuthoredCell> Cells)
{
    public bool Equals(LevelGrid other) =>
        Width == other.Width && Depth == other.Depth
        && (Cells ?? Array.Empty<AuthoredCell>()).SequenceEqual(other.Cells ?? Array.Empty<AuthoredCell>());

    public override int GetHashCode() => HashCode.Combine(Width, Depth, Cells?.Count);

    public LevelState ToLevelState() =>
        LevelState.FromTiles((Cells ?? Array.Empty<AuthoredCell>()).Select(cell =>
            KeyValuePair.Create((X: cell.X, Z: cell.Z), new TileState(cell.Height, cell.Slope))));
}

// Position is world [x, y, z]; Rotation is Euler degrees [x, y, z]. Scale and HiddenChildren apply to the boss spawner only.
public readonly record struct SpawnPoint(
    IReadOnlyList<float> Position,
    IReadOnlyList<float> Rotation,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] IReadOnlyList<float> Scale = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] IReadOnlyList<string> HiddenChildren = null)
{
    public bool Equals(SpawnPoint other) =>
        (Position ?? Array.Empty<float>()).SequenceEqual(other.Position ?? Array.Empty<float>())
        && (Rotation ?? Array.Empty<float>()).SequenceEqual(other.Rotation ?? Array.Empty<float>())
        && (Scale ?? Array.Empty<float>()).SequenceEqual(other.Scale ?? Array.Empty<float>())
        && (HiddenChildren ?? Array.Empty<string>()).SequenceEqual(other.HiddenChildren ?? Array.Empty<string>());

    public override int GetHashCode() => HashCode.Combine(Position?.Count, Rotation?.Count);
}
