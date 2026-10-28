using System.Numerics;

namespace MegabonkLevels.Tests;

public class WarehouseRoofTests
{
    const float MinX = -1f, MaxX = 1f, MinZ = -1.5f, MaxZ = 1.5f, SkirtBottom = 0.68f, RoofY = 1.5f, Inset = 0.003f;

    static Vector3 FrontNormal(Vector3[] quad) => Vector3.Normalize(Vector3.Cross(quad[1] - quad[0], quad[2] - quad[0]));

    static Vector3[][] Build() => WarehouseRoof.Quads(MinX, MaxX, MinZ, MaxZ, SkirtBottom, RoofY, Inset).ToArray();

    [Fact]
    public void Quads_ReturnsFourWallsAndARoof()
    {
        Assert.Equal(5, Build().Length);
    }

    [Fact]
    public void Quads_RoofIsFlatAtRoofHeightAndFacesDown()
    {
        var roof = Build().Single(q => q.All(p => p.Y == RoofY));

        Assert.Equal(-1f, FrontNormal(roof).Y, 4);
    }

    [Fact]
    public void Quads_WallsSpanSkirtBottomToRoofAndFaceTheRoomCentre()
    {
        var walls = Build().Where(q => q.Any(p => p.Y == SkirtBottom)).ToArray();

        Assert.Equal(4, walls.Length);
        foreach (var wall in walls)
        {
            Assert.Equal(RoofY, wall.Max(p => p.Y));
            var centre = wall.Aggregate(Vector3.Zero, (sum, p) => sum + p) / 4;
            Assert.True(Vector3.Dot(FrontNormal(wall), new Vector3(-centre.X, 0, -centre.Z)) > 0);
        }
    }

    [Fact]
    public void Quads_StayInsideTheFootprintByTheInset()
    {
        foreach (var p in Build().SelectMany(q => q))
        {
            Assert.InRange(p.X, MinX + Inset - 1e-6f, MaxX - Inset + 1e-6f);
            Assert.InRange(p.Z, MinZ + Inset - 1e-6f, MaxZ - Inset + 1e-6f);
        }
    }

    [Fact]
    public void RoofWorldHeight_ClearsHighestStandableSurfacePlusTwoFeatherReach()
    {
        const float highestStandable = 55f, measuredJumpChainRise = 56.4f, capsuleTop = 2f;

        Assert.True(WarehouseRoof.RoofWorldHeight >= highestStandable + measuredJumpChainRise + capsuleTop);
    }
}
