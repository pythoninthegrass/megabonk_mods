using System.Collections.Generic;
using System.Numerics;

// Pure geometry with no Unity types, so the unit tests can compile it directly.
public static class WarehouseRoof
{
    // World height of the roof underside: the highest standable surface (55) plus the measured two-feather jump chain (about 56) plus the capsule top, with margin for coarse sampling.
    public const float RoofWorldHeight = 120f;

    // Four inward-facing wall skirts from skirtBottom to roofY plus a downward-facing roof, inset from the footprint; front faces follow Unity's clockwise-from-front rule (cross(b - a, c - a) is the front normal).
    public static IEnumerable<Vector3[]> Quads(float minX, float maxX, float minZ, float maxZ, float skirtBottom, float roofY, float inset)
    {
        float x0 = minX + inset, x1 = maxX - inset, z0 = minZ + inset, z1 = maxZ - inset;
        var centre = new Vector3((x0 + x1) / 2, (skirtBottom + roofY) / 2, (z0 + z1) / 2);
        yield return Facing(new Vector3(x0, skirtBottom, z0), new Vector3(x0, roofY, z0), new Vector3(x0, roofY, z1), new Vector3(x0, skirtBottom, z1), centre);
        yield return Facing(new Vector3(x1, skirtBottom, z0), new Vector3(x1, roofY, z0), new Vector3(x1, roofY, z1), new Vector3(x1, skirtBottom, z1), centre);
        yield return Facing(new Vector3(x0, skirtBottom, z0), new Vector3(x0, roofY, z0), new Vector3(x1, roofY, z0), new Vector3(x1, skirtBottom, z0), centre);
        yield return Facing(new Vector3(x0, skirtBottom, z1), new Vector3(x0, roofY, z1), new Vector3(x1, roofY, z1), new Vector3(x1, skirtBottom, z1), centre);
        yield return Facing(new Vector3(x0, roofY, z0), new Vector3(x1, roofY, z0), new Vector3(x1, roofY, z1), new Vector3(x0, roofY, z1), centre);
    }

    static Vector3[] Facing(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 towards)
    {
        var normal = Vector3.Cross(b - a, c - a);
        return Vector3.Dot(normal, towards - a) >= 0 ? new[] { a, b, c, d } : new[] { d, c, b, a };
    }
}
