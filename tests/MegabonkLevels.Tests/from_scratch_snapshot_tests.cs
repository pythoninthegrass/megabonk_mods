namespace MegabonkLevels.Tests;

public class FromScratchSnapshotTests
{
    private static readonly Vector3Data One = new(1, 1, 1);
    private static readonly Vector3Data Zero = new(0, 0, 0);

    private static LevelFile Template(int size = 3) => BlankLevel.Create(EMap.Forest, 0, 0, size, 40f, "build-1");

    private static EditOp Place(string catalogId, float x, float z, int? id = null, IReadOnlyList<ObjectAttachmentSpec> attachments = null) =>
        new PlaceObject(catalogId, new Vector3Data(x, 0, z), Zero, One, Attachments: attachments, PlacementId: id).ToEditOp();

    private static EditOp Move(int id, float x, float z, IReadOnlyList<string> hiddenChildren = null) =>
        new MoveObject(ObjectTarget.FromPlacementId(id), new TransformData(new Vector3Data(x, 0, z), Zero, One), hiddenChildren).ToEditOp();

    private static EditOp Remove(int id) => new RemoveObject(ObjectTarget.FromPlacementId(id)).ToEditOp();

    private static LevelState Tiles(params (int X, int Z, int Height)[] cells) =>
        LevelState.FromTiles(cells.Select(c => KeyValuePair.Create((c.X, c.Z), new TileState(c.Height, SlopeDirection.None))));

    private static IReadOnlyList<PlaceObject> Placements(LevelFile level) =>
        level.Edits.Where(op => op.OpType == PlaceObject.OpType).Select(PlaceObject.FromEditOp).ToList();

    [Fact]
    public void Build_WritesTheCurrentTilesIntoTheGrid()
    {
        var state = LevelState.FromTiles(new Dictionary<(int X, int Z), TileState>
        {
            [(0, 0)] = new TileState(0, SlopeDirection.None),
            [(1, 0)] = new TileState(2, SlopeDirection.East),
        });

        var level = FromScratchSnapshot.Build(Template(), state, Array.Empty<EditOp>(), null, null);

        Assert.Equal(3, level.Grid!.Value.Width);
        Assert.Equal(3, level.Grid!.Value.Depth);
        Assert.Equal(new[] { new AuthoredCell(0, 0, 0), new AuthoredCell(1, 0, 2, SlopeDirection.East) }, level.Grid!.Value.Cells);
    }

    [Fact]
    public void Build_LeavesARemovedTileAsAnEmptyCell()
    {
        var level = FromScratchSnapshot.Build(Template(), Tiles((0, 0, 0)), Array.Empty<EditOp>(), null, null);

        Assert.Single(level.Grid!.Value.Cells);
    }

    [Fact]
    public void Build_DropsTileOpsAndGenTargets()
    {
        var edits = new[]
        {
            new SetTileHeight(0, 0, 3).ToEditOp(),
            new RemoveTile(1, 1).ToEditOp(),
            new RemoveObject(ObjectTarget.FromGenId("rock:1")).ToEditOp(),
            Place("bundle:thps/rail", 1, 1),
        };

        var level = FromScratchSnapshot.Build(Template(), Tiles((0, 0, 3)), edits, null, null);

        Assert.All(level.Edits, op => Assert.Equal(PlaceObject.OpType, op.OpType));
        Assert.Single(level.Edits);
        LevelFileValidator.Validate(level);
    }

    [Fact]
    public void Build_MovingAPlacedObjectSavesOnePlacementAtTheFinalPosition()
    {
        var edits = new[] { Place("bundle:thps/rail", 1, 1), Move(0, 5, 6), Move(0, 7, 8) };

        var placements = Placements(FromScratchSnapshot.Build(Template(), Tiles(), edits, null, null));

        var placement = Assert.Single(placements);
        Assert.Equal("bundle:thps/rail", placement.CatalogId);
        Assert.Equal(new Vector3Data(7, 0, 8), placement.Position);
    }

    [Fact]
    public void Build_MovingThenRemovingAPlacedObjectSavesNoPlacement()
    {
        var edits = new[] { Place("bundle:thps/rail", 1, 1), Move(0, 5, 6), Remove(0) };

        var level = FromScratchSnapshot.Build(Template(), Tiles(), edits, null, null);

        Assert.Empty(level.Edits);
    }

    [Fact]
    public void Build_KeepsEachRemainingPlacementUnderItsOwnPlacementId()
    {
        var edits = new[] { Place("bundle:thps/a", 1, 1), Place("bundle:thps/b", 2, 2), Place("bundle:thps/c", 3, 3), Remove(1), Move(2, 9, 9) };

        var placements = Placements(FromScratchSnapshot.Build(Template(), Tiles(), edits, null, null));

        Assert.Equal(new[] { "bundle:thps/a", "bundle:thps/c" }, placements.Select(p => p.CatalogId));
        Assert.Equal(new int?[] { 0, 2 }, placements.Select(p => p.PlacementId));
        Assert.Equal(new Vector3Data(9, 0, 9), placements[1].Position);
    }

    [Fact]
    public void Build_PreservesAttachmentsAndTheirFinalLocalTransform()
    {
        var local = new TransformData(new Vector3Data(0, 3, 0), Zero, One);
        var attachments = new[] { new ObjectAttachmentSpec("post", "bundle:thps/post", local) };
        var edits = new[] { Place("bundle:thps/rail", 1, 1, attachments: attachments), Move(0, 4, 4) };

        var placement = Assert.Single(Placements(FromScratchSnapshot.Build(Template(), Tiles(), edits, null, null)));

        var attachment = Assert.Single(placement.Attachments);
        Assert.Equal("post", attachment.Name);
        Assert.Equal(local, attachment.LocalTransform);
        Assert.Equal(new Vector3Data(4, 0, 4), placement.Position);
    }

    [Fact]
    public void Build_KeepsTheHiddenChildrenOfAMovedPlacement()
    {
        var edits = new[] { Place("bundle:thps/rail", 1, 1), Move(0, 4, 4, new[] { "Pillar" }) };

        var level = FromScratchSnapshot.Build(Template(), Tiles(), edits, null, null);

        var move = Assert.Single(level.Edits, op => op.OpType == MoveObject.OpType);
        Assert.Equal(new[] { "Pillar" }, MoveObject.FromEditOp(move).HiddenChildren);
        Assert.Equal("placement:0", move.Target);
    }

    [Fact]
    public void Build_TakesSpawnAndBossSpawnerFromTheMarkersAndKeepsTheirRotation()
    {
        var template = Template();

        var level = FromScratchSnapshot.Build(template, Tiles(), Array.Empty<EditOp>(), new[] { 1f, 2f, 3f }, new[] { 4f, 5f, 6f });

        Assert.Equal(new[] { 1f, 2f, 3f }, level.Spawn!.Value.Position);
        Assert.Equal(template.Spawn!.Value.Rotation, level.Spawn!.Value.Rotation);
        Assert.Equal(new[] { 4f, 5f, 6f }, level.BossSpawner!.Value.Position);
        Assert.Equal(template.BossSpawner!.Value.Rotation, level.BossSpawner!.Value.Rotation);
        Assert.Null(level.PlayerStart);
        Assert.Null(level.BossSpawnPosition);
    }

    [Fact]
    public void Build_KeepsTheTemplateSpawnAndBossSpawnerWithoutMarkers()
    {
        var template = Template();

        var level = FromScratchSnapshot.Build(template, Tiles(), Array.Empty<EditOp>(), null, null);

        Assert.Equal(template.Spawn, level.Spawn);
        Assert.Equal(template.BossSpawner, level.BossSpawner);
    }

    [Fact]
    public void Build_KeepsTheTemplateMetadata()
    {
        var template = Template() with { Title = "Arena", NoGrass = true };

        var level = FromScratchSnapshot.Build(template, Tiles(), Array.Empty<EditOp>(), null, null);

        Assert.Equal("Arena", level.Title);
        Assert.True(level.NoGrass);
        Assert.True(level.IsFromScratch);
    }
}
