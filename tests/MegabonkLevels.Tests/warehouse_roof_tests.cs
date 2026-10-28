using System.Numerics;

namespace MegabonkLevels.Tests;

public class WarehouseRoofTests
{
    const float Cell = 10f, Inset = 0.5f, SkirtBottom = 54f;

    static Vector3[] FlatTriangle(float x, float z, float y, float size = 4f) =>
        new[] { new Vector3(x, y, z), new Vector3(x + size, y, z), new Vector3(x, y, z + size) };

    static Vector3 FrontNormal(Vector3[] quad) => Vector3.Normalize(Vector3.Cross(quad[1] - quad[0], quad[2] - quad[0]));

    static float[,] Tops(params (int ix, int iz, float y)[] cells)
    {
        var tops = new float[3, 1];
        for (var i = 0; i < 3; i++)
            tops[i, 0] = float.NaN;
        foreach (var (ix, iz, y) in cells)
            tops[ix, iz] = y;
        return tops;
    }

    [Fact]
    public void CellTops_TakesTheHighestStandableSurfaceTouchingEachCell()
    {
        var triangles = new[] { FlatTriangle(1, 1, 48), FlatTriangle(2, 2, 55), FlatTriangle(21, 1, 9) };

        var tops = WarehouseRoof.CellTops(triangles, 0, 0, Cell, 3, 1);

        Assert.Equal(55f, tops[0, 0]);
        Assert.Equal(9f, tops[2, 0]);
        Assert.True(float.IsNaN(tops[1, 0]));
    }

    [Fact]
    public void CellTops_IgnoresSteepFaces()
    {
        var wall = new[] { new Vector3(1, 0, 1), new Vector3(1, 60, 1), new Vector3(1, 0, 5) };

        var tops = WarehouseRoof.CellTops(new[] { wall }, 0, 0, Cell, 3, 1);

        Assert.True(float.IsNaN(tops[0, 0]));
    }

    [Fact]
    public void RoofHeights_AddsClearanceToTheTallestTopWithinReach()
    {
        var roof = WarehouseRoof.RoofHeights(Tops((0, 0, 48), (2, 0, 9)), 1, 6f);

        Assert.Equal(54f, roof[0, 0]);
        Assert.Equal(54f, roof[1, 0]);
        Assert.Equal(15f, roof[2, 0]);
    }

    [Fact]
    public void RoofHeights_FallsBackToTheTallestTopWhenNothingIsInReach()
    {
        var roof = WarehouseRoof.RoofHeights(Tops((0, 0, 48)), 0, 6f);

        Assert.Equal(54f, roof[2, 0]);
    }

    [Fact]
    public void Quads_PutsADownFacingRoofOverEachCellAtItsHeight()
    {
        var roof = new float[,] { { 54f }, { 61f } };

        var quads = WarehouseRoof.Quads(roof, 0, 0, 20, 10, Cell, SkirtBottom, Inset).ToArray();

        var roofQuads = quads.Where(q => q.All(p => p.Y == q[0].Y) && FrontNormal(q).Y < -0.99f).ToArray();
        Assert.Equal(new[] { 54f, 61f }, roofQuads.Select(q => q[0].Y).OrderBy(y => y));
    }

    [Fact]
    public void Quads_ClosesTheStepBetweenCellsFacingTheTallerCell()
    {
        var roof = new float[,] { { 54f }, { 61f } };

        var quads = WarehouseRoof.Quads(roof, 0, 0, 20, 10, Cell, SkirtBottom, Inset).ToArray();

        var step = quads.Single(q => q.All(p => p.X == Cell) && q.Min(p => p.Y) == 54f && q.Max(p => p.Y) == 61f);
        Assert.True(FrontNormal(step).X > 0.99f);
    }

    [Fact]
    public void Quads_AddsEdgeSkirtsFromTheLowestWallTopUpToTheRoofFacingInward()
    {
        var roof = new float[,] { { 54f }, { 61f } };

        var quads = WarehouseRoof.Quads(roof, 0, 0, 20, 10, Cell, SkirtBottom, Inset).ToArray();

        var east = quads.Single(q => q.All(p => p.X == 20 - Inset));
        Assert.Equal(SkirtBottom, east.Min(p => p.Y));
        Assert.Equal(61f, east.Max(p => p.Y));
        Assert.True(FrontNormal(east).X < -0.99f);
    }

    [Fact]
    public void Quads_OmitsASkirtWhereTheRoofIsNotAboveTheLowestWallTop()
    {
        var roof = new float[,] { { 54f }, { 54f } };

        var quads = WarehouseRoof.Quads(roof, 0, 0, 20, 10, Cell, SkirtBottom, Inset).ToArray();

        Assert.Equal(2, quads.Length);
    }
}
