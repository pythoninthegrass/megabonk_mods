using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// Super Mario Bros style kill floor for mod-loaded levels: anything that falls below the lowest tile dies.
public static class KillFloor
{
    // The floor sits `margin` below the lowest tile, but never at or below the game's own catch floor, or a body
    // resting on that floor would never count as fallen.
    public static float FloorY(IEnumerable<int> tileLevels, float tileHeight, float margin, float catchFloorY)
    {
        var levels = tileLevels.ToList();
        if (levels.Count == 0)
        {
            return float.NegativeInfinity;
        }

        var derived = levels.Min() * tileHeight - margin;
        return Math.Max(derived, catchFloorY + CatchFloorClearance);
    }

    // A terrain map has one heightmap mesh instead of tile levels; the same margin and catch-floor rule apply to its lowest point.
    public static float FloorYForTerrain(float lowestTerrainY, float margin, float catchFloorY) =>
        float.IsFinite(lowestTerrainY)
            ? Math.Max(lowestTerrainY - margin, catchFloorY + CatchFloorClearance)
            : float.NegativeInfinity;

    public static bool ShouldKill(float y, float floorY) => y < floorY;

    // An actor's pivot can sit well above its feet, so a tall one standing on the catch floor never has a pivot below
    // the kill floor; the collider bottom is what has actually fallen.
    public static float LowestPoint(float pivotY, float? colliderMinY) =>
        colliderMinY.HasValue ? Math.Min(pivotY, colliderMinY.Value) : pivotY;

    private const float CatchFloorClearance = 8f;
}
