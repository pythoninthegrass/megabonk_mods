namespace MegabonkLevels.Tests;

public class FillEdgePlanTests
{
    private static bool All(int x, int z) => x >= 0 && x < 15 && z >= 0 && z < 15;

    [Fact]
    public void HoleEdges_RemovedCell_HasFourOccupiedNeighbours()
    {
        var edges = FillEdgePlan.EdgesAroundRemovals(new[] { (5, 5) },
            (x, z) => All(x, z) && (x, z) != (5, 5), All);

        Assert.Equal(4, edges.Count);
        Assert.All(edges, e => Assert.True((e.Ax, e.Az).CompareTo((e.Bx, e.Bz)) < 0));
    }

    [Fact]
    public void HoleEdges_AdjacentRemovedCells_OmitSharedEdgeAndDeduplicate()
    {
        var edges = FillEdgePlan.EdgesAroundRemovals(new[] { (5, 5), (6, 5), (5, 5) },
            (x, z) => All(x, z) && (x, z) != (5, 5) && (x, z) != (6, 5), All);

        Assert.Equal(6, edges.Count);
    }

    [Fact]
    public void HoleEdges_EditNextToExistingHole_RebuildsHoleWall()
    {
        Assert.Single(FillEdgePlan.EdgesAroundRemovals(new[] { (5, 5) },
            (x, z) => All(x, z) && (x, z) != (6, 5), All),
            e => e == new CellEdge(5, 5, 6, 5));
    }

    [Fact]
    public void HoleEdges_CornerRemoval_SkipsOutsideGrid()
    {
        Assert.Equal(2, FillEdgePlan.EdgesAroundRemovals(new[] { (0, 0), (-1, 0) },
            (x, z) => All(x, z) && (x, z) != (0, 0), All).Count);
    }

    [Fact]
    public void CleanupEdges_Removals_IncludeEmptySharedEdgeAndOuterBorder()
    {
        var edges = FillEdgePlan.CleanupEdges(new[] { (0, 0), (1, 0), (0, 0) },
            (x, z) => All(x, z) && (x, z) != (0, 0) && (x, z) != (1, 0), All);

        Assert.Equal(7, edges.Count);
        Assert.Contains(new CellEdge(0, 0, 1, 0), edges);
        Assert.Contains(new CellEdge(-1, 0, 0, 0), edges);
    }

    [Fact]
    public void CleanupEdges_OccupiedCorner_PreservesUntouchedOuterCliffs()
    {
        Assert.Equal(2, FillEdgePlan.CleanupEdges(new[] { (0, 0) }, All, All).Count);
    }

    [Fact]
    public void HoleEdges_AllEmpty_HasNothingToBuildButStillCleansEdges()
    {
        Assert.Empty(FillEdgePlan.EdgesAroundRemovals(new[] { (5, 5) }, (_, _) => false, All));
        Assert.Equal(4, FillEdgePlan.CleanupEdges(new[] { (5, 5) }, (_, _) => false, All).Count);
    }

    [Fact]
    public void HoleEdges_RestoredCell_HasOnlyOccupiedEdges()
    {
        Assert.Empty(FillEdgePlan.EdgesAroundRemovals(new[] { (5, 5) }, All, All));
        Assert.Equal(4, FillEdgePlan.EdgesAround(new[] { (5, 5) }, All).Count);
    }

    [Theory]
    [InlineData(0, 0, -1)]
    [InlineData(0, 3, -4)]
    [InlineData(-2, 1, -4)]
    public void HoleWallOffset_UsesIslandCliffDepth(int minimumHeight, int tileHeight, int expected)
    {
        Assert.Equal(expected, FillEdgePlan.HoleWallOffset(minimumHeight, tileHeight));
    }

    [Fact]
    public void EdgesAround_InteriorCell_HasFourEdges()
    {
        var edges = FillEdgePlan.EdgesAround(new[] { (5, 5) }, All);

        Assert.Equal(4, edges.Count);
        Assert.All(edges, e => Assert.True((e.Ax, e.Az) == (5, 5) || (e.Bx, e.Bz) == (5, 5)));
    }

    [Fact]
    public void EdgesAround_EdgesAreCanonicallyOrdered()
    {
        var edges = FillEdgePlan.EdgesAround(new[] { (5, 5) }, All);

        Assert.All(edges, e => Assert.True((e.Ax, e.Az).CompareTo((e.Bx, e.Bz)) < 0));
    }

    [Fact]
    public void EdgesAround_CornerCell_SkipsNeighboursOutsideTheGrid()
    {
        var edges = FillEdgePlan.EdgesAround(new[] { (0, 0) }, All);

        Assert.Equal(2, edges.Count);
    }

    [Fact]
    public void EdgesAround_UnoccupiedNeighbour_OmitsThatEdge()
    {
        var edges = FillEdgePlan.EdgesAround(new[] { (5, 5) }, (x, z) => (x, z) != (6, 5));

        Assert.Equal(3, edges.Count);
        Assert.DoesNotContain(edges, e => (e.Ax, e.Az) == (6, 5) || (e.Bx, e.Bz) == (6, 5));
    }

    [Fact]
    public void EdgesAround_UnoccupiedTouchedCell_HasNoEdges()
    {
        Assert.Empty(FillEdgePlan.EdgesAround(new[] { (5, 5) }, (x, z) => (x, z) != (5, 5)));
    }

    [Fact]
    public void EdgesAround_AdjacentTouchedCells_ShareTheirEdgeOnce()
    {
        var edges = FillEdgePlan.EdgesAround(new[] { (5, 5), (6, 5) }, All);

        Assert.Equal(7, edges.Count);
        Assert.Single(edges, e => (e.Ax, e.Az, e.Bx, e.Bz) == (5, 5, 6, 5));
    }

    [Fact]
    public void EdgesAround_DuplicateTouchedCells_AreDeduplicated()
    {
        Assert.Equal(4, FillEdgePlan.EdgesAround(new[] { (5, 5), (5, 5) }, All).Count);
    }

    [Theory]
    [InlineData(100f, 0f, 100f, 15f, true)]
    [InlineData(100f, 0f, 100f, -20f, true)]
    [InlineData(100f, 0f, 100f, 21f, false)]
    [InlineData(100f, 0f, 101f, 0f, false)]
    [InlineData(100f, 0f, 120f, 0f, false)]
    public void LiesOnEdge_AlongZ_MatchesOnlyPiecesOnTheEdgeLine(float mx, float mz, float px, float pz, bool expected)
    {
        Assert.Equal(expected, FillEdgePlan.LiesOnEdge(mx, mz, alongX: false, halfLength: 20f, px, pz));
    }

    [Fact]
    public void LiesOnEdge_AlongX_UsesTheXRangeAndAZLine()
    {
        Assert.True(FillEdgePlan.LiesOnEdge(0f, 40f, alongX: true, halfLength: 20f, 18f, 40f));
        Assert.False(FillEdgePlan.LiesOnEdge(0f, 40f, alongX: true, halfLength: 20f, 18f, 41f));
    }
}
