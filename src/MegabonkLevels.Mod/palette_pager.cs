using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// Unity-free paging maths for the palette grid.
public static class PalettePager
{
    public static int PageCount(int count, int perPage) => Math.Max(1, (count + perPage - 1) / perPage);

    public static int Clamp(int page, int count, int perPage) => Math.Clamp(page, 0, PageCount(count, perPage) - 1);

    public static IReadOnlyList<T> Slice<T>(IReadOnlyList<T> items, int page, int perPage) =>
        items.Skip(Clamp(page, items.Count, perPage) * perPage).Take(perPage).ToArray();

    public static int PageOf(int index, int perPage) => Math.Max(0, index) / perPage;

    // One wheel notch is one page; the result stops at the first and last page.
    public static int Step(int page, float notches, int pageCount) =>
        Math.Clamp(page + (int)MathF.Round(notches), 0, pageCount - 1);
}
