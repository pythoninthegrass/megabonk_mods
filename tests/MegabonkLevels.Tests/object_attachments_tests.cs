namespace MegabonkLevels.Tests;

public class ObjectAttachmentsTests
{
    private static readonly Vector3Data One = new(1, 1, 1);
    private static readonly TransformData Root = new(new(10, 2, 20), new(0, 90, 0), new(2, 2, 2));
    private static readonly ObjectAttachmentSpec Post = new("post", "bundle:thps/added-post-0", new(new(1, 0, 0), default, One));

    private static EditOp Assembly(TransformData? transform = null)
    {
        var t = transform ?? Root;
        return new PlaceObject("bundle:thps/piece-rail-big-straight", t.Position, t.Rotation, t.Scale, Attachments: new[] { Post }).ToEditOp();
    }

    [Fact]
    public void Serialization_RoundTripsAttachments_AndKeepsLegacyPayloadUnchanged()
    {
        var op = Assembly();
        var restored = PlaceObject.FromEditOp(op);
        Assert.Equal(Post, Assert.Single(restored.Attachments));
        Assert.Equal(op, restored.ToEditOp());
        Assert.DoesNotContain("attachments", new PlaceObject("interactable/rail/0", default, default, One).ToEditOp().Payload);
    }

    [Fact]
    public void Attachments_ValidateCatalogScaleAndUniqueNames()
    {
        Assert.Throws<ArgumentException>(() => new ObjectAttachmentSpec("", Post.CatalogId, Post.LocalTransform));
        Assert.Throws<ArgumentException>(() => new ObjectAttachmentSpec("post", "bogus", Post.LocalTransform));
        Assert.Throws<ArgumentException>(() => new ObjectAttachmentSpec("post", Post.CatalogId, Post.LocalTransform with { Scale = default }));
        Assert.Throws<ArgumentException>(() => new PlaceObject(Post.CatalogId, default, default, One, Attachments: new[] { Post, Post }));
    }

    [Fact]
    public void Placement_AllocatesIndependentTargetsAndOwnerLinks()
    {
        var planner = new LiveEditPlanner(new LevelState());
        var action = planner.Apply(Assembly());
        Assert.Single(action.Attachments);
        Assert.Equal(2, planner.NextPlacementId);
        var child = planner.State.GetObject(ObjectTarget.FromPlacementId(1))!.Value;
        Assert.Equal(ObjectTarget.FromPlacementId(0), child.Owner);
        Assert.Equal(Post.LocalTransform, child.LocalTransform);
        Near(new(10, 2, 18), child.Transform!.Value.Position);
        Assert.Equal(One, child.Transform.Value.Scale);
    }

    [Fact]
    public void OwnerMove_UpdatesChildWorldPosition_ButKeepsItsLocalScale()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(Assembly());
        stack.Apply(new MoveObject(ObjectTarget.FromPlacementId(0), Root with { Position = new(30, 3, 40), Scale = new(3, 4, 5) }).ToEditOp());
        var child = stack.State.GetObject(ObjectTarget.FromPlacementId(1))!.Value;
        Near(new(30, 3, 37), child.Transform!.Value.Position);
        Assert.Equal(Post.LocalTransform, child.LocalTransform);
        stack.Undo();
        Near(new(10, 2, 18), stack.State.GetObject(ObjectTarget.FromPlacementId(1))!.Value.Transform!.Value.Position);
        stack.Redo();
        Near(new(30, 3, 37), stack.State.GetObject(ObjectTarget.FromPlacementId(1))!.Value.Transform!.Value.Position);
    }

    [Fact]
    public void IndependentMove_ChangesLocalOffset_AndSurvivesOwnerMoveAndUndo()
    {
        var planner = new LiveEditPlanner(new LevelState());
        planner.Apply(Assembly());
        var child = ObjectTarget.FromPlacementId(1);
        var move = planner.Apply(new MoveObject(child, new(new(10, 2, 16), new(0, 90, 0), One)).ToEditOp());
        Assert.Equal(ObjectTarget.FromPlacementId(0), move.Owner);
        Near(new(2, 0, 0), move.Transform!.Value.Position);
        planner.Apply(new MoveObject(ObjectTarget.FromPlacementId(0), Root with { Position = new(20, 2, 20) }).ToEditOp());
        Near(new(20, 2, 16), planner.State.GetObject(child)!.Value.Transform!.Value.Position);
    }

    [Fact]
    public void RemovalAndRestore_HideAssemblyWithoutRevivingIndependentlyDeletedChild()
    {
        var planner = new LiveEditPlanner(new LevelState());
        planner.Apply(Assembly());
        var owner = ObjectTarget.FromPlacementId(0);
        var child = ObjectTarget.FromPlacementId(1);
        planner.Apply(new RemoveObject(owner).ToEditOp());
        Assert.False(planner.State.IsObjectActive(child));
        planner.Apply(new MoveObject(owner, Root).ToEditOp());
        Assert.True(planner.State.IsObjectActive(child));
        planner.Apply(new RemoveObject(child).ToEditOp());
        planner.Apply(new RemoveObject(owner).ToEditOp());
        planner.Apply(new MoveObject(owner, Root).ToEditOp());
        Assert.False(planner.State.IsObjectActive(child));
    }

    [Fact]
    public void DuplicatedAssembly_HasIndependentChildren_AndUndoDoesNotReuseIds()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(Assembly());
        stack.Apply(Assembly(Root with { Position = new(50, 2, 20) }));
        Assert.Equal(ObjectTarget.FromPlacementId(2), stack.State.GetObject(ObjectTarget.FromPlacementId(3))!.Value.Owner);
        stack.Apply(new RemoveObject(ObjectTarget.FromPlacementId(0)).ToEditOp());
        Assert.True(stack.State.IsObjectActive(ObjectTarget.FromPlacementId(3)));
        stack.Undo();
        stack.Undo();
        Assert.Null(stack.State.GetObject(ObjectTarget.FromPlacementId(3)));
        stack.Redo();
        Assert.NotNull(stack.State.GetObject(ObjectTarget.FromPlacementId(3)));
        stack.Apply(Assembly());
        Assert.NotNull(stack.State.GetObject(ObjectTarget.FromPlacementId(5)));
    }

    [Fact]
    public void Replay_PreservesChildEditTargetsAndLocalTransforms()
    {
        var ops = new[] { Assembly(), new MoveObject(ObjectTarget.FromPlacementId(1), new(new(12, 2, 18), new(0, 90, 0), One)).ToEditOp(), Assembly() };
        var a = new LiveEditPlanner(new LevelState());
        var b = new LiveEditPlanner(new LevelState());
        foreach (var op in ops)
        {
            a.Apply(op);
            b.Apply(new EditOp(op.OpType, op.Target, op.Payload));
        }
        Assert.Equal(a.State.Objects, b.State.Objects);
        Assert.Equal(4, b.NextPlacementId);
    }

    private static void Near(Vector3Data expected, Vector3Data actual)
    {
        Assert.Equal(expected.X, actual.X, 3);
        Assert.Equal(expected.Y, actual.Y, 3);
        Assert.Equal(expected.Z, actual.Z, 3);
    }

    [Fact]
    public void ExplicitIds_PreserveTargetsWhenSavingAfterUndoAndBranching()
    {
        var replay = new LiveEditPlanner(new LevelState());
        var op = new PlaceObject(Post.CatalogId, Root.Position, Root.Rotation, Root.Scale,
            Attachments: new[] { Post }, PlacementId: 4).ToEditOp();
        replay.Apply(op);
        Assert.Equal(6, replay.NextPlacementId);
        Assert.NotNull(replay.State.GetObject(ObjectTarget.FromPlacementId(5)));
        Assert.Throws<ArgumentException>(() => replay.Apply(op));
        Assert.Equal(6, replay.NextPlacementId);
    }

    [Fact]
    public void HiddenCatchColliders_SelectTheirOwnerUnlessExplicitlyRequested()
    {
        var state = new LevelState();
        var stack = new EditStack(state);
        var rail = new ObjectAttachmentSpec(Post.Name, Post.CatalogId, Post.LocalTransform, true);
        stack.Apply(new PlaceObject(Post.CatalogId, default, default, One, Attachments: new[] { rail }).ToEditOp());
        var child = ObjectTarget.FromPlacementId(1);
        Assert.Equal(ObjectTarget.FromPlacementId(0), state.SelectionTarget(child, false));
        Assert.Equal(child, state.SelectionTarget(child, true));
    }

    [Fact]
    public void FailedIdReservation_DoesNotAllocatePartOfAnAssembly()
    {
        var planner = new LiveEditPlanner(new LevelState());
        var invalid = new PlaceObject(Post.CatalogId, default, default, One,
            Attachments: new[] { Post }, PlacementId: int.MaxValue - 1).ToEditOp();
        Assert.Throws<ArgumentException>(() => planner.Apply(invalid));
        Assert.Empty(planner.State.Objects);
        Assert.Equal(0, planner.NextPlacementId);
        planner.Apply(Assembly());
        Assert.NotNull(planner.State.GetObject(ObjectTarget.FromPlacementId(0)));
    }

    [Fact]
    public void IndependentMoveUndo_RestoresTheAttachmentOffsetAndOwnerLink()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(Assembly());
        var child = ObjectTarget.FromPlacementId(1);
        var before = stack.State.GetObject(child);
        stack.Apply(new MoveObject(child, new(new(10, 5, 16), new(12, 45, 20), new(2, 3, 4))).ToEditOp());
        stack.Undo();
        Assert.Equal(before, stack.State.GetObject(child));
        stack.Redo();
        Assert.Equal(ObjectTarget.FromPlacementId(0), stack.State.GetObject(child)!.Value.Owner);
        Near(new(10, 5, 16), stack.State.GetObject(child)!.Value.Transform!.Value.Position);
    }

    [Fact]
    public void LocalWorldRoundTrip_PreservesRotationAndNonuniformOwnerScale()
    {
        var owner = Root with { Rotation = new(33, 68, -29), Scale = new(2, 3, 4) };
        var local = new TransformData(new(1, 2, -3), new(20, -60, 13), new(.5f, .6f, .7f));
        var restored = AttachmentTransform.ToLocal(owner, AttachmentTransform.ToWorld(owner, local));
        Near(local.Position, restored.Position);
        Near(local.Rotation, restored.Rotation);
        Assert.Equal(local.Scale, restored.Scale);
    }

    [Fact]
    public void EditorUndoBranch_SaveAndReplayKeepChildIdsStable()
    {
        var live = new LiveEditPlanner(new LevelState());
        var editor = new EditorEditSession();
        bool Apply(EditOp op) { live.Apply(op); return true; }
        var first = new PlaceObject(Post.CatalogId, default, default, One, Attachments: new[] { Post }, PlacementId: 0).ToEditOp();
        editor.Apply(EditCommandPlanner.Plan(first, live.State, live.NextPlacementId, null), Apply);
        editor.Undo(Apply);
        var branched = new PlaceObject(Post.CatalogId, Root.Position, Root.Rotation, Root.Scale, Attachments: new[] { Post }, PlacementId: live.NextPlacementId).ToEditOp();
        editor.Apply(EditCommandPlanner.Plan(branched, live.State, live.NextPlacementId, null), Apply);
        var target = ObjectTarget.FromPlacementId(3);
        var move = new MoveObject(target, new(new(20, 3, 15), default, One)).ToEditOp();
        editor.Apply(EditCommandPlanner.Plan(move, live.State, live.NextPlacementId, null), Apply);
        var replay = new LiveEditPlanner(new LevelState());
        foreach (var op in editor.CurrentEdits) { replay.Apply(op); }
        Assert.Null(replay.State.GetObject(ObjectTarget.FromPlacementId(0)));
        Assert.Equal(live.State.GetObject(target), replay.State.GetObject(target));
        Assert.Equal(ObjectTarget.FromPlacementId(2), replay.State.GetObject(target)!.Value.Owner);
    }
}
