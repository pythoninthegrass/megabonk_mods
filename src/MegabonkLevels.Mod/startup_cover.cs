using System;
using HarmonyLib;
using Assets.Scripts.Actors.Player;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace MegabonkLevels;

// Applies the gate's cover, hold and one-time placement decisions, never correcting position drift.
public static class StartupCover
{
    private const int SortingOrder = 30000;
    private const float LabelWidth = 1200f;
    private const float LabelHeight = 90f;
    private const float LabelFontSize = 34f;

    private static readonly StartupGate Gate = new StartupGate(
        timeoutSeconds: StartupGate.ParseTimeoutSeconds(Environment.GetEnvironmentVariable("MEGABONK_STARTUP_TIMEOUT_SECONDS")));

    private static GameObject _root;
    private static TextMeshProUGUI _label;
    private static bool _visible;
    private static Vector3? _holdPoint;
    private static MapGenerationController _generationController;
    private static (int Tiles, int FlatTiles, int FillTiles) _generationCounts;

    // The game moved the player itself; the next Tick resolves it to the authored start, once.
    public static void OnGameSpawned() => Gate.GameSpawnedPlayer(Time.realtimeSinceStartup);

    public static void OnRunStarting(bool customLevel)
    {
        _generationController = null;
        _generationCounts = default;
        Gate.RunStarted(customLevel, Time.realtimeSinceStartup, waitForPortal: customLevel);
    }

    public static void OnProgress() => Gate.Progress(Time.realtimeSinceStartup);

    public static void OnPortalClosed() => Gate.PortalClosed(Time.realtimeSinceStartup);

    public static void OnPortalOpened() => Gate.PortalOpened(Time.realtimeSinceStartup);

    // The harness moved the player on purpose, so the cover must stop owing a placement that would undo it. The cached
    // hold point is dropped too: the hold that keeps following must follow the harness point, not the old one.
    public static void OnHarnessTeleported()
    {
        _holdPoint = null;
        Gate.HarnessTeleported(Time.realtimeSinceStartup);
    }

    public static void OnGenerationStarting()
    {
        if (Gate.Phase != StartupGatePhase.Covering)
        {
            return;
        }

        _generationController = UnityEngine.Object.FindObjectOfType<MapGenerationController>();
        OnProgress();
    }

    // Generation is done and the level's edits are in the world: the single placement becomes owed.
    public static void OnContentReady() => Gate.ContentReady(Time.realtimeSinceStartup);

    public static void OnStartFailed(string reason) => Gate.Failed(reason);

    public static void OnCancelled(string reason) => Gate.Cancelled(reason);

    public static bool CoverVisible => _visible;

    public static StartupGatePhase Phase => Gate.Phase;

    public static void Tick(ModLogger logger)
    {
        var now = Time.realtimeSinceStartup;
        PollGenerationProgress(now);
        Gate.Tick(now);
        if (Gate.ShouldAttemptPlace)
        {
            AttemptPlace(logger, now);
        }

        ApplyHold();
        Drain(logger);
    }

    private static void PollGenerationProgress(float now)
    {
        if (Gate.Phase != StartupGatePhase.Covering || _generationController == null)
        {
            _generationController = null;
            return;
        }

        var tiles = _generationController.proceduralTileGeneration;
        var counts = (tiles?.tiles?.Count ?? 0, tiles?.flatTiles?.Count ?? 0, tiles?.fillTiles?.Count ?? 0);
        if (counts != _generationCounts)
        {
            _generationCounts = counts;
            Gate.Progress(now);
        }
    }

    private const float InPlaceTolerance = 0.5f;

    private static void AttemptPlace(ModLogger logger, float now)
    {
        var start = LiveEditPatch.PlayerStart;
        var player = MyPlayer.Instance;
        var body = player?.playerMovement?.rb;
        if (body == null || start == null || start.Count < 3)
        {
            Gate.PlaceAttemptFailed("no player body or no authored start in this run", now);
            return;
        }

        var target = new Vector3(start[0], start[1] - TeleportTarget.PlayerBodyOffsetY, start[2]);
        var facing = player.transform.forward;

        // The from-scratch spawn portal already put the player on the start, so there is nothing to move.
        var at = body.position;
        if (FromScratchLayout.IsInPlace(new[] { at.x, at.y, at.z }, new[] { target.x, target.y, target.z }, InPlaceTolerance))
        {
            _holdPoint = null;
            Gate.PlacementCompleted(now);
            logger.Msg("StartupCover: player already at the level start");
            return;
        }

        // Drop the hold before the teleport so a later hold write cannot pull the player back off the start.
        _holdPoint = null;
        player.TeleportPlayerImmediate(target, facing, facing, 20f);
        Gate.PlacementCompleted(now);
        logger.Msg($"StartupCover: player placed at the level start {target}");
    }

    private static void ApplyHold()
    {
        if (!Gate.ShouldHoldPlayer)
        {
            _holdPoint = null;
            return;
        }

        var body = MyPlayer.Instance?.playerMovement?.rb;
        if (body == null)
        {
            return;
        }

        _holdPoint ??= body.position;
        body.position = _holdPoint.Value;
        body.velocity = Vector3.zero;
    }

    private static void Drain(ModLogger logger)
    {
        var commands = Gate.Drain();
        for (var i = 0; i < commands.Count; i++)
        {
            var command = commands[i];
            switch (command.Kind)
            {
                case StartupGateCommandKind.ShowCover:
                    Show();
                    break;
                case StartupGateCommandKind.HideCover:
                    Hide();
                    break;
                case StartupGateCommandKind.HoldPlayer:
                    logger.Msg($"StartupCover: {command.Detail}");
                    break;
                case StartupGateCommandKind.PlacePlayer:
                case StartupGateCommandKind.ReleaseHold:
                    // Decision-log entries: Tick polls placement/retry and hold state, rather than executing these twice.
                    break;
                case StartupGateCommandKind.Log:
                    logger.Warning($"StartupCover: {command.Detail}");
                    break;
            }
        }
    }

    private static void Show()
    {
        if (_root == null)
        {
            Build();
        }

        var title = LevelTitle.Title;
        _label.text = string.IsNullOrEmpty(title) ? "Loading" : title;
        _root.SetActive(true);
        _visible = true;
    }

    private static void Hide()
    {
        if (_root != null)
        {
            _root.SetActive(false);
        }

        _visible = false;
    }

    private static void Build()
    {
        _root = EditorUi.NewCanvas("MegabonkLevelsStartupCover");
        var canvas = _root.GetComponent<Canvas>();
        canvas.sortingOrder = SortingOrder;

        var backdrop = EditorUi.NewRect("Backdrop", _root.transform);
        backdrop.anchorMin = Vector2.zero;
        backdrop.anchorMax = Vector2.one;
        backdrop.offsetMin = Vector2.zero;
        backdrop.offsetMax = Vector2.zero;
        var image = backdrop.gameObject.AddComponent<Image>();
        image.color = Color.black;
        image.raycastTarget = false;

        var textRect = EditorUi.NewRect("Title", backdrop);
        textRect.anchorMin = new Vector2(0.5f, 0.5f);
        textRect.anchorMax = new Vector2(0.5f, 0.5f);
        textRect.pivot = new Vector2(0.5f, 0.5f);
        textRect.anchoredPosition = Vector2.zero;
        textRect.sizeDelta = new Vector2(LabelWidth, LabelHeight);
        _label = EditorUi.NewLabel(textRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.Center, LabelFontSize);
        _root.SetActive(false);
    }

    [HarmonyPatch(typeof(MyPlayer), nameof(MyPlayer.Spawn))]
    private static class SpawnPostfix
    {
        private static void Postfix() => OnGameSpawned();
    }

    [HarmonyPatch(typeof(MyPlayer), nameof(MyPlayer.StartPlayer))]
    private static class StartPlayerPostfix
    {
        private static void Postfix() => OnGameSpawned();
    }

    [HarmonyPatch(typeof(MyPlayer), nameof(MyPlayer.TeleportPlayerNextStage))]
    private static class NextStagePostfix
    {
        // Level files describe one stage; multi-stage levels will need a separate authored start for each stage.
        private static void Postfix() => OnGameSpawned();
    }
}
