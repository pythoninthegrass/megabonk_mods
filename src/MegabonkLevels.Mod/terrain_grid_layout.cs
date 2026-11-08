using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// Array-layout candidates and checks for opaque interop grid buffers.
public static class TerrainGridLayout
{
    public const int MaxCells = 1_000_000;

    // Above this a bulk copy is taken for garbage bytes rather than terrain heights, which are single digits.
    public const float MaxMagnitude = 1e7f;

    // An il2cpp array starts with the object header (klass pointer, monitor pointer). A single-dimensional array
    // follows it with the element count and then the cells; a multi-dimensional one inserts a bounds pointer first.
    public readonly record struct Layout(string Name, int LengthOffset, int DataOffset);

    public static readonly IReadOnlyList<Layout> CandidateLayouts = new[]
    {
        new Layout("multi", 24, 32),
        new Layout("sz", 16, 24),
    };

    public static bool IsReadable(int length) => length > 0 && length <= MaxCells;

    // Summary of a copied grid, kept so a run can show what it hashed rather than only that the hash looked sane.
    public readonly record struct Stats(int Cells, float Min, float Max, float Mean);

    public static Stats? Of(float[] cells)
    {
        if (cells == null || cells.Length == 0)
        {
            return null;
        }

        var min = cells[0];
        var max = cells[0];
        double sum = 0;
        foreach (var value in cells)
        {
            if (!float.IsFinite(value))
            {
                return null;
            }

            min = Math.Min(min, value);
            max = Math.Max(max, value);
            sum += value;
        }

        return new Stats(cells.Length, min, max, (float)(sum / cells.Length));
    }

    // A bulk copy that no cell read could confirm still has to look like a grid: finite values, not one repeated value.
    public static bool IsPlausible(float[] cells)
    {
        if (cells == null || cells.Length == 0)
        {
            return false;
        }

        var first = cells[0];
        if (!float.IsFinite(first))
        {
            return false;
        }

        var varied = false;
        foreach (var value in cells)
        {
            if (!float.IsFinite(value) || Math.Abs(value) > MaxMagnitude)
            {
                return false;
            }

            varied |= value != first;
        }

        return varied;
    }

    // Whether a count read out of an array header can be believed, checked against the cell count the caller
    // expects so a header read that landed on garbage cannot quietly hash a truncated grid.
    public static bool LengthMatches(int length, int expected)
    {
        return IsReadable(length) && (expected <= 0 || length == expected);
    }

    public static int[] CheckIndices(int length, int samples)
    {
        if (length <= 0 || samples <= 0)
        {
            return Array.Empty<int>();
        }

        var indices = new int[Math.Min(samples, length)];
        if (indices.Length == 1)
        {
            return new[] { 0 };
        }

        for (var i = 0; i < indices.Length; i++)
        {
            indices[i] = (int)((long)i * (length - 1) / (indices.Length - 1));
        }

        return indices;
    }

    public static bool Agrees(float[] copied, float?[] samples, int[] indices)
    {
        if (copied == null || samples == null || indices == null || indices.Length != samples.Length || indices.Length == 0)
        {
            return false;
        }

        foreach (var (index, sample) in Zip(indices, samples))
        {
            if (index < 0 || index >= copied.Length || sample == null)
            {
                return false;
            }

            if (Math.Abs(sample.Value - copied[index]) > 0.0001f * Math.Max(1f, Math.Abs(sample.Value)))
            {
                return false;
            }
        }

        return true;
    }

    static IEnumerable<(int Index, float? Sample)> Zip(int[] indices, float?[] samples)
    {
        for (var i = 0; i < indices.Length; i++)
        {
            yield return (indices[i], samples[i]);
        }
    }
}
