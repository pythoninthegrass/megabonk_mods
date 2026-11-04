namespace MegabonkLevels.Tests;

public class BossSpawnRedirectTests
{
    private static Vec3 V(float x, float y, float z) => new(x, y, z);

    private static readonly Vec3 Spawner = V(170f, 15.6f, 27f);

    [Theory]
    [InlineData(0, 1)]
    [InlineData(1, 2)]
    [InlineData(3, 4)]
    public void ExpectedMoves_IsOnePlusBossCurses(int bossCurses, int expected)
    {
        Assert.Equal(expected, BossSpawnRedirect.ExpectedMoves(bossCurses));
    }

    [Fact]
    public void ExpectedMoves_ClampsNegativeCursesToOne()
    {
        Assert.Equal(1, BossSpawnRedirect.ExpectedMoves(-5));
    }

    [Fact]
    public void ShouldArm_NeedsAnActiveCustomLevel()
    {
        Assert.True(BossSpawnRedirect.ShouldArm(true, fromScratch: false));
        Assert.False(BossSpawnRedirect.ShouldArm(false, fromScratch: false));
    }

    [Fact]
    public void ShouldArm_NeverOnAFromScratchLevel()
    {
        Assert.False(BossSpawnRedirect.ShouldArm(true, fromScratch: true));
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
    public void ShouldExpire_TrueWhenWindowPassed()
    {
        Assert.True(BossSpawnRedirect.ShouldExpire(100, 2, 0, 103, BossSpawnRedirect.ArmWindowFrames));
    }

    [Fact]
    public void ShouldExpire_TrueWhenExpectedCountMet()
    {
        Assert.True(BossSpawnRedirect.ShouldExpire(100, 2, 2, 101, BossSpawnRedirect.ArmWindowFrames));
    }

    [Fact]
    public void ShouldExpire_FalseWhenWithinWindowAndCountNotMet()
    {
        Assert.False(BossSpawnRedirect.ShouldExpire(100, 2, 1, 101, BossSpawnRedirect.ArmWindowFrames));
    }

    [Fact]
    public void ShouldExpire_FalseWhenNotArmed()
    {
        Assert.False(BossSpawnRedirect.ShouldExpire(null, 2, 0, 101, BossSpawnRedirect.ArmWindowFrames));
    }

    [Fact]
    public void CandidateRing_KeepsEverySampleInsideTheDistanceBand()
    {
        foreach (var candidate in BossSpawnRedirect.CandidateRing(Spawner, 1234, 32))
        {
            var distance = MathF.Sqrt((candidate.X - Spawner.X) * (candidate.X - Spawner.X)
                                    + (candidate.Z - Spawner.Z) * (candidate.Z - Spawner.Z));
            Assert.InRange(distance, BossSpawnRedirect.MinDistanceFromSpawner, BossSpawnRedirect.MaxDistanceFromSpawner);
        }
    }

    [Fact]
    public void CandidateRing_IsDeterministicForItsSeed()
    {
        Assert.Equal(BossSpawnRedirect.CandidateRing(Spawner, 77, 8), BossSpawnRedirect.CandidateRing(Spawner, 77, 8));
    }

    [Fact]
    public void CandidateRing_DifferentSeedsGiveDifferentSpots()
    {
        Assert.NotEqual(BossSpawnRedirect.CandidateRing(Spawner, 1, 8), BossSpawnRedirect.CandidateRing(Spawner, 2, 8));
    }

    [Fact]
    public void SpotUsable_RejectsSpotsTooCloseToTheSpawner()
    {
        var near = V(Spawner.X + 30f, -4.9f, Spawner.Z);

        Assert.False(BossSpawnRedirect.SpotUsable(near, Spawner, -35f, Array.Empty<Vec3>()));
    }

    [Fact]
    public void SpotUsable_RejectsSpotsBelowTheKillFloor()
    {
        var below = V(Spawner.X + 45f, -40f, Spawner.Z);

        Assert.False(BossSpawnRedirect.SpotUsable(below, Spawner, -35f, Array.Empty<Vec3>()));
    }

    [Fact]
    public void SpotUsable_RejectsSpotsTooCloseToAnEarlierCopy()
    {
        // Live finding (2026-11-02): copies 14.7 units apart still fought on the same spot, so the spacing floor is 20.
        var first = V(Spawner.X + 45f, 0.5f, Spawner.Z);
        var second = V(Spawner.X + 59.7f, 0.5f, Spawner.Z);

        Assert.False(BossSpawnRedirect.SpotUsable(second, Spawner, -35f, new[] { first }));
        Assert.True(BossSpawnRedirect.SpotUsable(V(Spawner.X + 66f, 0.5f, Spawner.Z), Spawner, -35f, new[] { first }));
    }

    [Fact]
    public void SpotUsable_AcceptsAFarSpotAboveTheKillFloor()
    {
        var spot = V(Spawner.X + 45f, -4.9f, Spawner.Z);

        Assert.True(BossSpawnRedirect.SpotUsable(spot, Spawner, -35f, Array.Empty<Vec3>()));
    }

    [Fact]
    public void PickSpot_PicksTheUsableCandidateFarthestFromTheTakenSpots()
    {
        // Live findings (2026-11-02): first-fit landed copies 14.7 and 21.2 apart, just over the spacing floor, so
        // the patch picks the best of the whole ring instead of the first candidate that passes.
        var first = V(Spawner.X + 45f, 0.5f, Spawner.Z);
        var near = V(Spawner.X + 47f, 0.5f, Spawner.Z + 2f);
        var far = V(Spawner.X + 45f, 0.5f, Spawner.Z + 40f);

        Assert.True(BossSpawnRedirect.PickSpot(new[] { near, far }, new[] { first }, out var picked));
        Assert.Equal(far, picked);
    }

    [Fact]
    public void PickSpot_ScoresAgainstEveryTakenCopyNotJustTheFirst()
    {
        var takenA = V(Spawner.X + 45f, 0.5f, Spawner.Z);
        var takenB = V(Spawner.X + 45f, 0.5f, Spawner.Z + 30f);
        var closeToB = V(Spawner.X + 45f, 0.5f, Spawner.Z + 34f);
        var balanced = V(Spawner.X + 75f, 0.5f, Spawner.Z + 15f);

        Assert.True(BossSpawnRedirect.PickSpot(new[] { closeToB, balanced }, new[] { takenA, takenB }, out var picked));
        Assert.Equal(balanced, picked);
    }

    [Fact]
    public void PickSpot_FirstCopyTakesTheFirstUsableCandidate()
    {
        var a = V(Spawner.X + 40f, 0.5f, Spawner.Z);
        var b = V(Spawner.X - 40f, 0.5f, Spawner.Z);

        Assert.True(BossSpawnRedirect.PickSpot(new[] { a, b }, Array.Empty<Vec3>(), out var picked));
        Assert.Equal(a, picked);
    }

    [Fact]
    public void PickSpot_FailsWhenNothingIsUsable()
    {
        Assert.False(BossSpawnRedirect.PickSpot(Array.Empty<Vec3>(), Array.Empty<Vec3>(), out _));
    }

    [Fact]
    public void FloorPlacement_KeepsTheGamesOwnLift()
    {
        // The game lifts a spawned enemy well above the position it was asked for, so the boss's feet, not its pivot,
        // have to land on the floor.
        var placed = BossSpawnRedirect.FloorPlacement(V(140f, -4.933f, 40f), V(176f, 15.6f, 31f), V(176f, 27.5f, 31f));

        Assert.Equal(140f, placed.X);
        Assert.Equal(6.967f, placed.Y, 3);
        Assert.Equal(40f, placed.Z);
    }
}
