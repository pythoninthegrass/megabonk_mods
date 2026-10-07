using HarmonyLib;
using Il2Cpp;
using Il2CppAssets.Scripts.Game.Other;
using Il2CppAssets.Scripts.Managers;
using MelonLoader;

namespace MegabonkLevels;

// TASK-004.01 investigation: MapController.TestMap(RunConfig) sets currentMap/currentStage but does
// not by itself leave the main menu (confirmed live: MapController.IsMainMenu() stays true before and
// after the call). This probe logs the game's own map-start calls a normal manual playthrough makes
// so LevelLoaderPatch can be extended to trigger the same path TestMap alone doesn't cover.
//
// Deliberately does NOT patch UnityEngine.SceneManagement.SceneManager.LoadScene: that's a core Unity
// engine icall, not game code, and Harmony-patching it crashed the game (Il2Cpp interop can't safely
// hook native icalls the way it hooks the game's own IL2CPP-compiled methods like
// ProceduralTileGeneration.Generate).
//
// Also deliberately does NOT patch MapMenu.StartMap: its RVA (0x3321E0) is shared by 1,453 other
// methods in the il2cpp dump — a linker-folded trivial/empty-body address, not a unique method body.
// Harmony patching it crashed the game by intercepting every one of those unrelated call sites too.
// Before adding any new Harmony target, check its RVA's uniqueness in .tools/il2cpp_dump/dump.cs
// first (`grep -c "RVA: 0x<addr> "`) — a count greater than 1 means it is unsafe to patch.
public static class SceneTransitionProbe
{
    private static MelonLogger.Instance _logger;

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    [HarmonyPatch(typeof(MapController), nameof(MapController.StartNewMap))]
    private static class StartNewMapPostfix
    {
        private static void Postfix(RunConfig newRunConfig)
        {
            _logger?.Msg($"SceneTransitionProbe: MapController.StartNewMap map={newRunConfig?.mapData?.GetInternalName()}");
        }
    }

    [HarmonyPatch(typeof(LoadingScreen), nameof(LoadingScreen.LoadInstant))]
    private static class LoadInstantPostfix
    {
        private static void Postfix()
        {
            _logger?.Msg("SceneTransitionProbe: LoadingScreen.LoadInstant");
        }
    }
}
