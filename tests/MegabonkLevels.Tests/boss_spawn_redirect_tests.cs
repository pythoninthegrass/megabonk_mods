namespace MegabonkLevels.Tests;

public class BossSpawnRedirectTests
{
    private static Vec3 V(float x, float y, float z) => new(x, y, z);

    [Theory]
    [InlineData(null)]
    [InlineData(new float[] { })]
    [InlineData(new float[] { 1f, 2f })]
    [InlineData(new float[] { 1f, 2f, 3f, 4f })]
    public void IsUsablePosition_RejectsAnythingButThreeComponents(float[] position)
    {
        Assert.False(BossSpawnRedirect.IsUsablePosition(position));
    }

    [Fact]
    public void IsUsablePosition_RejectsNaNAndInfinities()
    {
        Assert.False(BossSpawnRedirect.IsUsablePosition(new[] { 1f, float.NaN, 3f }));
        Assert.False(BossSpawnRedirect.IsUsablePosition(new[] { 1f, float.PositiveInfinity, 3f }));
        Assert.False(BossSpawnRedirect.IsUsablePosition(new[] { float.NegativeInfinity, 2f, 3f }));
    }

    [Fact]
    public void IsUsablePosition_AcceptsThreeFiniteComponents()
    {
        Assert.True(BossSpawnRedirect.IsUsablePosition(new[] { 130f, -4.933f, 65f }));
    }

    [Fact]
    public void ShouldArm_NeedsAnActiveCustomLevelAndAnAuthoredPosition()
    {
        var authored = new[] { 130f, -4.933f, 65f };

        Assert.True(BossSpawnRedirect.ShouldArm(true, authored));
        Assert.False(BossSpawnRedirect.ShouldArm(false, authored));
        Assert.False(BossSpawnRedirect.ShouldArm(true, null));
    }

    [Fact]
    public void ShouldConsume_OnlyInsideTheWindowAfterArming()
    {
        Assert.False(BossSpawnRedirect.ShouldConsume(null, 100));
        Assert.False(BossSpawnRedirect.ShouldConsume(100, 99));
        Assert.True(BossSpawnRedirect.ShouldConsume(100, 100));
        Assert.True(BossSpawnRedirect.ShouldConsume(100, 100 + BossSpawnRedirect.ArmWindowFrames));
        Assert.False(BossSpawnRedirect.ShouldConsume(100, 101 + BossSpawnRedirect.ArmWindowFrames));
    }

    [Fact]
    public void Placement_KeepsWhateverOffsetTheGamePutOnTheEnemy()
    {
        // The game lifts a spawned enemy well above the position it was asked for, so the boss's feet, not its pivot,
        // have to land on the authored point.
        var placed = BossSpawnRedirect.Placement(V(130f, -4.933f, 65f), V(150f, 15.6f, 26f), V(150f, 27.5f, 26f));

        Assert.Equal(130f, placed.X);
        Assert.Equal(6.967f, placed.Y, 3);
        Assert.Equal(65f, placed.Z);
    }

    [Fact]
    public void Placement_LeavesTheEnemyWhereItWasWhenTheGamePlacedItAtTheRequestedPoint()
    {
        var spawn = V(150f, 15.6f, 26f);
        var placed = BossSpawnRedirect.Placement(V(130f, -4.933f, 65f), spawn, spawn);

        Assert.Equal(130f, placed.X);
        Assert.Equal(-4.933f, placed.Y, 3);
        Assert.Equal(65f, placed.Z);
    }
}
