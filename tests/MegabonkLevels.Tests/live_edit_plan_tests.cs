namespace MegabonkLevels.Tests;

public class LiveEditPlanTests
{
    private static readonly TransformData SomeTransform =
        new(new Vector3Data(1, 2, 3), new Vector3Data(0, 90, 0), new Vector3Data(1, 1, 1));

    [Fact]
    public void Build_NoEdits_ReturnsEmptyPlan()
    {
        Assert.Empty(LiveEditPlan.Build(Array.Empty<EditOp>()));
    }

    [Fact]
    public void Build_SetTileHeight_EmitsSetTileWithResultingState()
    {
        var plan = LiveEditPlan.Build(new[] { new SetTileHeight(2, 3, 4).ToEditOp() });

        var action = Assert.Single(plan);
        Assert.Equal(LiveActionKind.SetTile, action.Kind);
        Assert.Equal((2, 3), (action.X, action.Z));
        Assert.Equal(new TileState(4, SlopeDirection.None), action.Tile);
    }

    [Fact]
    public void Build_HeightThenSlope_SlopeActionCarriesEarlierHeight()
    {
        var plan = LiveEditPlan.Build(new[]
        {
            new SetTileHeight(2, 3, 4).ToEditOp(),
            new SetTileSlope(2, 3, SlopeDirection.East).ToEditOp(),
        });

        Assert.Equal(new TileState(4, SlopeDirection.East), plan[1].Tile);
    }

    [Fact]
    public void Build_AddTile_EmitsSetTile()
    {
        var plan = LiveEditPlan.Build(new[] { new AddTile(1, 1, 2).ToEditOp() });

        Assert.Equal(LiveActionKind.SetTile, plan[0].Kind);
        Assert.Equal(new TileState(2, SlopeDirection.None), plan[0].Tile);
    }

    [Fact]
    public void Build_RemoveTile_EmitsRemoveTile()
    {
        var plan = LiveEditPlan.Build(new[] { new RemoveTile(5, 6).ToEditOp() });

        Assert.Equal(LiveActionKind.RemoveTile, plan[0].Kind);
        Assert.Equal((5, 6), (plan[0].X, plan[0].Z));
    }

    [Fact]
    public void Build_PlaceObject_EmitsSpawnWithMonotonicPlacementIds()
    {
        var place = new PlaceObject("forest/shrines/0", SomeTransform.Position, SomeTransform.Rotation, SomeTransform.Scale);

        var plan = LiveEditPlan.Build(new[] { place.ToEditOp(), place.ToEditOp() });

        Assert.Equal(LiveActionKind.SpawnObject, plan[0].Kind);
        Assert.Equal("forest/shrines/0", plan[0].CatalogId);
        Assert.Equal(ObjectTarget.FromPlacementId(0), plan[0].Target);
        Assert.Equal(ObjectTarget.FromPlacementId(1), plan[1].Target);
        Assert.Equal(SomeTransform, plan[0].Transform);
    }

    [Fact]
    public void Build_MoveAndRemoveObject_CarryTargetAndTransform()
    {
        var target = ObjectTarget.FromGenId("chest:0003");

        var plan = LiveEditPlan.Build(new[]
        {
            new MoveObject(target, SomeTransform).ToEditOp(),
            new RemoveObject(target).ToEditOp(),
        });

        Assert.Equal(LiveActionKind.MoveObject, plan[0].Kind);
        Assert.Equal(target, plan[0].Target);
        Assert.Equal(SomeTransform, plan[0].Transform);
        Assert.Equal(LiveActionKind.RemoveObject, plan[1].Kind);
        Assert.Equal(target, plan[1].Target);
    }

    [Fact]
    public void Build_UnknownOpType_Throws()
    {
        Assert.Throws<ArgumentException>(() => LiveEditPlan.Build(new[] { new EditOp("bogus", "", "{}") }));
    }

    [Fact]
    public void ChangesTerrain_NoActions_IsFalse()
    {
        Assert.False(LiveEditPlan.ChangesTerrain(LiveEditPlan.Build(Array.Empty<EditOp>())));
    }

    [Fact]
    public void ChangesTerrain_ObjectOnlyEdits_IsFalse()
    {
        var plan = LiveEditPlan.Build(new[] { new PlaceObject("forest/shrines/0", SomeTransform.Position, SomeTransform.Rotation, SomeTransform.Scale).ToEditOp() });

        Assert.False(LiveEditPlan.ChangesTerrain(plan));
    }

    [Theory]
    [MemberData(nameof(TerrainEdits))]
    public void ChangesTerrain_TileEdit_IsTrue(EditOp op)
    {
        Assert.True(LiveEditPlan.ChangesTerrain(LiveEditPlan.Build(new[] { op })));
    }

    public static IEnumerable<object[]> TerrainEdits()
    {
        yield return new object[] { new SetTileHeight(2, 3, 4).ToEditOp() };
        yield return new object[] { new SetTileSlope(2, 3, SlopeDirection.East).ToEditOp() };
        yield return new object[] { new AddTile(1, 1, 2).ToEditOp() };
        yield return new object[] { new RemoveTile(1, 1).ToEditOp() };
    }
}
