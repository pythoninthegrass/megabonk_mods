using MegabonkLevels;

namespace MegabonkLevels.Tests;

public class ShrineGuaranteesTests
{
    private static LevelFile Level() => LevelFileSerializer.Deserialize("""{"schemaVersion":3,"map":1,"seed":20261007,"packs":{},"edits":[]}""");

    private const string Json = """[{"kind":"moai","minX":-100,"maxX":100,"minZ":-300,"maxZ":-100,"outside":true},{"kind":"shadyGuy","minX":-100,"maxX":100,"minZ":-300,"maxZ":-100,"outside":true}]""";

    private static readonly ShrineGuarantee OutsideMeadow = new("moai", -100, 100, -300, -100, true);
    private static readonly Vector3Data InMeadow = new(0, 0, -200);
    private static readonly Vector3Data OnHill = new(0, 0, 0);

    [Fact]
    public void AnOutsideGuaranteeIsSatisfiedOnlyByItsKindBeyondTheRectangle()
    {
        Assert.True(ShrineGuarantees.Satisfies(OutsideMeadow, ExtraShrineKind.Moai, OnHill));
        Assert.False(ShrineGuarantees.Satisfies(OutsideMeadow, ExtraShrineKind.Moai, InMeadow));
        Assert.False(ShrineGuarantees.Satisfies(OutsideMeadow, ExtraShrineKind.ShadyGuy, OnHill));
    }

    [Fact]
    public void AnInsideGuaranteeIsSatisfiedWithinTheRectangleEdgesIncluded()
    {
        var inside = OutsideMeadow with { Outside = false };
        Assert.True(ShrineGuarantees.Satisfies(inside, ExtraShrineKind.Moai, new Vector3Data(100, 0, -100)));
        Assert.False(ShrineGuarantees.Satisfies(inside, ExtraShrineKind.Moai, new Vector3Data(100.5f, 0, -100)));
    }

    [Fact]
    public void UnmetListsGuaranteesNoPlacedShrineSatisfies()
    {
        var guarantees = LevelSettings.Change(Level(), "shrineGuarantees", Json).ShrineGuarantees;
        var placed = new[] { (ExtraShrineKind.Moai, InMeadow), (ExtraShrineKind.ShadyGuy, OnHill) };
        Assert.Equal(new[] { guarantees[0] }, ShrineGuarantees.Unmet(guarantees, placed));
        Assert.Empty(ShrineGuarantees.Unmet(guarantees, placed.Append((ExtraShrineKind.Moai, OnHill)).ToList()));
        Assert.Equal(guarantees, ShrineGuarantees.Unmet(guarantees, Array.Empty<(ExtraShrineKind, Vector3Data)>()));
        Assert.Empty(ShrineGuarantees.Unmet(null, placed));
    }

    [Fact]
    public void CandidatesAreTheSpotsThatSatisfyTheFirstUnmetGuaranteeOfTheKind()
    {
        var guarantees = new[] { OutsideMeadow, OutsideMeadow with { Kind = "shadyGuy" } };
        var spots = new[] { InMeadow, OnHill, new Vector3Data(300, 0, 300) };
        Assert.Equal(new[] { 1, 2 }, ShrineGuarantees.CandidateIndexes(guarantees, ExtraShrineKind.Moai, spots, Array.Empty<(ExtraShrineKind, Vector3Data)>()));
        Assert.Null(ShrineGuarantees.CandidateIndexes(guarantees, ExtraShrineKind.Charge, spots, Array.Empty<(ExtraShrineKind, Vector3Data)>()));
        Assert.Null(ShrineGuarantees.CandidateIndexes(guarantees, ExtraShrineKind.Moai, spots, new[] { (ExtraShrineKind.Moai, OnHill) }));
    }

    [Fact]
    public void GuaranteesRoundTripAndSurviveSaveCopyAndHistory()
    {
        var original = Level();
        var changed = LevelSettings.Change(original, "shrineGuarantees", Json);
        Assert.NotEqual(original, changed);
        Assert.Equal(2, changed.ShrineGuarantees.Count);
        Assert.Equal(changed, LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(changed)));
        Assert.Equal(changed, LevelSettings.CopyTo(changed, original));
        Assert.Null(LevelFileSerializer.Deserialize(LevelFileSerializer.Serialize(original)).ShrineGuarantees);
        Assert.Equal(original, LevelSettings.Change(changed, "shrineGuarantees", "null"));
    }

    [Theory]
    [InlineData("""[{"kind":"nope","minX":0,"maxX":1,"minZ":0,"maxZ":1}]""")]
    [InlineData("""[{"kind":"moai","minX":2,"maxX":1,"minZ":0,"maxZ":1}]""")]
    public void InvalidGuaranteesAreRejected(string json)
    {
        Assert.Throws<ArgumentException>(() => LevelSettings.Change(Level(), "shrineGuarantees", json));
    }
}
