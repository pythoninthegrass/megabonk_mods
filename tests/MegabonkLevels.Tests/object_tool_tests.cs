namespace MegabonkLevels.Tests;

public class ObjectToolTests
{
    private const string Chest = "interactable/chest";
    private static readonly ObjectTarget Generated = ObjectTarget.FromGenId("object:Tree0:0003");
    private static readonly TransformData Current = new(new Vector3Data(1, 2, 3), new Vector3Data(10, 90, 20), new Vector3Data(2, 2, 2));

    [Theory]
    [InlineData("object:Tree0:0003", true)]
    [InlineData("object:Chest:0000", true)]
    [InlineData("tileObject:0001", false)]
    [InlineData("tile:0042", false)]
    [InlineData("flatTile:0017", false)]
    [InlineData("fillTile:0203", false)]
    public void IsPickableGenId_OnlyCoversSpawnedObjects(string genId, bool expected)
    {
        Assert.Equal(expected, ObjectTools.IsPickableGenId(genId));
    }

    [Theory]
    [InlineData("Chest(Clone)", true, false, true)]
    [InlineData("AltarIcon", true, false, true)]
    [InlineData("MinimapIcon", true, false, false)]
    [InlineData("ChargeShrine(Clone)", false, false, false)]
    [InlineData("Dust", true, true, false)]
    public void IsModelRenderer_ExcludesDisabledParticleAndMinimapRenderers(string name, bool enabled, bool isParticle, bool expected)
    {
        Assert.Equal(expected, ObjectTools.IsModelRenderer(name, enabled, isParticle));
    }

    [Theory]
    [InlineData(-0.64f, 0f, 0f)]
    [InlineData(-8.48f, 0f, 0f)]
    [InlineData(8.18f, 0f, 8.18f)]
    [InlineData(1f, 3f, 3f)]
    public void RingBaseY_NeverSinksBelowTheTileSurface(float boundsMinY, float surfaceY, float expected)
    {
        Assert.Equal(expected, ObjectTools.RingBaseY(boundsMinY, surfaceY), 3);
    }

    [Theory]
    [InlineData(1.41f, 1.7625f)]
    [InlineData(0.95f, 1.1875f)]
    [InlineData(2.5f, 2.5f)]
    [InlineData(7.83f, 3.132f)]
    [InlineData(20f, 8f)]
    public void RingRadius_ClearsSmallObjectsAndStaysTightOnLargeOnes(float extent, float expected)
    {
        Assert.Equal(expected, ObjectTools.RingRadius(extent), 2);
    }

    [Fact]
    public void RingBaseY_WithoutASurface_IsTheBoundsMinimum()
    {
        Assert.Equal(-2f, ObjectTools.RingBaseY(-2f, null), 3);
    }

    [Fact]
    public void Ring_PlacesEveryPointOnTheCircleAtTheGivenHeight()
    {
        var ring = ObjectTools.Ring(10f, 5f, -3f, 4f, 8);

        Assert.Equal(8, ring.Count);
        Assert.All(ring, p =>
        {
            Assert.Equal(5f, p.Y);
            Assert.Equal(4f, MathF.Sqrt((p.X - 10f) * (p.X - 10f) + (p.Z + 3f) * (p.Z + 3f)), 3);
        });
    }

    [Fact]
    public void Ring_StartsOnTheEastAxis()
    {
        var ring = ObjectTools.Ring(0f, 0f, 0f, 2f, 4);

        Assert.Equal(2f, ring[0].X, 3);
        Assert.Equal(0f, ring[0].Z, 3);
    }

    [Fact]
    public void PositionAt_FlatTile_AtTheCellCentre_IsTheCentreAtTheTileSurface()
    {
        var position = ObjectTools.PositionAt(9, 7, new TileState(2, SlopeDirection.None), 15, 15, 40f, 20f, 80f, 0f);

        Assert.Equal(new Vector3Data(80f, 40f, 0f), position);
    }

    [Fact]
    public void PositionAt_KeepsTheCursorPointInsideTheCell()
    {
        var position = ObjectTools.PositionAt(7, 7, new TileState(0, SlopeDirection.None), 15, 15, 40f, 20f, 13f, -4f);

        Assert.Equal(new Vector3Data(13f, 0f, -4f), position);
    }

    [Fact]
    public void PositionAt_ClampsToTheCell()
    {
        var position = ObjectTools.PositionAt(7, 7, new TileState(0, SlopeDirection.None), 15, 15, 40f, 20f, 25f, -30f);

        Assert.Equal(new Vector3Data(20f, 0f, -20f), position);
    }

    [Theory]
    [InlineData(0f, 30f)]
    [InlineData(20f, 40f)]
    [InlineData(-20f, 20f)]
    [InlineData(10f, 35f)]
    [InlineData(13f, 36.5f)]
    public void PositionAt_Ramp_FollowsTheSurfaceAlongTheUphillAxis(float pointX, float expectedY)
    {
        var position = ObjectTools.PositionAt(7, 7, new TileState(1, SlopeDirection.East), 15, 15, 40f, 20f, pointX, 0f);

        Assert.Equal(expectedY, position.Y);
    }

    [Fact]
    public void IsStacked_SamePrefabAtTheSamePosition_IsTrue()
    {
        var others = new[] { ("Tree0", new Vector3Data(10f, 0f, 20f)) };

        Assert.True(ObjectTools.IsStacked("Tree0", new Vector3Data(10f, 0f, 20f), others));
    }

    [Fact]
    public void IsStacked_DifferentPrefab_IsFalse()
    {
        var others = new[] { ("Tree0", new Vector3Data(10f, 0f, 20f)) };

        Assert.False(ObjectTools.IsStacked("Log0", new Vector3Data(10f, 0f, 20f), others));
    }

    [Fact]
    public void IsStacked_DifferentPosition_IsFalse()
    {
        var others = new[] { ("Tree0", new Vector3Data(10f, 0f, 20f)) };

        Assert.False(ObjectTools.IsStacked("Tree0", new Vector3Data(20f, 0f, 20f), others));
    }

    [Theory]
    [InlineData(0f, false)]
    [InlineData(0.1f, false)]
    [InlineData(0.2f, true)]
    [InlineData(1f, true)]
    public void DragStarted_OnlyAfterTheButtonHasBeenHeldForTheThreshold(float heldSeconds, bool expected)
    {
        Assert.Equal(expected, ObjectTools.DragStarted(heldSeconds));
    }

    [Fact]
    public void HasMoved_SamePosition_IsFalse()
    {
        Assert.False(ObjectTools.HasMoved(new Vector3Data(1f, 2f, 3f), new Vector3Data(1f, 2f, 3f)));
    }

    [Theory]
    [InlineData(1.5f, 2f, 3f)]
    [InlineData(1f, 2.5f, 3f)]
    [InlineData(1f, 2f, 3.5f)]
    public void HasMoved_AnyAxisDiffers_IsTrue(float x, float y, float z)
    {
        Assert.True(ObjectTools.HasMoved(new Vector3Data(1f, 2f, 3f), new Vector3Data(x, y, z)));
    }

    [Fact]
    public void GridLines_CoversTheCellWithQuarterTileLines()
    {
        var lines = ObjectTools.GridLines(7, 7, new TileState(1, SlopeDirection.None), 15, 15, 40f, 20f, 0.5f);

        Assert.All(lines, p => Assert.InRange(p.X, -20f, 20f));
        Assert.All(lines, p => Assert.InRange(p.Z, -20f, 20f));
        Assert.All(lines, p => Assert.Equal(20.5f, p.Y));
        Assert.Equal(new[] { -20f, -10f, 0f, 10f, 20f }, lines.Select(p => p.X).Distinct().OrderBy(v => v));
        Assert.Equal(new[] { -20f, -10f, 0f, 10f, 20f }, lines.Select(p => p.Z).Distinct().OrderBy(v => v));
    }

    [Fact]
    public void GridLines_EverySegmentIsAxisAligned()
    {
        var lines = ObjectTools.GridLines(7, 7, new TileState(0, SlopeDirection.None), 15, 15, 40f, 20f, 0f);

        for (var i = 1; i < lines.Count; i++)
        {
            Assert.True(lines[i].X == lines[i - 1].X || lines[i].Z == lines[i - 1].Z);
        }
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
