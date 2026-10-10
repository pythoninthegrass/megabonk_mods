using System.Collections.Generic;

namespace MegabonkLevels;

// World-space outline of a tile's top surface, on the same centred grid as PositionReadout.CellOf.
public static class TileOutline
{
    private static readonly (int Dx, int Dz)[] CornerSigns = { (-1, -1), (1, -1), (1, 1), (-1, 1) };

    // lift raises the outline above the surface so it is not hidden inside the tile mesh.
    public static IReadOnlyList<Vector3Data> Corners(int x, int z, TileState state, int width, int depth, float spacing, float tileHeight, float lift)
    {
        var centreX = (x - (width - 1) / 2f) * spacing;
        var centreZ = (z - (depth - 1) / 2f) * spacing;
        var half = spacing / 2f;
        var baseY = state.Height * tileHeight + lift;
        var uphill = state.Slope == SlopeDirection.None ? (Dx: 0, Dz: 0) : TilePlacement.UphillVector(state.Slope);

        var corners = new Vector3Data[CornerSigns.Length];
        for (var i = 0; i < CornerSigns.Length; i++)
        {
            var (sx, sz) = CornerSigns[i];
            var onUphillEdge = sx * uphill.Dx + sz * uphill.Dz > 0;
            corners[i] = new Vector3Data(centreX + sx * half, baseY + (onUphillEdge ? tileHeight : 0f), centreZ + sz * half);
        }

        return corners;
    }
}
