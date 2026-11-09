using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;

namespace MegabonkLevels;

public readonly record struct GridCell(int X, int Z, bool InGrid);

public readonly record struct ReadoutActor(string Label, uint Id, float X, float Y, float Z, string TypeName = null);

public sealed class CoordinateVisibility
{
    public bool Enabled { get; private set; }
    public void Set(bool enabled) => Enabled = enabled;
    public void Toggle() => Set(!Enabled);
    public bool Visible(bool armed, bool playerAlive) => playerAlive && PositionReadout.Visible(armed, Enabled);
}

// See "Position readout" in docs/development.md for the on-screen format and the column-sizing rule.
public static class PositionReadout
{
    private const string BelowFloorFlag = "BELOW FLOOR";
    private const string MeLabel = "me:";
    private const int MinIdWidth = 3;

    public static bool Visible(bool armed, bool enabled) => armed && enabled;

    public static bool ShouldToggle(bool armed, bool pressed, bool consoleOpen, bool textFocused, bool modConsoleFocused = false) =>
        armed && pressed && !consoleOpen && !textFocused && !modConsoleFocused;

    public static GridCell CellOf(float x, float z, int width, int depth, float spacing)
    {
        var cellX = (int)MathF.Floor(x / spacing + (width - 1) / 2f + 0.5f);
        var cellZ = (int)MathF.Floor(z / spacing + (depth - 1) / 2f + 0.5f);
        return new GridCell(cellX, cellZ, cellX >= 0 && cellX < width && cellZ >= 0 && cellZ < depth);
    }

    // World XZ of a cell's centre, the inverse of CellOf's grid origin.
    public static (float X, float Z) CellCentre(int cellX, int cellZ, int width, int depth, float spacing) =>
        ((cellX - (width - 1) / 2f) * spacing, (cellZ - (depth - 1) / 2f) * spacing);

    public static int LevelOf(float y, float tileHeight) => (int)MathF.Round(y / tileHeight, MidpointRounding.AwayFromZero);

    public static string Render(float playerX, float playerY, float playerZ, float floorY, IReadOnlyList<ReadoutActor> actors)
    {
        var labelWidth = Math.Max(MeLabel.Length, actors.Count == 0 ? 0 : actors.Max(a => a.Label.Length));
        var idWidth = actors.Count == 0 ? 0 : Math.Max(MinIdWidth, actors.Max(a => IdText(a.Id).Length));
        var xWidth = ColumnWidth(playerX, actors, a => a.X);
        var yWidth = ColumnWidth(playerY, actors, a => a.Y);
        var zWidth = ColumnWidth(playerZ, actors, a => a.Z);

        var lines = new List<string>(actors.Count + 1)
        {
            RenderMe(playerX, playerY, playerZ, floorY, labelWidth, idWidth, xWidth, yWidth, zWidth),
        };
        foreach (var actor in actors)
        {
            lines.Add(RenderActor(actor, floorY, labelWidth, idWidth, xWidth, yWidth, zWidth));
        }

        return string.Join("\n", lines);
    }

    public static string FormatCellLog(string name, float x, float y, float z, GridCell cell, int level)
    {
        var cellText = $"cell ({cell.X},{cell.Z}){(cell.InGrid ? string.Empty : " outside")}";
        return $"{name} {cellText} h{level} pos ({Whole(x)}, {Whole(y)}, {Whole(z)})";
    }

    private static int ColumnWidth(float playerValue, IReadOnlyList<ReadoutActor> actors, Func<ReadoutActor, float> select)
    {
        var width = Whole(playerValue).Length;
        foreach (var actor in actors)
        {
            width = Math.Max(width, Whole(select(actor)).Length);
        }

        return width;
    }

    private static string RenderMe(float x, float y, float z, float floorY, int labelWidth, int idWidth, int xWidth, int yWidth, int zWidth)
    {
        var text = MeLabel.PadRight(labelWidth) + " " + IdColumn(string.Empty, idWidth) + Pos(x, y, z, xWidth, yWidth, zWidth);
        if (float.IsNegativeInfinity(floorY))
        {
            return text;
        }

        text += $" floor {Whole(floorY)}";
        return KillFloor.ShouldKill(y, floorY) ? text + " " + BelowFloorFlag : text;
    }

    private static string RenderActor(ReadoutActor actor, float floorY, int labelWidth, int idWidth, int xWidth, int yWidth, int zWidth)
    {
        var text = actor.Label.PadRight(labelWidth) + " " + IdColumn(IdText(actor.Id), idWidth) + Pos(actor.X, actor.Y, actor.Z, xWidth, yWidth, zWidth);
        var below = !float.IsNegativeInfinity(floorY) && KillFloor.ShouldKill(actor.Y, floorY);
        if (below)
        {
            text += " " + BelowFloorFlag;
        }

        return actor.TypeName == null ? text : text + " " + actor.TypeName;
    }

    private static string IdColumn(string id, int idWidth) => idWidth == 0 ? string.Empty : id.PadRight(idWidth) + " ";

    private static string Pos(float x, float y, float z, int xWidth, int yWidth, int zWidth) =>
        $"pos({Whole(x).PadLeft(xWidth)}, {Whole(y).PadLeft(yWidth)}, {Whole(z).PadLeft(zWidth)})";

    private static string IdText(uint id) => id.ToString(CultureInfo.InvariantCulture);

    // Drops the sign of a negative zero, which (int) cast would otherwise print as "-0".
    private static string Whole(float value) => ((int)MathF.Round(value, MidpointRounding.AwayFromZero)).ToString(CultureInfo.InvariantCulture);
}
