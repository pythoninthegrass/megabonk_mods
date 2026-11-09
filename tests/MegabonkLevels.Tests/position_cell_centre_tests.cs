namespace MegabonkLevels.Tests;

public class CellCentreTests
{
    [Fact]
    public void CellCentre_IsGridCentredWithTheSameOriginAsCellOf()
    {
        var (x, z) = PositionReadout.CellCentre(9, 7, 15, 15, 40f);

        Assert.Equal((80f, 0f), (x, z));
    }

    [Fact]
    public void CellCentre_EvenSizedGrid_FallsBetweenTheMiddleCells()
    {
        var (x, z) = PositionReadout.CellCentre(0, 0, 4, 4, 10f);

        Assert.Equal((-15f, -15f), (x, z));
    }

    [Theory]
    [InlineData(3, 11)]
    [InlineData(0, 0)]
    [InlineData(14, 14)]
    public void CellCentre_MapsBackToTheSameCell(int cellX, int cellZ)
    {
        var (x, z) = PositionReadout.CellCentre(cellX, cellZ, 15, 15, 40f);

        Assert.Equal(new GridCell(cellX, cellZ, true), PositionReadout.CellOf(x, z, 15, 15, 40f));
    }
}
