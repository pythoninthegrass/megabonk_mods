using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace MegabonkLevels;

public static class TrackFileName
{
    private static readonly Regex Prefix = new("^[0-9]+(\\.[0-9]+)*", RegexOptions.Compiled);

    public static IComparer<string> Comparer { get; } = System.Collections.Generic.Comparer<string>.Create(Compare);

    private static int Compare(string left, string right)
    {
        var a = Prefix.Match(left).Value;
        var b = Prefix.Match(right).Value;
        if (a.Length == 0 || b.Length == 0)
        {
            return a.Length == 0 && b.Length == 0
                ? StringComparer.Ordinal.Compare(left, right)
                : a.Length == 0 ? 1 : -1;
        }

        var ac = a.Split('.');
        var bc = b.Split('.');
        for (var i = 0; i < Math.Min(ac.Length, bc.Length); i++)
        {
            var x = ac[i].TrimStart('0');
            var y = bc[i].TrimStart('0');
            var compared = x.Length.CompareTo(y.Length);
            if (compared == 0)
            {
                compared = StringComparer.Ordinal.Compare(x, y);
            }

            if (compared != 0)
            {
                return compared;
            }
        }

        var length = ac.Length.CompareTo(bc.Length);
        return length != 0 ? length : StringComparer.Ordinal.Compare(left, right);
    }
}
