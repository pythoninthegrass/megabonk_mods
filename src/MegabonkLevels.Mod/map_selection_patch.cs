using System;
using System.Collections.Generic;
using System.IO;
using HarmonyLib;
using Il2Cpp;
using Il2CppAssets.Scripts.Managers;
using MelonLoader;
using UnityEngine;
using UnityEngine.UI;

namespace MegabonkLevels;

// Lists titled levels from UserData/Levels beside the native maps on the game's Map Selection screen; see docs/development.md.
public static class MapSelectionPatch
{
    private static readonly Color PlaceholderColor = new(0.35f, 0.2f, 0.55f, 1f);

    private static MelonLogger.Instance _logger;
    private static Texture2D _placeholder;
    private static readonly List<GameObject> _spawned = new();
    private static readonly Dictionary<int, CustomMapEntry> _entryByButton = new();
    private static CustomMapEntry? _selectedEntry;
    private static readonly Dictionary<int, (Selectable Button, Navigation Navigation)> _navigation = new();

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    private static IReadOnlyList<CustomMapEntry> ReadEntries()
    {
        var levels = new List<(string Path, LevelFile Level)>();
        foreach (var path in Directory.GetFiles(LiveEditPatch.LevelsDirectoryPath(), "*.mblevel.json"))
        {
            try
            {
                levels.Add((path, LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(path))));
            }
            catch (Exception ex)
            {
                _logger?.Warning($"MapSelection: skipped '{path}': {ex.Message}");
            }
        }

        return CustomMapEntries.From(levels);
    }

    private static Texture2D PlaceholderTexture()
    {
        if (_placeholder == null)
        {
            _placeholder = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            for (var x = 0; x < 2; x++)
            {
                for (var y = 0; y < 2; y++)
                {
                    _placeholder.SetPixel(x, y, PlaceholderColor);
                }
            }

            _placeholder.Apply();
        }

        return _placeholder;
    }

    private static void DestroySpawned()
    {
        RestoreNavigation();
        foreach (var entry in _spawned)
        {
            if (entry != null)
            {
                UnityEngine.Object.Destroy(entry);
            }
        }

        _spawned.Clear();
        _entryByButton.Clear();
        _selectedEntry = null;
    }

    // The game wires explicit up/down navigation once when it builds the list, so appended entries are unreachable until relinked.
    private static void LinkNavigation(SelectionGroupToggleSingle group)
    {
        Selectable previous = null;
        for (var i = 0; ; i++)
        {
            Selectable current;
            try
            {
                current = group.GetButton(i)?.GetComponent<Selectable>();
            }
            catch (Exception)
            {
                return;
            }

            if (current == null)
            {
                return;
            }

            if (previous != null)
            {
                var down = previous.navigation;
                down.selectOnDown = current;
                previous.navigation = down;

                var up = current.navigation;
                up.selectOnUp = previous;
                current.navigation = up;
            }

            previous = current;
        }
    }

    private static void AddEntry(MapSelectionWindow window, CustomMapEntry entry)
    {
        var mapData = LevelLoaderPatch.FindMapData(entry.Map);
        if (mapData == null)
        {
            _logger?.Warning($"MapSelection: no MapData for map={entry.Map}, '{entry.Title}' not listed");
            return;
        }

        var clone = UnityEngine.Object.Instantiate(window.mapEntryPrefab, window.selectionGroup.transform);
        var mapEntry = clone.GetComponent<MapEntry>();
        mapEntry.Set(mapData);
        mapEntry.t_name.text = entry.Title;
        mapEntry.t_description.text = entry.Description;
        mapEntry.mapIcon.texture = PlaceholderTexture();

        _spawned.Add(clone);
        _entryByButton[mapEntry.buttonScript.GetInstanceID()] = entry;
        _logger?.Msg($"MapSelection: listed '{entry.Title}' ({Path.GetFileName(entry.Path)})");
    }

    [HarmonyPatch(typeof(MapSelectionWindow), nameof(MapSelectionWindow.InitButtons))]
    private static class InitButtonsPostfix
    {
        private static void Postfix(MapSelectionWindow __instance)
        {
            try
            {
                DestroySpawned();
                foreach (var entry in ReadEntries())
                {
                    AddEntry(__instance, entry);
                }

                __instance.selectionGroup.FindButtons();
                LinkNavigation(__instance.selectionGroup);
            }
            catch (Exception ex)
            {
                _logger?.Error($"MapSelection: could not add custom entries: {ex}");
            }
        }
    }

    private static void RestoreNavigation()
    {
        foreach (var saved in _navigation.Values)
        {
            if (saved.Button != null)
            {
                saved.Button.navigation = saved.Navigation;
            }
        }

        _navigation.Clear();
    }

    private sealed class TierMenu : ICustomTierMenu
    {
        private readonly MapStatsWindow _window;

        public TierMenu(MapStatsWindow window) => _window = window;
        public int TierCount => _window.tierButtons.Length;

        public void SetAvailable(int index, bool available)
        {
            var button = _window.tierButtons[index];
            button.gameObject.SetActive(available);
            button.CanSelect(available);
        }

        private Selectable Redirect(Selectable target)
        {
            for (var i = 1; i < TierCount; i++)
            {
                if (target == _window.tierButtons[i].GetComponent<Selectable>())
                {
                    return _window.tierButtons[0].GetComponent<Selectable>();
                }
            }

            return target;
        }

        public void RebuildNavigation()
        {
            foreach (var button in _window.transform.root.GetComponentsInChildren<Selectable>(true))
            {
                var nav = button.navigation;
                // Navigation is a reference-backed interop value; capture a separate copy before changing it.
                var original = button.navigation;
                nav.selectOnUp = Redirect(nav.selectOnUp);
                nav.selectOnDown = Redirect(nav.selectOnDown);
                nav.selectOnLeft = Redirect(nav.selectOnLeft);
                nav.selectOnRight = Redirect(nav.selectOnRight);
                if (nav.selectOnUp != original.selectOnUp || nav.selectOnDown != original.selectOnDown
                    || nav.selectOnLeft != original.selectOnLeft || nav.selectOnRight != original.selectOnRight)
                {
                    _navigation.TryAdd(button.GetInstanceID(), (button, original));
                    button.navigation = nav;
                }
            }

            var first = _window.tierButtons[0].GetComponent<Selectable>();
            _navigation.TryAdd(first.GetInstanceID(), (first, first.navigation));
            var down = first.navigation;
            down.selectOnDown = _window.btnChallenges.GetComponent<Selectable>();
            first.navigation = down;

            var challenges = _window.btnChallenges.GetComponent<Selectable>();
            _navigation.TryAdd(challenges.GetInstanceID(), (challenges, challenges.navigation));
            var up = challenges.navigation;
            up.selectOnUp = first;
            challenges.navigation = up;
        }

        public void SelectFirst()
        {
            _window.tierSelection.ForceSelect(0);
            ButtonManager.ForceHoverButton(_window.tierButtons[0]);
        }
    }

    private static void LimitTiers(MapStatsWindow window, bool select = false)
    {
        try
        {
            CustomTierSelection.Repair(new TierMenu(window), select);
        }
        catch (Exception ex)
        {
            _logger?.Warning($"MapSelection: could not limit the tier buttons: {ex.Message}");
        }
    }

    [HarmonyPatch(typeof(MapStatsWindow), nameof(MapStatsWindow.RefreshTiers))]
    private static class RefreshTiersPostfix
    {
        private static void Postfix(MapStatsWindow __instance)
        {
            if (_selectedEntry != null)
            {
                LimitTiers(__instance);
            }
        }
    }

    [HarmonyPatch(typeof(MapSelectionUi), "OnMapSelected")]
    private static class MapSelectedPatch
    {
        private static void Prefix(SelectionGroupToggleSingleButton btn)
        {
            RestoreNavigation();
            _selectedEntry = _entryByButton.TryGetValue(btn.GetInstanceID(), out var entry) ? entry : null;
        }

        private static void Postfix(MapSelectionUi __instance)
        {
            if (_selectedEntry != null)
            {
                LimitTiers(__instance.mapStatsWindow, select: true);
            }

            _logger?.Msg($"MapSelection: selected {(_selectedEntry is { } selected ? Path.GetFileName(selected.Path) : "native map")}");
        }
    }

    [HarmonyPatch(typeof(MapStatsInfoUi), nameof(MapStatsInfoUi.SetConfig))]
    private static class StatsConfigPostfix
    {
        private static void Postfix(MapStatsInfoUi __instance)
        {
            if (_selectedEntry != null)
            {
                __instance.t_mapRuns.text = string.Empty;
                __instance.t_highscore.text = string.Empty;
                __instance.t_fastestTime.text = string.Empty;
            }
        }
    }

    [HarmonyPatch(typeof(MapSelectionUi), "OnDisable")]
    private static class OnDisablePostfix
    {
        private static void Postfix() => LevelLoaderPatch.OnMenuDisabled();
    }

    // Custom Confirm holds the level for StartNewMap; native Confirm drops any previously held level.
    [HarmonyPatch(typeof(MapSelectionUi), nameof(MapSelectionUi.StartMap))]
    private static class StartMapPrefix
    {
        private static bool Prefix()
        {
            if (_selectedEntry is not { } entry)
            {
                LevelLoaderPatch.CancelAwaitingCharacter();
                CharacterScreenPatch.SetRestricted(false);
                return true;
            }

            var allowedIds = CharacterPolicy.AllowedIds(entry.AllowedCharacters);
            var character = (int)CharacterMenu.selectedCharacter;
            if (!CharacterPolicy.Permits(allowedIds, character))
            {
                var refusal = CharacterPolicy.Refusal(allowedIds, entry.Title);
                _logger?.Warning($"MapSelection: '{entry.Title}' refused, {(ECharacter)character} is selected: {refusal}");
                MenuNotice.Show(refusal);
                return false;
            }

            return LevelLoaderPatch.HoldForNextStart(entry.Path, _logger);
        }
    }
}
