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
