namespace MegabonkLevels.Tests;

public class PlayerDamagePolicyTests
{
    [Fact]
    public void HarnessHits_BypassShieldInEveryMode()
    {
        Assert.True(PlayerDamagePolicy.IgnoreShield);
    }

    [Theory]
    [InlineData(1)]
    [InlineData(5)]
    [InlineData(10)]
    [InlineData(37)]
    [InlineData(90)]
    [InlineData(99)]
    public void Parse_AmountAndDefaultSafety(int amount)
    {
        Assert.True(HarnessCommand.TryParse($$"""{"command":"damage","amount":{{amount}}}""", out var command, out var error));
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.Damage, command.Kind);
        Assert.Equal(amount, command.Damage.Amount);
        Assert.True(command.Damage.Nonlethal);
    }

    [Fact]
    public void Parse_ExplicitLethalOptOut()
    {
        Assert.True(HarnessCommand.TryParse("""{"command":"damage","amount":99,"nonlethal":false}""", out var command, out _));
        Assert.False(command.Damage.Nonlethal);
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{\"amount\":0}")]
    [InlineData("{\"amount\":-1}")]
    [InlineData("{\"amount\":100}")]
    [InlineData("{\"amount\":1.5}")]
    [InlineData("{\"amount\":true}")]
    [InlineData("{\"amount\":\"5\"}")]
    [InlineData("{\"amount\":null}")]
    [InlineData("{\"amount\":5,\"nonlethal\":null}")]
    [InlineData("{\"amount\":5,\"nonlethal\":\"false\"}")]
    public void Parse_RejectsInvalidArguments(string fields)
    {
        var json = fields.Insert(1, "\"command\":\"damage\"" + (fields.Length > 2 ? "," : ""));
        Assert.False(HarnessCommand.TryParse(json, out _, out var error));
        Assert.NotNull(error);
    }

    [Theory]
    [InlineData(90, 77, 0, true, 76)]
    [InlineData(5, 77, 0, true, 5)]
    [InlineData(99, 1, 0, true, 0)]
    [InlineData(99, 5, 10.5, true, 14)]
    [InlineData(99, 1, 0.5, true, 0)]
    [InlineData(99, 1, 0, false, 99)]
    [InlineData(250, 20, 0, true, 19)]
    public void Clamp_PreservesFloorAfterModifiers(float damage, int hp, float overheal, bool nonlethal, float expected)
    {
        Assert.Equal(expected, PlayerDamagePolicy.Clamp(damage, hp, overheal, nonlethal));
    }
}
