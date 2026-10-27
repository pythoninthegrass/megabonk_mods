namespace MegabonkLevels.Tests;

public class TerrainEditsTests
{
    private static readonly Vector3Data Origin = new(0, 0, 0);
    private static readonly Vector3Data One = new(1, 1, 1);

    private static EditOp Place() => new PlaceObject("interactable/chest", Origin, Origin, One).ToEditOp();

    private static EditOp Height() => new SetTileHeight(1, 2, 3).ToEditOp();

    [Fact]
    public void Split_KeepsObjectOpsInOrderAndRejectsTileOps()
    {
        var place = Place();
        var height = Height();
        var remove = new RemoveObject(ObjectTarget.FromGenId("object:Chest:0")).ToEditOp();

        var split = TerrainEdits.Split(new[] { place, height, remove });

        Assert.Equal(new[] { place, remove }, split.Kept);
        Assert.Equal(new[] { height }, split.Rejected);
    }

    [Fact]
    public void Split_NoTileOps_RejectsNothing()
    {
        var split = TerrainEdits.Split(new[] { Place() });

        Assert.Single(split.Kept);
        Assert.Empty(split.Rejected);
    }
}
