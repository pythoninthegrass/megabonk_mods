namespace MegabonkLevels.Tests;

public class SpawnSeedTests
{
    [Fact]
    public void DebugSeedMode_ForcesFixedSeed()
    {
        Assert.Equal(20261007, SpawnSeed.ForcedSeed(SeedForceMode.DebugSeed, 20261007, 42));
    }

    [Fact]
    public void LevelSeedMode_ForcesLevelSeedValue()
    {
        Assert.Equal(42, SpawnSeed.ForcedSeed(SeedForceMode.LevelSeed, 20261007, 42));
    }

    [Fact]
    public void OffMode_DoesNotReseed()
    {
        Assert.Null(SpawnSeed.ForcedSeed(SeedForceMode.Off, 20261007, 42));
    }

    [Fact]
    public void MapSeedOnlyMode_DoesNotReseed()
    {
        Assert.Null(SpawnSeed.ForcedSeed(SeedForceMode.MapSeedOnly, 20261007, 42));
    }

    [Fact]
    public void PhaseSeed_IsDeterministic()
    {
        Assert.Equal(SpawnSeed.PhaseSeed(20261007, 2), SpawnSeed.PhaseSeed(20261007, 2));
    }

    [Fact]
    public void PhaseSeed_DiffersPerPhase()
    {
        Assert.NotEqual(SpawnSeed.PhaseSeed(20261007, 1), SpawnSeed.PhaseSeed(20261007, 2));
    }

    [Fact]
    public void PhaseSeed_DiffersPerBaseSeed()
    {
        Assert.NotEqual(SpawnSeed.PhaseSeed(20261007, 1), SpawnSeed.PhaseSeed(42, 1));
    }
}
