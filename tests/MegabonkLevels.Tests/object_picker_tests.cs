namespace MegabonkLevels.Tests;

public class ObjectPickerTests
{
    private static RayHit Solid(float distance, bool resolves) => new(distance, false, resolves, false);

    private static RayHit Trigger(float distance, bool resolves, bool hitsModel) => new(distance, true, resolves, hitsModel);

    [Fact]
    public void NearestHit_SolidObjectHit_IsPicked()
    {
        Assert.Equal(1, ObjectPicker.NearestHit(new[] { Solid(50f, false), Solid(10f, true) }));
    }

    [Fact]
    public void NearestHit_TriggerWithoutModelBoundsHit_IsSkippedForTheObjectBehindIt()
    {
        var hits = new[] { Trigger(41f, true, false), Trigger(53f, true, true) };

        Assert.Equal(1, ObjectPicker.NearestHit(hits));
    }

    [Fact]
    public void NearestHit_TriggerWithModelBoundsHit_IsPicked()
    {
        Assert.Equal(0, ObjectPicker.NearestHit(new[] { Trigger(41f, true, true), Solid(60f, true) }));
    }

    [Fact]
    public void NearestHit_SolidNonObjectInFront_BlocksObjectsBehindIt()
    {
        Assert.Equal(-1, ObjectPicker.NearestHit(new[] { Solid(20f, false), Solid(30f, true) }));
    }

    [Fact]
    public void NearestHit_TriggerThatIsNotAnObject_DoesNotBlock()
    {
        Assert.Equal(1, ObjectPicker.NearestHit(new[] { Trigger(5f, false, false), Solid(30f, true) }));
    }

    [Fact]
    public void NearestHit_NoHits_ReturnsMinusOne()
    {
        Assert.Equal(-1, ObjectPicker.NearestHit(Array.Empty<RayHit>()));
    }

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
