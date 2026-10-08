using System;
using System.Collections;
using System.IO;
using System.Linq;
using Il2CppAssets.Scripts.Utility;
using MelonLoader;
using MelonLoader.Utils;
using UnityEngine;

namespace MegabonkLevels;

// Development-only command channel: scripts/run.py drops JSON command files into <game dir>/harness/commands.
// Inert unless <game dir>/harness/enabled exists when the game starts; see docs/development.md.
public static class DevHarness
{
    private const float PollIntervalSeconds = 0.5f;

    private static MelonLogger.Instance _logger;
    private static string _commandsDir;
    private static string _doneDir;
    private static string _rejectedDir;
    private static bool _enabled;
    private static float _nextPoll;

    public static void Install(MelonLogger.Instance logger)
    {
        var root = Path.Combine(MelonEnvironment.GameRootDirectory, "harness");
        if (!File.Exists(Path.Combine(root, "enabled")))
        {
            return;
        }

        _logger = logger;
        _commandsDir = Path.Combine(root, "commands");
        _doneDir = Path.Combine(root, "done");
        _rejectedDir = Path.Combine(root, "rejected");
        Directory.CreateDirectory(_commandsDir);
        Directory.CreateDirectory(_doneDir);
        Directory.CreateDirectory(_rejectedDir);
        _enabled = true;
        logger.Msg($"DevHarness: enabled, watching '{_commandsDir}'.");
    }

    public static void Poll()
    {
        if (!_enabled || Time.unscaledTime < _nextPoll)
        {
            return;
        }

        _nextPoll = Time.unscaledTime + PollIntervalSeconds;

        foreach (var file in Directory.GetFiles(_commandsDir, "*.json").OrderBy(f => f, StringComparer.Ordinal))
        {
            Process(file);
        }
    }

    private static void Process(string file)
    {
        string json;
        try
        {
            json = File.ReadAllText(file);
        }
        catch (IOException)
        {
            // Writer still holds the file; retry on the next poll.
            return;
        }

        if (!HarnessCommand.TryParse(json, out var command, out var error))
        {
            _logger.Warning($"DevHarness: rejected '{Path.GetFileName(file)}': {error}");
            MoveTo(file, _rejectedDir);
            return;
        }

        // Move first so a command that throws or quits the game is never replayed.
        MoveTo(file, _doneDir);
        try
        {
            Execute(command);
        }
        catch (Exception ex)
        {
            _logger.Error($"DevHarness: '{command.Kind}' failed: {ex.Message}");
        }
    }

    private static void Execute(HarnessCommand command)
    {
        switch (command.Kind)
        {
            case HarnessCommandKind.LoadLevel:
                _logger.Msg($"DevHarness: load-level '{command.Path}'.");
                LevelLoaderPatch.LoadAndStart(command.Path, _logger);
                break;
            case HarnessCommandKind.Screenshot:
                _logger.Msg($"DevHarness: screenshot '{command.Path}'.");
                MelonCoroutines.Start(CaptureAtEndOfFrame(command.Path));
                break;
            case HarnessCommandKind.Freeze:
                MyTime.Pause();
                _logger.Msg($"DevHarness: freeze, MyTime.paused={MyTime.paused}.");
                break;
            case HarnessCommandKind.Resume:
                MyTime.Unpause();
                _logger.Msg($"DevHarness: resume, MyTime.paused={MyTime.paused}.");
                break;
            case HarnessCommandKind.Camera:
                CameraOverride.Set(command.Pose);
                _logger.Msg($"DevHarness: camera override {command.Pose}.");
                break;
            case HarnessCommandKind.CameraClear:
                CameraOverride.Clear();
                _logger.Msg("DevHarness: camera override cleared.");
                break;
            case HarnessCommandKind.Invulnerable:
                PlayerInvulnerability.Set(true, _logger);
                break;
            case HarnessCommandKind.Vulnerable:
                PlayerInvulnerability.Set(false, _logger);
                break;
            case HarnessCommandKind.HeartbeatOn:
                KillFloorWatcher.SetHeartbeat(true, _logger);
                break;
            case HarnessCommandKind.HeartbeatOff:
                KillFloorWatcher.SetHeartbeat(false, _logger);
                break;
            case HarnessCommandKind.Quit:
                _logger.Msg("DevHarness: quit requested, calling Application.Quit.");
                Application.Quit();
                break;
        }
    }

    // ScreenCapture.CaptureScreenshot(path) and ImageConversion.EncodeToPNG both fail in Il2CppInterop
    // marshalling, so read the finished frame back with Texture2D.ReadPixels and encode the PNG ourselves.
    private static IEnumerator CaptureAtEndOfFrame(string path)
    {
        yield return new WaitForEndOfFrame();

        try
        {
            var texture = new Texture2D(Screen.width, Screen.height, TextureFormat.RGB24, false);
            texture.ReadPixels(new Rect(0, 0, Screen.width, Screen.height), 0, 0);
            texture.Apply();
            var pixels = texture.GetPixels32();
            var rgb = new byte[pixels.Length * 3];
            for (var i = 0; i < pixels.Length; i++)
            {
                rgb[i * 3] = pixels[i].r;
                rgb[i * 3 + 1] = pixels[i].g;
                rgb[i * 3 + 2] = pixels[i].b;
            }

            File.WriteAllBytes(path, PngEncoder.EncodeRgb(texture.width, texture.height, rgb));
            UnityEngine.Object.Destroy(texture);
            _logger.Msg($"DevHarness: wrote screenshot '{path}'.");
        }
        catch (Exception ex)
        {
            _logger.Error($"DevHarness: screenshot '{path}' failed: {ex.Message}");
        }
    }

    private static void MoveTo(string file, string dir)
    {
        var target = Path.Combine(dir, Path.GetFileName(file));
        File.Move(file, target, overwrite: true);
    }
}
