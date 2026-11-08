using System;
using System.Globalization;
using System.Reflection;
using System.Runtime.InteropServices;
using Il2CppInterop.Runtime.InteropTypes;

namespace MegabonkLevels;

// Report whether an opaque grid copy agrees with sampled cells or only passes plausibility checks.
public static class TerrainGrid
{
    private const int Checks = 4;

    public static float[] Read(Il2CppObjectBase grid, int expectedCells, out string via)
    {
        via = "none";
        if (grid == null || grid.Pointer == IntPtr.Zero)
        {
            return null;
        }

        foreach (var layout in TerrainGridLayout.CandidateLayouts)
        {
            var length = ReadLength(grid.Pointer, layout.LengthOffset, expectedCells);
            if (length == null)
            {
                continue;
            }

            var copied = TryBulk(grid.Pointer, layout.DataOffset, length.Value);
            if (copied == null)
            {
                continue;
            }

            var indices = TerrainGridLayout.CheckIndices(length.Value, Checks);
            if (TerrainGridLayout.Agrees(copied, Samples(grid, indices), indices))
            {
                via = $"cells@{layout.Name}";
                return copied;
            }

            if (TerrainGridLayout.IsPlausible(copied))
            {
                via = $"buffer@{layout.Name}";
                return copied;
            }
        }

        via = $"unreadable:{grid.GetType().Name}";
        return null;
    }

    static int? ReadLength(IntPtr pointer, int lengthOffset, int expectedCells)
    {
        try
        {
            var length = checked((int)Marshal.ReadInt64(pointer, lengthOffset));
            return TerrainGridLayout.LengthMatches(length, expectedCells) ? length : (int?)null;
        }
        catch (Exception)
        {
            return null;
        }
    }

    static float[] TryBulk(IntPtr pointer, int dataOffset, int length)
    {
        try
        {
            var copied = new float[length];
            Marshal.Copy(pointer + dataOffset, copied, 0, length);
            return copied;
        }
        catch (Exception)
        {
            return null;
        }
    }

    static float?[] Samples(object grid, int[] indices)
    {
        var reader = CellReader(grid?.GetType());
        var values = new float?[indices.Length];
        if (reader == null)
        {
            return values;
        }

        for (var i = 0; i < indices.Length; i++)
        {
            try
            {
                values[i] = Parse(reader(grid, indices[i]));
            }
            catch (Exception)
            {
                values[i] = null;
            }
        }

        return values;
    }

    // Whatever the wrapper exposes for one cell: a CLR array's GetValue, or an interop indexer taking an index or an
    // index vector. A multi-dimensional indexer cannot be driven with a linear index, so it is left unused.
    static Func<object, int, object> CellReader(Type type)
    {
        if (type == null)
        {
            return null;
        }

        if (typeof(Array).IsAssignableFrom(type))
        {
            return (grid, index) => ((Array)grid).GetValue(index);
        }

        var indexer = type.GetMethod("get_Item", BindingFlags.Instance | BindingFlags.Public, null, new[] { typeof(int) }, null);
        return indexer == null ? null : (grid, index) => indexer.Invoke(grid, new object[] { index });
    }

    static float? Parse(object cell)
    {
        if (cell == null)
        {
            return null;
        }

        if (cell is float value)
        {
            return value;
        }

        if (cell is double wide)
        {
            return (float)wide;
        }

        if (cell is int whole)
        {
            return whole;
        }

        return float.TryParse(cell.ToString(), NumberStyles.Float, CultureInfo.InvariantCulture, out var parsed)
            ? parsed
            : (float?)null;
    }
}
