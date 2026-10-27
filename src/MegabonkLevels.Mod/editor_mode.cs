using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Player;
using Il2CppAssets.Scripts.UI.Debug;
using Il2CppAssets.Scripts.Utility;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Editor overlay mode: F8 (or the harness) freezes the run through MyTime.Pause and flies the camera free of the player while the right mouse button is held.
public static class EditorMode
{
    private const KeyCode ToggleKey = KeyCode.F8;
    private const KeyCode CenterKey = KeyCode.C;
    private const float LookSensitivityScale = 1.1f;
    private static readonly FreeFlySettings DefaultSettings = new(MoveSpeed: 60f, FastMultiplier: 4f, LookDegreesPerUnit: 1f);

    private static readonly EditorSessionState _session = new();
    private static CameraPose _pose;
    private static FreeFlySettings _settings = DefaultSettings;
    private static float _horizontalSign = 1f;
    private static float _verticalSign = 1f;
    private static bool _looking;
    private static bool _reenterRequested;

    // The editor can be entered before the grid session exists, so the grid-aware overview is applied once the grid appears.
    private static bool _overviewAwaitsGrid;

    public static bool Active => _session.Active;

    public static void Tick(MelonLogger.Instance logger)
    {
        if (_session.Active && !RunInProgress())
        {
            Exit(logger);
        }

        if (EditorReenterPolicy.ShouldEnter(_reenterRequested, _session.Active, RunInProgress(), ConsoleOpen()))
        {
            _reenterRequested = false;
            Enter(logger);
        }

        if (EditorInput.GetKeyDown(ToggleKey) && !ConsoleOpen())
        {
            Set(!_session.Active, logger);
        }

        if (_session.Active)
        {
            EditorEscapeInput.Tick();
            EditorPalette.Tick();
            EditorTileTools.Tick();
            Fly();
        }
    }

    public static void Set(bool enabled, MelonLogger.Instance logger)
    {
        _reenterRequested = false;
        if (enabled)
        {
            Enter(logger);
        }
        else
        {
            Exit(logger);
        }
    }

    public static void RequestReenter(MelonLogger.Instance logger)
    {
        _reenterRequested = true;
        logger.Msg("EditorMode: re-enter requested after level load.");
    }

    private static void Enter(MelonLogger.Instance logger)
    {
        var camera = PlayerCamera.Instance?.camera;
        if (!RunInProgress() || camera == null)
        {
            logger.Warning("EditorMode: enter ignored, no run in progress.");
            return;
        }

        var support = CurrentMapSupport();
        if (!support.Supported)
        {
            logger.Warning($"EditorMode: unsupported map: {support.Reason}");
            return;
        }

        if (!_session.Enter(MyTime.paused))
        {
            return;
        }

        CustomLevelState.MarkEditorUsed();
        MyTime.Pause();
        ReadLookSettings();
        _pose = OverviewPoseForPlayer();
        _overviewAwaitsGrid = LiveEditPatch.Grid == null;
        CameraOverride.Set(_pose);
        EditorEscapeInput.Reset();
        EditorPalette.OnEditorEntered(logger);
        EditorTileTools.OnEditorEntered(logger);
        logger.Msg($"EditorMode: entered, MyTime.paused={MyTime.paused}.");
    }

    public static EditorMapSupportResult CurrentMapSupport()
    {
        var map = Il2CppAssets.Scripts.Managers.MapController.currentMap;
        return map == null
            ? new EditorMapSupportResult(true, "")
            : EditorMapSupport.Check(map.name, (int)map.mapType);
    }

    private static void Exit(MelonLogger.Instance logger)
    {
        if (!_session.TryExit(out var shouldUnpause))
        {
            return;
        }

        _looking = false;
        EditorEscapeInput.Reset();
        CameraOverride.Clear();
        EditorPalette.OnEditorExited();
        EditorTileTools.OnEditorExited();
        if (shouldUnpause)
        {
            MyTime.Unpause();
        }

        logger.Msg($"EditorMode: exited, MyTime.paused={MyTime.paused}.");
    }

    private static void Fly()
    {
        if (EditorTileTools.TextInputFocused)
        {
            _looking = false;
            return;
        }

        // A sweep that starts off the palette keeps turning when the pointer crosses it.
        if (EditorInput.GetMouseButtonDown(1))
        {
            _looking = !EditorPalette.PointerOverPanel && !EditorTileTools.PointerOverEditorOverlay;
        }

        if (_overviewAwaitsGrid && LiveEditPatch.Grid != null)
        {
            _overviewAwaitsGrid = false;
            _pose = OverviewPoseForPlayer();
        }

        if (CenterRequested())
        {
            _pose = OverviewPoseForPlayer();
        }

        var look = _looking && EditorInput.GetMouseButton(1);
        var input = new FreeFlyInput(
            Forward: Axis(KeyCode.W, KeyCode.S),
            Right: Axis(KeyCode.D, KeyCode.A),
            Up: Axis(KeyCode.Space, AltKey()),
            MouseDx: look ? EditorInput.GetAxisRaw("Mouse X") * _horizontalSign : 0f,
            MouseDy: look ? EditorInput.GetAxisRaw("Mouse Y") * _verticalSign : 0f,
            Fast: EditorInput.GetKey(KeyCode.LeftShift));

        _pose = FreeFlyCamera.Step(_pose, input, Time.unscaledDeltaTime, _settings);
        CameraOverride.Set(_pose);
    }

    // The game turns the player by 1 degree per raw mouse unit times this saved sensitivity, measured in play.
    private static void ReadLookSettings()
    {
        var controls = SaveManager.Instance?.config?.cfControlSettings;
        _settings = DefaultSettings with { LookDegreesPerUnit = (controls?.sensitivity ?? DefaultSettings.LookDegreesPerUnit) * LookSensitivityScale };
        _horizontalSign = controls?.inverted_horizontal_axis == 1 ? -1f : 1f;
        _verticalSign = controls?.inverted_vertical_axis == 1 ? -1f : 1f;
    }

    private static CameraPose OverviewPoseForPlayer()
    {
        var player = MyPlayer.Instance.transform.position;
        if (LiveEditPatch.Grid is not { } grid)
        {
            return FreeFlyCamera.OverviewPose(player.x, player.y, player.z);
        }

        var (centreX, centreZ) = OverviewTarget.CentreCell(grid.Width, grid.Depth);
        var (x, y, z) = OverviewTarget.Of(player.x, player.y, player.z, grid.Width, grid.Depth, grid.Spacing, grid.TileHeight, LiveEditPatch.TileAt(centreX, centreZ));
        return FreeFlyCamera.OverviewPose(x, y, z);
    }

    private static float Axis(KeyCode positive, KeyCode negative) =>
        EditorTileTools.TextInputFocused ? 0f : (EditorInput.GetKey(positive) ? 1f : 0f) - (EditorInput.GetKey(negative) ? 1f : 0f);

    // Ctrl+C is left free for copy shortcuts.
    private static bool CenterRequested() =>
        EditorInput.GetKeyDown(CenterKey)
        && !EditorTileTools.TextInputFocused
        && !EditorInput.GetKey(KeyCode.LeftControl)
        && !EditorInput.GetKey(KeyCode.RightControl);

    private static KeyCode AltKey() => EditorInput.GetKey(KeyCode.RightAlt) ? KeyCode.RightAlt : KeyCode.LeftAlt;

    private static bool RunInProgress() => MyPlayer.Instance != null && PlayerCamera.Instance != null;

    private static bool ConsoleOpen() => DebugConsole.Instance != null && DebugConsole.Instance.IsActive();
}
