namespace MegabonkLevels;

// Unity-free grid shape of the palette: four columns expanded, one column compact.
public sealed class PaletteLayout
{
    public const int Rows = 6;
    public const int ExpandedColumns = 4;

    public bool Compact { get; private set; }

    public int Columns => Compact ? 1 : ExpandedColumns;

    public int PerPage => Columns * Rows;

    // Returns the page that keeps the first entry of the old page visible under the new shape.
    public int SetCompact(bool compact, int page)
    {
        if (compact == Compact)
        {
            return page;
        }

        var firstIndex = page * PerPage;
        Compact = compact;
        return PalettePager.PageOf(firstIndex, PerPage);
    }

    public void Reset() => Compact = false;
}
