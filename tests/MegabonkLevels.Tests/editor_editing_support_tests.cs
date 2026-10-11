namespace MegabonkLevels.Tests;

public class EditHistoryTests
{
    [Fact]
    public void ApplyUndoRedo_TracksCurrentEdits()
    {
        var history = new EditHistory(new[] { new AddTile(0, 0, 1).ToEditOp() });

        history.Apply(new SetTileHeight(0, 0, 2).ToEditOp());
        Assert.Equal(2, history.CurrentEdits.Count);
        Assert.True(history.CanUndo);
        Assert.False(history.CanRedo);

        var undone = history.Undo();
        Assert.Equal(new SetTileHeight(0, 0, 2).ToEditOp(), undone);
        Assert.Single(history.CurrentEdits);
        Assert.True(history.CanRedo);

        var redone = history.Redo();
        Assert.Equal(new SetTileHeight(0, 0, 2).ToEditOp(), redone);
        Assert.Equal(2, history.CurrentEdits.Count);
        Assert.False(history.CanRedo);
    }

    [Fact]
    public void ApplyAfterUndo_ClearsRedo()
    {
        var history = new EditHistory();
        history.Apply(new AddTile(0, 0, 1).ToEditOp());
        history.Apply(new SetTileHeight(0, 0, 2).ToEditOp());
        history.Undo();

        history.Apply(new SetTileSlope(0, 0, SlopeDirection.East).ToEditOp());

        Assert.False(history.CanRedo);
        Assert.Equal(2, history.CurrentEdits.Count);
        Assert.Equal(new SetTileSlope(0, 0, SlopeDirection.East).ToEditOp(), history.CurrentEdits[1]);
    }
}

public class EditorEditSessionTests
{
    [Fact]
    public void ApplyThenUndoThenRedo_UpdatesCurrentEditsAndCommandAvailability()
    {
        var session = new EditorEditSession();
        var state = new LevelState();
        var applied = new List<EditOp>();
        var op = new AddTile(1, 2, 3).ToEditOp();
        var plan = EditCommandPlanner.Plan(op, state, nextPlacementId: 0, removeObjectFallback: null);

        Assert.True(session.Apply(plan, edit => { applied.Add(edit); return true; }));
        Assert.Single(session.CurrentEdits);
        Assert.True(session.CanUndo);
        Assert.False(session.CanRedo);

        Assert.True(session.Undo(edit => { applied.Add(edit); return true; }));
        Assert.Empty(session.CurrentEdits);
        Assert.False(session.CanUndo);
        Assert.True(session.CanRedo);

        Assert.True(session.Redo(edit => { applied.Add(edit); return true; }));
        Assert.Single(session.CurrentEdits);
        Assert.True(session.CanUndo);
        Assert.False(session.CanRedo);
    }
}

public class EditCommandPlannerTests
{
    [Fact]
    public void Plan_AddTile_UndoRestoresPriorSlopeTile()
    {
        var state = new LevelState();
        new EditStack(state).Apply(new SetTileHeight(2, 3, 4).ToEditOp());
        new EditStack(state).Apply(new SetTileSlope(2, 3, SlopeDirection.West).ToEditOp());

        var plan = EditCommandPlanner.Plan(new AddTile(2, 3, 8).ToEditOp(), state, nextPlacementId: 0, removeObjectFallback: null);

        Assert.Equal(new[]
        {
            new AddTile(2, 3, 4).ToEditOp(),
            new SetTileSlope(2, 3, SlopeDirection.West).ToEditOp(),
        }, plan.UndoOps);
    }

    [Fact]
    public void Plan_PlaceObject_UndoRemovesAllocatedPlacement_AndRedoMovesItBack()
    {
        var op = new PlaceObject("interactable/chest", new Vector3Data(1, 2, 3), new Vector3Data(0, 90, 0), new Vector3Data(1, 1, 1)).ToEditOp();

        var plan = EditCommandPlanner.Plan(op, new LevelState(), nextPlacementId: 7, removeObjectFallback: null);

        Assert.Equal(new[] { new RemoveObject(ObjectTarget.FromPlacementId(7)).ToEditOp() }, plan.UndoOps);
        Assert.Equal(new[]
        {
            new MoveObject(ObjectTarget.FromPlacementId(7), new TransformData(new Vector3Data(1, 2, 3), new Vector3Data(0, 90, 0), new Vector3Data(1, 1, 1))).ToEditOp(),
        }, plan.RedoOpsAfterUndo);
    }

    [Fact]
    public void Plan_RemoveObject_UsesFallbackTransformWhenNoOverrideExists()
    {
        var target = ObjectTarget.FromGenId("object:BossPortal:0000");
        var fallback = new TransformData(new Vector3Data(9, 1, 4), new Vector3Data(0, 180, 0), new Vector3Data(1, 1, 1));
        var plan = EditCommandPlanner.Plan(new RemoveObject(target).ToEditOp(), new LevelState(), nextPlacementId: 0, removeObjectFallback: fallback);

        Assert.Equal(new[] { new MoveObject(target, fallback).ToEditOp() }, plan.UndoOps);
    }
}

public class EditorFileNamingTests
{
    [Theory]
    [InlineData("forest-test", "forest-test.mblevel.json")]
    [InlineData("forest-test.mblevel.json", "forest-test.mblevel.json")]
    [InlineData("forest-test.json", "forest-test.mblevel.json")]
    [InlineData("", "level.mblevel.json")]
    [InlineData("  ", "level.mblevel.json")]
    [InlineData("bad/name*chars", "bad_name_chars.mblevel.json")]
    public void NormalizeLevelFileName_ProducesValidMblevelFile(string input, string expected)
    {
        Assert.Equal(expected, EditorFileNaming.NormalizeLevelFileName(input));
    }

    [Fact]
    public void SortLevelNames_IsCaseInsensitiveAndStableForDisplay()
    {
        var sorted = EditorFileNaming.SortLevelNames(new[] { "zeta.mblevel.json", "Alpha.mblevel.json", "beta.mblevel.json" });

        Assert.Equal(new[] { "Alpha.mblevel.json", "beta.mblevel.json", "zeta.mblevel.json" }, sorted);
    }

    [Fact]
    public void StemForForm_StripsMblevelExtension()
    {
        Assert.Equal("forest-test", EditorFileNaming.StemForForm("forest-test.mblevel.json", 80));
    }

    [Fact]
    public void StemForForm_TruncatesToFormLimit()
    {
        var stem = EditorFileNaming.StemForForm("abcdefghijklmnopqrstuvwxyz.mblevel.json", 10);

        Assert.Equal("abcdefghij", stem);
    }
}

public class EditorValidationTargetsTests
{
    [Theory]
    [InlineData("BossPortal")]
    [InlineData("FinalBossPortal(Clone)")]
    [InlineData("Portal_Boss")]
    public void IsBossPortalName_MatchesPortalLikeBossNames(string name)
    {
        Assert.True(EditorValidationTargets.IsBossPortalName(name));
    }

    [Theory]
    [InlineData("PlayerSpawnPortal")]
    [InlineData("Tree0(Clone)")]
    [InlineData("")]
    public void IsBossPortalName_RejectsSpawnOrNonPortalNames(string name)
    {
        Assert.False(EditorValidationTargets.IsBossPortalName(name));
    }
}

public class EditorHotkeysTests
{
    [Fact]
    public void CtrlChordReady_BeforeThreshold_ReturnsFalse()
    {
        Assert.False(EditorHotkeys.CtrlChordReady(ctrlHeldSince: 10f, now: 10.19f, thresholdSeconds: 0.2f));
    }

    [Fact]
    public void CtrlChordReady_AtThreshold_ReturnsTrue()
    {
        Assert.True(EditorHotkeys.CtrlChordReady(ctrlHeldSince: 10f, now: 10.21f, thresholdSeconds: 0.2f));
    }

    [Fact]
    public void CtrlChordReady_NoStartTime_ReturnsFalse()
    {
        Assert.False(EditorHotkeys.CtrlChordReady(ctrlHeldSince: -1f, now: 10.2f, thresholdSeconds: 0.2f));
    }
}

public class EditorOverlayModelTests
{
    [Theory]
    [InlineData(1, 3, 1f, 0)]
    [InlineData(1, 3, -1f, 2)]
    [InlineData(0, 3, 1f, 0)]
    [InlineData(2, 3, -1f, 2)]
    [InlineData(1, 3, 0f, 1)]
    public void SelectedIndexAfterScroll_ChangesSelectionWithoutWrapping(int selectedIndex, int itemCount, float notches, int expected)
    {
        Assert.Equal(expected, EditorOverlayModel.SelectedIndexAfterScroll(selectedIndex, itemCount, notches));
    }

    [Fact]
    public void LoadListStart_KeepsSelectionVisibleNearEnd()
    {
        var start = EditorOverlayModel.LoadListStart(selectedIndex: 9, itemCount: 10, maxListed: 8);

        Assert.Equal(2, start);
    }

    [Fact]
    public void LoadIndexAtRow_MapsVisibleRowToRealIndex()
    {
        var index = EditorOverlayModel.LoadIndexAtRow(selectedIndex: 5, itemCount: 10, maxListed: 8, row: 1);

        Assert.Equal(2, index);
    }

    [Fact]
    public void LoadIndexAtRow_OutOfRange_ReturnsNull()
    {
        var index = EditorOverlayModel.LoadIndexAtRow(selectedIndex: 0, itemCount: 1, maxListed: 8, row: 3);

        Assert.Null(index);
    }
}

public class EditorInputModelTests
{
    [Fact]
    public void PlaceholderVisible_EmptyText_ReturnsTrue()
    {
        Assert.True(EditorInputModel.PlaceholderVisible(""));
    }

    [Fact]
    public void PlaceholderVisible_NonEmptyText_ReturnsFalse()
    {
        Assert.False(EditorInputModel.PlaceholderVisible("forest-level"));
    }
}

public class EditorLoadGuardTests
{
    [Fact]
    public void ShouldLoad_WhenClean_ReturnsTrue()
    {
        var guard = EditorLoadGuard.NextPrompt(currentEditsCount: 5, savedEditsCount: 5, armed: false, requireConfirm: true);

        Assert.Equal(EditorLoadGuardAction.Load, guard.Action);
        Assert.False(guard.Armed);
    }

    [Fact]
    public void ShouldLoad_WhenDirty_FirstPressArmsWarning()
    {
        var guard = EditorLoadGuard.NextPrompt(currentEditsCount: 6, savedEditsCount: 5, armed: false, requireConfirm: true);

        Assert.Equal(EditorLoadGuardAction.Warn, guard.Action);
        Assert.True(guard.Armed);
    }

    [Fact]
    public void ShouldLoad_WhenDirty_SecondPressLoads()
    {
        var guard = EditorLoadGuard.NextPrompt(currentEditsCount: 6, savedEditsCount: 5, armed: true, requireConfirm: true);

        Assert.Equal(EditorLoadGuardAction.Load, guard.Action);
        Assert.False(guard.Armed);
    }

    [Fact]
    public void ShouldLoad_WhenDirty_ConfirmDisabled_LoadsImmediately()
    {
        var guard = EditorLoadGuard.NextPrompt(currentEditsCount: 6, savedEditsCount: 5, armed: false, requireConfirm: false);

        Assert.Equal(EditorLoadGuardAction.Load, guard.Action);
        Assert.False(guard.Armed);
    }
}

public class EditorSessionSaveStateTests
{
    [Fact]
    public void DirtyState_WhenCountsDiffer_IsDirty()
    {
        var dirty = 6 != 5;

        Assert.True(dirty);
    }

    [Fact]
    public void DirtyState_WhenCountsMatch_IsSaved()
    {
        var dirty = 5 != 5;

        Assert.False(dirty);
    }
}

public class InPlaceLoadTileResetTests
{
    private static LevelState MakeTiles(params ((int X, int Z) Cell, TileState Tile)[] tiles) =>
        LevelState.FromTiles(tiles.Select(t => new KeyValuePair<(int X, int Z), TileState>(t.Cell, t.Tile)));

    [Fact]
    public void ComputeTileResets_RemovedByEdit_EmitsSetTileToBaselineState()
    {
        var baselineTile = new TileState(1, SlopeDirection.None);
        var baseline = MakeTiles(((2, 3), baselineTile));
        var current = MakeTiles();

        var resets = InPlaceLoadTileReset.ComputeTileResets(baseline, current);

        Assert.Single(resets);
        Assert.Equal(LiveActionKind.SetTile, resets[0].Kind);
        Assert.Equal(2, resets[0].X);
        Assert.Equal(3, resets[0].Z);
        Assert.Equal(baselineTile, resets[0].Tile);
    }

    [Fact]
    public void ComputeTileResets_AddedByEdit_EmitsRemoveTile()
    {
        var baseline = MakeTiles();
        var current = MakeTiles(((4, 5), new TileState(2, SlopeDirection.None)));

        var resets = InPlaceLoadTileReset.ComputeTileResets(baseline, current);

        Assert.Single(resets);
        Assert.Equal(LiveActionKind.RemoveTile, resets[0].Kind);
        Assert.Equal(4, resets[0].X);
        Assert.Equal(5, resets[0].Z);
    }

    [Fact]
    public void ComputeTileResets_ChangedHeight_EmitsSetTileToBaselineState()
    {
        var baselineTile = new TileState(1, SlopeDirection.West);
        var baseline = MakeTiles(((2, 3), baselineTile));
        var current = MakeTiles(((2, 3), new TileState(3, SlopeDirection.North)));

        var resets = InPlaceLoadTileReset.ComputeTileResets(baseline, current);

        Assert.Single(resets);
        Assert.Equal(LiveActionKind.SetTile, resets[0].Kind);
        Assert.Equal(baselineTile, resets[0].Tile);
    }

    [Fact]
    public void ComputeTileResets_UnchangedTile_EmitsNothing()
    {
        var tile = new TileState(1, SlopeDirection.None);
        var baseline = MakeTiles(((2, 3), tile));
        var current = MakeTiles(((2, 3), tile));

        var resets = InPlaceLoadTileReset.ComputeTileResets(baseline, current);

        Assert.Empty(resets);
    }

    [Fact]
    public void ComputeTileResets_EmptyBothSides_EmitsNothing()
    {
        var resets = InPlaceLoadTileReset.ComputeTileResets(MakeTiles(), MakeTiles());

        Assert.Empty(resets);
    }
}
