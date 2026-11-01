using System.Collections.Generic;
using HarmonyLib;
using Il2Cpp;
using Il2CppAssets.Scripts.Saves___Serialization.SaveFiles.Configs;
using MelonLoader;
using UnityEngine;
using UnityEngine.EventSystems;

namespace MegabonkLevels;

// Restricts the game's own Character Selection screen to Calcium and Tony McZoom while a custom run is being set up; see docs/development.md.
public static class CharacterScreenPatch
{
    private const int PlaceholderId = -1;

    private static MelonLogger.Instance _logger;
    private static readonly Dictionary<int, ButtonSnapshot> _stock = new();

    // True while the character screen should show the custom-run restriction.
    public static bool Restricted { get; private set; }

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    // Re-styles the grid when it is already built, so the change shows without reopening the screen.
    public static void SetRestricted(bool restricted, IReadOnlyList<int> allowedIds = null)
    {
        _allowedIds = allowedIds ?? DefaultAllowedIds;
        if (restricted && !Restricted)
        {
            _savedCharacter = SavedPreferences()?.selectedCharacter;
        }
        else if (!restricted && Restricted)
        {
            RestoreSavedCharacter();
        }

        Restricted = restricted;
        foreach (var menu in Resources.FindObjectsOfTypeAll<CharacterMenu>())
        {
            Apply(menu);
        }
    }

    private static readonly int[] DefaultAllowedIds = { CharacterOverride.CalciumId, CharacterOverride.TonyMcZoomId };
    private static IReadOnlyList<int> _allowedIds = DefaultAllowedIds;

    private static bool IsAllowed(int id) => CharacterPolicy.Permits(_allowedIds, id);

    // The game saves the confirmed character as the player's preference; a custom run puts the previous one back.
    private static ECharacter? _savedCharacter;

    private static Preferences SavedPreferences() => SaveManager.Instance?.config?.preferences;

    private static void RestoreSavedCharacter()
    {
        var preferences = SavedPreferences();
        if (_savedCharacter is ECharacter saved && preferences != null && preferences.selectedCharacter != saved)
        {
            preferences.selectedCharacter = saved;
            SaveManager.Instance.SaveConfig();
            _logger?.Msg($"CharacterScreen: saved character restored to {saved}");
        }

        _savedCharacter = null;
    }

    private readonly record struct ButtonSnapshot(int SiblingIndex, bool CanUse, Color IconColor, bool OverlayActive, string Reason);

    private static void Apply(CharacterMenu menu)
    {
        if (menu == null || menu.characterGridParent == null)
        {
            return;
        }

        var buttons = menu.characterGridParent.GetComponentsInChildren<MyButtonCharacter>(true);
        if (buttons.Length < 2)
        {
            return;
        }

        foreach (var button in buttons)
        {
            if (!_stock.ContainsKey(button.GetInstanceID()))
            {
                _stock[button.GetInstanceID()] = Snapshot(button);
            }
        }

        if (Restricted)
        {
            Restrict(menu, buttons);
        }
        else
        {
            RestoreStock(buttons);
        }

        RebuildNavigation(menu);
        if (Restricted && menu.gameObject.activeInHierarchy)
        {
            FocusFirstAllowed(buttons);
        }
    }

    // The game focuses its saved character before the grid is reordered, which leaves controller focus on a stale button.
    private static void FocusFirstAllowed(MyButtonCharacter[] buttons)
    {
        MyButtonCharacter first = null;
        foreach (var button in buttons)
        {
            if (IsAllowed(IdOf(button)) && (first == null || button.transform.GetSiblingIndex() < first.transform.GetSiblingIndex()))
            {
                first = button;
            }
        }

        if (first != null && EventSystem.current != null)
        {
            EventSystem.current.SetSelectedGameObject(first.gameObject);
        }
    }

    // The game builds d-pad navigation from its characterButtons list, so the list follows the grid order before it is rebuilt.
    private static void RebuildNavigation(CharacterMenu menu)
    {
        try
        {
            var list = Traverse.Create(menu).Property("characterButtons").GetValue<Il2CppSystem.Collections.Generic.List<MyButtonCharacter>>();
            if (list != null)
            {
                var ordered = new List<MyButtonCharacter>();
                foreach (var button in list)
                {
                    ordered.Add(button);
                }

                ordered.Sort((a, b) => a.transform.GetSiblingIndex().CompareTo(b.transform.GetSiblingIndex()));
                list.Clear();
                foreach (var button in ordered)
                {
                    list.Add(button);
                }
            }

            AccessTools.Method(typeof(CharacterMenu), "SetupButtonNavigation").Invoke(menu, null);
        }
        catch (System.Exception ex)
        {
            _logger?.Warning($"CharacterScreen: could not rebuild navigation: {ex.Message}");
        }
    }

    private static ButtonSnapshot Snapshot(MyButtonCharacter button) => new(
        button.transform.GetSiblingIndex(),
        button.canUseCharacter,
        button.i_icon != null ? button.i_icon.color : Color.white,
        button.unavailableOverlay != null && button.unavailableOverlay.activeSelf,
        button.cantUseCharacterReason);

    private static int IdOf(MyButtonCharacter button) => button.characterData != null ? (int)button.characterData.eCharacter : PlaceholderId;

    private static void Restrict(CharacterMenu menu, MyButtonCharacter[] buttons)
    {
        var stockOrder = new List<MyButtonCharacter>(buttons);
        stockOrder.Sort((a, b) => _stock[a.GetInstanceID()].SiblingIndex.CompareTo(_stock[b.GetInstanceID()].SiblingIndex));

        var stockIds = stockOrder.ConvertAll(IdOf);
        var byId = new Dictionary<int, Queue<MyButtonCharacter>>();
        for (var i = 0; i < stockOrder.Count; i++)
        {
            if (!byId.TryGetValue(stockIds[i], out var queue))
            {
                byId[stockIds[i]] = queue = new Queue<MyButtonCharacter>();
            }

            queue.Enqueue(stockOrder[i]);
        }

        var position = 0;
        foreach (var id in CharacterGridOrder.Pin(stockIds))
        {
            byId[id].Dequeue().transform.SetSiblingIndex(position++);
        }

        foreach (var button in buttons)
        {
            if (button.characterData == null || IsAllowed(IdOf(button)))
            {
                continue;
            }

            button.canUseCharacter = false;
            button.cantUseCharacterReason = CharacterPolicy.Refusal(_allowedIds, null);
            if (button.i_icon != null)
            {
                button.i_icon.color = Color.black;
            }

            if (button.unavailableOverlay != null)
            {
                button.unavailableOverlay.SetActive(true);
            }
        }

        _logger?.Msg($"CharacterScreen: restricted to {string.Join(", ", _allowedIds)}, {buttons.Length} buttons");
    }

    private static void RestoreStock(MyButtonCharacter[] buttons)
    {
        foreach (var button in buttons)
        {
            var stock = _stock[button.GetInstanceID()];
            button.transform.SetSiblingIndex(stock.SiblingIndex);
            button.canUseCharacter = stock.CanUse;
            button.cantUseCharacterReason = stock.Reason;
            if (button.i_icon != null)
            {
                button.i_icon.color = stock.IconColor;
            }

            if (button.unavailableOverlay != null)
            {
                button.unavailableOverlay.SetActive(stock.OverlayActive);
            }
        }
    }

    [HarmonyPatch(typeof(CharacterMenu), "OnEnable")]
    private static class OnEnablePostfix
    {
        private static void Postfix(CharacterMenu __instance)
        {
            if (Restricted)
            {
                Apply(__instance);
            }
        }
    }

    [HarmonyPatch(typeof(CharacterMenu), "OnDisable")]
    private static class OnDisablePostfix
    {
        private static void Postfix(CharacterMenu __instance)
        {
            // Forward navigation enables the map tab before disabling the character tab.
            var maps = __instance.mainMenu?.tabMaps;
            LevelLoaderPatch.OnMenuDisabled(maps != null && maps.activeInHierarchy);
        }
    }
}
