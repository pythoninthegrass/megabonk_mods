using Assets.Scripts._Data.Hats;
using Assets.Scripts.Saves___Serialization.Progression;
using Assets.Scripts.Saves___Serialization.Progression.Stats;
using Assets.Scripts.Saves___Serialization.SaveFiles;
using Assets.Scripts.Saves___Serialization.SaveFiles.Configs;
using HarmonyLib;
using System.Collections.Generic;
using System.Linq;

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

    private sealed class ProgressionWrite
    {
        public CharacterProgression Entry;
        public readonly List<MapProgress> TiersWithModCharacter = new();
        public readonly List<int> Tiers = new();
    }

    [HarmonyPatch(typeof(SaveManager), nameof(SaveManager.SaveProgression))]
    private static class SaveProgressionGuard
    {
        private static void Prefix(SaveManager __instance, out ProgressionWrite __state)
        {
            __state = new ProgressionWrite();
            var progression = __instance.progression;
            var table = progression?.characterProgression;
            if (table != null && table.TryGetValue(ModCharacter, out var entry))
            {
                __state.Entry = entry;
                table.Remove(ModCharacter);
            }

            var maps = progression?.menuMeta?.mapsProgress;
            if (maps == null)
            {
                return;
            }

            foreach (var map in maps.Values)
            {
                var completions = map?.tierCompletionsWithCharacters;
                if (completions == null)
                {
                    continue;
                }

                var tierKeys = new List<int>();
                foreach (var tier in completions.Keys)
                {
                    tierKeys.Add(tier);
                }

                foreach (var tier in tierKeys)
                {
                    if (completions[tier].Remove(ModCharacter))
                    {
                        __state.TiersWithModCharacter.Add(map);
                        __state.Tiers.Add(tier);
                    }
                }
            }
        }

        private static void Postfix(SaveManager __instance, ProgressionWrite __state)
        {
            if (__state == null)
            {
                return;
            }

            if (__state.Entry != null)
            {
                __instance.progression.characterProgression[ModCharacter] = __state.Entry;
            }

            for (var i = 0; i < __state.Tiers.Count; i++)
            {
                __state.TiersWithModCharacter[i].tierCompletionsWithCharacters[__state.Tiers[i]].Add(ModCharacter);
            }
        }
    }

    [HarmonyPatch(typeof(SaveManager), nameof(SaveManager.SaveStats))]
    private static class SaveStatsGuard
    {
        private static void Prefix(SaveManager __instance, out List<KeyValuePair<string, MyStat>> __state)
        {
            __state = new List<KeyValuePair<string, MyStat>>();
            var stats = __instance.stats?.stats;
            if (stats == null)
            {
                return;
            }

            var keys = new List<string>();
            foreach (var key in stats.Keys)
            {
                keys.Add(key);
            }

            foreach (var key in keys)
            {
                if (ModCharacterStatKeys.IsModCharacterKey(key))
                {
                    __state.Add(new KeyValuePair<string, MyStat>(key, stats[key]));
                    stats.Remove(key);
                }
            }
        }

        private static void Postfix(SaveManager __instance, List<KeyValuePair<string, MyStat>> __state)
        {
            foreach (var entry in __state)
            {
                __instance.stats.stats[entry.Key] = entry.Value;
            }
        }
    }
}
