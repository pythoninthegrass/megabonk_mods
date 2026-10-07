using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// Mirrors the game's EMap flags enum (.tools/il2cpp_dump/dump.cs) by value, not by reference to the Il2Cpp type.
public enum EMap
{
    None = 0,
    Forest = 1,
    Desert = 2,
    Hell = 4,
    Graveyard = 8,
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
    IReadOnlyList<EditOp> Edits)
{
    public const int CurrentSchemaVersion = 1;

    public bool Equals(LevelFile other) =>
        SchemaVersion == other.SchemaVersion
        && GameBuildId == other.GameBuildId
        && Map == other.Map
        && StageIndex == other.StageIndex
        && Tier == other.Tier
        && Seed == other.Seed
        && Edits.SequenceEqual(other.Edits);

    public override int GetHashCode() =>
        HashCode.Combine(SchemaVersion, GameBuildId, Map, StageIndex, Tier, Seed, Edits.Count);
}
