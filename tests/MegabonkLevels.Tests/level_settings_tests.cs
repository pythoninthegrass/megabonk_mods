using MegabonkLevels;

namespace MegabonkLevels.Tests;

public class LevelSettingsTests
{
    private static LevelFile Level() => LevelFileSerializer.Deserialize("""{"schemaVersion":3,"map":1,"seed":20261007,"packs":{},"edits":[],"playerStart":[109,38,-116],"bossSpawnPosition":[170,-4.933,20],"killFloorY":-35,"maxSlopeAngle":88,"grindRequiresSlide":true}""");

    [Fact]
    public void MarkersAndSettingsRoundTripWithoutMovingEachOther()
    {
        var original = Level();
        var changed = LevelSettings.Change(original, "playerStart", "[100,40,-100]");
        changed = LevelSettings.Change(changed, "killFloorY", "-40");
        changed = LevelSettings.Change(changed, "grindRequiresSlide", "false");
        changed = LevelSettings.Change(changed, "title", "My Warehouse");
        Assert.Equal(original.BossSpawnPosition, changed.BossSpawnPosition);
        Assert.Equal(new float[] { 100, 40, -100 }, changed.PlayerStart);
        Assert.Equal(-40f, changed.KillFloorY);
        Assert.False(changed.GrindRequiresSlide);
        Assert.Equal("My Warehouse", changed.Title);
        Assert.Equal(changed, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(changed)));
    }

    [Theory]
    [InlineData("playerStart", "[1,2]")]
    [InlineData("bossSpawnPosition", "[1,2,3,4]")]
    [InlineData("maxSlopeAngle", "90")]
    [InlineData("maxSlopeAngle", "-1")]
    [InlineData("killFloorY", "NaN")]
    [InlineData("grindRequiresSlide", "yes")]
    [InlineData("music", "bad:path")]
    [InlineData("allowedCharacters", "[\"unknown\"]")]
    [InlineData("edits", "[]")]
    public void InvalidEditsDoNotMutateTheSource(string field, string text)
    {
        var level = Level();
        Assert.ThrowsAny<ArgumentException>(() => LevelSettings.Change(level, field, text));
        Assert.Equal(Level(), level);
    }

    [Fact]
    public void GenerationCannotChangeUnderSeedSpecificEdits()
    {
        var level = Level() with { Edits = new[] { new RemoveTile(0, 0).ToEditOp() } };
        Assert.Throws<ArgumentException>(() => LevelSettings.Change(level, "seed", "12"));
        Assert.Equal(12, LevelSettings.Change(Level(), "seed", "12").Seed);
    }

    [Fact]
    public void HistoryTracksSavedStateAcrossUndoRedoAndBranches()
    {
        var history = new LevelSettingsHistory(Level());
        Assert.False(history.Dirty);
        history.Apply("killFloorY", "-40");
        Assert.True(history.Dirty);
        history.MarkSaved();
        Assert.False(history.Dirty);
        Assert.True(history.Undo());
        Assert.True(history.Dirty);
        Assert.True(history.Redo());
        Assert.False(history.Dirty);
        history.Undo();
        history.Apply("killFloorY", "-42");
        Assert.False(history.CanRedo);
        Assert.True(history.Dirty);
    }
}
