using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Player;
using Il2CppTMPro;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Dev-only text under the game's minimap that shows the player's world position, grid cell and kill-floor height.
// Drawn only when the dev harness is enabled and the level is mod-loaded (the kill floor is armed); see docs/development.md.
public static class PositionLabel
{
    private const float UpdateIntervalSeconds = 0.1f;
    private const float FontSize = 20f;

    private static MelonLogger.Instance _logger;
    private static bool _armed;
    private static int _gridWidth;
    private static int _gridDepth;
    private static float _spacing;
    private static float _tileHeight;
    private static float _floorY;
    private static TextMeshProUGUI _label;
    private static bool _warnedNoMinimap;
    private static float _nextUpdate;

    public static void Arm(int gridWidth, int gridDepth, float spacing, float tileHeight, float floorY, MelonLogger.Instance logger)
    {
        _logger = logger;
        _gridWidth = gridWidth;
        _gridDepth = gridDepth;
        _spacing = spacing;
        _tileHeight = tileHeight;
        _floorY = floorY;
        _warnedNoMinimap = false;
        _armed = DevHarness.Enabled;
    }

    public static void Disarm()
    {
        _armed = false;
        Hide();
    }

    public static void Tick()
    {
        if (!_armed || Time.unscaledTime < _nextUpdate)
        {
            return;
        }

        _nextUpdate = Time.unscaledTime + UpdateIntervalSeconds;
        var player = MyPlayer.Instance;
        if (player == null)
        {
            return;
        }

        // A destroyed label is Unity-null: the HUD, and the minimap under it, is rebuilt for each run.
        if (_label == null && !TryCreate())
        {
            return;
        }

        var position = player.transform.position;
        var cell = PositionReadout.CellOf(position.x, position.z, _gridWidth, _gridDepth, _spacing);
        var level = PositionReadout.LevelOf(position.y, _tileHeight);
        _label.text = PositionReadout.Format(position.x, position.y, position.z, cell, level, _floorY);
    }

    private static void Hide()
    {
        if (_label != null)
        {
            Object.Destroy(_label.gameObject);
        }

        _label = null;
    }

    // The label is a copy of one of the minimap's own direction letters, which brings the game's font and material.
    private static bool TryCreate()
    {
        var minimap = Object.FindObjectOfType<MinimapUi>();
        var letters = minimap?.directionLetters;
        if (letters == null || letters.Length == 0)
        {
            if (!_warnedNoMinimap)
            {
                _warnedNoMinimap = true;
                _logger.Warning("PositionLabel: no minimap found, readout not drawn");
            }

            return false;
        }

        var copy = Object.Instantiate(letters[0].gameObject, minimap.transform, false);
        copy.name = "MegabonkLevelsPosition";
        var label = copy.GetComponent<TextMeshProUGUI>();
        if (label == null)
        {
            Object.Destroy(copy);
            _logger.Warning("PositionLabel: minimap direction letter has no TextMeshProUGUI, readout not drawn");
            _armed = false;
            return false;
        }

        // Anchored to the minimap's bottom-right corner and right-aligned so the text grows into the screen.
        var rect = copy.GetComponent<RectTransform>();
        rect.anchorMin = rect.anchorMax = new Vector2(1f, 0f);
        rect.pivot = new Vector2(1f, 1f);
        rect.anchoredPosition = new Vector2(0f, -34f);
        rect.sizeDelta = new Vector2(700f, 28f);
        rect.localRotation = Quaternion.identity;
        rect.localScale = Vector3.one;
        label.alignment = TextAlignmentOptions.TopRight;
        label.enableWordWrapping = false;
        label.overflowMode = TextOverflowModes.Overflow;
        label.fontSize = FontSize;
        label.color = Color.yellow;
        _label = label;
        _logger.Msg("PositionLabel: created under the minimap");
        return true;
    }
}
