using System.Linq;

namespace MegabonkLevels;

public enum TileTool
{
    Raise,
    Lower,
    Slope,
    Remove,
}

// Unity-free rules for what each editor tile tool does to the tile it targets.
public static class TileTools
{
    private const string CurrentToolColor = "#ffd84d";
    private static readonly TileTool[] Tools = { TileTool.Raise, TileTool.Lower, TileTool.Slope, TileTool.Remove };

    public static SlopeDirection NextSlope(SlopeDirection current) => current switch
    {
        SlopeDirection.None => SlopeDirection.North,
        SlopeDirection.North => SlopeDirection.East,
        SlopeDirection.East => SlopeDirection.South,
        SlopeDirection.South => SlopeDirection.West,
        _ => SlopeDirection.None,
    };

    // Returns null when the tool has nothing to do: lowering a tile already at lowestLevel, the map's lowest generated level.
    public static EditOp? Build(TileTool tool, int x, int z, TileState current, int lowestLevel) => tool switch
    {
        TileTool.Raise => new SetTileHeight(x, z, current.Height + 1).ToEditOp(),
        TileTool.Lower when current.Height > lowestLevel => new SetTileHeight(x, z, current.Height - 1).ToEditOp(),
        TileTool.Lower => null,
        TileTool.Slope => new SetTileSlope(x, z, NextSlope(current.Slope)).ToEditOp(),
        _ => new RemoveTile(x, z).ToEditOp(),
    };

    public static string ToolbarText(TileTool current, (int X, int Z, TileState State)? target)
    {
        var tools = string.Join("   ", Tools.Select((tool, i) =>
            tool == current ? $"<color={CurrentToolColor}>[{i + 1} {tool}]</color>" : $"{i + 1} {tool}"));
        var line = target is { } t ? $"target ({t.X},{t.Z}) level {t.State.Height} slope {t.State.Slope}" : "target none";
        return $"{tools}\n{line}";
    }

    public static TileTool? FromHotkey(int digit) => digit switch
    {
        1 => TileTool.Raise,
        2 => TileTool.Lower,
        3 => TileTool.Slope,
        4 => TileTool.Remove,
        _ => null,
    };
}
