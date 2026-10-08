namespace MegabonkLevels.Tests;

public class HarnessCommandTests
{
    [Fact]
    public void TryParse_LoadLevel_ReturnsKindAndPath()
    {
        var ok = HarnessCommand.TryParse("""{"command":"load-level","path":"/tmp/a.mblevel.json"}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.LoadLevel, command.Kind);
        Assert.Equal("/tmp/a.mblevel.json", command.Path);
    }

    [Fact]
    public void TryParse_Screenshot_ReturnsKindAndPath()
    {
        var ok = HarnessCommand.TryParse("""{"command":"screenshot","path":"C:\\shots\\one.png"}""", out var command, out _);

        Assert.True(ok);
        Assert.Equal(HarnessCommandKind.Screenshot, command.Kind);
        Assert.Equal("C:\\shots\\one.png", command.Path);
    }

    [Fact]
    public void TryParse_Quit_NeedsNoPath()
    {
        var ok = HarnessCommand.TryParse("""{"command":"quit"}""", out var command, out _);

        Assert.True(ok);
        Assert.Equal(HarnessCommandKind.Quit, command.Kind);
        Assert.Null(command.Path);
    }

    [Theory]
    [InlineData("freeze", HarnessCommandKind.Freeze)]
    [InlineData("resume", HarnessCommandKind.Resume)]
    [InlineData("camera-clear", HarnessCommandKind.CameraClear)]
    [InlineData("invulnerable", HarnessCommandKind.Invulnerable)]
    [InlineData("vulnerable", HarnessCommandKind.Vulnerable)]
    public void TryParse_ArglessCommands_NeedNoPath(string name, HarnessCommandKind expected)
    {
        var ok = HarnessCommand.TryParse($$"""{"command":"{{name}}"}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(expected, command.Kind);
        Assert.Null(command.Path);
    }

    [Theory]
    [InlineData("true", true)]
    [InlineData("false", false)]
    public void TryParse_Heartbeat_ReadsTheEnabledFlag(string enabled, bool expected)
    {
        var ok = HarnessCommand.TryParse($$"""{"command":"heartbeat","enabled":{{enabled}}}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.Heartbeat, command.Kind);
        Assert.Equal(expected, command.Enabled);
        Assert.Null(command.Path);
    }

    [Theory]
    [InlineData("""{"command":"heartbeat"}""")]
    [InlineData("""{"command":"heartbeat","enabled":"yes"}""")]
    [InlineData("""{"command":"heartbeat","enabled":1}""")]
    [InlineData("""{"command":"heartbeat","enabled":null}""")]
    public void TryParse_Heartbeat_MissingOrNonBooleanEnabled_IsRejected(string json)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains("enabled", error);
    }

    [Fact]
    public void TryParse_Camera_ReturnsPositionAndEulerRotation()
    {
        var ok = HarnessCommand.TryParse("""{"command":"camera","position":[1.5,200,-3],"rotation":[90,0,45.5]}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.Camera, command.Kind);
        Assert.Equal(new CameraPose(1.5f, 200f, -3f, 90f, 0f, 45.5f), command.Pose);
    }

    [Theory]
    [InlineData("""{"command":"camera"}""", "position")]
    [InlineData("""{"command":"camera","position":[1,2,3]}""", "rotation")]
    [InlineData("""{"command":"camera","position":[1,2],"rotation":[0,0,0]}""", "position")]
    [InlineData("""{"command":"camera","position":[1,2,3],"rotation":[0,0,0,0]}""", "rotation")]
    [InlineData("""{"command":"camera","position":[1,"a",3],"rotation":[0,0,0]}""", "position")]
    [InlineData("""{"command":"camera","position":"1,2,3","rotation":[0,0,0]}""", "position")]
    public void TryParse_CameraWithoutUsableVectors_FailsNamingTheField(string json, string expectedFragment)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains(expectedFragment, error);
    }

    [Fact]
    public void TryParse_IgnoresUnknownFields()
    {
        var ok = HarnessCommand.TryParse("""{"command":"quit","id":7}""", out var command, out _);

        Assert.True(ok);
        Assert.Equal(HarnessCommandKind.Quit, command.Kind);
    }

    [Theory]
    [InlineData("""{"command":"load-level"}""", "path")]
    [InlineData("""{"command":"load-level","path":""}""", "path")]
    [InlineData("""{"command":"screenshot","path":"  "}""", "path")]
    [InlineData("""{"command":"load-level","path":3}""", "path")]
    public void TryParse_PathCommandWithoutUsablePath_FailsNamingPath(string json, string expectedFragment)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains(expectedFragment, error);
    }

    [Theory]
    [InlineData("""{"command":"reboot"}""", "reboot")]
    [InlineData("""{"command":"Quit"}""", "Quit")]
    public void TryParse_UnknownCommand_FailsNamingTheCommand(string json, string expectedFragment)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains(expectedFragment, error);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("not json")]
    [InlineData("{")]
    [InlineData("[]")]
    [InlineData("null")]
    [InlineData("""{"path":"x"}""")]
    [InlineData("""{"command":5}""")]
    public void TryParse_MalformedInput_FailsWithoutThrowing(string json)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.False(string.IsNullOrEmpty(error));
    }
}
