namespace MegabonkLevels.Tests;

public class TerrainSeedMeasurementTests
{
    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, false)]
    public void RequiresBothDevelopmentAndExplicitOptIn(bool development, bool enabled)
    {
        TerrainSeedMeasurement.Arm(424242, development, enabled);
        Assert.False(TerrainSeedMeasurement.IsArmed);
        Assert.Null(TerrainSeedMeasurement.TakePin());
    }

    [Fact]
    public void AnUnseededLoadPinsNothing()
    {
        TerrainSeedMeasurement.Arm(424242, true, true);
        TerrainSeedMeasurement.Arm(null, true, true);
        Assert.False(TerrainSeedMeasurement.IsArmed);
        Assert.Null(TerrainSeedMeasurement.TakePin());
    }

    [Fact]
    public void PinsExactlyOneGeneration()
    {
        TerrainSeedMeasurement.Arm(424242, true, true);
        Assert.True(TerrainSeedMeasurement.IsArmed);
        Assert.Equal((int?)424242, TerrainSeedMeasurement.TakePin());
        Assert.False(TerrainSeedMeasurement.IsArmed);
        Assert.Null(TerrainSeedMeasurement.TakePin());
    }

    [Fact]
    public void ADisabledLoadClearsAnEarlierPin()
    {
        TerrainSeedMeasurement.Arm(424242, true, true);
        TerrainSeedMeasurement.Arm(1, true, false);
        Assert.Null(TerrainSeedMeasurement.TakePin());
    }

    [Fact]
    public void StaysDisabledUnlessBothSwitchesAreSet()
    {
        var terrain = Environment.GetEnvironmentVariable(TerrainSeedMeasurement.EnvironmentVariable);
        var development = Environment.GetEnvironmentVariable("MEGABONK_DEV");
        try
        {
            Environment.SetEnvironmentVariable(TerrainSeedMeasurement.EnvironmentVariable, "true");
            Environment.SetEnvironmentVariable("MEGABONK_DEV", null);
            Assert.False(TerrainSeedMeasurement.IsEnabled);

            Environment.SetEnvironmentVariable("MEGABONK_DEV", "true");
            Assert.True(TerrainSeedMeasurement.IsEnabled);
        }
        finally
        {
            Environment.SetEnvironmentVariable(TerrainSeedMeasurement.EnvironmentVariable, terrain);
            Environment.SetEnvironmentVariable("MEGABONK_DEV", development);
        }
    }
}
