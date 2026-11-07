namespace MegabonkLevels.Tests;

public class PlacePreviewTests
{
    private const string Chest = "interactable/chest";
    private static readonly ObjectTarget Generated = ObjectTarget.FromGenId("object:Chest:0001");
    private static readonly Vector3Data Prefab = new(5f, 33f, 7f);
    private static readonly TransformData Upright = new(new Vector3Data(1, 2, 3), new Vector3Data(0, 0, 0), new Vector3Data(1, 1, 1));

    [Theory]
    [InlineData(true, false, true, true, true, true, true)]
    [InlineData(false, false, true, true, true, true, false)]
    [InlineData(true, true, true, true, true, true, false)]
    [InlineData(true, false, false, true, true, true, false)]
    [InlineData(true, false, true, false, true, true, false)]
    [InlineData(true, false, true, true, false, true, false)]
    [InlineData(true, false, true, true, true, false, false)]
    public void IsVisible_NeedsEveryConditionAClickNeeds(bool placeTool, bool pointerBlocked, bool hasSelection, bool hasPrefab, bool hasCamera,
        bool hasPosition, bool expected)
    {
        Assert.Equal(expected, PlacePreview.IsVisible(placeTool, pointerBlocked, hasSelection, hasPrefab, hasCamera, hasPosition));
    }

    [Fact]
    public void Facing_KeepsThePrefabsPitchAndRollAndFacesTheCamera()
    {
        Assert.Equal(new Vector3Data(5f, 90f, 7f), PlacePreview.Facing(Prefab, 270f));
    }

    [Fact]
    public void Rotation_FacesTheCameraWhileNoKeyIsPressed()
    {
        Assert.Equal(new Vector3Data(5f, 270f, 7f), PlacePreview.Rotation(null, Prefab, 90f, null, true));
    }

    [Fact]
    public void Rotation_KeepsTheUserRotationWhenNoKeyIsPressed()
    {
        var stored = new Vector3Data(0f, 90f, 0f);

        Assert.Equal(stored, PlacePreview.Rotation(stored, Prefab, 180f, null, true));
    }

    [Fact]
    public void Rotation_StepsTheCameraFacingPoseRatherThanThePrefabEuler()
    {
        Assert.Equal(new Vector3Data(5f, 270f, 7f), PlacePreview.Rotation(null, Prefab, 0f, RotationAxis.Yaw, true));
    }

    [Fact]
    public void Rotation_ShiftStepsBackwards()
    {
        Assert.Equal(new Vector3Data(5f, 90f, 7f), PlacePreview.Rotation(null, Prefab, 0f, RotationAxis.Yaw, false));
    }

    [Fact]
    public void Rotation_StepsFromTheStoredRotationOnceTheUserHasRotated()
    {
        var stored = new Vector3Data(0f, 90f, 0f);

        Assert.Equal(new Vector3Data(0f, 180f, 0f), PlacePreview.Rotation(stored, Prefab, 0f, RotationAxis.Yaw, true));
    }

    [Theory]
    [InlineData(RotationAxis.Pitch)]
    [InlineData(RotationAxis.Roll)]
    public void Rotation_StepsPitchAndRollLikeTheSelectedObjectsRotateKey(RotationAxis axis)
    {
        var stored = new Vector3Data(10f, 90f, 20f);

        var expected = MoveObject.FromEditOp(ObjectTools.Rotate(Generated, Upright with { Rotation = stored }, axis, true)).NewTransform.Rotation;
        Assert.Equal(expected, PlacePreview.Rotation(stored, Prefab, 0f, axis, true));
    }

    [Fact]
    public void Rotation_AndPlaceWithRotationAgreeOnWhatAClickCreates()
    {
        var rotation = PlacePreview.Rotation(new Vector3Data(0f, 90f, 0f), Prefab, 0f, RotationAxis.Yaw, true);
        var position = new Vector3Data(80f, 40f, 0f);
        var scale = new Vector3Data(1f, 1f, 1f);

        var expected = new PlaceObject(Chest, position, rotation, scale);
        Assert.Equal(expected.ToEditOp(), ObjectTools.PlaceWithRotation(CatalogId.Parse(Chest), position, rotation, scale));
    }
}
