using System;

namespace MegabonkLevels;

// Unity-free rules for what each editor tile tool does to the tile it targets.
public static class TileTools
{
    public static SlopeDirection NextSlope(SlopeDirection current) => current switch
    {
        SlopeDirection.None => SlopeDirection.North,
        SlopeDirection.North => SlopeDirection.East,
        SlopeDirection.East => SlopeDirection.South,
        SlopeDirection.South => SlopeDirection.West,
        _ => SlopeDirection.None,
    };

    // Returns null when the tool has nothing to do: lowering a tile already at lowestLevel, the map's lowest generated level.
    public static EditOp? Build(EditorTool tool, int x, int z, TileState current, int lowestLevel) => tool switch
    {
        EditorTool.Raise => new SetTileHeight(x, z, current.Height + 1).ToEditOp(),
        EditorTool.Lower when current.Height > lowestLevel => new SetTileHeight(x, z, current.Height - 1).ToEditOp(),
        EditorTool.Lower => null,
        EditorTool.Slope => new SetTileSlope(x, z, NextSlope(current.Slope)).ToEditOp(),
        EditorTool.Remove => new RemoveTile(x, z).ToEditOp(),
        _ => throw new ArgumentException($"{tool} is not a tile tool.", nameof(tool)),
    };
}
