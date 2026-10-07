using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

namespace MegabonkLevels;

public readonly record struct SpawnRecord(
    string Name,
    float X, float Y, float Z,
    float QX, float QY, float QZ, float QW,
    float SX, float SY, float SZ);

// Hashes a flat set of spawned-object transforms into a stable fingerprint for determinism checks.
// Sorts by a quantized grid key first so hierarchy-walk order never affects the result, then formats
// each record with fixed precision before hashing, so float jitter below the quantization step is ignored.
public static class GenerationHash
{
    private const float GridCellSize = 0.01f;

    public static string Compute(IEnumerable<SpawnRecord> records)
    {
        var sorted = records
            .OrderBy(r => GridKey(r.X))
            .ThenBy(r => GridKey(r.Z))
            .ThenBy(r => GridKey(r.Y))
            .ThenBy(r => r.Name, StringComparer.Ordinal);

        var builder = new StringBuilder();
        foreach (var r in sorted)
        {
            builder.Append(r.Name).Append('|')
                .Append(Fmt(r.X)).Append(',').Append(Fmt(r.Y)).Append(',').Append(Fmt(r.Z)).Append('|')
                .Append(Fmt(r.QX)).Append(',').Append(Fmt(r.QY)).Append(',').Append(Fmt(r.QZ)).Append(',').Append(Fmt(r.QW)).Append('|')
                .Append(Fmt(r.SX)).Append(',').Append(Fmt(r.SY)).Append(',').Append(Fmt(r.SZ)).Append('\n');
        }

        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(builder.ToString())));
    }

    private static long GridKey(float value) => (long)MathF.Round(value / GridCellSize);

    private static string Fmt(float value) => value.ToString("F4", CultureInfo.InvariantCulture);
}
