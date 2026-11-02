namespace MegabonkLevels.Tests;

public class PerfCommandTests
{
    [Theory]
    [InlineData("report")]
    [InlineData("status")]
    [InlineData("start")]
    [InlineData("reset")]
    [InlineData("spawn")]
    [InlineData("timescale")]
    [InlineData("toggle")]
    [InlineData("vsync")]
    [InlineData("health")]
    [InlineData("census")]
    public void TryParse_Perf_AcceptsTheDocumentedActions(string action)
    {
        var json = $$"""{"command":"perf","action":"{{action}}","count":40,"value":2,"target":"killFloor","enabled":false}""";

        var ok = HarnessCommand.TryParse(json, out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.Perf, command.Kind);
        Assert.Equal("perf", command.Name);
        Assert.Equal(action, command.Perf.Action);
    }

    [Fact]
    public void TryParse_Perf_SpawnPreservesCount()
    {
        Assert.True(HarnessCommand.TryParse("""{"command":"perf","action":"spawn","count":120}""", out var command, out _));

        Assert.Equal("spawn", command.Perf.Action);
        Assert.Equal(120, command.Perf.Count);
    }

    [Fact]
    public void TryParse_Perf_TimescaleValueIsOptionalAndNullable()
    {
        Assert.True(HarnessCommand.TryParse("""{"command":"perf","action":"timescale"}""", out var released, out _));
        Assert.True(HarnessCommand.TryParse("""{"command":"perf","action":"timescale","value":3.5}""", out var held, out _));

        Assert.Null(released.Perf.Value);
        Assert.Equal(3.5f, held.Perf.Value);
    }

    [Fact]
    public void TryParse_Perf_HealthPreservesHpAndLeavesItUnsetWhenOmitted()
    {
        Assert.True(HarnessCommand.TryParse("""{"command":"perf","action":"health","hp":250000}""", out var set, out _));
        Assert.True(HarnessCommand.TryParse("""{"command":"perf","action":"health"}""", out var omitted, out _));

        Assert.Equal("health", set.Perf.Action);
        Assert.Equal(250000, set.Perf.Hp);
        Assert.Null(omitted.Perf.Hp);
    }

    [Fact]
    public void TryParse_Perf_TogglePreservesTargetAndEnabled()
    {
        Assert.True(HarnessCommand.TryParse("""{"command":"perf","action":"toggle","target":"EnemyHpBar.Update","enabled":false}""", out var command, out _));

        Assert.Equal("toggle", command.Perf.Action);
        Assert.Equal("EnemyHpBar.Update", command.Perf.Target);
        Assert.False(command.Perf.Enabled);
    }

    [Theory]
    [InlineData("""{"command":"perf"}""")]
    [InlineData("""{"command":"perf","action":"profile"}""")]
    [InlineData("""{"command":"perf","action":"spawn"}""")]
    [InlineData("""{"command":"perf","action":"spawn","count":0}""")]
    [InlineData("""{"command":"perf","action":"spawn","count":301}""")]
    [InlineData("""{"command":"perf","action":"spawn","count":"many"}""")]
    [InlineData("""{"command":"perf","action":"timescale","value":0}""")]
    [InlineData("""{"command":"perf","action":"timescale","value":21}""")]
    [InlineData("""{"command":"perf","action":"toggle","enabled":true}""")]
    [InlineData("""{"command":"perf","action":"toggle","target":"killFloor"}""")]
    [InlineData("""{"command":"perf","action":"toggle","target":"","enabled":true}""")]
    [InlineData("""{"command":"perf","action":"vsync"}""")]
    [InlineData("""{"command":"perf","action":"vsync","enabled":"off"}""")]
    public void TryParse_Perf_RejectsInvalidArguments(string json)
    {
        Assert.False(HarnessCommand.TryParse(json, out _, out var error));

        Assert.NotNull(error);
    }

    [Fact]
    public void TryParse_Perf_SpawnCountAboveTheMaximum_ReportsTheLimit()
    {
        Assert.False(HarnessCommand.TryParse("""{"command":"perf","action":"spawn","count":5000}""", out _, out var error));

        Assert.Contains("300", error);
    }
}
