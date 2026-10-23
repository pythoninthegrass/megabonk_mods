namespace MegabonkLevels;

public static class TeleportTarget
{
    // The feet point at a cell's centre on its tile surface; an empty cell keeps the player's current height.
    public static (float X, float Y, float Z) CellStandingPoint(int cellX, int cellZ, TileState? tile, int width, int depth, float spacing, float tileHeight, float currentY)
    {
        var (x, z) = PositionReadout.CellCentre(cellX, cellZ, width, depth, spacing);
        var y = tile is { } state ? ObjectTools.SurfaceY(state, 0f, 0f, spacing, tileHeight) : currentY;
        return (x, y, z);
    }
}
