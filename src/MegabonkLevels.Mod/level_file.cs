using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Serialization;

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
    float? MaxSlopeAngle = null,
    string Music = null,
    string Title = null,
    string Description = null,
    IReadOnlyList<string> AllowedCharacters = null,
    string MapDescription = null,
    float? KillFloorY = null,
    IReadOnlyList<float> BossSpawnPosition = null,
    bool GrindRequiresSlide = false,
    // Character whose fall damage a landing on this level is scored with, or null to leave each character's own.
    string FallDamageCharacter = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] IReadOnlyDictionary<string, string> PackKitVersions = null,
    bool RandomizeShadyGuy = false,
    bool RandomizeChests = false,
    bool RandomizeMoai = false)
{
    public const int CurrentSchemaVersion = 3;

    public bool Equals(LevelFile other) =>
        SchemaVersion == other.SchemaVersion
        && GameBuildId == other.GameBuildId
        && Map == other.Map
        && StageIndex == other.StageIndex
        && Tier == other.Tier
        && Seed == other.Seed
        && PacksDictionaryEquals(Packs, other.Packs)
        && (PackKitVersions == null ? other.PackKitVersions == null : other.PackKitVersions != null && PacksDictionaryEquals(PackKitVersions, other.PackKitVersions))
        && NoGrass == other.NoGrass
        && ListEquals(PlayerStart, other.PlayerStart)
        && MaxSlopeAngle == other.MaxSlopeAngle
        && KillFloorY == other.KillFloorY
        && GrindRequiresSlide == other.GrindRequiresSlide
        && FallDamageCharacter == other.FallDamageCharacter
        && RandomizeShadyGuy == other.RandomizeShadyGuy
        && RandomizeChests == other.RandomizeChests
        && RandomizeMoai == other.RandomizeMoai
        && ListEquals(BossSpawnPosition, other.BossSpawnPosition)
        && Music == other.Music
        && Title == other.Title
        && Description == other.Description
        && MapDescription == other.MapDescription
        && ListEquals(AllowedCharacters, other.AllowedCharacters)
        && Edits.SequenceEqual(other.Edits);

    public override int GetHashCode() =>
        HashCode.Combine(SchemaVersion, GameBuildId, Map, StageIndex, Tier, Seed, Packs.Count, Edits.Count);

    private static bool ListEquals<T>(IReadOnlyList<T> a, IReadOnlyList<T> b) =>
        a == null ? b == null : b != null && a.SequenceEqual(b);

    private static bool PacksDictionaryEquals(IReadOnlyDictionary<string, string> a, IReadOnlyDictionary<string, string> b) =>
        a.Count == b.Count && a.All(kvp => b.TryGetValue(kvp.Key, out var value) && value == kvp.Value);
}
