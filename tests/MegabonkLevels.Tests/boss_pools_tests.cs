using MegabonkLevels;

namespace MegabonkLevels.Tests;

public class BossPoolsTests
{
    private static LevelFile Level() => LevelFileSerializer.Deserialize("""{"schemaVersion":3,"map":1,"seed":20261007,"packs":{},"edits":[]}""");

    [Theory]
    [InlineData(4, BossPoolKind.Boss)]
    [InlineData(32, BossPoolKind.Boss)]
    [InlineData(2 | 4, BossPoolKind.Boss)]
    [InlineData(2, BossPoolKind.Miniboss)]
    [InlineData(16, BossPoolKind.Miniboss)]
    [InlineData(2 | 16, BossPoolKind.Miniboss)]
    [InlineData(0, BossPoolKind.None)]
    [InlineData(1, BossPoolKind.None)]
    [InlineData(8, BossPoolKind.None)]
    public void FlagsDecideWhichPoolASpawnDrawsFrom(int flags, BossPoolKind expected) =>
        Assert.Equal(expected, BossPools.Classify(flags));

    [Fact]
    public void PickDrawsEveryNameAndNothingFromAnEmptyPool()
    {
        var pool = new[] { "Ent1", "Pharaoh1", "Bandit" };
        var seen = new HashSet<string>();
        for (var seed = 0; seed < 200; seed++) seen.Add(BossPools.Pick(pool, new Random(seed)));
        Assert.Equal(pool.ToHashSet(), seen);
        Assert.Null(BossPools.Pick(null, new Random(1)));
        Assert.Null(BossPools.Pick(Array.Empty<string>(), new Random(1)));
    }

    [Fact]
    public void EachDrawBurnsItsNameSoNoEnemyAppearsTwiceInARun()
    {
        var pool = new[] { "CalciumDad", "MinibossPig", "Ghostham" };
        var used = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var random = new Random(7);
        var drawn = new List<string>();
        for (var i = 0; i < pool.Length; i++) drawn.Add(BossPools.Pick(pool, random, used));
        Assert.Equal(pool.OrderBy(name => name), drawn.OrderBy(name => name));
        Assert.Null(BossPools.Pick(pool, random, used));
        Assert.Equal(pool.Length, used.Count);
    }

    [Fact]
    public void BurningIgnoresCaseAndANameUsedElsewhereIsSkipped()
    {
        var used = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "calciumdad" };
        for (var seed = 0; seed < 50; seed++)
        {
            var scratch = new HashSet<string>(used, StringComparer.OrdinalIgnoreCase);
            Assert.Equal("Ghostham", BossPools.Pick(new[] { "CalciumDad", "Ghostham" }, new Random(seed), scratch));
        }
    }

    [Fact]
    public void PoolsRoundTripAndSurviveSaveCopyAndHistory()
    {
        var original = Level();
        var changed = LevelSettings.Change(LevelSettings.Change(original, "bossPool", """["Ent1","Pharaoh2"]"""), "minibossPool", """["MinibossPig"]""");
        Assert.NotEqual(original, changed);
        Assert.Equal(new[] { "Ent1", "Pharaoh2" }, changed.BossPool);
        Assert.Equal(new[] { "MinibossPig" }, changed.MinibossPool);
        Assert.Equal(changed, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(changed)));
        Assert.Equal(changed, LevelSettings.CopyTo(changed, original));
        var plain = LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(original));
        Assert.Null(plain.BossPool);
        Assert.Null(plain.MinibossPool);

        var history = new LevelSettingsHistory(original);
        history.Apply("bossPool", """["Ent1"]""", hasEdits: true);
        Assert.True(history.Dirty);
        Assert.True(history.Undo());
        Assert.Equal(original, history.Current);
    }

    [Theory]
    [InlineData("bossPool", """[""]""")]
    [InlineData("bossPool", """["  "]""")]
    [InlineData("minibossPool", """[""]""")]
    public void BlankNamesAreRejected(string field, string json) =>
        Assert.ThrowsAny<ArgumentException>(() => LevelSettings.Change(Level(), field, json));
}
