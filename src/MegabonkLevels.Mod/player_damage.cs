using System;
using System.Linq;
using System.Text.Json.Nodes;
using HarmonyLib;
using Il2CppAssets.Scripts.Actors;
using Il2CppAssets.Scripts.Actors.Player;
using Il2CppAssets.Scripts.Inventory__Items__Pickups;
using UnityEngine;

namespace MegabonkLevels;

public static class PlayerDamage
{
    private const string Source = "Enemy";
    private static PlayerHealth _target;
    private static bool _nonlethal;
    private static bool _clamped;
    private static bool _stopped;
    private static float? _effectiveDamage;
    private static int _damageEvents;

    public static JsonObject Apply(DamageArgs args)
    {
        if (args == null || args.Amount is < 1 or > 99)
        {
            throw new ArgumentException("damage amount must be an integer from 1 to 99");
        }

        var health = MyPlayer.Instance?.inventory?.playerHealth
            ?? throw new InvalidOperationException("damage: no player health in the scene");
        if (health.hp <= 0 || health.IsDead())
        {
            throw new InvalidOperationException("damage: player is dead");
        }

        if (args.Nonlethal && HarmonyLib.Harmony.GetPatchInfo(AccessTools.Method(typeof(PlayerHealth), nameof(PlayerHealth.CheckStopDamage)))
            ?.Postfixes.Any(patch => patch.PatchMethod.DeclaringType == typeof(NonlethalGuard)) != true)
        {
            throw new InvalidOperationException("damage: nonlethal guard is not installed");
        }

        var before = Snapshot(health);
        var cooldown = health.DamageCooldown();
        var canTakeDamage = health.CanTakeDamage();
        _target = health;
        _nonlethal = args.Nonlethal;
        _clamped = false;
        _stopped = false;
        _effectiveDamage = null;
        _damageEvents = 0;
        var observer = (Il2CppSystem.Action<PlayerHealth, DamageContainer, bool>)((player, dc, _) =>
        {
            if (IsOurs(player, dc))
            {
                _damageEvents++;
            }
        });
        PlayerHealth.A_TakeDamage += observer;
        try
        {
            health.DamagePlayerExternal(args.Amount, 0f, Vector3.zero, PlayerDamagePolicy.IgnoreShield, Source, 0, 0, null);
        }
        finally
        {
            _target = null;
            PlayerHealth.A_TakeDamage -= observer;
        }

        var after = Snapshot(health);
        var hpDamage = before["hp"].GetValue<int>() - health.hp;
        var shieldDamage = before["shield"].GetValue<float>() - health.shield;
        var overhealDamage = before["overheal"].GetValue<float>() - health.overheal;
        var actual = Math.Max(0, hpDamage) + Math.Max(0f, shieldDamage) + Math.Max(0f, overhealDamage);
        var blocked = _damageEvents == 0;
        var reason = cooldown ? "damage-cooldown" : !canTakeDamage ? "cannot-take-damage"
            : _clamped && _effectiveDamage == 0f ? "nonlethal-floor" : _stopped ? "game-damage-check"
            : blocked ? "game-gate" : null;
        return new JsonObject
        {
            ["requestedDamage"] = args.Amount,
            ["submittedDamage"] = args.Amount,
            ["effectiveDamage"] = _effectiveDamage,
            ["actualDamage"] = actual,
            ["hpDamage"] = hpDamage,
            ["shieldDamage"] = shieldDamage,
            ["overhealDamage"] = overhealDamage,
            ["nonlethal"] = args.Nonlethal,
            ["ignoreShield"] = PlayerDamagePolicy.IgnoreShield,
            ["clamped"] = _clamped,
            ["blocked"] = blocked,
            ["reason"] = reason,
            ["damageEvents"] = _damageEvents,
            ["damageCooldownBefore"] = cooldown,
            ["damageCooldownAfter"] = health.DamageCooldown(),
            ["before"] = before,
            ["after"] = after,
        };
    }

    private static JsonObject Snapshot(PlayerHealth health) => new()
    {
        ["hp"] = health.hp,
        ["maxHp"] = health.maxHp,
        ["shield"] = health.shield,
        ["maxShield"] = health.maxShield,
        ["overheal"] = health.overheal,
        ["maxOverheal"] = health.maxOverheal,
    };

    private static bool IsOurs(PlayerHealth health, DamageContainer dc) =>
        _target != null && health.Pointer == _target.Pointer && dc?.damageSource == Source;

    [HarmonyPatch(typeof(PlayerHealth), nameof(PlayerHealth.CheckStopDamage))]
    private static class NonlethalGuard
    {
        private static void Postfix(PlayerHealth __instance, DamageContainer dc, ref bool __result)
        {
            if (!IsOurs(__instance, dc))
            {
                return;
            }

            _stopped = __result;
            if (!__result)
            {
                var safe = PlayerDamagePolicy.Clamp(dc.damage, __instance.hp, __instance.overheal, _nonlethal);
                _clamped = safe < dc.damage;
                dc.damage = safe;
                __result = safe <= 0f;
            }

            _effectiveDamage = dc.damage;
        }
    }

}
