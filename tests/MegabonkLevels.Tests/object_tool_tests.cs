namespace MegabonkLevels.Tests;

public class ObjectToolTests
{
    private const string Chest = "interactable/chest";
    private static readonly ObjectTarget Generated = ObjectTarget.FromGenId("object:Tree0:0003");
    private static readonly TransformData Current = new(new Vector3Data(1, 2, 3), new Vector3Data(10, 90, 20), new Vector3Data(2, 2, 2));

    [Fact]
    public void SnapPosition_FlatTile_IsTheCellCentreAtTheTileSurface()
    {
        var position = ObjectTools.SnapPosition(9, 7, new TileState(2, SlopeDirection.None), 15, 15, 40f, 20f);

        Assert.Equal(new Vector3Data(80f, 40f, 0f), position);
    }

    [Fact]
    public void SnapPosition_Ramp_SitsHalfALevelUp()
    {
        var position = ObjectTools.SnapPosition(7, 7, new TileState(1, SlopeDirection.East), 15, 15, 40f, 20f);

        Assert.Equal(new Vector3Data(0f, 30f, 0f), position);
    }

    [Theory]
    [InlineData(0f, 180f)]
    [InlineData(40f, 180f)]
    [InlineData(50f, 270f)]
    [InlineData(90f, 270f)]
    [InlineData(180f, 0f)]
    [InlineData(270f, 90f)]
    [InlineData(359f, 180f)]
    [InlineData(-90f, 90f)]
    public void FacingYaw_IsCameraYawPlus180RoundedToNinety(float cameraYaw, float expected)
    {
        Assert.Equal(expected, ObjectTools.FacingYaw(cameraYaw));
    }

    [Fact]
    public void Place_KeepsThePrefabPitchRollAndScaleWithTheFacingYaw()
    {
        var op = ObjectTools.Place(CatalogId.Parse(Chest), new Vector3Data(80f, 40f, 0f), new Vector3Data(5f, 33f, 7f), new Vector3Data(2f, 2f, 2f), 90f);

        var expected = new PlaceObject(Chest, new Vector3Data(80f, 40f, 0f), new Vector3Data(5f, 270f, 7f), new Vector3Data(2f, 2f, 2f));
        Assert.Equal(expected.ToEditOp(), op);
    }

    [Fact]
    public void Move_ChangesOnlyThePosition()
    {
        var op = ObjectTools.Move(Generated, Current, new Vector3Data(80f, 40f, 0f));

        var expected = new MoveObject(Generated, new TransformData(new Vector3Data(80f, 40f, 0f), Current.Rotation, Current.Scale));
        Assert.Equal(expected.ToEditOp(), op);
    }

    [Theory]
    [InlineData(true, 180f)]
    [InlineData(false, 0f)]
    public void Rotate_StepsYawNinetyDegreesKeepingPitchRollAndPosition(bool clockwise, float expectedYaw)
    {
        var op = ObjectTools.Rotate(Generated, Current, clockwise);

        var expected = new MoveObject(Generated, new TransformData(Current.Position, new Vector3Data(10, expectedYaw, 20), Current.Scale));
        Assert.Equal(expected.ToEditOp(), op);
    }

    [Theory]
    [InlineData(270f, true, 0f)]
    [InlineData(0f, false, 270f)]
    public void Rotate_WrapsYawIntoZeroToThreeSixty(float yaw, bool clockwise, float expectedYaw)
    {
        var start = Current with { Rotation = new Vector3Data(0, yaw, 0) };

        var op = ObjectTools.Rotate(Generated, start, clockwise);

        Assert.Equal(expectedYaw, MoveObject.FromEditOp(op).NewTransform.Rotation.Y);
    }

    [Fact]
    public void Remove_RemovesTheTarget()
    {
        Assert.Equal(new RemoveObject(Generated).ToEditOp(), ObjectTools.Remove(Generated));
    }

    [Fact]
    public void PlannerRoundTrip_PlacementIdsAllocateInOrderAndMovesTargetThem()
    {
        var planner = new LiveEditPlanner(LevelState.FromTiles(new Dictionary<(int X, int Z), TileState>()));
        var place = ObjectTools.Place(CatalogId.Parse(Chest), new Vector3Data(0, 0, 0), new Vector3Data(0, 0, 0), new Vector3Data(1, 1, 1), 0f);

        var first = planner.Apply(place);
        var second = planner.Apply(place);
        var move = planner.Apply(ObjectTools.Move(second.Target, new TransformData(new Vector3Data(0, 0, 0), new Vector3Data(0, 180, 0), new Vector3Data(1, 1, 1)), new Vector3Data(5, 0, 5)));
        var remove = planner.Apply(ObjectTools.Remove(first.Target));

        Assert.Equal(ObjectTarget.FromPlacementId(0), first.Target);
        Assert.Equal(ObjectTarget.FromPlacementId(1), second.Target);
        Assert.Equal(LiveActionKind.MoveObject, move.Kind);
        Assert.Equal(second.Target, move.Target);
        Assert.Equal(LiveActionKind.RemoveObject, remove.Kind);
        Assert.Equal(first.Target, remove.Target);
    }
}
