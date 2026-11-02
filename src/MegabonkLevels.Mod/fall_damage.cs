using System;
using System.Text.Json.Nodes;
using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Player;
using Il2CppAssets.Scripts.Inventory__Items__Pickups;
using Il2CppAssets.Scripts.Inventory__Items__Pickups.Stats;
using Il2CppAssets.Scripts.Menu.Shop;
using UnityEngine;

namespace MegabonkLevels;

// Reads what decides fall damage in the live run: PlayerHealth's thresholds, the stats the landing damage is built
// from, and the stat modifiers each playable character brings. See "Fall damage" in docs/development.md.
public static class FallDamage
{
    private static readonly (EStat Stat, string Name)[] TrackedStats =
    {
        (EStat.FallDamageReduction, "fallDamageReduction"),
        (EStat.MaxHealth, "maxHealth"),
        (EStat.DamageReductionMultiplier, "damageReduction"),
    };

    public static JsonObject Read()
    {
        var player = MyPlayer.Instance ?? throw new InvalidOperationException("fall-damage: no player in the scene");
        var inventory = player.inventory ?? throw new InvalidOperationException("fall-damage: no player inventory in the scene");
        var health = inventory.playerHealth ?? throw new InvalidOperationException("fall-damage: no player health in the scene");
        var movement = player.playerMovement;
        var velocity = movement?.rb?.velocity;

        return new JsonObject
        {
            ["character"] = CharacterOverride.DisplayName((int)player.character),
            ["characterId"] = (int)player.character,
            ["hp"] = health.hp,
            ["maxHp"] = health.maxHp,
            ["shield"] = health.shield,
            ["overheal"] = health.overheal,
            ["minFallDamageSpeed"] = health.minFallDamageSpeed,
            ["maxFallDamageSpeed"] = health.maxFallDamageSpeed,
            ["fallDamageTakenAtTime"] = health.fallDamageTakenAtTime,
            ["time"] = Time.time,
            ["stats"] = Stats(inventory.playerStats),
            ["modifiers"] = Modifiers(inventory.characterData),
            ["grounded"] = movement?.grounded,
            ["fallSpeed"] = movement?.fallSpeed,
            ["velocityY"] = velocity.HasValue ? JsonValue.Create(velocity.Value.y) : null,
            ["characters"] = Characters(),
            ["fallDamageOverride"] = Override(),
        };
    }

    // What FallDamagePatch would do to the next landing, so a run can be checked before the drop that proves it.
    private static JsonObject Override()
    {
        return new JsonObject
        {
            ["levelNames"] = LiveEditPatch.FallDamageCharacter,
            ["referenceId"] = FallDamagePatch.ReferenceCharacterId is { } id ? JsonValue.Create(id) : null,
            ["activeCharacterId"] = FallDamagePatch.ActiveCharacterId,
            ["active"] = FallDamagePatch.IsActive,
            ["referenceValue"] = Number(FallDamagePatch.ReferenceValue()),
            ["swaps"] = FallDamagePatch.SwapCount,
            ["lastPlayerValue"] = Number(FallDamagePatch.LastPlayerValue),
            ["lastReferenceValue"] = Number(FallDamagePatch.LastReferenceValue),
            ["lastReadBack"] = Number(FallDamagePatch.LastReadBack),
        };
    }

    private static JsonNode Number(float value) => float.IsNaN(value) ? null : JsonValue.Create(value);

    private static JsonObject Stats(PlayerStatsNew stats)
    {
        var node = new JsonObject();
        if (stats == null)
        {
            return node;
        }

        foreach (var (stat, name) in TrackedStats)
        {
            node[name] = stats.GetStat(stat);
        }

        return node;
    }

    // The character asset's own modifiers, the per-character part of the stat totals.
    private static JsonArray Modifiers(CharacterData data)
    {
        var rows = new JsonArray();
        foreach (var modifier in data?.statModifiers ?? new Il2CppSystem.Collections.Generic.List<StatModifier>())
        {
            rows.Add(new JsonObject
            {
                ["stat"] = (int)modifier.stat,
                ["statName"] = modifier.stat.ToString(),
                ["modifyType"] = (int)modifier.modifyType,
                ["modification"] = modifier.modification,
            });
        }

        return rows;
    }

    // Both Warehouse-playable characters straight from DataManager, so one read compares them without a second run.
    private static JsonArray Characters()
    {
        var rows = new JsonArray();
        var data = DataManager.Instance;
        if (data == null)
        {
            return rows;
        }

        foreach (var id in new[] { CharacterOverride.CalciumId, CharacterOverride.TonyMcZoomId })
        {
            var character = data.GetCharacterData((ECharacter)id);
            rows.Add(new JsonObject
            {
                ["id"] = id,
                ["name"] = CharacterOverride.DisplayName(id),
                ["modifiers"] = Modifiers(character),
            });
        }

        return rows;
    }
}
