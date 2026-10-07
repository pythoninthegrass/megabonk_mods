using System;
using System.Text.Json;

namespace MegabonkLevels;

// Validation convention for every op type in this file: reject bad input in the constructor by throwing
// ArgumentException (or its ArgumentOutOfRangeException subclass for numeric-range violations), so all
// callers can catch a single base type. There is no Result/error-code type here by design — construction
// failure means the caller passed data that can never be valid, not a recoverable runtime condition.
internal static class EditOpValidation
{
    public static void RequireNonNegative(int value, string paramName)
    {
        if (value < 0)
        {
            throw new ArgumentOutOfRangeException(paramName, value, $"{paramName} must not be negative.");
        }
    }

    // Placeholder until TASK-003.05 defines the real catalogId format (including the reserved
    // bundle:<pack>/<asset> namespace) — revisit this check once that lands.
    public static void RequireNonBlankCatalogId(string catalogId)
    {
        if (string.IsNullOrWhiteSpace(catalogId))
        {
            throw new ArgumentException("catalogId must not be null or whitespace.", nameof(catalogId));
        }
    }

    public static void RequirePositiveScale(Vector3Data scale)
    {
        if (scale.X <= 0 || scale.Y <= 0 || scale.Z <= 0)
        {
            throw new ArgumentException(
                $"scale components must all be positive, got ({scale.X}, {scale.Y}, {scale.Z}).", nameof(scale));
        }
    }
}

internal static class EditOpJson
{
    public static readonly JsonSerializerOptions Options = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
}

public enum SlopeDirection
{
    None = 0,
    North = 1,
    South = 2,
    East = 3,
    West = 4,
}

public readonly record struct Vector3Data(float X, float Y, float Z);

public readonly record struct TransformData(Vector3Data Position, Vector3Data Rotation, Vector3Data Scale);

public enum ObjectTargetKind
{
    GenId,
    PlacementId,
}

// Distinguishes a generator-spawned object (TASK-002.03's opaque "{category}:{sequentialIndex}" genId
// scheme, format TBD by that task and treated as an opaque string here) from an object the editor itself
// placed, identified by an incrementing placement id scoped to the edit list.
public readonly record struct ObjectTarget
{
    public ObjectTargetKind Kind { get; }
    public string GenId { get; }
    public int PlacementId { get; }

    private ObjectTarget(ObjectTargetKind kind, string genId, int placementId)
    {
        Kind = kind;
        GenId = genId;
        PlacementId = placementId;
    }

    public static ObjectTarget FromGenId(string genId)
    {
        if (string.IsNullOrWhiteSpace(genId))
        {
            throw new ArgumentException("genId must not be null or whitespace.", nameof(genId));
        }

        return new ObjectTarget(ObjectTargetKind.GenId, genId, 0);
    }

    public static ObjectTarget FromPlacementId(int placementId)
    {
        EditOpValidation.RequireNonNegative(placementId, nameof(placementId));
        return new ObjectTarget(ObjectTargetKind.PlacementId, "", placementId);
    }

    public string Serialize() => Kind switch
    {
        ObjectTargetKind.GenId => $"gen:{GenId}",
        ObjectTargetKind.PlacementId => $"placement:{PlacementId}",
        _ => throw new ArgumentException($"Unknown {nameof(ObjectTargetKind)}: {Kind}"),
    };

    public static ObjectTarget Parse(string target)
    {
        if (target.StartsWith("gen:", StringComparison.Ordinal))
        {
            return FromGenId(target.Substring("gen:".Length));
        }

        if (target.StartsWith("placement:", StringComparison.Ordinal)
            && int.TryParse(target.Substring("placement:".Length), out var placementId))
        {
            return FromPlacementId(placementId);
        }

        throw new ArgumentException($"Unrecognized object target format: '{target}'.", nameof(target));
    }
}

public readonly record struct SetTileHeight
{
    public const string OpType = "tile.setHeight";

    public int X { get; }
    public int Z { get; }
    public int Height { get; }

    public SetTileHeight(int X, int Z, int Height)
    {
        EditOpValidation.RequireNonNegative(X, nameof(X));
        EditOpValidation.RequireNonNegative(Z, nameof(Z));
        this.X = X;
        this.Z = Z;
        this.Height = Height;
    }

    public EditOp ToEditOp() =>
        new(OpType, "", JsonSerializer.Serialize(new Payload(X, Z, Height), EditOpJson.Options));

    public static SetTileHeight FromEditOp(EditOp op)
    {
        RequireOpType(op, OpType);
        var payload = JsonSerializer.Deserialize<Payload>(op.Payload, EditOpJson.Options);
        return new SetTileHeight(payload.X, payload.Z, payload.Height);
    }

    private readonly record struct Payload(int X, int Z, int Height);

    internal static void RequireOpType(EditOp op, string expected)
    {
        if (op.OpType != expected)
        {
            throw new ArgumentException($"Expected opType '{expected}', got '{op.OpType}'.", nameof(op));
        }
    }
}

public readonly record struct SetTileSlope
{
    public const string OpType = "tile.setSlope";

    public int X { get; }
    public int Z { get; }
    public SlopeDirection Direction { get; }

    public SetTileSlope(int X, int Z, SlopeDirection Direction)
    {
        EditOpValidation.RequireNonNegative(X, nameof(X));
        EditOpValidation.RequireNonNegative(Z, nameof(Z));
        if (!Enum.IsDefined(typeof(SlopeDirection), Direction))
        {
            throw new ArgumentException($"Unknown {nameof(SlopeDirection)}: {Direction}.", nameof(Direction));
        }

        this.X = X;
        this.Z = Z;
        this.Direction = Direction;
    }

    public EditOp ToEditOp() =>
        new(OpType, "", JsonSerializer.Serialize(new Payload(X, Z, Direction), EditOpJson.Options));

    public static SetTileSlope FromEditOp(EditOp op)
    {
        SetTileHeight.RequireOpType(op, OpType);
        var payload = JsonSerializer.Deserialize<Payload>(op.Payload, EditOpJson.Options);
        return new SetTileSlope(payload.X, payload.Z, payload.Direction);
    }

    private readonly record struct Payload(int X, int Z, SlopeDirection Direction);
}

public readonly record struct AddTile
{
    public const string OpType = "tile.add";

    public int X { get; }
    public int Z { get; }
    public int Height { get; }

    public AddTile(int X, int Z, int Height)
    {
        EditOpValidation.RequireNonNegative(X, nameof(X));
        EditOpValidation.RequireNonNegative(Z, nameof(Z));
        this.X = X;
        this.Z = Z;
        this.Height = Height;
    }

    public EditOp ToEditOp() =>
        new(OpType, "", JsonSerializer.Serialize(new Payload(X, Z, Height), EditOpJson.Options));

    public static AddTile FromEditOp(EditOp op)
    {
        SetTileHeight.RequireOpType(op, OpType);
        var payload = JsonSerializer.Deserialize<Payload>(op.Payload, EditOpJson.Options);
        return new AddTile(payload.X, payload.Z, payload.Height);
    }

    private readonly record struct Payload(int X, int Z, int Height);
}

public readonly record struct RemoveTile
{
    public const string OpType = "tile.remove";

    public int X { get; }
    public int Z { get; }

    public RemoveTile(int X, int Z)
    {
        EditOpValidation.RequireNonNegative(X, nameof(X));
        EditOpValidation.RequireNonNegative(Z, nameof(Z));
        this.X = X;
        this.Z = Z;
    }

    public EditOp ToEditOp() =>
        new(OpType, "", JsonSerializer.Serialize(new Payload(X, Z), EditOpJson.Options));

    public static RemoveTile FromEditOp(EditOp op)
    {
        SetTileHeight.RequireOpType(op, OpType);
        var payload = JsonSerializer.Deserialize<Payload>(op.Payload, EditOpJson.Options);
        return new RemoveTile(payload.X, payload.Z);
    }

    private readonly record struct Payload(int X, int Z);
}

public readonly record struct PlaceObject
{
    public const string OpType = "object.place";

    public string CatalogId { get; }
    public Vector3Data Position { get; }
    public Vector3Data Rotation { get; }
    public Vector3Data Scale { get; }

    public PlaceObject(string CatalogId, Vector3Data Position, Vector3Data Rotation, Vector3Data Scale)
    {
        EditOpValidation.RequireNonBlankCatalogId(CatalogId);
        EditOpValidation.RequirePositiveScale(Scale);
        this.CatalogId = CatalogId;
        this.Position = Position;
        this.Rotation = Rotation;
        this.Scale = Scale;
    }

    public EditOp ToEditOp() =>
        new(OpType, "", JsonSerializer.Serialize(new Payload(CatalogId, Position, Rotation, Scale), EditOpJson.Options));

    public static PlaceObject FromEditOp(EditOp op)
    {
        SetTileHeight.RequireOpType(op, OpType);
        var payload = JsonSerializer.Deserialize<Payload>(op.Payload, EditOpJson.Options);
        return new PlaceObject(payload.CatalogId, payload.Position, payload.Rotation, payload.Scale);
    }

    private readonly record struct Payload(string CatalogId, Vector3Data Position, Vector3Data Rotation, Vector3Data Scale);
}

public readonly record struct MoveObject
{
    public const string OpType = "object.move";

    public ObjectTarget Target { get; }
    public TransformData NewTransform { get; }

    public MoveObject(ObjectTarget Target, TransformData NewTransform)
    {
        EditOpValidation.RequirePositiveScale(NewTransform.Scale);
        this.Target = Target;
        this.NewTransform = NewTransform;
    }

    public EditOp ToEditOp() =>
        new(OpType, Target.Serialize(), JsonSerializer.Serialize(new Payload(NewTransform), EditOpJson.Options));

    public static MoveObject FromEditOp(EditOp op)
    {
        SetTileHeight.RequireOpType(op, OpType);
        var target = ObjectTarget.Parse(op.Target);
        var payload = JsonSerializer.Deserialize<Payload>(op.Payload, EditOpJson.Options);
        return new MoveObject(target, payload.NewTransform);
    }

    private readonly record struct Payload(TransformData NewTransform);
}

public readonly record struct RemoveObject(ObjectTarget Target)
{
    public const string OpType = "object.remove";

    public EditOp ToEditOp() => new(OpType, Target.Serialize(), "{}");

    public static RemoveObject FromEditOp(EditOp op)
    {
        SetTileHeight.RequireOpType(op, OpType);
        return new RemoveObject(ObjectTarget.Parse(op.Target));
    }
}
