namespace MegabonkLevels.Tests;

public class ThpsEditableLevelTests
{
    private static LevelFile Read()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null && !File.Exists(Path.Combine(dir.FullName, "Taskfile.yml"))) dir = dir.Parent;
        return LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(Path.Combine(dir!.FullName, "levels/thps-editable.mblevel.json")));
    }

    [Fact]
    public void WholeAssemblyReplaysAndReservesAllChildIds()
    {
        var level = Read();
        var stack = new EditStack(new LevelState());
        foreach (var op in level.Edits) stack.Apply(op);
        var placed = stack.State.Objects.Where(pair => pair.Key.Kind == ObjectTargetKind.PlacementId).ToArray();
        var roots = level.Edits.Count(op => op.OpType == PlaceObject.OpType);
        Assert.Equal(roots + 58, placed.Length);
        Assert.True(roots < 615);
        Assert.Equal(58, placed.Count(pair => pair.Value.Owner != null));
        Assert.Equal(41, placed.Count(pair => pair.Value.CatalogId == "interactable/rail/0"));
        Assert.DoesNotContain(placed, pair => pair.Value.CatalogId == "bundle:thps/Warehouse");
        Assert.Single(stack.State.Tiles);
        Assert.Equal(new TileState(-1, SlopeDirection.None), stack.State.GetTile(10, 7));
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
