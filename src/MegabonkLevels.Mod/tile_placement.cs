using System;

namespace MegabonkLevels;

public enum TilePlacementKind
{
    MoveOnly,
    ReplaceWithFlat,
    ReplaceWithSlope,
    AddFlat,
    AddSlope,
}

// Unity-free rules for putting a TileState onto the live grid. SlopeDirection names the uphill side of a
// slope tile and matches ProceduralTile.dir: North is +Z (yaw 0), East +X (90), South -Z (180), West -X (270).
public static class TilePlacement
{
    public static (int Dx, int Dz) UphillVector(SlopeDirection direction) => direction switch
    {
        SlopeDirection.North => (0, 1),
        SlopeDirection.South => (0, -1),
        SlopeDirection.East => (1, 0),
        SlopeDirection.West => (-1, 0),
        _ => throw new ArgumentException($"{nameof(direction)} must be a cardinal direction, got {direction}.", nameof(direction)),
    };

    public static SlopeDirection SlopeFromVector(int dx, int dz) => (dx, dz) switch
    {
        (0, 1) => SlopeDirection.North,
        (0, -1) => SlopeDirection.South,
        (1, 0) => SlopeDirection.East,
        (-1, 0) => SlopeDirection.West,
        _ => SlopeDirection.None,
    };

    // liveSlope is the slope direction of the tile currently in the cell (None for a flat tile).
    public static TilePlacementKind Decide(bool liveTileExists, SlopeDirection liveSlope, TileState target, bool liveIsStaticBatch = false)
    {
        var targetIsSlope = target.Slope != SlopeDirection.None;
        if (!liveTileExists)
        {
            return targetIsSlope ? TilePlacementKind.AddSlope : TilePlacementKind.AddFlat;
        }

        if (liveSlope == target.Slope && !liveIsStaticBatch)
        {
            return TilePlacementKind.MoveOnly;
        }

        return targetIsSlope ? TilePlacementKind.ReplaceWithSlope : TilePlacementKind.ReplaceWithFlat;
    }

    public static (float X, float Y, float Z) WorldPosition(int x, int z, int height, float originX, float originZ, float scaledTileWidth, float scaledTileHeight) =>
        (originX + x * scaledTileWidth, height * scaledTileHeight, originZ + z * scaledTileWidth);
}
