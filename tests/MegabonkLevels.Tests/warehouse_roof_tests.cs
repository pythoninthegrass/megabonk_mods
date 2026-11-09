using System.Numerics;

namespace MegabonkLevels.Tests;

public class WarehouseRoofTests
{
    const float Inset = 0.5f, Band = 1f, FloorY = 0f, RoofY = 66f;

    static Vector3 FrontNormal(Vector3[] quad) => Vector3.Normalize(Vector3.Cross(quad[1] - quad[0], quad[2] - quad[0]));

    // Two triangles forming a rectangle on the plane x = across, spanning z from a0 to a1 and y from 0 to top.
    static Vector3[][] WestWall(float across, float a0, float a1, float top) => new[]
    {
        new[] { new Vector3(across, 0, a0), new Vector3(across, top, a0), new Vector3(across, top, a1) },
        new[] { new Vector3(across, 0, a0), new Vector3(across, top, a1), new Vector3(across, 0, a1) },
    };

    // A gable face on the plane z = across: a pentagon rising from y 50 at both ends to a peak of 65 at x 10, fanned from the floor corner.
    static Vector3[][] SouthGable(float across) => new[]
    {
        new[] { new Vector3(0, 0, across), new Vector3(0, 50, across), new Vector3(10, 65, across) },
        new[] { new Vector3(0, 0, across), new Vector3(10, 65, across), new Vector3(20, 50, across) },
        new[] { new Vector3(0, 0, across), new Vector3(20, 50, across), new Vector3(20, 0, across) },
    };

    static Vector2[] Flat(float alongMin, float alongMax, float y) => new[] { new Vector2(alongMin, y), new Vector2(alongMax, y) };

    static Vector2[][] Profiles(Vector2[] west, Vector2[] east, Vector2[] south, Vector2[] north) => new[] { west, east, south, north };

    static float ProfileAt(Vector2[] profile, float along)
    {
        for (var i = 0; i + 1 < profile.Length; i++)
        {
            Vector2 p = profile[i], q = profile[i + 1];
            if (p.X < along && along < q.X)
                return p.Y + (q.Y - p.Y) * (along - p.X) / (q.X - p.X);
        }

        throw new InvalidOperationException("no segment strictly contains " + along);
    }

    [Fact]
    public void EdgeWallProfile_FollowsASlopingGableInsteadOfItsPeak()
    {
        var profile = WarehouseRoof.EdgeWallProfile(SouthGable(0.2f), WarehouseRoof.Side.South, 0, 20, 0, Band, FloorY);

        Assert.Equal(53f, ProfileAt(profile, 2), 3);
        Assert.Equal(62f, ProfileAt(profile, 8), 3);
        Assert.Equal(65f, profile.Max(p => p.Y), 3);
    }

    [Fact]
    public void EdgeWallProfile_StepsWhereAdjacentWallsChangeHeight()
    {
        var walls = WestWall(0.2f, 0, 6, 40).Concat(WestWall(0.4f, 6, 12, 58));

        var profile = WarehouseRoof.EdgeWallProfile(walls, WarehouseRoof.Side.West, 0, 12, 0, Band, FloorY);

        Assert.Equal(new[] { new Vector2(0, 40), new Vector2(6, 40), new Vector2(6, 58), new Vector2(12, 58) }, profile);
    }

    [Fact]
    public void EdgeWallProfile_UsesTheFloorWhereNoWallStandsOnTheEdge()
    {
        var far = WestWall(5f, 1, 4, 54);
        var flat = new[] { new Vector3(0.2f, 30, 1), new Vector3(0.2f, 30, 4), new Vector3(3, 30, 1) };

        var profile = WarehouseRoof.EdgeWallProfile(far.Append(flat), WarehouseRoof.Side.West, 0, 20, 0, Band, FloorY);

        Assert.Equal(new[] { new Vector2(0, FloorY), new Vector2(20, FloorY) }, profile);
    }

    [Fact]
    public void EdgeWallProfile_NeverRisesAboveTheWallBeneathIt()
    {
        var spans = new[] { (0f, 10f, 40f), (5f, 15f, 55f), (12f, 20f, 30f) };
        var walls = spans.SelectMany(s => WestWall(0.2f, s.Item1, s.Item2, s.Item3)).ToArray();

        var profile = WarehouseRoof.EdgeWallProfile(walls, WarehouseRoof.Side.West, 0, 20, 0, Band, FloorY);

        for (var along = 0.5f; along < 20; along += 1f)
        {
            var wallTop = spans.Where(s => s.Item1 < along && along < s.Item2).Select(s => s.Item3).DefaultIfEmpty(FloorY).Max();
            Assert.Equal(wallTop, ProfileAt(profile, along), 3);
        }
    }

    static float[,] Grid(int cellsX, int cellsZ, float fill)
    {
        var grid = new float[cellsX, cellsZ];
        for (var i = 0; i < cellsX; i++)
            for (var j = 0; j < cellsZ; j++)
                grid[i, j] = fill;
        return grid;
    }

    [Fact]
    public void ColumnTops_TakesTheSurfaceHeightOverEveryCellAFaceCovers()
    {
        var flat = new[] { new Vector3(0.1f, 48, 0.1f), new Vector3(0.1f, 48, 1.9f), new Vector3(1.9f, 48, 0.1f) };

        var tops = WarehouseRoof.ColumnTops(new[] { flat }, 0, 0, 1, 3, 3);

        Assert.Equal(48f, tops[0, 0]);
        Assert.Equal(48f, tops[1, 0]);
        Assert.Equal(48f, tops[0, 1]);
        Assert.True(float.IsNaN(tops[2, 2]));
    }

    [Fact]
    public void ColumnTops_RunsAWallsTopLineAcrossEveryCellItPasses()
    {
        var wall = new[] { new Vector3(0.5f, 0, 0.2f), new Vector3(0.5f, 40, 0.2f), new Vector3(0.5f, 40, 4.8f) };

        var tops = WarehouseRoof.ColumnTops(new[] { wall }, 0, 0, 1, 2, 5);

        Assert.Equal(40f, tops[0, 4], 0);
        Assert.True(tops[0, 0] >= 0 && tops[0, 0] <= 40);
        Assert.Equal(5, Enumerable.Range(0, 5).Count(j => !float.IsNaN(tops[0, j])));
        Assert.All(Enumerable.Range(0, 5), j => Assert.True(float.IsNaN(tops[1, j])));
    }

    [Fact]
    public void ColumnTops_FollowsADiagonalWall()
    {
        var wall = new[] { new Vector3(0.2f, 0, 0.2f), new Vector3(0.2f, 30, 0.2f), new Vector3(4.8f, 30, 4.8f) };

        var tops = WarehouseRoof.ColumnTops(new[] { wall }, 0, 0, 1, 5, 5);

        Assert.All(Enumerable.Range(0, 5), k => Assert.False(float.IsNaN(tops[k, k])));
        Assert.True(float.IsNaN(tops[0, 4]));
        Assert.True(float.IsNaN(tops[4, 0]));
    }

    [Fact]
    public void SpillLevels_FillABasinToItsLowestRim()
    {
        var tops = Grid(5, 5, 0);
        for (var k = 0; k < 5; k++)
            (tops[0, k], tops[4, k], tops[k, 0], tops[k, 4]) = (10, 10, 10, 10);
        tops[2, 4] = 8;

        var level = WarehouseRoof.SpillLevels(tops, 5, 70);

        Assert.Equal(8f, level[2, 2]);
        Assert.Equal(8f, level[1, 1]);
        Assert.Equal(10f, level[0, 2]);
        Assert.Equal(8f, level[2, 4]);
    }

    [Fact]
    public void SpillLevels_KeepAnInteriorBumpAtItsOwnHeight()
    {
        var tops = Grid(5, 5, 0);
        for (var k = 0; k < 5; k++)
            (tops[0, k], tops[4, k], tops[k, 0], tops[k, 4]) = (10, 10, 10, 10);
        tops[2, 2] = 12;

        var level = WarehouseRoof.SpillLevels(tops, 5, 70);

        Assert.Equal(12f, level[2, 2]);
        Assert.Equal(10f, level[1, 2]);
    }

    [Fact]
    public void SpillLevels_SealAnOpenBoundaryAtTheSealHeight()
    {
        var tops = Grid(5, 5, 0);
        tops[2, 2] = 12;

        var level = WarehouseRoof.SpillLevels(tops, 5, 70);

        Assert.Equal(70f, level[0, 0]);
        Assert.Equal(70f, level[2, 1]);
        Assert.Equal(70f, level[2, 2]);
    }

    [Fact]
    public void SpillLevels_LowerAnOpenBoundaryGapToTheRimAroundIt()
    {
        var tops = Grid(5, 5, 0);
        for (var k = 0; k < 5; k++)
            (tops[0, k], tops[4, k], tops[k, 0], tops[k, 4]) = (10, 10, 10, 10);
        tops[4, 2] = 0;

        var level = WarehouseRoof.SpillLevels(tops, 5, 70);

        Assert.Equal(10f, level[2, 2]);
        Assert.Equal(10f, level[4, 2]);
    }

    static float[,] Ceiling(params float[] row)
    {
        var ceiling = new float[row.Length, 1];
        for (var i = 0; i < row.Length; i++)
            ceiling[i, 0] = row[i];
        return ceiling;
    }

    static readonly Vector2[][] FlatProfiles = Profiles(Flat(0, 10, 54), Flat(0, 10, 54), Flat(0, 20, 54), Flat(0, 20, 54));

    [Fact]
    public void Quads_MergesEqualHeightCellsInARowIntoOneDownFacingRoof()
    {
        var quads = WarehouseRoof.Quads(Ceiling(RoofY, RoofY), 0, 0, 20, 10, 10, Inset, FlatProfiles).ToArray();

        var roof = quads.Where(q => q.All(p => p.Y == RoofY && p.X != 0)).ToArray();
        Assert.Single(roof);
        Assert.Equal(-1f, FrontNormal(roof[0]).Y, 4);
        Assert.Equal(Inset, roof[0].Min(p => p.X));
        Assert.Equal(20 - Inset, roof[0].Max(p => p.X));
    }

    [Fact]
    public void Quads_AddsAStepFaceBetweenCellsOfDifferentHeightFacingTheTallerSide()
    {
        var quads = WarehouseRoof.Quads(Ceiling(RoofY, 50), 0, 0, 20, 10, 10, Inset, FlatProfiles).ToArray();

        var step = quads.Single(q => q.All(p => p.X == 10));
        Assert.Equal(50f, step.Min(p => p.Y));
        Assert.Equal(RoofY, step.Max(p => p.Y));
        Assert.True(FrontNormal(step).X < -0.99f);
    }

    [Fact]
    public void Quads_AddsOneInwardFacingSkirtPerProfileSegmentUpToTheEdgeCellCeiling()
    {
        var south = new[] { new Vector2(0, 40), new Vector2(10, 40), new Vector2(20, 40) };

        var quads = WarehouseRoof.Quads(Ceiling(RoofY, 58), 0, 0, 20, 10, 10, Inset, Profiles(Flat(0, 10, 54), Flat(0, 10, 50), south, Flat(0, 20, 50))).ToArray();

        var east = quads.Where(q => q.All(p => p.X == 20 - Inset)).ToArray();
        Assert.Single(east);
        Assert.Equal(50f, east[0].Min(p => p.Y));
        Assert.Equal(58f, east[0].Max(p => p.Y));
        Assert.True(FrontNormal(east[0]).X < -0.99f);
        var southSkirts = quads.Where(q => q.All(p => p.Z == Inset)).OrderBy(q => q.Min(p => p.X)).ToArray();
        Assert.Equal(2, southSkirts.Length);
        Assert.All(southSkirts, q => Assert.True(FrontNormal(q).Z > 0.99f));
        Assert.Equal(new[] { RoofY, 58f }, southSkirts.Select(q => q.Max(p => p.Y)));
    }

    [Fact]
    public void Quads_StartsTheSkirtAtEachEndOfASlopingSegment()
    {
        var south = new[] { new Vector2(0, 50), new Vector2(10, 62) };

        var quads = WarehouseRoof.Quads(Ceiling(RoofY, RoofY), 0, 0, 20, 10, 10, Inset, Profiles(Flat(0, 10, 54), Flat(0, 10, 54), south, Flat(0, 20, 54))).ToArray();

        var skirt = quads.Single(q => q.All(p => p.Z == Inset));
        Assert.Contains(skirt, p => p.X == 0 && p.Y == 50);
        Assert.Contains(skirt, p => p.X == 10 && p.Y == 62);
        Assert.Contains(skirt, p => p.X == 10 && p.Y == RoofY);
    }

    [Fact]
    public void Quads_OmitsASkirtWhereTheWallReachesTheCeiling()
    {
        var quads = WarehouseRoof.Quads(Ceiling(RoofY, RoofY), 0, 0, 20, 10, 10, Inset, Profiles(Flat(0, 10, RoofY), Flat(0, 10, 54), Flat(0, 20, 54), Flat(0, 20, 54))).ToArray();

        Assert.DoesNotContain(quads, q => q.All(p => p.X == Inset));
    }
}
