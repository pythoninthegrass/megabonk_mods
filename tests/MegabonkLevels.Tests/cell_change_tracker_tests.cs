namespace MegabonkLevels.Tests;

public class CellChangeTrackerTests
{
    private static readonly GridCell CellA = new(10, 7, true);
    private static readonly GridCell CellB = new(11, 7, true);

    [Fact]
    public void Changed_FirstSightingOfAnId_IsAlwaysAChange()
    {
        var tracker = new CellChangeTracker();

        Assert.True(tracker.Changed(1, CellA, 0));
    }

    [Fact]
    public void Changed_SameCellAndLevel_IsNotAChange()
    {
        var tracker = new CellChangeTracker();
        tracker.Changed(1, CellA, 0);

        Assert.False(tracker.Changed(1, CellA, 0));
    }

    [Fact]
    public void Changed_DifferentCell_IsAChange()
    {
        var tracker = new CellChangeTracker();
        tracker.Changed(1, CellA, 0);

        Assert.True(tracker.Changed(1, CellB, 0));
    }

    [Fact]
    public void Changed_SameCellDifferentLevel_IsAChange()
    {
        var tracker = new CellChangeTracker();
        tracker.Changed(1, CellA, 0);

        Assert.True(tracker.Changed(1, CellA, 1));
    }

    [Fact]
    public void Changed_InAndOutOfGrid_IsAChangeEvenAtTheSameIndices()
    {
        var tracker = new CellChangeTracker();
        tracker.Changed(1, new GridCell(-1, 7, false), 0);

        Assert.True(tracker.Changed(1, new GridCell(-1, 7, true), 0));
    }

    [Fact]
    public void Changed_DifferentIds_AreTrackedIndependently()
    {
        var tracker = new CellChangeTracker();
        tracker.Changed(1, CellA, 0);

        Assert.True(tracker.Changed(2, CellA, 0));
        Assert.False(tracker.Changed(2, CellA, 0));
        Assert.False(tracker.Changed(1, CellA, 0));
    }

    [Fact]
    public void Reset_ForgetsEveryId()
    {
        var tracker = new CellChangeTracker();
        tracker.Changed(1, CellA, 0);

        tracker.Reset();

        Assert.True(tracker.Changed(1, CellA, 0));
    }

    [Fact]
    public void PlayerId_IsAReservedConstant()
    {
        var tracker = new CellChangeTracker();

        Assert.True(tracker.Changed(CellChangeTracker.PlayerId, CellA, 0));
        Assert.False(tracker.Changed(CellChangeTracker.PlayerId, CellA, 0));
    }
}
