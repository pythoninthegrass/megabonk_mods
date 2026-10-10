namespace MegabonkLevels.Tests;

public class FreeFlyCameraTests
{
    private static readonly FreeFlySettings Settings = new(MoveSpeed: 10f, FastMultiplier: 4f, LookDegreesPerUnit: 0.1f);
    private static readonly CameraPose Origin = new(0f, 0f, 0f, 0f, 0f, 0f);

    [Fact]
    public void Step_ForwardAtYawZero_MovesAlongPositiveZ()
    {
        var next = FreeFlyCamera.Step(Origin, new FreeFlyInput(Forward: 1f), 1f, Settings);

        Assert.Equal(0f, next.X, 3);
        Assert.Equal(0f, next.Y, 3);
        Assert.Equal(10f, next.Z, 3);
    }

    [Fact]
    public void Step_ForwardAtYawNinety_MovesAlongPositiveX()
    {
        var pose = Origin with { Ry = 90f };

        var next = FreeFlyCamera.Step(pose, new FreeFlyInput(Forward: 1f), 1f, Settings);

        Assert.Equal(10f, next.X, 3);
        Assert.Equal(0f, next.Z, 3);
    }

    [Fact]
    public void Step_RightAtYawZero_MovesAlongPositiveX()
    {
        var next = FreeFlyCamera.Step(Origin, new FreeFlyInput(Right: 1f), 1f, Settings);

        Assert.Equal(10f, next.X, 3);
        Assert.Equal(0f, next.Z, 3);
    }

    [Fact]
    public void Step_ForwardWhileLookingDown_MovesDown()
    {
        var pose = Origin with { Rx = 90f };

        var next = FreeFlyCamera.Step(pose, new FreeFlyInput(Forward: 1f), 1f, Settings with { MoveSpeed = 10f });

        Assert.True(next.Y < 0f);
    }

    [Theory]
    [InlineData(0f)]
    [InlineData(60f)]
    [InlineData(-60f)]
    public void Step_UpInput_MovesAlongPositiveYRegardlessOfPitch(float pitch)
    {
        var pose = Origin with { Rx = pitch, Ry = 33f };

        var next = FreeFlyCamera.Step(pose, new FreeFlyInput(Up: 1f), 1f, Settings);

        Assert.Equal(0f, next.X, 3);
        Assert.Equal(10f, next.Y, 3);
        Assert.Equal(0f, next.Z, 3);
    }

    [Fact]
    public void Step_MovementScalesWithDeltaTime()
    {
        var next = FreeFlyCamera.Step(Origin, new FreeFlyInput(Forward: 1f), 0.5f, Settings);

        Assert.Equal(5f, next.Z, 3);
    }

    [Fact]
    public void Step_FastModifier_MultipliesDistance()
    {
        var next = FreeFlyCamera.Step(Origin, new FreeFlyInput(Forward: 1f, Fast: true), 1f, Settings);

        Assert.Equal(40f, next.Z, 3);
    }

    [Fact]
    public void Step_DiagonalInput_IsNotFasterThanStraight()
    {
        var next = FreeFlyCamera.Step(Origin, new FreeFlyInput(Forward: 1f, Right: 1f), 1f, Settings);

        var distance = MathF.Sqrt(next.X * next.X + next.Y * next.Y + next.Z * next.Z);
        Assert.Equal(10f, distance, 3);
    }

    [Fact]
    public void Step_ZeroInput_LeavesPoseUnchanged()
    {
        var pose = new CameraPose(1f, 2f, 3f, 20f, 40f, 0f);

        var next = FreeFlyCamera.Step(pose, default, 1f, Settings);

        Assert.Equal(pose, next);
    }

    [Fact]
    public void Step_MouseRight_IncreasesYaw()
    {
        var next = FreeFlyCamera.Step(Origin, new FreeFlyInput(MouseDx: 100f), 1f, Settings);

        Assert.Equal(10f, next.Ry, 3);
    }

    [Fact]
    public void Step_MouseUp_LooksUp()
    {
        var next = FreeFlyCamera.Step(Origin, new FreeFlyInput(MouseDy: 100f), 1f, Settings);

        Assert.Equal(-10f, next.Rx, 3);
    }

    [Fact]
    public void Step_MouseLook_IsNotScaledByDeltaTime()
    {
        var slow = FreeFlyCamera.Step(Origin, new FreeFlyInput(MouseDx: 100f), 1f, Settings);
        var fast = FreeFlyCamera.Step(Origin, new FreeFlyInput(MouseDx: 100f), 0.01f, Settings);

        Assert.Equal(slow.Ry, fast.Ry, 3);
    }

    [Fact]
    public void Step_PitchClampsAtBothExtremes()
    {
        var down = FreeFlyCamera.Step(Origin, new FreeFlyInput(MouseDy: -100000f), 1f, Settings);
        var up = FreeFlyCamera.Step(Origin, new FreeFlyInput(MouseDy: 100000f), 1f, Settings);

        Assert.Equal(89f, down.Rx, 3);
        Assert.Equal(-89f, up.Rx, 3);
    }

    [Theory]
    [InlineData(350f, 20f, 10f)]
    [InlineData(10f, -20f, 350f)]
    [InlineData(0f, 360f, 0f)]
    public void Step_YawWrapsIntoZeroToThreeSixty(float startYaw, float yawDelta, float expected)
    {
        var pose = Origin with { Ry = startYaw };

        var next = FreeFlyCamera.Step(pose, new FreeFlyInput(MouseDx: yawDelta / Settings.LookDegreesPerUnit), 1f, Settings);

        Assert.Equal(expected, next.Ry, 2);
    }

    [Fact]
    public void Step_PreservesRoll()
    {
        var pose = Origin with { Rz = 5f };

        var next = FreeFlyCamera.Step(pose, new FreeFlyInput(MouseDx: 10f), 1f, Settings);

        Assert.Equal(5f, next.Rz);
    }
}
