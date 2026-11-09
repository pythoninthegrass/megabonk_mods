namespace MegabonkLevels.Tests;

public class EditStackTileTests
{
    [Fact]
    public void Apply_AddTile_CreatesTileWithNoSlope()
    {
        var stack = new EditStack(new LevelState());

        stack.Apply(new AddTile(1, 2, 3).ToEditOp());

        Assert.Equal(new TileState(3, SlopeDirection.None), stack.State.GetTile(1, 2));
    }

    [Fact]
    public void Undo_AfterAddTile_RemovesTile()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(new AddTile(1, 2, 3).ToEditOp());

        var undone = stack.Undo();

        Assert.True(undone);
        Assert.Null(stack.State.GetTile(1, 2));
    }

    [Fact]
    public void Redo_AfterUndoAddTile_RestoresTile()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(new AddTile(1, 2, 3).ToEditOp());
        stack.Undo();

        var redone = stack.Redo();

        Assert.True(redone);
        Assert.Equal(new TileState(3, SlopeDirection.None), stack.State.GetTile(1, 2));
    }

    [Fact]
    public void Undo_SetTileHeight_RestoresPriorHeightAndKeepsSlope()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(new AddTile(0, 0, 1).ToEditOp());
        stack.Apply(new SetTileSlope(0, 0, SlopeDirection.North).ToEditOp());
        stack.Apply(new SetTileHeight(0, 0, 9).ToEditOp());

        stack.Undo();

        Assert.Equal(new TileState(1, SlopeDirection.North), stack.State.GetTile(0, 0));
    }

    [Fact]
    public void Undo_SetTileSlope_RestoresPriorSlopeAndKeepsHeight()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(new AddTile(0, 0, 5).ToEditOp());
        stack.Apply(new SetTileSlope(0, 0, SlopeDirection.East).ToEditOp());

        stack.Undo();

        Assert.Equal(new TileState(5, SlopeDirection.None), stack.State.GetTile(0, 0));
    }

    [Fact]
    public void SetTileHeight_WithoutPriorTile_CreatesTileWithNoneSlope()
    {
        var stack = new EditStack(new LevelState());

        stack.Apply(new SetTileHeight(2, 2, 4).ToEditOp());

        Assert.Equal(new TileState(4, SlopeDirection.None), stack.State.GetTile(2, 2));
    }

    [Fact]
    public void Undo_SetTileHeight_WithoutPriorTile_RemovesTile()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(new SetTileHeight(2, 2, 4).ToEditOp());

        stack.Undo();

        Assert.Null(stack.State.GetTile(2, 2));
    }

    [Fact]
    public void Undo_RemoveTile_RestoresPriorHeightAndSlope()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(new AddTile(0, 0, 7).ToEditOp());
        stack.Apply(new SetTileSlope(0, 0, SlopeDirection.South).ToEditOp());
        stack.Apply(new RemoveTile(0, 0).ToEditOp());

        stack.Undo();

        Assert.Equal(new TileState(7, SlopeDirection.South), stack.State.GetTile(0, 0));
    }

    [Fact]
    public void RemoveTile_OnAbsentTile_IsNoOpAndUndoIsNoOp()
    {
        var stack = new EditStack(new LevelState());

        stack.Apply(new RemoveTile(3, 3).ToEditOp());
        Assert.Null(stack.State.GetTile(3, 3));

        stack.Undo();
        Assert.Null(stack.State.GetTile(3, 3));
    }
}

public class EditStackObjectTests
{
    private static PlaceObject SamplePlacement() => new(
        CatalogId: "props/rock_small",
        Position: new Vector3Data(1, 0, 3),
        Rotation: new Vector3Data(0, 90, 0),
        Scale: new Vector3Data(1, 1, 1));

    [Fact]
    public void Apply_PlaceObject_CreatesRecordUnderAllocatedPlacementTarget()
    {
        var stack = new EditStack(new LevelState());

        stack.Apply(SamplePlacement().ToEditOp());

        var target = ObjectTarget.FromPlacementId(0);
        var record = stack.State.GetObject(target);
        Assert.NotNull(record);
        Assert.False(record!.Value.Removed);
        Assert.Equal("props/rock_small", record.Value.CatalogId);
    }

    [Fact]
    public void Undo_PlaceObject_RemovesRecordEntirely()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(SamplePlacement().ToEditOp());

        stack.Undo();

        Assert.Null(stack.State.GetObject(ObjectTarget.FromPlacementId(0)));
    }

    [Fact]
    public void Redo_PlaceObject_ReusesSamePlacementId()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(SamplePlacement().ToEditOp());
        stack.Undo();

        stack.Redo();

        Assert.NotNull(stack.State.GetObject(ObjectTarget.FromPlacementId(0)));
    }

    [Fact]
    public void Undo_MoveObject_OnGenIdWithNoPriorOverride_RemovesOverride()
    {
        var stack = new EditStack(new LevelState());
        var target = ObjectTarget.FromGenId("randomObject:Tree:5");
        var transform = new TransformData(new Vector3Data(2, 0, 2), default, new Vector3Data(1, 1, 1));

        stack.Apply(new MoveObject(target, transform).ToEditOp());
        Assert.Equal(transform, stack.State.GetObject(target)!.Value.Transform);

        stack.Undo();

        Assert.Null(stack.State.GetObject(target));
    }

    [Fact]
    public void Undo_MoveObject_OnPlacedObject_RestoresPriorTransformAndCatalogId()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(SamplePlacement().ToEditOp());
        var target = ObjectTarget.FromPlacementId(0);
        var originalTransform = stack.State.GetObject(target)!.Value.Transform;

        var moved = new TransformData(new Vector3Data(9, 9, 9), default, new Vector3Data(1, 1, 1));
        stack.Apply(new MoveObject(target, moved).ToEditOp());
        stack.Undo();

        var restored = stack.State.GetObject(target);
        Assert.Equal(originalTransform, restored!.Value.Transform);
        Assert.Equal("props/rock_small", restored.Value.CatalogId);
    }

    [Fact]
    public void Undo_RemoveObject_OnGenIdWithNoPriorOverride_RemovesOverride()
    {
        var stack = new EditStack(new LevelState());
        var target = ObjectTarget.FromGenId("randomObject:Tree:5");

        stack.Apply(new RemoveObject(target).ToEditOp());
        Assert.True(stack.State.GetObject(target)!.Value.Removed);

        stack.Undo();

        Assert.Null(stack.State.GetObject(target));
    }

    [Fact]
    public void Undo_RemoveObject_OnPlacedObject_RestoresNotRemoved()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(SamplePlacement().ToEditOp());
        var target = ObjectTarget.FromPlacementId(0);

        stack.Apply(new RemoveObject(target).ToEditOp());
        stack.Undo();

        Assert.False(stack.State.GetObject(target)!.Value.Removed);
    }
}

public class EditStackSequenceTests
{
    [Fact]
    public void Undo_WithEmptyStack_IsNoOp()
    {
        var stack = new EditStack(new LevelState());

        var undone = stack.Undo();

        Assert.False(undone);
        Assert.False(stack.CanUndo);
    }

    [Fact]
    public void Redo_WithEmptyStack_IsNoOp()
    {
        var stack = new EditStack(new LevelState());

        var redone = stack.Redo();

        Assert.False(redone);
    }

    [Fact]
    public void Apply_AfterUndo_ClearsRedoStack()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(new AddTile(0, 0, 1).ToEditOp());
        stack.Undo();
        Assert.True(stack.CanRedo);

        stack.Apply(new AddTile(1, 1, 2).ToEditOp());

        Assert.False(stack.CanRedo);
        Assert.False(stack.Redo());
    }

    [Fact]
    public void MultiStep_ApplyUndoRedoSequence_ProducesExpectedFinalState()
    {
        var stack = new EditStack(new LevelState());

        stack.Apply(new AddTile(0, 0, 1).ToEditOp());
        stack.Apply(new SetTileHeight(0, 0, 5).ToEditOp());
        stack.Apply(new SetTileSlope(0, 0, SlopeDirection.West).ToEditOp());

        stack.Undo();
        stack.Undo();
        Assert.Equal(new TileState(1, SlopeDirection.None), stack.State.GetTile(0, 0));

        stack.Redo();
        Assert.Equal(new TileState(5, SlopeDirection.None), stack.State.GetTile(0, 0));

        stack.Redo();
        Assert.Equal(new TileState(5, SlopeDirection.West), stack.State.GetTile(0, 0));

        Assert.False(stack.Redo());
    }
}
