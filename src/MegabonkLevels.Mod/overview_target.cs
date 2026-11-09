namespace MegabonkLevels;

public static class OverviewTarget
{
    public static (int X, int Z) CentreCell(int width, int depth) => (width / 2, depth / 2);

    // The player's body point when it is on the grid, else a body standing on the centre tile, so a spawn away from the grid (Graveyard) still frames tiles.
    public static (float X, float Y, float Z) Of(float playerX, float playerY, float playerZ, int width, int depth, float spacing, float tileHeight, TileState? centreTile)
    {
        if (PositionReadout.CellOf(playerX, playerZ, width, depth, spacing).InGrid)
        {
            return (playerX, playerY, playerZ);
        }

        var (cellX, cellZ) = CentreCell(width, depth);
        var feet = TeleportTarget.CellStandingPoint(cellX, cellZ, centreTile, width, depth, spacing, tileHeight, playerY - TeleportTarget.PlayerBodyOffsetY);
        return (feet.X, feet.Y + TeleportTarget.PlayerBodyOffsetY, feet.Z);
    }
}
