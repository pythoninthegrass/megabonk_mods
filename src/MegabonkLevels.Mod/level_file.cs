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
    bool RandomizeMoai = false,
    int ExtraShrines = 0,
    IReadOnlyList<string> ExtraShrineKinds = null,
    // Upper end of a per-run random shrine count, or null for exactly ExtraShrines.
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] int? ExtraShrinesMax = null,
    // World positions [x, y, z] extra shrines are placed at, instead of probing the generated tiles; each run picks some of them at random. Height only needs to be near the floor.
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] IReadOnlyList<IReadOnlyList<float>> ShrineSpots = null,
    // Shrine kinds placed once each every run, ahead of the random extras; a repeated name is a minimum of that many.
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] IReadOnlyList<string> GuaranteedShrineKinds = null,
    // [min, max] added to chest loot luck, one value drawn per run, or null for the game's own odds.
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] IReadOnlyList<float> ChestLuckRange = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string Baseline = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] LevelGrid? Grid = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] SpawnPoint? Spawn = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] SpawnPoint? BossSpawner = null,
    // From-scratch only: keeps the boss spawn redirect on for a level whose boss spawner stands in a closed room.
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)] bool BossRedirect = false)
{
    public const int CurrentSchemaVersion = 4;

    public const string GeneratedBaseline = "generated";
    public const string NoBaseline = "none";

    public bool IsFromScratch => Baseline == NoBaseline;

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
        && ExtraShrines == other.ExtraShrines
        && ListEquals(ExtraShrineKinds, other.ExtraShrineKinds)
        && ExtraShrinesMax == other.ExtraShrinesMax
        && (ShrineSpots == null ? other.ShrineSpots == null : other.ShrineSpots != null && ShrineSpots.Count == other.ShrineSpots.Count && ShrineSpots.Zip(other.ShrineSpots).All(pair => ListEquals(pair.First, pair.Second)))
        && ListEquals(GuaranteedShrineKinds, other.GuaranteedShrineKinds)
        && ListEquals(ChestLuckRange, other.ChestLuckRange)
        && ListEquals(BossSpawnPosition, other.BossSpawnPosition)
        && Music == other.Music
        && Title == other.Title
        && Description == other.Description
        && MapDescription == other.MapDescription
        && ListEquals(AllowedCharacters, other.AllowedCharacters)
        && Baseline == other.Baseline
        && Equals(Grid, other.Grid)
        && Equals(Spawn, other.Spawn)
        && Equals(BossSpawner, other.BossSpawner)
        && BossRedirect == other.BossRedirect
        && Edits.SequenceEqual(other.Edits);

    public override int GetHashCode() =>
        HashCode.Combine(SchemaVersion, GameBuildId, Map, StageIndex, Tier, Seed, Packs.Count, Edits.Count);

    private static bool ListEquals<T>(IReadOnlyList<T> a, IReadOnlyList<T> b) =>
        a == null ? b == null : b != null && a.SequenceEqual(b);

    private static bool PacksDictionaryEquals(IReadOnlyDictionary<string, string> a, IReadOnlyDictionary<string, string> b) =>
        a.Count == b.Count && a.All(kvp => b.TryGetValue(kvp.Key, out var value) && value == kvp.Value);
}
