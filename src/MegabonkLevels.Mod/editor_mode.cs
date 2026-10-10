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
    private const float LookSensitivityScale = 1.1f;
    private static readonly FreeFlySettings DefaultSettings = new(MoveSpeed: 60f, FastMultiplier: 4f, LookDegreesPerUnit: 1f);

    private static readonly EditorSessionState _session = new();
    private static CameraPose _pose;
    private static FreeFlySettings _settings = DefaultSettings;
    private static float _horizontalSign = 1f;
    private static float _verticalSign = 1f;

    public static bool Active => _session.Active;

    public static void Tick(MelonLogger.Instance logger)
    {
        if (_session.Active && !RunInProgress())
        {
            Exit(logger);
        }

        if (Input.GetKeyDown(ToggleKey) && !ConsoleOpen())
        {
            Set(!_session.Active, logger);
        }

        if (_session.Active)
        {
            EditorPalette.Tick();
            Fly();
        }
    }

    public static void Set(bool enabled, MelonLogger.Instance logger)
    {
        if (enabled)
        {
            Enter(logger);
        }
        else
        {
            Exit(logger);
        }
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
        var position = camera.transform.position;
        var rotation = camera.transform.eulerAngles;
        _pose = new CameraPose(position.x, position.y, position.z, NormalizePitch(rotation.x), rotation.y, rotation.z);
        CameraOverride.Set(_pose);
        EditorPalette.OnEditorEntered(logger);
        logger.Msg($"EditorMode: entered, MyTime.paused={MyTime.paused}.");
    }

    private static void Exit(MelonLogger.Instance logger)
    {
        if (!_session.TryExit(out var shouldUnpause))
        {
            return;
        }

        CameraOverride.Clear();
        EditorPalette.OnEditorExited();
        if (shouldUnpause)
        {
            MyTime.Unpause();
        }

        logger.Msg($"EditorMode: exited, MyTime.paused={MyTime.paused}.");
    }

    private static void Fly()
    {
        var look = Input.GetMouseButton(1) && !EditorPalette.PointerOverPanel;
        var input = new FreeFlyInput(
            Forward: Axis(KeyCode.W, KeyCode.S),
            Right: Axis(KeyCode.D, KeyCode.A),
            Up: Axis(KeyCode.Space, KeyCode.LeftControl),
            MouseDx: look ? Input.GetAxisRaw("Mouse X") * _horizontalSign : 0f,
            MouseDy: look ? Input.GetAxisRaw("Mouse Y") * _verticalSign : 0f,
            Fast: Input.GetKey(KeyCode.LeftShift));

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
        (Input.GetKey(positive) ? 1f : 0f) - (Input.GetKey(negative) ? 1f : 0f);

    // Unity reports pitch in [0, 360); the free-fly maths works in [-180, 180).
    private static float NormalizePitch(float degrees) => degrees > 180f ? degrees - 360f : degrees;

    private static bool RunInProgress() => MyPlayer.Instance != null && PlayerCamera.Instance != null;

    private static bool ConsoleOpen() => DebugConsole.Instance != null && DebugConsole.Instance.IsActive();
}
