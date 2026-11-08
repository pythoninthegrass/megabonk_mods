using System;

namespace MegabonkLevels;

// Row arithmetic for the terminal-style console: the prompt is the last row of the output, and the history search puts
// its list above an info row and the query row.
public static class ConsoleLayout
{
    // Right after the last printed row, pinned to the bottom row once the output fills the panel or is scrolled back.
    public static int PromptRow(int visibleLines, int rows, int offset) =>
        offset > 0 ? rows - 1 : Math.Min(visibleLines, rows - 1);

    public static int FinderListRows(int rows) => Math.Max(1, rows - 2);

    public static int FinderInfoRow(int rows) => Math.Max(0, rows - 2);

    // Index into the finder's rows shown on a screen row, or -1 for the info and query rows. Index 0 is the newest match and sits on the row nearest the prompt.
    public static int FinderIndex(int row, int rows, int top)
    {
        var listRows = FinderListRows(rows);
        return row >= listRows ? -1 : top + (listRows - 1 - row);
    }
}
