using HarmonyLib;
using Unity.AI.Navigation;

namespace MegabonkLevels;

// Empirically confirms whether/when a runtime navmesh bake happens (TASK-002.03 AC#3). Static analysis
// of the dumped declarations found exactly one NavMeshSurface reference in the whole game
// (RsgController.navmeshSurface, used by the crypt/graveyard boss dungeon, not the main Tiles/
// ProceduralMesh maps), but method bodies aren't visible in the IL2CppDumper output, so the actual
// bake trigger can only be confirmed by observing it fire at runtime.
//
// Patching RsgController.Generate(int, EDungeonType, out float) itself was tried and dropped: entering
// a crypt threw a NullReferenceException inside the IL2CppInterop native->managed trampoline before
// even this patch's Prefix logged, with or without the postfix's own try/catch - i.e. the crash isn't
// in this mod's patch code, it's the Harmony detour/trampoline choking on that method's signature (or
// a pre-existing game bug independent of modding). BuildNavMesh is the method that actually answers
// AC#3, so it's left as the sole hook here rather than chasing the crypt crash further.
public static class NavMeshPatch
{
    private static ModLogger _logger;

    public static void Install(ModLogger logger)
    {
        _logger = logger;
    }

    [HarmonyPatch(typeof(NavMeshSurface), nameof(NavMeshSurface.BuildNavMesh))]
    private static class BuildNavMeshPostfix
    {
        private static void Postfix(NavMeshSurface __instance)
        {
            try
            {
                _logger?.Msg($"NavMesh: BuildNavMesh() called on '{__instance?.gameObject.name}'");
            }
            catch (System.Exception ex)
            {
                _logger?.Msg($"NavMesh: BuildNavMeshPostfix.Postfix threw: {ex}");
            }
        }
    }
}
