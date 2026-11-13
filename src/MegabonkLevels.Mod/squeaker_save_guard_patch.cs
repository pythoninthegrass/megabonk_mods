using Assets.Scripts._Data.Hats;
using Assets.Scripts.Saves___Serialization.Progression;
using Assets.Scripts.Saves___Serialization.SaveFiles;
using Assets.Scripts.Saves___Serialization.SaveFiles.Configs;
using HarmonyLib;

namespace MegabonkLevels;

// Keeps the mod character's id out of the files the game writes, so removing the mod leaves the saves loadable; see docs/characters.md.
public static class SqueakerSaveGuardPatch
{
    private static readonly ECharacter ModCharacter = (ECharacter)SqueakerCharacter.Id;

    // The last stock selection the config held, read when Preferences.Init loads it.
    private static int? _lastStockSelection;

    [HarmonyPatch(typeof(Preferences), nameof(Preferences.Init))]
    private static class RememberStockSelection
    {
        private static void Postfix(Preferences __instance)
        {
            if (!ModCharacterRegistration.IsModCharacter((int)__instance.selectedCharacter))
            {
                _lastStockSelection = (int)__instance.selectedCharacter;
            }
        }
    }

    private sealed class ConfigWrite
    {
        public ECharacter? Selected;
        public bool HadSkin;
        public int Skin;
        public bool HadHat;
        public EHat Hat;
    }

    [HarmonyPatch(typeof(SaveManager), nameof(SaveManager.SaveConfig))]
    private static class SaveConfigGuard
    {
        private static void Prefix(SaveManager __instance, out ConfigWrite __state)
        {
            __state = new ConfigWrite();
            var preferences = __instance.config?.preferences;
            if (preferences == null)
            {
                return;
            }

            if (SelectedCharacterGuard.RestoreTarget((int)preferences.selectedCharacter, _lastStockSelection) is { } target)
            {
                __state.Selected = preferences.selectedCharacter;
                preferences.selectedCharacter = (ECharacter)target;
            }
            else
            {
                _lastStockSelection = (int)preferences.selectedCharacter;
            }

            if (preferences.characterSkins != null && preferences.characterSkins.TryGetValue(ModCharacter, out var skin))
            {
                __state.HadSkin = true;
                __state.Skin = skin;
                preferences.characterSkins.Remove(ModCharacter);
            }

            if (preferences.characterHats != null && preferences.characterHats.TryGetValue(ModCharacter, out var hat))
            {
                __state.HadHat = true;
                __state.Hat = hat;
                preferences.characterHats.Remove(ModCharacter);
            }
        }

        private static void Postfix(SaveManager __instance, ConfigWrite __state)
        {
            var preferences = __instance.config?.preferences;
            if (preferences == null || __state == null)
            {
                return;
            }

            if (__state.Selected is { } selected)
            {
                preferences.selectedCharacter = selected;
            }

            if (__state.HadSkin)
            {
                preferences.characterSkins[ModCharacter] = __state.Skin;
            }

            if (__state.HadHat)
            {
                preferences.characterHats[ModCharacter] = __state.Hat;
            }
        }
    }

    [HarmonyPatch(typeof(SaveManager), nameof(SaveManager.SaveProgression))]
    private static class SaveProgressionGuard
    {
        private static void Prefix(SaveManager __instance, out CharacterProgression __state)
        {
            __state = null;
            var table = __instance.progression?.characterProgression;
            if (table != null && table.TryGetValue(ModCharacter, out var entry))
            {
                __state = entry;
                table.Remove(ModCharacter);
            }
        }

        private static void Postfix(SaveManager __instance, CharacterProgression __state)
        {
            if (__state != null)
            {
                __instance.progression.characterProgression[ModCharacter] = __state;
            }
        }
    }
}
