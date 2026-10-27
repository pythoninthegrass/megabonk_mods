using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// A ProceduralMesh map has no tile grid, so only the object ops of a level file can be replayed on it.
public static class TerrainEdits
{
    public static (IReadOnlyList<EditOp> Kept, IReadOnlyList<EditOp> Rejected) Split(IReadOnlyList<EditOp> edits)
    {
        var kept = edits.Where(IsObjectOp).ToList();
        var rejected = edits.Where(op => !IsObjectOp(op)).ToList();
        return (kept, rejected);
    }

    private static bool IsObjectOp(EditOp op) =>
        op.OpType is PlaceObject.OpType or MoveObject.OpType or RemoveObject.OpType;
}
