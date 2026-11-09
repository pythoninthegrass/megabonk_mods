namespace MegabonkLevels.Tests;

public class ThpsEditableLevelTests
{
    private static LevelFile Read()
    {
        var level = LevelFileSerializer.DeserializeWithMigration("""
            {"schemaVersion":4,"gameBuildId":"test","baseline":"none","map":1,
             "stageIndex":0,"tier":0,"packs":{"thps":"2.0.21"},"packKitVersions":{"thps":"2"},
             "grid":{"width":15,"depth":15,"cells":[{"x":10,"z":7,"height":-2}]},
             "spawn":{"position":[0,2,0],"rotation":[0,0,0]},
             "bossSpawner":{"position":[80,0,0],"rotation":[0,0,0]},"edits":[]}
            """);
        var one = new Vector3Data(1, 1, 1);
        var children = new[]
        {
            new ObjectAttachmentSpec("rail", "interactable/rail/0", new(new(1, 0, 0), default, one), true),
            new ObjectAttachmentSpec("post", "bundle:thps/added-post-0", new(new(0, 1, 0), default, one))
        };
        return level with
        {
            Edits = new[]
            {
                new PlaceObject("bundle:thps/piece-rail-big-straight", default, default, one,
                    Attachments: children, PlacementId: 0).ToEditOp(),
                new PlaceObject("bundle:thps/added-post-0", new(5, 0, 0), default, one,
                    PlacementId: 3).ToEditOp()
            }
        };
    }

    [Fact]
    public void WholeAssemblyReplaysAndReservesAllChildIds()
    {
        var level = Read();
        var stack = new EditStack(new LevelState());
        foreach (var op in level.Edits) stack.Apply(op);
        var placed = stack.State.Objects.Where(pair => pair.Key.Kind == ObjectTargetKind.PlacementId).ToArray();
        var roots = level.Edits.Count(op => op.OpType == PlaceObject.OpType);
        Assert.Equal(2, roots);
        Assert.Equal(roots + 2, placed.Length);
        Assert.Equal(2, placed.Count(pair => pair.Value.Owner != null));
        Assert.Equal(1, placed.Count(pair => pair.Value.CatalogId == "interactable/rail/0"));
        Assert.DoesNotContain(placed, pair => pair.Value.CatalogId == "bundle:thps/Warehouse");
        Assert.Empty(stack.State.Tiles);
        Assert.True(level.IsFromScratch);
        var floor = Assert.Single(level.Grid!.Value.Cells);
        Assert.Equal(new AuthoredCell(10, 7, -2), floor);
        Assert.Equal("2", level.PackKitVersions["thps"]);
        Assert.Equal(level, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(level)));
        var actions = LiveEditPlan.Build(level.Edits, new LevelState());
        Assert.Equal(roots, actions.Count(action => action.Kind == LiveActionKind.SpawnObject));
    }

    [Fact]
    public void PieceMoveDeleteUndoAndIndependentChildEditSurviveSaveReplay()
    {
        var level = Read();
        var root = level.Edits.Where(op => op.OpType == PlaceObject.OpType).Select(PlaceObject.FromEditOp).First(place => place.Attachments.Count > 1);
        var owner = ObjectTarget.FromPlacementId(root.PlacementId!.Value);
        var child = ObjectTarget.FromPlacementId(root.PlacementId.Value + 1);
        var stack = new EditStack(new LevelState());
        foreach (var op in level.Edits) stack.Apply(op);
        var moved = new TransformData(new(50, 10, 20), new(0, 90, 0), new(79.2f, 79.2f, 79.2f));
        var move = new MoveObject(owner, moved).ToEditOp();
        stack.Apply(move);
        Assert.Equal(AttachmentTransform.ToWorld(moved, root.Attachments[0].LocalTransform), stack.State.GetObject(child)!.Value.Transform);
        stack.Apply(new RemoveObject(owner).ToEditOp());
        Assert.False(stack.State.IsObjectActive(child));
        stack.Undo();
        Assert.True(stack.State.IsObjectActive(child));
        var childMove = new MoveObject(child, moved).ToEditOp();
        var saved = level with { Edits = level.Edits.Concat(new[] { move, childMove }).ToArray() };
        var replay = new EditStack(new LevelState());
        foreach (var op in LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(saved)).Edits) replay.Apply(op);
        Assert.Equal(moved, replay.State.GetObject(child)!.Value.Transform);
        Assert.Equal(moved, replay.State.GetObject(owner)!.Value.Transform);
    }
}
