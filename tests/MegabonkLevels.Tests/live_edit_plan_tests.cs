namespace MegabonkLevels.Tests;

public class LiveEditPlanTests
{
    private static readonly TransformData SomeTransform =
        new(new Vector3Data(1, 2, 3), new Vector3Data(0, 90, 0), new Vector3Data(1, 1, 1));

    private static IReadOnlyList<LiveAction> Build(params EditOp[] edits) => LiveEditPlan.Build(edits, new LevelState());

    private static LevelState Baseline(params ((int X, int Z) Cell, TileState Tile)[] tiles) =>
        LevelState.FromTiles(tiles.Select(t => new KeyValuePair<(int X, int Z), TileState>(t.Cell, t.Tile)));

    [Fact]
    public void Build_SetTileHeightOnBaselineSlope_KeepsTheSlope()
    {
        var baseline = Baseline(((2, 3), new TileState(1, SlopeDirection.West)));

        var plan = LiveEditPlan.Build(new[] { new SetTileHeight(2, 3, 2).ToEditOp() }, baseline);

        Assert.Equal(new TileState(2, SlopeDirection.West), plan[0].Tile);
    }

    [Fact]
    public void Build_SetTileSlopeOnBaselineTile_KeepsTheHeight()
    {
        var baseline = Baseline(((2, 3), new TileState(3, SlopeDirection.None)));

        var plan = LiveEditPlan.Build(new[] { new SetTileSlope(2, 3, SlopeDirection.North).ToEditOp() }, baseline);

        Assert.Equal(new TileState(3, SlopeDirection.North), plan[0].Tile);
    }

    [Fact]
    public void Build_RemoveThenAddOnBaselineTile_AddsAFlatTileAtTheNewHeight()
    {
        var baseline = Baseline(((2, 3), new TileState(3, SlopeDirection.East)));

        var plan = LiveEditPlan.Build(new[] { new RemoveTile(2, 3).ToEditOp(), new AddTile(2, 3, 1).ToEditOp() }, baseline);

        Assert.Equal(LiveActionKind.RemoveTile, plan[0].Kind);
        Assert.Equal(new TileState(1, SlopeDirection.None), plan[1].Tile);
    }

    [Fact]
    public void Build_DoesNotMutateTheBaseline()
    {
        var baseline = Baseline(((2, 3), new TileState(3, SlopeDirection.None)));

        LiveEditPlan.Build(new[] { new SetTileHeight(2, 3, 5).ToEditOp(), new RemoveTile(2, 3).ToEditOp() }, baseline);

        Assert.Equal(new TileState(3, SlopeDirection.None), baseline.GetTile(2, 3));
    }

    [Fact]
    public void Planner_AppliedOneByOne_MatchesBuild()
    {
        var baseline = Baseline(((2, 3), new TileState(1, SlopeDirection.South)));
        var place = new PlaceObject("forest/shrines/0", SomeTransform.Position, SomeTransform.Rotation, SomeTransform.Scale);
        var edits = new[]
        {
            new SetTileHeight(2, 3, 2).ToEditOp(),
            place.ToEditOp(),
            new SetTileSlope(2, 3, SlopeDirection.None).ToEditOp(),
            place.ToEditOp(),
        };

        var planner = new LiveEditPlanner(baseline);
        var incremental = edits.Select(planner.Apply).ToList();

        Assert.Equal(LiveEditPlan.Build(edits, baseline), incremental);
        Assert.Equal(new TileState(2, SlopeDirection.None), planner.State.GetTile(2, 3));
    }

    [Fact]
    public void Build_NoEdits_ReturnsEmptyPlan()
    {
        Assert.Empty(Build());
    }

    [Fact]
    public void Build_SetTileHeight_EmitsSetTileWithResultingState()
    {
        var plan = Build(new[] { new SetTileHeight(2, 3, 4).ToEditOp() });

        var action = Assert.Single(plan);
        Assert.Equal(LiveActionKind.SetTile, action.Kind);
        Assert.Equal((2, 3), (action.X, action.Z));
        Assert.Equal(new TileState(4, SlopeDirection.None), action.Tile);
    }

    [Fact]
    public void Build_HeightThenSlope_SlopeActionCarriesEarlierHeight()
    {
        var plan = Build(new[]
        {
            new SetTileHeight(2, 3, 4).ToEditOp(),
            new SetTileSlope(2, 3, SlopeDirection.East).ToEditOp(),
        });

        Assert.Equal(new TileState(4, SlopeDirection.East), plan[1].Tile);
    }

    [Fact]
    public void Build_AddTile_EmitsSetTile()
    {
        var plan = Build(new[] { new AddTile(1, 1, 2).ToEditOp() });

        Assert.Equal(LiveActionKind.SetTile, plan[0].Kind);
        Assert.Equal(new TileState(2, SlopeDirection.None), plan[0].Tile);
    }

    [Fact]
    public void Build_RemoveTile_EmitsRemoveTile()
    {
        var plan = Build(new[] { new RemoveTile(5, 6).ToEditOp() });

        Assert.Equal(LiveActionKind.RemoveTile, plan[0].Kind);
        Assert.Equal((5, 6), (plan[0].X, plan[0].Z));
    }

    [Fact]
    public void Build_PlaceObject_EmitsSpawnWithMonotonicPlacementIds()
    {
        var place = new PlaceObject("forest/shrines/0", SomeTransform.Position, SomeTransform.Rotation, SomeTransform.Scale);

        var plan = Build(new[] { place.ToEditOp(), place.ToEditOp() });

        Assert.Equal(LiveActionKind.SpawnObject, plan[0].Kind);
        Assert.Equal("forest/shrines/0", plan[0].CatalogId);
        Assert.Equal(ObjectTarget.FromPlacementId(0), plan[0].Target);
        Assert.Equal(ObjectTarget.FromPlacementId(1), plan[1].Target);
        Assert.Equal(SomeTransform, plan[0].Transform);
    }

    [Fact]
    public void Build_HiddenPlaceObject_EmitsAHiddenSpawn()
    {
        var hidden = new PlaceObject("interactable/rail/0", SomeTransform.Position, SomeTransform.Rotation, SomeTransform.Scale, Hidden: true);
        var visible = new PlaceObject("interactable/rail/0", SomeTransform.Position, SomeTransform.Rotation, SomeTransform.Scale);

        var plan = Build(new[] { hidden.ToEditOp(), visible.ToEditOp() });

        Assert.True(plan[0].Hidden);
        Assert.False(plan[1].Hidden);
    }

    [Fact]
    public void Build_MoveObjectWithHiddenChildren_CarriesTheChildNames()
    {
        var move = new MoveObject(ObjectTarget.FromGenId("chest:0003"), SomeTransform, new[] { "BottomPiece" });

        var plan = Build(new[] { move.ToEditOp() });

        Assert.Equal(new[] { "BottomPiece" }, plan[0].HiddenChildren);
    }

    [Fact]
    public void Build_MoveAndRemoveObject_CarryTargetAndTransform()
    {
        var target = ObjectTarget.FromGenId("chest:0003");

        var plan = Build(new[]
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
        Assert.Throws<ArgumentException>(() => Build(new[] { new EditOp("bogus", "", "{}") }));
    }

    [Fact]
    public void ChangesTerrain_NoActions_IsFalse()
    {
        Assert.False(LiveEditPlan.ChangesTerrain(Build()));
    }

    [Fact]
    public void ChangesTerrain_ObjectOnlyEdits_IsFalse()
    {
        var plan = Build(new[] { new PlaceObject("forest/shrines/0", SomeTransform.Position, SomeTransform.Rotation, SomeTransform.Scale).ToEditOp() });

        Assert.False(LiveEditPlan.ChangesTerrain(plan));
    }

    [Theory]
    [MemberData(nameof(TerrainEdits))]
    public void ChangesTerrain_TileEdit_IsTrue(EditOp op)
    {
        Assert.True(LiveEditPlan.ChangesTerrain(Build(new[] { op })));
    }

    public static IEnumerable<object[]> TerrainEdits()
    {
        yield return new object[] { new SetTileHeight(2, 3, 4).ToEditOp() };
        yield return new object[] { new SetTileSlope(2, 3, SlopeDirection.East).ToEditOp() };
        yield return new object[] { new AddTile(1, 1, 2).ToEditOp() };
        yield return new object[] { new RemoveTile(1, 1).ToEditOp() };
    }
}
