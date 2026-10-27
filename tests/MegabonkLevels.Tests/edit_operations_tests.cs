namespace MegabonkLevels.Tests;

public class ObjectTargetTests
{
    [Fact]
    public void FromGenId_ValidId_RoundTripsThroughSerialize()
    {
        var target = ObjectTarget.FromGenId("randomObject:Tree:5");

        var parsed = ObjectTarget.Parse(target.Serialize());

        Assert.Equal(target, parsed);
    }

    [Fact]
    public void FromPlacementId_ValidId_RoundTripsThroughSerialize()
    {
        var target = ObjectTarget.FromPlacementId(7);

        var parsed = ObjectTarget.Parse(target.Serialize());

        Assert.Equal(target, parsed);
    }

    [Fact]
    public void FromGenId_BlankId_Throws() =>
        Assert.Throws<ArgumentException>(() => ObjectTarget.FromGenId("  "));

    [Fact]
    public void FromPlacementId_Negative_Throws() =>
        Assert.Throws<ArgumentOutOfRangeException>(() => ObjectTarget.FromPlacementId(-1));

    [Fact]
    public void Parse_UnrecognizedFormat_Throws() =>
        Assert.Throws<ArgumentException>(() => ObjectTarget.Parse("nonsense:foo"));
}

public class SetTileHeightTests
{
    [Fact]
    public void ValidConstruction_RoundTripsThroughEditOp()
    {
        var op = new SetTileHeight(X: 3, Z: 4, Height: 2);

        var restored = SetTileHeight.FromEditOp(op.ToEditOp());

        Assert.Equal(op, restored);
    }

    [Fact]
    public void NegativeX_Throws() =>
        Assert.Throws<ArgumentOutOfRangeException>(() => new SetTileHeight(X: -1, Z: 0, Height: 1));

    [Fact]
    public void FromEditOp_WrongOpType_Throws() =>
        Assert.Throws<ArgumentException>(() => SetTileHeight.FromEditOp(new EditOp("tile.add", "", "{}")));
}

public class SetTileSlopeTests
{
    [Fact]
    public void ValidConstruction_RoundTripsThroughEditOp()
    {
        var op = new SetTileSlope(X: 1, Z: 2, Direction: SlopeDirection.North);

        var restored = SetTileSlope.FromEditOp(op.ToEditOp());

        Assert.Equal(op, restored);
    }

    [Fact]
    public void NoneDirection_RoundTripsThroughEditOp()
    {
        var op = new SetTileSlope(X: 1, Z: 2, Direction: SlopeDirection.None);

        var restored = SetTileSlope.FromEditOp(op.ToEditOp());

        Assert.Equal(op, restored);
    }

    [Fact]
    public void NegativeZ_Throws() =>
        Assert.Throws<ArgumentOutOfRangeException>(() => new SetTileSlope(X: 0, Z: -1, Direction: SlopeDirection.None));

    [Fact]
    public void UndefinedDirection_Throws() =>
        Assert.Throws<ArgumentException>(() => new SetTileSlope(X: 0, Z: 0, Direction: (SlopeDirection)99));
}

public class AddTileTests
{
    [Fact]
    public void ValidConstruction_RoundTripsThroughEditOp()
    {
        var op = new AddTile(X: 5, Z: 6, Height: 0);

        var restored = AddTile.FromEditOp(op.ToEditOp());

        Assert.Equal(op, restored);
    }

    [Fact]
    public void NegativeX_Throws() =>
        Assert.Throws<ArgumentOutOfRangeException>(() => new AddTile(X: -2, Z: 0, Height: 0));
}

public class RemoveTileTests
{
    [Fact]
    public void ValidConstruction_RoundTripsThroughEditOp()
    {
        var op = new RemoveTile(X: 2, Z: 9);

        var restored = RemoveTile.FromEditOp(op.ToEditOp());

        Assert.Equal(op, restored);
    }

    [Fact]
    public void NegativeZ_Throws() =>
        Assert.Throws<ArgumentOutOfRangeException>(() => new RemoveTile(X: 0, Z: -3));
}

public class PlaceObjectTests
{
    private static PlaceObject SampleOp() => new(
        CatalogId: "props/rock_small",
        Position: new Vector3Data(1, 0, 3),
        Rotation: new Vector3Data(0, 90, 0),
        Scale: new Vector3Data(1, 1, 1));

    [Fact]
    public void ValidConstruction_RoundTripsThroughEditOp()
    {
        var op = SampleOp();

        var restored = PlaceObject.FromEditOp(op.ToEditOp());

        Assert.Equal(op, restored);
    }

    [Fact]
    public void BlankCatalogId_Throws() =>
        Assert.Throws<ArgumentException>(() => new PlaceObject(
            "   ", new Vector3Data(1, 0, 3), new Vector3Data(0, 90, 0), new Vector3Data(1, 1, 1)));

    [Fact]
    public void MalformedCatalogId_Throws() =>
        Assert.Throws<ArgumentException>(() => new PlaceObject(
            "unknownns:rock_small", new Vector3Data(1, 0, 3), new Vector3Data(0, 90, 0), new Vector3Data(1, 1, 1)));

    [Fact]
    public void ZeroScale_Throws() =>
        Assert.Throws<ArgumentException>(() => new PlaceObject(
            "props/rock_small", new Vector3Data(1, 0, 3), new Vector3Data(0, 90, 0), new Vector3Data(0, 1, 1)));
}

public class MoveObjectTests
{
    private static TransformData SampleTransform() => new(
        Position: new Vector3Data(2, 0, 2),
        Rotation: new Vector3Data(0, 0, 0),
        Scale: new Vector3Data(1, 1, 1));

    [Fact]
    public void ValidConstruction_WithGenIdTarget_RoundTripsThroughEditOp()
    {
        var op = new MoveObject(ObjectTarget.FromGenId("tile:42"), SampleTransform());

        var restored = MoveObject.FromEditOp(op.ToEditOp());

        Assert.Equal(op, restored);
    }

    [Fact]
    public void ValidConstruction_WithPlacementIdTarget_RoundTripsThroughEditOp()
    {
        var op = new MoveObject(ObjectTarget.FromPlacementId(3), SampleTransform());

        var restored = MoveObject.FromEditOp(op.ToEditOp());

        Assert.Equal(op, restored);
    }

    [Fact]
    public void ZeroScale_Throws() =>
        Assert.Throws<ArgumentException>(() => new MoveObject(
            ObjectTarget.FromPlacementId(0),
            SampleTransform() with { Scale = new Vector3Data(1, 0, 1) }));
}

public class RemoveObjectTests
{
    [Fact]
    public void ValidConstruction_WithGenIdTarget_RoundTripsThroughEditOp()
    {
        var op = new RemoveObject(ObjectTarget.FromGenId("randomObject:Tree:5"));

        var restored = RemoveObject.FromEditOp(op.ToEditOp());

        Assert.Equal(op, restored);
    }

    [Fact]
    public void ValidConstruction_WithPlacementIdTarget_RoundTripsThroughEditOp()
    {
        var op = new RemoveObject(ObjectTarget.FromPlacementId(12));

        var restored = RemoveObject.FromEditOp(op.ToEditOp());

        Assert.Equal(op, restored);
    }

    [Fact]
    public void InvalidTarget_Throws() =>
        Assert.Throws<ArgumentException>(() => RemoveObject.FromEditOp(new EditOp("object.remove", "nonsense", "{}")));
}

public class EditOperationsInLevelFileTests
{
    [Fact]
    public void AllSevenOpTypes_RoundTripInsideLevelFileEditsArray()
    {
        var level = new LevelFile(
            SchemaVersion: LevelFile.CurrentSchemaVersion,
            GameBuildId: "1.0.69",
            Map: EMap.Forest,
            StageIndex: 0,
            Tier: 1,
            Seed: 20261007,
            Packs: new Dictionary<string, string>(),
            Edits:
            [
                new SetTileHeight(0, 0, 2).ToEditOp(),
                new SetTileSlope(0, 1, SlopeDirection.North).ToEditOp(),
                new AddTile(1, 0, 0).ToEditOp(),
                new RemoveTile(1, 1).ToEditOp(),
                new PlaceObject("props/rock_small", new Vector3Data(1, 0, 3), new Vector3Data(0, 90, 0), new Vector3Data(1, 1, 1)).ToEditOp(),
                new MoveObject(ObjectTarget.FromGenId("tile:42"), new TransformData(new Vector3Data(2, 0, 2), default, new Vector3Data(1, 1, 1))).ToEditOp(),
                new RemoveObject(ObjectTarget.FromPlacementId(0)).ToEditOp(),
            ]);

        var json = LevelFileSerializer.Serialize(level);
        var restored = LevelFileSerializer.Deserialize(json);

        Assert.Equal(level, restored);
        Assert.Equal(new SetTileHeight(0, 0, 2), SetTileHeight.FromEditOp(restored.Edits[0]));
        Assert.Equal(new SetTileSlope(0, 1, SlopeDirection.North), SetTileSlope.FromEditOp(restored.Edits[1]));
        Assert.Equal(new AddTile(1, 0, 0), AddTile.FromEditOp(restored.Edits[2]));
        Assert.Equal(new RemoveTile(1, 1), RemoveTile.FromEditOp(restored.Edits[3]));
        Assert.Equal(
            new PlaceObject("props/rock_small", new Vector3Data(1, 0, 3), new Vector3Data(0, 90, 0), new Vector3Data(1, 1, 1)),
            PlaceObject.FromEditOp(restored.Edits[4]));
        Assert.Equal(
            new MoveObject(ObjectTarget.FromGenId("tile:42"), new TransformData(new Vector3Data(2, 0, 2), default, new Vector3Data(1, 1, 1))),
            MoveObject.FromEditOp(restored.Edits[5]));
        Assert.Equal(new RemoveObject(ObjectTarget.FromPlacementId(0)), RemoveObject.FromEditOp(restored.Edits[6]));
    }
}
