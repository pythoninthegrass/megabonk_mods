using System;
using System.Collections;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;

namespace MegabonkLevels;

// Fingerprints grid values at four decimal places; a missing grid has no fingerprint.
public static class TerrainHash
{
    public static string Of(IEnumerable cells, out int cellCount)
    {
        cellCount = 0;
        if (cells == null)
        {
            return null;
        }

        var builder = new StringBuilder();
        foreach (var cell in cells)
        {
            cellCount++;
            builder.Append(Fmt(cell)).Append(',');
        }

        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(builder.ToString())));
    }

    private static string Fmt(object cell)
    {
        if (cell == null)
        {
            return "<null>";
        }

        try
        {
            return Convert.ToSingle(cell, CultureInfo.InvariantCulture).ToString("F4", CultureInfo.InvariantCulture);
        }
        catch (Exception)
        {
            return "<" + cell.GetType().Name + ">";
        }
    }
}
