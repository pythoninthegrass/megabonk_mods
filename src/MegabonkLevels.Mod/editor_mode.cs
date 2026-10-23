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

        if (!_session.Enter(MyTime.paused))
        {
            return;
        }

        MyTime.Pause();
        ReadLookSettings();
        var player = MyPlayer.Instance.transform.position;
        _pose = FreeFlyCamera.OverviewPose(player.x, player.y, player.z);
        CameraOverride.Set(_pose);
        EditorPalette.OnEditorEntered(logger);
        EditorTileTools.OnEditorEntered(logger);
        logger.Msg($"EditorMode: entered, MyTime.paused={MyTime.paused}.");
    }

    private static void Exit(MelonLogger.Instance logger)
    {
        if (!_session.TryExit(out var shouldUnpause))
        {
            return;
        }

        _looking = false;
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
        // A sweep that starts off the palette keeps turning when the pointer crosses it.
        if (EditorInput.GetMouseButtonDown(1))
        {
            _looking = !EditorPalette.PointerOverPanel && !EditorTileTools.PointerOverEditorOverlay;
        }

        if (CenterRequested())
        {
            var player = MyPlayer.Instance.transform.position;
            _pose = FreeFlyCamera.OverviewPose(player.x, player.y, player.z);
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
