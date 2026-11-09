using System.Collections.Generic;
using Assets.Scripts.Actors.Enemies;
using Assets.Scripts.Actors.Player;
using Assets.Scripts.Managers;
using Assets.Scripts.UI.Debug;
using TMPro;
using UnityEngine;

namespace MegabonkLevels;

// See "Position readout" in docs/development.md.
public static class PositionLabel
{
    private const float UpdateIntervalSeconds = 0.1f;
    // The actor overlay walks every live enemy, so it runs well below the readout's own cadence; at a few hundred
    // enemies a 4 Hz full sweep is a measurable share of a frame for text nobody reads that fast.
    private const float ActorIntervalSeconds = 0.75f;
    private const float FontSize = 20f;
    private const float WidthMargin = 20f;
    private const float RightOffsetX = 0f;
    private const string MonoFontName = "RobotoMono";
    private const int MaxEliteLines = 3;
    private const int MaxEnemyLines = 3;
    private const string CellLogVariable = "MEGABONK_CELL_LOG";

    private static ModLogger _logger;
    private static bool _armed;
    private static int _gridWidth;
    private static int _gridDepth;
    private static float _spacing;
    private static float _tileHeight;
    private static float _floorY;
    private static TextMeshProUGUI _label;
    private static bool _warnedNoMinimap;
    private static readonly CoordinateVisibility Visibility = new();
    private static float _nextUpdate;
    private static float _nextActorUpdate;
    private static readonly NearbyEnemySelector EliteSelector = new(MaxEliteLines);
    private static readonly NearbyEnemySelector EnemySelector = new(MaxEnemyLines);
    private static readonly List<ReadoutActor> Actors = new();
    private static bool _cellLogEnabled = EnvFlag.IsSet(CellLogVariable);
    private static readonly CellChangeTracker CellLog = new();

    public static bool Enabled => Visibility.Enabled;
    public static bool Visible => _label != null && _label.gameObject.activeInHierarchy && (UiManager.Instance?.hudGroup?.alpha ?? 0f) > 0f;

    public static void Arm(int gridWidth, int gridDepth, float spacing, float tileHeight, float floorY, ModLogger logger)
    {
        _logger = logger;
        _gridWidth = gridWidth;
        _gridDepth = gridDepth;
        _spacing = spacing;
        _tileHeight = tileHeight;
        _floorY = floorY;
        Hide();
        _warnedNoMinimap = false;
        _nextUpdate = 0f;
        Actors.Clear();
        _nextActorUpdate = 0f;
        CellLog.Reset();
        _armed = DevHarness.Enabled;
    }

    public static GridCell? CellOf(float x, float z) => _armed ? PositionReadout.CellOf(x, z, _gridWidth, _gridDepth, _spacing) : null;

    public static void Disarm()
    {
        _armed = false;
        Hide();
    }

    public static void SetCellLog(bool enabled, ModLogger logger)
    {
        _cellLogEnabled = enabled;
        CellLog.Reset();
        logger.Msg($"PositionLabel: cell log {(enabled ? "on" : "off")}");
    }

    public static void SetVisible(bool enabled, ModLogger logger)
    {
        Visibility.Set(enabled);
        _nextUpdate = 0f;
        if (!enabled)
        {
            Hide();
        }

        logger.Msg($"PositionLabel: coordinates {(enabled ? "on" : "off")}");
    }

    public static void Tick()
    {
        if (!_armed)
        {
            Hide();
            return;
        }

        if (_armed && EditorInput.GetKeyDown(KeyCode.F7)
            && PositionReadout.ShouldToggle(_armed, true, DebugConsole.Instance != null && DebugConsole.Instance.IsActive(), EditorTileTools.TextInputFocused, ConsoleOverlay.Focused))
        {
            SetVisible(!Enabled, _logger);
        }

        var player = MyPlayer.Instance;
        var alive = player?.inventory?.playerHealth is { } health && !health.IsDead();
        var visible = Visibility.Visible(_armed, alive);
        if (!visible)
        {
            Hide();
        }

        if (!alive || (!visible && !_cellLogEnabled))
        {
            return;
        }

        if (Time.unscaledTime < _nextUpdate)
        {
            return;
        }

        _nextUpdate = Time.unscaledTime + UpdateIntervalSeconds;
        var position = player.transform.position;
        if (_cellLogEnabled)
        {
            LogCellChange(CellChangeTracker.PlayerId, "me", position);
        }

        if (Time.unscaledTime >= _nextActorUpdate)
        {
            _nextActorUpdate = Time.unscaledTime + ActorIntervalSeconds;
            RefreshActors(position);
        }

        if (!visible || (_label == null && !TryCreate()))
        {
            return;
        }

        var text = PositionReadout.Render(position.x, position.y, position.z, _floorY, Actors);
        var preferred = _label.GetPreferredValues(text);
        _label.rectTransform.sizeDelta = new Vector2(preferred.x + WidthMargin, preferred.y);
        _label.text = text;
    }

    private static void RefreshActors(Vector3 player)
    {
        Actors.Clear();
        var manager = EnemyManager.Instance;
        if (manager?.enemies == null)
        {
            return;
        }

        var bosses = manager.stageBosses;
        for (var i = 0; bosses != null && i < bosses.Count; i++)
        {
            var boss = bosses[i];
            if (boss != null)
            {
                AddBossTier(boss);
            }
        }

        EliteSelector.Begin(player.x, player.z, _floorY);
        EnemySelector.Begin(player.x, player.z, _floorY);
        foreach (var enemy in manager.enemies.Values)
        {
            if (enemy == null || IsBoss(bosses, enemy.id))
            {
                continue;
            }

            var kind = ActorKinds.Of(RawFlags(enemy));
            if (ActorKinds.IsBossTier(kind))
            {
                AddBossTier(enemy);
                continue;
            }

            var position = enemy.transform.position;
            var actor = new ActorPosition(enemy.id, position.x, position.y, position.z);
            (kind == ActorKind.Elite ? EliteSelector : EnemySelector).Offer(actor);
        }

        for (var i = 0; i < EliteSelector.Count; i++)
        {
            var actor = EliteSelector[i];
            Actors.Add(new ReadoutActor(ActorKinds.Label(ActorKind.Elite), actor.Id, actor.X, actor.Y, actor.Z));
        }

        for (var i = 0; i < EnemySelector.Count; i++)
        {
            var actor = EnemySelector[i];
            Actors.Add(new ReadoutActor(ActorKinds.Label(ActorKind.Enemy), actor.Id, actor.X, actor.Y, actor.Z));
        }
    }

    private static void AddBossTier(Enemy enemy)
    {
        var kind = ActorKinds.Of(RawFlags(enemy));
        var position = enemy.transform.position;
        var typeName = enemy.enemyData != null ? enemy.enemyData.enemyName.ToString() : null;
        var label = ActorKinds.Label(kind);
        Actors.Add(new ReadoutActor(label, enemy.id, position.x, position.y, position.z, typeName));
        if (_cellLogEnabled)
        {
            LogCellChange(enemy.id, $"{label} {enemy.id}" + (typeName != null ? $" {typeName}" : string.Empty), position);
        }
    }

    // The raw EEnemyFlag bits are a private field; this rebuilds them from Enemy's public Is*() methods in the
    // order ActorKinds.Of expects (see docs/development.md, "Enemy kinds").
    private static int RawFlags(Enemy enemy) =>
        (enemy.IsElite() ? 1 : 0) | (enemy.IsBoss() ? 2 : 0) | (enemy.IsStageBoss() ? 4 : 0) | (enemy.IsFinalBoss() ? 32 : 0);

    private static bool IsBoss(Il2CppSystem.Collections.Generic.List<Enemy> bosses, uint id)
    {
        for (var i = 0; bosses != null && i < bosses.Count; i++)
        {
            if (bosses[i] != null && bosses[i].id == id)
            {
                return true;
            }
        }

        return false;
    }

    private static void LogCellChange(uint id, string name, Vector3 position)
    {
        var cell = PositionReadout.CellOf(position.x, position.z, _gridWidth, _gridDepth, _spacing);
        var level = PositionReadout.LevelOf(position.y, _tileHeight);
        if (CellLog.Changed(id, cell, level))
        {
            _logger.Msg($"PositionLabel: {PositionReadout.FormatCellLog(name, position.x, position.y, position.z, cell, level)}");
        }
    }

    private static void Hide()
    {
        if (_label != null)
        {
            _label.gameObject.SetActive(false);
            Object.Destroy(_label.gameObject);
        }

        _label = null;
    }

    // Clone a minimap direction letter to keep the game's original font, material and placement.
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

        var rect = copy.GetComponent<RectTransform>();
        rect.anchorMin = rect.anchorMax = new Vector2(1f, 0f);
        rect.pivot = new Vector2(1f, 1f);
        rect.anchoredPosition = new Vector2(RightOffsetX, -34f);
        rect.localRotation = Quaternion.identity;
        rect.localScale = Vector3.one;
        label.alignment = TextAlignmentOptions.TopLeft;
        label.enableWordWrapping = false;
        label.overflowMode = TextOverflowModes.Overflow;
        label.fontSize = FontSize;
        label.color = Color.yellow;

        var monoFont = FindFontAsset(MonoFontName);
        if (monoFont != null)
        {
            label.font = monoFont;
        }
        else
        {
            _logger.Warning($"PositionLabel: font asset '{MonoFontName}' not found, columns will not line up exactly");
        }

        _label = label;
        _logger.Msg("PositionLabel: created under the minimap");
        return true;
    }

    internal static TMP_FontAsset FindFontAsset(string assetName)
    {
        foreach (var asset in Resources.FindObjectsOfTypeAll<TMP_FontAsset>())
        {
            if (asset != null && asset.name == assetName)
            {
                return asset;
            }
        }

        return null;
    }
}
