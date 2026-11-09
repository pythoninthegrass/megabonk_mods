namespace MegabonkLevels.Tests;

public class NativeLavaGeometryTests
{
    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public void TemplateTrianglesFaceUpAfterTheirNativeTransformIsBaked(bool reversed)
    {
        var vertices = new[] { new Vector3Data(-1, 0, -1), new Vector3Data(-1, 0, 1), new Vector3Data(1, 0, 1), new Vector3Data(1, 0, -1) };
        var triangles = reversed ? new[] { 0, 2, 1, 0, 3, 2 } : new[] { 0, 1, 2, 0, 2, 3 };
        Assert.Equal(new[] { 0, 1, 2, 0, 2, 3 }, NativeLavaGeometry.FaceUp(vertices, triangles));
    }

    [Fact]
    public void NativeQuadIsFittedToTheCellWithoutReorderingItsUvVertices()
    {
        var vertices = new[] { new Vector3Data(-1497, -1.5f, 11.5f), new Vector3Data(-1453, -1.5f, 11.5f), new Vector3Data(-1453, -1.5f, 91.5f), new Vector3Data(-1497, -1.5f, 91.5f) };
        Assert.True(NativeLavaGeometry.CanFit(vertices));
        Assert.Equal(new[] { new Vector3Data(180, 0.02f, -180), new Vector3Data(220, 0.02f, -180), new Vector3Data(220, 0.02f, -140), new Vector3Data(180, 0.02f, -140) },
            NativeLavaGeometry.Fit(vertices, new Vector3Data(200, 0.02f, -160), 40, 40));
    }

    [Fact]
    public void NonPlanarOrIncompleteSurfacesAreNotEligibleNativeTemplates()
    {
        Assert.False(NativeLavaGeometry.CanFit(Array.Empty<Vector3Data>()));
        Assert.False(NativeLavaGeometry.CanFit(new[] { new Vector3Data(0, 0, 0), new Vector3Data(1, 0, 0), new Vector3Data(1, 0, 1) }));
        Assert.False(NativeLavaGeometry.CanFit(new[] { new Vector3Data(0, 0, 0), new Vector3Data(1, 0, 0), new Vector3Data(1, 1, 1), new Vector3Data(0, 0, 1) }));
    }

    [Fact]
    public void SplitUvVerticesKeepTheirOriginalIndicesAndRectangularAspectFitsIndependently()
    {
        var vertices = new[] { new Vector3Data(0, 0, 0), new Vector3Data(1, 0, 0), new Vector3Data(1, 0, 1), new Vector3Data(0, 0, 0), new Vector3Data(1, 0, 1), new Vector3Data(0, 0, 1) };
        var fitted = NativeLavaGeometry.Fit(vertices, new Vector3Data(0, 3, 0), 40, 80);
        Assert.Equal(6, fitted.Count);
        Assert.Equal(fitted[0], fitted[3]);
        Assert.Equal(fitted[2], fitted[4]);
        Assert.Equal(new Vector3Data(-20, 3, -40), fitted[0]);
        Assert.Equal(new Vector3Data(20, 3, 40), fitted[2]);
    }
}
