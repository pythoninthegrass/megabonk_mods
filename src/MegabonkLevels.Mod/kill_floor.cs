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

    public static bool ShouldKill(float y, float floorY) => y < floorY;

    private const float CatchFloorClearance = 8f;
}
