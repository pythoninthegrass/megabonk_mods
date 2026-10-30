using System;
using System.Numerics;
using System.Text.Json.Serialization;

namespace MegabonkLevels;

public readonly record struct ObjectAttachmentSpec
{
    public string Name { get; }
    public string CatalogId { get; }
    public TransformData LocalTransform { get; }
    public bool Hidden { get; }

    [JsonConstructor]
    public ObjectAttachmentSpec(string Name, string CatalogId, TransformData LocalTransform, bool Hidden = false)
    {
        if (string.IsNullOrWhiteSpace(Name))
        {
            throw new ArgumentException("An attachment must have a name.", nameof(Name));
        }
        EditOpValidation.RequireNonBlankCatalogId(CatalogId);
        EditOpValidation.RequirePositiveScale(LocalTransform.Scale);
        this.Name = Name;
        this.CatalogId = CatalogId;
        this.LocalTransform = LocalTransform;
        this.Hidden = Hidden;
    }
}

// Object transforms use world position/rotation and local scale, matching the editor's Transform snapshots.
public static class AttachmentTransform
{
    private const float Radians = MathF.PI / 180f;

    public static TransformData ToWorld(TransformData owner, TransformData local) => new(
        Data(Vec(owner.Position) + Vector3.Transform(Vec(local.Position) * Vec(owner.Scale), Rotation(owner.Rotation))),
        Euler(Rotation(owner.Rotation) * Rotation(local.Rotation)), local.Scale);

    public static TransformData ToLocal(TransformData owner, TransformData world) => new(
        Data(Vector3.Transform(Vec(world.Position) - Vec(owner.Position), Quaternion.Inverse(Rotation(owner.Rotation))) / Vec(owner.Scale)),
        Euler(Quaternion.Inverse(Rotation(owner.Rotation)) * Rotation(world.Rotation)), world.Scale);

    private static Quaternion Rotation(Vector3Data euler) => Quaternion.CreateFromYawPitchRoll(euler.Y * Radians, euler.X * Radians, euler.Z * Radians);

    private static Vector3Data Euler(Quaternion rotation)
    {
        var matrix = Matrix4x4.CreateFromQuaternion(Quaternion.Normalize(rotation));
        var x = MathF.Asin(Math.Clamp(-matrix.M32, -1f, 1f));
        if (MathF.Abs(MathF.Cos(x)) > 0.0001f)
        {
            return new(x / Radians, MathF.Atan2(matrix.M31, matrix.M33) / Radians, MathF.Atan2(matrix.M12, matrix.M22) / Radians);
        }
        return new(x / Radians, MathF.Atan2(-matrix.M13, matrix.M11) / Radians, 0);
    }

    private static Vector3 Vec(Vector3Data value) => new(value.X, value.Y, value.Z);
    private static Vector3Data Data(Vector3 value) => new(value.X, value.Y, value.Z);
}
