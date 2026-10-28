using System.Numerics;

namespace MegabonkLevels.Tests;

public class CoplanarLayeringTests
{
    // Corner order matches the importer: the front normal is that of the reversed polygon, so these quads in the x-y plane face +z.
    static int[] AddQuad(List<Vector3> vertices, float minX, float minY, float maxX, float maxY, float z)
    {
        var first = vertices.Count;
        vertices.Add(new Vector3(minX, minY, z));
        vertices.Add(new Vector3(minX, maxY, z));
        vertices.Add(new Vector3(maxX, maxY, z));
        vertices.Add(new Vector3(maxX, minY, z));
        return new[] { first, first + 1, first + 2, first + 3 };
    }

    static float Z(List<Vector3> vertices, int[] face) => vertices[face[0]].Z;

    [Fact]
    public void Separate_LiftsSmallerFaceAlongNormal_WhenInsideLargerCoplanarFace()
    {
        var vertices = new List<Vector3>();
        var poster = AddQuad(vertices, 0.2f, 0.2f, 0.4f, 0.4f, 0);
        var wall = AddQuad(vertices, 0, 0, 1, 1, 0);

        CoplanarLayering.Separate(vertices, new[] { poster, wall });

        Assert.Equal(CoplanarLayering.LiftStep, Z(vertices, poster), 6);
        Assert.Equal(0f, Z(vertices, wall), 6);
    }

    [Fact]
    public void Separate_LiftsAllCornersOfAFaceEqually()
    {
        var vertices = new List<Vector3>();
        var poster = AddQuad(vertices, 0.2f, 0.2f, 0.4f, 0.4f, 0);
        var wall = AddQuad(vertices, 0, 0, 1, 1, 0);

        CoplanarLayering.Separate(vertices, new[] { poster, wall });

        Assert.All(poster, i => Assert.Equal(CoplanarLayering.LiftStep, vertices[i].Z, 6));
    }

    [Fact]
    public void Separate_LiftsLaterFace_WhenAreasAreEqual()
    {
        var vertices = new List<Vector3>();
        var first = AddQuad(vertices, 0, 0, 1, 1, 0);
        var second = AddQuad(vertices, 0.5f, 0.5f, 1.5f, 1.5f, 0);

        CoplanarLayering.Separate(vertices, new[] { first, second });

        Assert.Equal(0f, Z(vertices, first), 6);
        Assert.Equal(CoplanarLayering.LiftStep, Z(vertices, second), 6);
    }

    [Fact]
    public void Separate_StacksThreeFacesInOrderOfSize()
    {
        var vertices = new List<Vector3>();
        var small = AddQuad(vertices, 0.4f, 0.4f, 0.5f, 0.5f, 0);
        var medium = AddQuad(vertices, 0.2f, 0.2f, 0.7f, 0.7f, 0);
        var large = AddQuad(vertices, 0, 0, 1, 1, 0);

        CoplanarLayering.Separate(vertices, new[] { small, medium, large });

        Assert.Equal(0f, Z(vertices, large), 6);
        Assert.Equal(CoplanarLayering.LiftStep, Z(vertices, medium), 6);
        Assert.Equal(2 * CoplanarLayering.LiftStep, Z(vertices, small), 6);
    }

    [Fact]
    public void Separate_LeavesCoplanarFacesThatDoNotOverlap()
    {
        var vertices = new List<Vector3>();
        var left = AddQuad(vertices, 0, 0, 1, 1, 0);
        var right = AddQuad(vertices, 2, 0, 3, 1, 0);

        CoplanarLayering.Separate(vertices, new[] { left, right });

        Assert.Equal(0f, Z(vertices, left), 6);
        Assert.Equal(0f, Z(vertices, right), 6);
    }

    [Fact]
    public void Separate_LeavesFacesThatOnlyShareAnEdge()
    {
        var vertices = new List<Vector3>();
        var left = AddQuad(vertices, 0, 0, 1, 1, 0);
        var right = AddQuad(vertices, 1, 0, 2, 1, 0);

        CoplanarLayering.Separate(vertices, new[] { left, right });

        Assert.Equal(0f, Z(vertices, left), 6);
        Assert.Equal(0f, Z(vertices, right), 6);
    }

    [Fact]
    public void Separate_LeavesParallelFacesBeyondPlaneTolerance()
    {
        var vertices = new List<Vector3>();
        var poster = AddQuad(vertices, 0.2f, 0.2f, 0.4f, 0.4f, 0.01f);
        var wall = AddQuad(vertices, 0, 0, 1, 1, 0);

        CoplanarLayering.Separate(vertices, new[] { poster, wall });

        Assert.Equal(0.01f, Z(vertices, poster), 6);
        Assert.Equal(0f, Z(vertices, wall), 6);
    }

    [Fact]
    public void Separate_LeavesBackToBackFaces()
    {
        var vertices = new List<Vector3>();
        var front = AddQuad(vertices, 0, 0, 1, 1, 0);
        var first = vertices.Count;
        vertices.Add(new Vector3(0.2f, 0.2f, 0));
        vertices.Add(new Vector3(0.4f, 0.2f, 0));
        vertices.Add(new Vector3(0.4f, 0.4f, 0));
        vertices.Add(new Vector3(0.2f, 0.4f, 0));
        var back = new[] { first, first + 1, first + 2, first + 3 };

        CoplanarLayering.Separate(vertices, new[] { front, back });

        Assert.Equal(0f, Z(vertices, front), 6);
        Assert.Equal(0f, Z(vertices, back), 6);
    }

    [Fact]
    public void Separate_LeavesPerpendicularFaces()
    {
        var vertices = new List<Vector3>();
        var wall = AddQuad(vertices, 0, 0, 1, 1, 0);
        var first = vertices.Count;
        vertices.Add(new Vector3(0.5f, 0, -0.5f));
        vertices.Add(new Vector3(0.5f, 1, -0.5f));
        vertices.Add(new Vector3(0.5f, 1, 0.5f));
        vertices.Add(new Vector3(0.5f, 0, 0.5f));
        var crossing = new[] { first, first + 1, first + 2, first + 3 };

        CoplanarLayering.Separate(vertices, new[] { wall, crossing });

        Assert.Equal(0f, Z(vertices, wall), 6);
        Assert.Equal(0.5f, vertices[crossing[2]].Z, 6);
    }
}
