using System.Text.Json.Nodes;

namespace MegabonkLevels.Tests;

public class HarnessRunnerTests
{
    private static HarnessCommand Command(string json)
    {
        Assert.True(HarnessCommand.TryParse(json, out var command, out var error), error);
        return command;
    }

    [Fact]
    public void Run_HandlerReturnsObject_ReturnsSuccessEnvelopeWithCommandName()
    {
        var result = HarnessRunner.Run(Command("""{"command":"state"}"""), _ => new JsonObject { ["levelLoaded"] = true });

        var root = JsonNode.Parse(result.ToJson())!.AsObject();
        Assert.Equal("state", (string?)root["command"]);
        Assert.True((bool?)root["ok"]);
        Assert.True((bool?)root["result"]!["levelLoaded"]);
    }

    [Fact]
    public void Run_HandlerReturnsNull_ReturnsSuccessWithNullResult()
    {
        var result = HarnessRunner.Run(Command("""{"command":"freeze"}"""), _ => null);

        Assert.True(result.Ok);
        Assert.Null(result.Result);
    }

    [Fact]
    public void Run_HandlerThrows_ReturnsFailureWithMessage()
    {
        var result = HarnessRunner.Run(Command("""{"command":"freeze"}"""), _ => throw new InvalidOperationException("no player"));

        Assert.False(result.Ok);
        Assert.Equal("freeze", result.Command);
        Assert.Equal("no player", result.Error);
    }

    [Fact]
    public void Run_HandlerReceivesTheCommand()
    {
        HarnessCommandKind? seen = null;

        HarnessRunner.Run(Command("""{"command":"resume"}"""), c =>
        {
            seen = c.Kind;
            return null;
        });

        Assert.Equal(HarnessCommandKind.Resume, seen);
    }
}
