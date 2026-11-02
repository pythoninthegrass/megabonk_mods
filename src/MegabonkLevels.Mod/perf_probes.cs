using System;
using System.Collections.Generic;
using System.Text.Json.Nodes;
using HarmonyLib;
using Il2Cpp;
using Il2CppActors.Enemies;
using Il2CppAssets.Scripts.Actors.Enemies;
using Il2CppAssets.Scripts.Inventory__Items__Pickups.Weapons;
using Il2CppAssets.Scripts.Managers;
using MelonLoader;

namespace MegabonkLevels;

// Times the stock per-frame work that scales with the enemy population, so a run's frame time can be split between the
// game's own systems and the mod's. The trampolines exist whether or not the harness is on; the bodies bail out when it
// is not, and `perf toggle <target> off` switches one probe off to measure even the trampoline cost. Every target here
// was checked for a unique RVA in .tools/il2cpp_dump/dump.cs first — a folded address would crash the game.
public static class PerfProbes
{
    public static void Install(MelonLogger.Instance logger)
    {
    }

    // Each probe's patch target, keyed by the report name, so the attach status can be checked against the ones the attribute patcher should have reached.
    private static readonly (string Name, Type Type, string Method)[] ProbeTargets =
    {
        ("EnemyManager.Update", typeof(EnemyManager), "Update"),
        ("EnemyManager.FixedUpdate", typeof(EnemyManager), "FixedUpdate"),
        ("Enemy.MyUpdate", typeof(Enemy), "MyUpdate"),
        ("Enemy.MyFixedUpdate", typeof(Enemy), "MyFixedUpdate"),
        ("EnemyMovementRb.MyFixedUpdate", typeof(EnemyMovementRb), "MyFixedUpdate"),
        ("AnimatedMesh.Update", typeof(AnimatedMesh), "Update"),
        ("EnemyHpBar.Update", typeof(EnemyHpBar), "Update"),
        ("EnemyDissolve.Update", typeof(EnemyDissolve), "Update"),
        ("VisualizeTargeting.Update", typeof(VisualizeTargeting), "Update"),
        ("MinimapUi.Update", typeof(MinimapUi), "Update"),
        ("AlwaysManager.Update", typeof(AlwaysManager), "Update"),
    };

    // Cached rows rather than a cached JsonArray: a JsonNode takes one parent and every report embeds a fresh copy.
    private static List<(string Name, bool Patched)> _attachRows;

    // Whether Harmony holds a patch on each target; resolved the same way the attribute patcher resolves it. Patches land at startup, so one pass is enough.
    public static JsonArray AttachNode()
    {
        if (_attachRows == null)
        {
            var rows = new List<(string, bool)>();
            foreach (var (name, type, method) in ProbeTargets)
            {
                var target = AccessTools.Method(type, method);
                rows.Add((name, target != null && Harmony.GetPatchInfo(target) != null));
            }

            _attachRows = rows;
        }

        return PerfProbePlan.AttachNode(_attachRows);
    }

    [HarmonyPatch(typeof(EnemyManager), "Update")]
    private static class EnemyManagerUpdateProbe
    {
        private const string Name = "EnemyManager.Update";

        private static void Prefix(out double __state) => PerfMonitor.ProbeEnter(Name, out __state);

        private static void Postfix(double __state) => PerfMonitor.ProbeExit(Name, __state);
    }

    [HarmonyPatch(typeof(EnemyManager), "FixedUpdate")]
    private static class EnemyManagerFixedUpdateProbe
    {
        private const string Name = "EnemyManager.FixedUpdate";

        private static void Prefix(out double __state) => PerfMonitor.ProbeEnter(Name, out __state);

        private static void Postfix(double __state) => PerfMonitor.ProbeExit(Name, __state);
    }

    // One AnimatedMesh component per enemy: the mesh-swap animation ticker.
    [HarmonyPatch(typeof(AnimatedMesh), "Update")]
    private static class AnimatedMeshUpdateProbe
    {
        private const string Name = "AnimatedMesh.Update";

        private static void Prefix(out double __state) => PerfMonitor.ProbeEnter(Name, out __state);

        private static void Postfix(double __state) => PerfMonitor.ProbeExit(Name, __state);
    }

    // The game dispatches its own actor ticks through MyUpdate/MyFixedUpdate rather than Unity's Update, so the per-enemy AI
    // and movement work is invisible to the EnemyManager probe alone.
    [HarmonyPatch(typeof(Enemy), "MyUpdate")]
    private static class EnemyMyUpdateProbe
    {
        private const string Name = "Enemy.MyUpdate";

        private static void Prefix(out double __state) => PerfMonitor.ProbeEnter(Name, out __state);

        private static void Postfix(double __state) => PerfMonitor.ProbeExit(Name, __state);
    }

    [HarmonyPatch(typeof(Enemy), "MyFixedUpdate")]
    private static class EnemyMyFixedUpdateProbe
    {
        private const string Name = "Enemy.MyFixedUpdate";

        private static void Prefix(out double __state) => PerfMonitor.ProbeEnter(Name, out __state);

        private static void Postfix(double __state) => PerfMonitor.ProbeExit(Name, __state);
    }

    [HarmonyPatch(typeof(EnemyMovementRb), "MyFixedUpdate")]
    private static class EnemyMovementRbMyFixedUpdateProbe
    {
        private const string Name = "EnemyMovementRb.MyFixedUpdate";

        private static void Prefix(out double __state) => PerfMonitor.ProbeEnter(Name, out __state);

        private static void Postfix(double __state) => PerfMonitor.ProbeExit(Name, __state);
    }

    [HarmonyPatch(typeof(EnemyHpBar), "Update")]
    private static class EnemyHpBarUpdateProbe
    {
        private const string Name = "EnemyHpBar.Update";

        private static void Prefix(out double __state) => PerfMonitor.ProbeEnter(Name, out __state);

        private static void Postfix(double __state) => PerfMonitor.ProbeExit(Name, __state);
    }

    [HarmonyPatch(typeof(EnemyDissolve), "Update")]
    private static class EnemyDissolveUpdateProbe
    {
        private const string Name = "EnemyDissolve.Update";

        private static void Prefix(out double __state) => PerfMonitor.ProbeEnter(Name, out __state);

        private static void Postfix(double __state) => PerfMonitor.ProbeExit(Name, __state);
    }

    [HarmonyPatch(typeof(VisualizeTargeting), "Update")]
    private static class VisualizeTargetingUpdateProbe
    {
        private const string Name = "VisualizeTargeting.Update";

        private static void Prefix(out double __state) => PerfMonitor.ProbeEnter(Name, out __state);

        private static void Postfix(double __state) => PerfMonitor.ProbeExit(Name, __state);
    }

    [HarmonyPatch(typeof(MinimapUi), "Update")]
    private static class MinimapUiUpdateProbe
    {
        private const string Name = "MinimapUi.Update";

        private static void Prefix(out double __state) => PerfMonitor.ProbeEnter(Name, out __state);

        private static void Postfix(double __state) => PerfMonitor.ProbeExit(Name, __state);
    }

    [HarmonyPatch(typeof(AlwaysManager), "Update")]
    private static class AlwaysManagerUpdateProbe
    {
        private const string Name = "AlwaysManager.Update";

        private static void Prefix(out double __state) => PerfMonitor.ProbeEnter(Name, out __state);

        private static void Postfix(double __state) => PerfMonitor.ProbeExit(Name, __state);
    }
}
