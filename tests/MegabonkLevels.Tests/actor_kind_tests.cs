namespace MegabonkLevels.Tests;

public class ActorKindTests
{
    private const int None = 0;
    private const int Elite = 1;
    private const int Boss = 2;
    private const int StageBoss = 4;
    private const int Challenge = 8;
    private const int SummonerMiniboss = 16;
    private const int FinalBoss = 32;

    [Fact]
    public void Of_NoFlags_IsEnemy()
    {
        Assert.Equal(ActorKind.Enemy, ActorKinds.Of(None));
    }

    [Fact]
    public void Of_EliteBit_IsElite()
    {
        Assert.Equal(ActorKind.Elite, ActorKinds.Of(Elite));
    }

    [Fact]
    public void Of_BossBit_IsMiniboss()
    {
        Assert.Equal(ActorKind.Miniboss, ActorKinds.Of(Boss));
    }

    [Fact]
    public void Of_SummonerMinibossBit_IsMiniboss()
    {
        Assert.Equal(ActorKind.Miniboss, ActorKinds.Of(SummonerMiniboss));
    }

    [Fact]
    public void Of_StageBossBit_IsStageBoss()
    {
        Assert.Equal(ActorKind.StageBoss, ActorKinds.Of(StageBoss));
    }

    [Fact]
    public void Of_FinalBossBit_IsFinalBoss()
    {
        Assert.Equal(ActorKind.FinalBoss, ActorKinds.Of(FinalBoss));
    }

    [Fact]
    public void Of_ChallengeAlone_IsEnemy()
    {
        Assert.Equal(ActorKind.Enemy, ActorKinds.Of(Challenge));
    }

    [Fact]
    public void Of_EliteAndBoss_IsMiniboss()
    {
        Assert.Equal(ActorKind.Miniboss, ActorKinds.Of(Elite | Boss));
    }

    [Fact]
    public void Of_StageBossAndBoss_IsStageBoss()
    {
        Assert.Equal(ActorKind.StageBoss, ActorKinds.Of(StageBoss | Boss));
    }

    [Fact]
    public void Of_FinalBossAndStageBossAndBoss_IsFinalBoss()
    {
        Assert.Equal(ActorKind.FinalBoss, ActorKinds.Of(FinalBoss | StageBoss | Boss));
    }

    [Fact]
    public void Of_EliteAndChallenge_IsElite()
    {
        Assert.Equal(ActorKind.Elite, ActorKinds.Of(Elite | Challenge));
    }

    [Theory]
    [InlineData(ActorKind.FinalBoss, "final boss:")]
    [InlineData(ActorKind.StageBoss, "boss:")]
    [InlineData(ActorKind.Miniboss, "miniboss:")]
    [InlineData(ActorKind.Elite, "elite:")]
    [InlineData(ActorKind.Enemy, "enemy:")]
    public void Label_ReturnsTheExpectedWord(ActorKind kind, string expected)
    {
        Assert.Equal(expected, ActorKinds.Label(kind));
    }

    [Theory]
    [InlineData(ActorKind.FinalBoss, true)]
    [InlineData(ActorKind.StageBoss, true)]
    [InlineData(ActorKind.Miniboss, true)]
    [InlineData(ActorKind.Elite, false)]
    [InlineData(ActorKind.Enemy, false)]
    public void IsBossTier_OnlyFinalBossStageBossAndMiniboss(ActorKind kind, bool expected)
    {
        Assert.Equal(expected, ActorKinds.IsBossTier(kind));
    }
}
