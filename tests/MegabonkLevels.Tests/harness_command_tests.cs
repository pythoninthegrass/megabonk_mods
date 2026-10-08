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
