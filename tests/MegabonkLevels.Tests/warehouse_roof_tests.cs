using System.Numerics;

namespace MegabonkLevels.Tests;

public class WarehouseRoofTests
{
    const float Cell = 10f, Inset = 0.5f, Band = 1f, FloorY = 0f, RoofY = 66f;

    static Vector3 FrontNormal(Vector3[] quad) => Vector3.Normalize(Vector3.Cross(quad[1] - quad[0], quad[2] - quad[0]));

    static Vector3[] WallTriangle(float x, float z0, float z1, float top) =>
        new[] { new Vector3(x, 0, z0), new Vector3(x, top, z0), new Vector3(x, 0, z1) };

    static float[][] Tops(float west, float east, float south, float north) =>
        new[] { new[] { west, west }, new[] { east, east }, new[] { south, south }, new[] { north, north } };

    [Fact]
    public void EdgeWallTops_TakesTheHighestSteepVertexOnTheEdgePerCell()
    {
        var triangles = new[] { WallTriangle(0.2f, 1, 4, 54), WallTriangle(0.4f, 2, 5, 58), WallTriangle(0.2f, 11, 14, 40) };

        var tops = WarehouseRoof.EdgeWallTops(triangles, WarehouseRoof.Side.West, 0, 20, 0, Cell, Band, FloorY);

        Assert.Equal(new[] { 58f, 40f }, tops);
    }

    [Fact]
    public void EdgeWallTops_UsesTheFloorWhereNoWallStandsOnTheEdge()
    {
        var far = WallTriangle(5f, 1, 4, 54);
        var flat = new[] { new Vector3(0.2f, 30, 1), new Vector3(0.2f, 30, 4), new Vector3(3, 30, 1) };

        var tops = WarehouseRoof.EdgeWallTops(new[] { far, flat }, WarehouseRoof.Side.West, 0, 20, 0, Cell, Band, FloorY);

        Assert.Equal(new[] { FloorY, FloorY }, tops);
    }

    [Fact]
    public void Quads_ReturnsOneFlatDownFacingRoofAtRoofHeight()
    {
        var quads = WarehouseRoof.Quads(RoofY, 0, 0, 20, 10, Cell, Inset, Tops(54, 54, 54, 54)).ToArray();

        var roof = quads.Where(q => q.All(p => p.Y == RoofY && p.X != 0)).ToArray();
        Assert.Single(roof);
        Assert.Equal(-1f, FrontNormal(roof[0]).Y, 4);
        Assert.Equal(Inset, roof[0].Min(p => p.X));
        Assert.Equal(20 - Inset, roof[0].Max(p => p.X));
    }

    [Fact]
    public void Quads_AddsOneInwardFacingSkirtPerEdgeCellFromTheWallTopToTheRoof()
    {
        var quads = WarehouseRoof.Quads(RoofY, 0, 0, 20, 10, Cell, Inset, Tops(54, 58, 40, 50)).ToArray();

        var east = quads.Where(q => q.All(p => p.X == 20 - Inset)).ToArray();
        Assert.Equal(1, east.Length);
        Assert.Equal(58f, east[0].Min(p => p.Y));
        Assert.Equal(RoofY, east[0].Max(p => p.Y));
        Assert.True(FrontNormal(east[0]).X < -0.99f);
        var south = quads.Where(q => q.All(p => p.Z == Inset)).ToArray();
        Assert.Equal(2, south.Length);
        Assert.All(south, q => Assert.True(FrontNormal(q).Z > 0.99f));
        Assert.All(south, q => Assert.Equal(40f, q.Min(p => p.Y)));
    }

    [Fact]
    public void Quads_OmitsASkirtWhereTheWallReachesTheRoof()
    {
        var quads = WarehouseRoof.Quads(RoofY, 0, 0, 20, 10, Cell, Inset, Tops(RoofY, 54, 54, 54)).ToArray();

        Assert.Empty(quads.Where(q => q.All(p => p.X == Inset)));
    }
}
