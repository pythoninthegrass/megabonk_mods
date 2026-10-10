namespace MegabonkLevels.Tests;

public class ObjectPickerTests
{
    [Fact]
    public void NearestIndex_PicksTheClosestWithinRange()
    {
        var positions = new[] { (0f, 0f), (10f, 0f), (4f, 3f) };

        Assert.Equal(2, ObjectPicker.NearestIndex(positions, 5f, 3f, 20f));
    }

    [Fact]
    public void NearestIndex_NothingWithinRange_ReturnsMinusOne()
    {
        var positions = new[] { (100f, 0f) };

        Assert.Equal(-1, ObjectPicker.NearestIndex(positions, 0f, 0f, 20f));
    }

    [Fact]
    public void NearestIndex_ExactlyAtTheMaxDistance_IsInRange()
    {
        Assert.Equal(0, ObjectPicker.NearestIndex(new[] { (20f, 0f) }, 0f, 0f, 20f));
    }

    [Fact]
    public void NearestIndex_Empty_ReturnsMinusOne()
    {
        Assert.Equal(-1, ObjectPicker.NearestIndex(Array.Empty<(float, float)>(), 0f, 0f, 20f));
    }

    [Fact]
    public void NearestIndex_UsesXzDistanceOnly()
    {
        Assert.Equal(0, ObjectPicker.NearestIndex(new[] { (3f, 4f) }, 0f, 0f, 5f));
    }
}
