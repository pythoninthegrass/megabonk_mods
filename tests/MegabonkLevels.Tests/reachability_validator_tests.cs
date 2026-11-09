namespace MegabonkLevels.Tests;

public class ReachabilityValidatorTests
{
    private static LevelState FlatGrid(int width, int depth)
    {
        var stack = new EditStack(new LevelState());
        for (var x = 0; x < width; x++)
        {
            for (var z = 0; z < depth; z++)
            {
                stack.Apply(new AddTile(x, z, 0).ToEditOp());
            }
        }

        return stack.State;
    }

    [Fact]
    public void Validate_FlatGrid_EverythingReachable()
    {
        var state = FlatGrid(3, 3);

        var result = ReachabilityValidator.Validate(state, (1, 1));

        Assert.Equal(9, result.Reachable.Count);
        Assert.Empty(result.Unreachable);
        Assert.True(result.IsReachable((0, 0)));
        Assert.True(result.IsReachable((2, 2)));
    }

    // A slope tile at height h spans h at its downhill edge to h + 1 at its uphill edge (SlopeDirection).
    [Fact]
    public void Validate_SlopeAssistedSingleStepClimb_BothTilesReachableFromEachOther()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(new AddTile(0, 0, 0).ToEditOp());
        stack.Apply(new AddTile(0, 1, 0).ToEditOp());
        stack.Apply(new SetTileSlope(0, 1, SlopeDirection.North).ToEditOp());
        stack.Apply(new AddTile(0, 2, 1).ToEditOp());
        var state = stack.State;

        var fromLow = ReachabilityValidator.Validate(state, (0, 0));
        var fromHigh = ReachabilityValidator.Validate(state, (0, 2));

        Assert.True(fromLow.IsReachable((0, 2)));
        Assert.True(fromHigh.IsReachable((0, 0)));
        Assert.Empty(fromLow.Unreachable);
        Assert.Empty(fromHigh.Unreachable);
    }

    [Fact]
    public void Validate_SlopeEntered_FromSide_IsNotConnected()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(new AddTile(0, 0, 0).ToEditOp());
        stack.Apply(new AddTile(0, 1, 0).ToEditOp());
        stack.Apply(new SetTileSlope(0, 1, SlopeDirection.East).ToEditOp());
        var state = stack.State;

        Assert.False(ReachabilityValidator.Validate(state, (0, 0)).IsReachable((0, 1)));
    }

    [Fact]
    public void Validate_FlatTileAtUphillEdgeHeightOnly_ConnectsUphillSide()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(new AddTile(0, 0, 0).ToEditOp());
        stack.Apply(new AddTile(0, 1, 0).ToEditOp());
        stack.Apply(new SetTileSlope(0, 1, SlopeDirection.North).ToEditOp());
        stack.Apply(new AddTile(0, 2, 0).ToEditOp());
        var state = stack.State;

        var result = ReachabilityValidator.Validate(state, (0, 0));

        Assert.True(result.IsReachable((0, 1)));
        Assert.False(result.IsReachable((0, 2)));
    }

    [Fact]
    public void Validate_FlatTileAboveDownhillEdge_IsNotConnected()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(new AddTile(0, 0, 1).ToEditOp());
        stack.Apply(new AddTile(0, 1, 0).ToEditOp());
        stack.Apply(new SetTileSlope(0, 1, SlopeDirection.North).ToEditOp());
        var state = stack.State;

        Assert.False(ReachabilityValidator.Validate(state, (0, 0)).IsReachable((0, 1)));
    }

    [Fact]
    public void Validate_OpposedSlopesMeetingAtTheirUphillEdges_Connect()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(new AddTile(0, 0, 0).ToEditOp());
        stack.Apply(new SetTileSlope(0, 0, SlopeDirection.North).ToEditOp());
        stack.Apply(new AddTile(0, 1, 0).ToEditOp());
        stack.Apply(new SetTileSlope(0, 1, SlopeDirection.South).ToEditOp());
        var state = stack.State;

        Assert.True(ReachabilityValidator.Validate(state, (0, 0)).IsReachable((0, 1)));
    }

    [Fact]
    public void Validate_CliffWithoutSlope_RegionsAreMutuallyUnreachable()
    {
        var stack = new EditStack(new LevelState());
        // Low region: (0,0)-(0,1) at height 0.
        stack.Apply(new AddTile(0, 0, 0).ToEditOp());
        stack.Apply(new AddTile(0, 1, 0).ToEditOp());
        // High region: (0,2)-(0,3) at height 2 — a 2-step cliff from the low region, no slope.
        stack.Apply(new AddTile(0, 2, 2).ToEditOp());
        stack.Apply(new AddTile(0, 3, 2).ToEditOp());
        var state = stack.State;

        var fromLow = ReachabilityValidator.Validate(state, (0, 0));

        Assert.True(fromLow.IsReachable((0, 1)));
        Assert.False(fromLow.IsReachable((0, 2)));
        Assert.False(fromLow.IsReachable((0, 3)));
        Assert.Equal(new[] { (0, 2), (0, 3) }, fromLow.Unreachable.OrderBy(t => t.Z).ToArray());

        var fromHigh = ReachabilityValidator.Validate(state, (0, 2));
        Assert.True(fromHigh.IsReachable((0, 3)));
        Assert.False(fromHigh.IsReachable((0, 0)));
        Assert.False(fromHigh.IsReachable((0, 1)));
    }

    [Fact]
    public void Validate_CliffFixedBySlopeChain_FullyReachable()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(new AddTile(0, 0, 0).ToEditOp());
        stack.Apply(new AddTile(0, 1, 0).ToEditOp());
        stack.Apply(new SetTileSlope(0, 1, SlopeDirection.North).ToEditOp());
        stack.Apply(new AddTile(0, 2, 1).ToEditOp());
        stack.Apply(new SetTileSlope(0, 2, SlopeDirection.North).ToEditOp());
        stack.Apply(new AddTile(0, 3, 2).ToEditOp());
        var state = stack.State;

        var result = ReachabilityValidator.Validate(state, (0, 0));

        Assert.Empty(result.Unreachable);
        Assert.True(result.IsReachable((0, 3)));
    }

    [Fact]
    public void Validate_BossPortalReachableFromSpawn_ReportsTrue()
    {
        var state = FlatGrid(2, 2);

        var result = ReachabilityValidator.Validate(state, (0, 0));

        Assert.True(result.IsReachable((1, 1)));
    }

    [Fact]
    public void Validate_BossPortalUnreachableFromSpawn_ReportsFalse()
    {
        var stack = new EditStack(new LevelState());
        stack.Apply(new AddTile(0, 0, 0).ToEditOp());
        stack.Apply(new AddTile(0, 1, 3).ToEditOp());
        var state = stack.State;

        var result = ReachabilityValidator.Validate(state, (0, 0));

        Assert.False(result.IsReachable((0, 1)));
    }

    [Fact]
    public void Validate_StartTileAbsent_ThrowsArgumentException()
    {
        var state = FlatGrid(1, 1);

        Assert.Throws<ArgumentException>(() => ReachabilityValidator.Validate(state, (5, 5)));
    }
}
