using System.Collections.Generic;
using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Enemies;
using Il2CppAssets.Scripts.Actors.Player;
using Il2CppAssets.Scripts.Managers;
using Il2CppTMPro;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// See "Position readout" in docs/development.md.
public static class PositionLabel
{
    private const float UpdateIntervalSeconds = 0.1f;
    private const float ActorIntervalSeconds = 0.25f;
    private const float FontSize = 20f;
    private const float WidthMargin = 20f;
    private const float RightOffsetX = 0f;
    private const string MonoFontName = "RobotoMono";
    private const int MaxEliteLines = 3;
    private const int MaxEnemyLines = 3;
    private const string CellLogVariable = "MEGABONK_CELL_LOG";

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
    private static float _nextActorUpdate;
    private static readonly NearbyEnemySelector EliteSelector = new(MaxEliteLines);
    private static readonly NearbyEnemySelector EnemySelector = new(MaxEnemyLines);
    private static readonly List<ReadoutActor> Actors = new();
    private static bool _cellLogEnabled = EnvFlag.IsSet(CellLogVariable);
    private static readonly CellChangeTracker CellLog = new();

    public static void Arm(int gridWidth, int gridDepth, float spacing, float tileHeight, float floorY, MelonLogger.Instance logger)
    {
        _logger = logger;
        _gridWidth = gridWidth;
        _gridDepth = gridDepth;
        _spacing = spacing;
        _tileHeight = tileHeight;
        _floorY = floorY;
        _warnedNoMinimap = false;
        Actors.Clear();
        _nextActorUpdate = 0f;
        CellLog.Reset();
        _armed = DevHarness.Enabled;
    }

    public static void Disarm()
    {
        _armed = false;
        Hide();
    }

    public static void SetCellLog(bool enabled, MelonLogger.Instance logger)
    {
        _cellLogEnabled = enabled;
        CellLog.Reset();
        logger.Msg($"PositionLabel: cell log {(enabled ? "on" : "off")}");
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

        if (_label == null && !TryCreate())
        {
            return;
        }

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

    private static TMP_FontAsset FindFontAsset(string assetName)
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
