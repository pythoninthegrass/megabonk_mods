namespace MegabonkLevels.Tests;

public class RailWallEndTests
{
    [Theory]
    [InlineData(0f)]
    [InlineData(0.5f)]
    [InlineData(RailWallEnd.MinSpeed - 0.1f)]
    public void IsMoving_IsFalseBelowTheGrindSpeed(float speed)
    {
        Assert.False(RailWallEnd.IsMoving(speed));
    }

    [Theory]
    [InlineData(0f, 0f)]
    [InlineData(3f, 3f)]
    [InlineData(RailWallEnd.MaxDismountSpeed, RailWallEnd.MaxDismountSpeed)]
    [InlineData(20f, RailWallEnd.MaxDismountSpeed)]
    [InlineData(60f, RailWallEnd.MaxDismountSpeed)]
    public void DismountSpeed_CapsAGrindButLeavesASlowPlayerAlone(float speed, float expected)
    {
        Assert.Equal(expected, RailWallEnd.DismountSpeed(speed));
    }

    [Theory]
    [InlineData(RailWallEnd.MinSpeed)]
    [InlineData(12f)]
    [InlineData(40f)]
    public void IsMoving_IsTrueAtOrAboveTheGrindSpeed(float speed)
    {
        Assert.True(RailWallEnd.IsMoving(speed));
    }

    [Theory]
    [InlineData(0f, 1f)]
    [InlineData(0.1f, 1f)]
    [InlineData(RailWallEnd.WallNormalMaxY, 1f)]
    [InlineData(-0.05f, 1f)]
    public void IsWall_IsTrueForANearVerticalFaceAimedAtThePlayer(float normalY, float againstTravel)
    {
        Assert.True(RailWallEnd.IsWall(normalY, againstTravel));
    }

    [Theory]
    // A floor, a 45 degree ramp face (normal y 0.71) and the half pipe above it are surfaces to ride, not to detach for.
    [InlineData(1f, 1f)]
    [InlineData(0.71f, 0.71f)]
    [InlineData(0.5f, 1f)]
    // A ceiling, and a wall seen edge on rather than head on.
    [InlineData(-1f, 1f)]
    [InlineData(0f, RailWallEnd.FacingDotMin - 0.1f)]
    [InlineData(0f, 0f)]
    public void IsWall_IsFalseForAnythingElse(float normalY, float againstTravel)
    {
        Assert.False(RailWallEnd.IsWall(normalY, againstTravel));
    }

    [Fact]
    public void ShouldDetach_IsTrueForAWallWithinTheDetachDistance()
    {
        Assert.True(RailWallEnd.ShouldDetach(RailWallEnd.DetachDistance - 1f, false));
    }

    [Fact]
    public void ShouldDetach_IsTrueExactlyAtTheDetachDistance()
    {
        Assert.True(RailWallEnd.ShouldDetach(RailWallEnd.DetachDistance, false));
    }

    [Fact]
    public void ShouldDetach_IsFalseBeyondTheDetachDistance()
    {
        Assert.False(RailWallEnd.ShouldDetach(RailWallEnd.DetachDistance + 0.1f, false));
    }

    [Theory]
    [InlineData(-1f)]
    [InlineData(-5f)]
    public void ShouldDetach_IsFalseWithNoWallAhead(float wallDistance)
    {
        Assert.False(RailWallEnd.ShouldDetach(wallDistance, false));
    }

    [Fact]
    public void ShouldDetach_IsFalseWhenAnotherRailCanTakeTheGrind()
    {
        Assert.False(RailWallEnd.ShouldDetach(1f, true));
    }

    [Fact]
    public void Dismount_HopsOffTheLipAndCutsTheGrindSpeed()
    {
        // Without the hop the player slides along the coping and the game catches the same rail again several times,
        // and a cap above the observed grind speed of 19.5 would never bite.
        Assert.True(RailWallEnd.DismountHop > 0f);
        Assert.True(RailWallEnd.MaxDismountSpeed < 19.5f);
    }
}
