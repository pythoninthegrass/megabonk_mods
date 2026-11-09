namespace MegabonkLevels.Tests;

public class BossEventLogTests
{
    [Fact]
    public void Format_NamesTheEventAlone()
    {
        Assert.Equal("BossEvents: A_BossSpawned", BossEventLog.Format("A_BossSpawned"));
    }

    [Fact]
    public void Format_AppendsTheValueWhenTheEventCarriesOne()
    {
        Assert.Equal("BossEvents: A_NumBossesDefeated 3", BossEventLog.Format("A_NumBossesDefeated", 3));
        Assert.Equal("BossEvents: A_BossDefeated True", BossEventLog.Format("A_BossDefeated", true));
    }
}
