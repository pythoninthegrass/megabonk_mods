using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// Mirrors the eMap values of the game's MapData assets, not the Il2Cpp EMap enum (it lists Hell as 4, the MapHell asset holds 64).
public enum EMap
{
    None = 0,
    Forest = 1,
    Desert = 2,
    Graveyard = 8,
    Dungeon = 16,
    Hell = 64,
}

public readonly record struct EditOp(string OpType, string Target, string Payload);

// Seed is the Tiles-map debugSeed (see docs/map-generation-determinism.md) — MapGenerationController.mapSeed
// is disconnected from generation and must never be stored here.
public readonly record struct LevelFile(
    int SchemaVersion,
    string GameBuildId,
    EMap Map,
    int StageIndex,
    int Tier,
    int Seed,
    IReadOnlyDictionary<string, string> Packs,
    IReadOnlyList<EditOp> Edits,
    bool NoGrass = false,
    IReadOnlyList<float> PlayerStart = null,
    float? MaxSlopeAngle = null)
{
    public const int CurrentSchemaVersion = 2;

    public bool Equals(LevelFile other) =>
        SchemaVersion == other.SchemaVersion
        && GameBuildId == other.GameBuildId
        && Map == other.Map
        && StageIndex == other.StageIndex
        && Tier == other.Tier
        && Seed == other.Seed
        && PacksDictionaryEquals(Packs, other.Packs)
        && NoGrass == other.NoGrass
        && PlayerStartEquals(PlayerStart, other.PlayerStart)
        && MaxSlopeAngle == other.MaxSlopeAngle
        && Edits.SequenceEqual(other.Edits);

    public override int GetHashCode() =>
        HashCode.Combine(SchemaVersion, GameBuildId, Map, StageIndex, Tier, Seed, Packs.Count, Edits.Count);

    private static bool PlayerStartEquals(IReadOnlyList<float> a, IReadOnlyList<float> b) =>
        a == null ? b == null : b != null && a.SequenceEqual(b);

    private static bool PacksDictionaryEquals(IReadOnlyDictionary<string, string> a, IReadOnlyDictionary<string, string> b) =>
        a.Count == b.Count && a.All(kvp => b.TryGetValue(kvp.Key, out var value) && value == kvp.Value);
}
