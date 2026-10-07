namespace MegabonkLevels.Tests;

public class GenerationHashTests
{
    private static SpawnRecord Tile(string name, float x, float y, float z) =>
        new(name, x, y, z, 0f, 0f, 0f, 1f, 1f, 1f, 1f);

    [Fact]
    public void Compute_SameRecordsDifferentOrder_ProducesSameHash()
    {
        var a = new[] { Tile("FlatTile", 0f, 0f, 0f), Tile("WallFlat", 1f, 0f, 0f) };
        var b = new[] { Tile("WallFlat", 1f, 0f, 0f), Tile("FlatTile", 0f, 0f, 0f) };

        Assert.Equal(GenerationHash.Compute(a), GenerationHash.Compute(b));
    }

    [Fact]
    public void Compute_DifferingPosition_ProducesDifferentHash()
    {
        var a = new[] { Tile("FlatTile", 0f, 0f, 0f) };
        var b = new[] { Tile("FlatTile", 0f, 0f, 1f) };

        Assert.NotEqual(GenerationHash.Compute(a), GenerationHash.Compute(b));
    }

    [Fact]
    public void Compute_DifferingName_ProducesDifferentHash()
    {
        var a = new[] { Tile("FlatTile", 0f, 0f, 0f) };
        var b = new[] { Tile("SlopeTile", 0f, 0f, 0f) };

        Assert.NotEqual(GenerationHash.Compute(a), GenerationHash.Compute(b));
    }

    [Fact]
    public void Compute_EmptySequence_ProducesStableHash()
    {
        Assert.Equal(GenerationHash.Compute([]), GenerationHash.Compute(System.Array.Empty<SpawnRecord>()));
    }

    [Fact]
    public void Compute_IsPureSha256HexOfCanonicalForm()
    {
        var records = new[] { Tile("FlatTile", 0f, 0f, 0f) };

        var hash = GenerationHash.Compute(records);

        Assert.Equal(64, hash.Length);
        Assert.Equal(hash, hash.ToUpperInvariant());
    }
}
