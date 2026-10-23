using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json.Nodes;
using Il2CppAssets.Scripts.Actors.Player;
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
    private static string _processingDir;
    private static string _doneDir;
    private static string _rejectedDir;
    private static string _resultsDir;
    private static bool _enabled;
    private static float _nextPoll;

    public static bool Enabled => _enabled;

    public static void Install(MelonLogger.Instance logger)
    {
        var root = Path.Combine(MelonEnvironment.GameRootDirectory, "harness");
        if (!File.Exists(Path.Combine(root, "enabled")))
        {
            return;
        }

        _logger = logger;
        _commandsDir = Path.Combine(root, "commands");
        _processingDir = Path.Combine(root, "processing");
        _doneDir = Path.Combine(root, "done");
        _rejectedDir = Path.Combine(root, "rejected");
        Directory.CreateDirectory(_commandsDir);
        Directory.CreateDirectory(_processingDir);
        Directory.CreateDirectory(_doneDir);
        _resultsDir = Path.Combine(root, "results");
        Directory.CreateDirectory(_rejectedDir);
        Directory.CreateDirectory(_resultsDir);
        _enabled = true;
        WarnOnUnparseableKeyNames();
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
            WriteResult(file, HarnessResult.Failure(null, error));
            MoveTo(file, _rejectedDir);
            return;
        }

        // Move first so a command that throws or quits the game is never replayed.
        var processingFile = MoveTo(file, _processingDir);
        try
        {
            var result = Execute(command);
            WriteResult(file, HarnessResult.Success(command.Name, result));
            MoveTo(processingFile, _doneDir);
        }
        catch (Exception ex)
        {
            _logger.Error($"DevHarness: '{command.Kind}' failed: {ex.Message}");
            WriteResult(file, HarnessResult.Failure(command.Name, ex.Message));
            MoveTo(processingFile, _rejectedDir);
        }
    }

    private static JsonObject Execute(HarnessCommand command)
    {
        switch (command.Kind)
        {
            case HarnessCommandKind.LoadLevel:
                _logger.Msg($"DevHarness: load-level '{command.Path}'.");
                // Always resolve relative paths from the repo workspace into the game's Z: mount.
                // run.py already rewrites host paths when invoked, but accept both repo-relative and absolute paths.
                var path = command.Path;
                if (!Path.IsPathRooted(path) && File.Exists(Path.Combine(Environment.CurrentDirectory, path)))
                {
                    path = Path.Combine(Environment.CurrentDirectory, path);
                }
                LevelLoaderPatch.LoadAndStart(path, _logger);
                // After loading, request editor auto-reenter so the run starts in editor mode for Forest.
                EditorMode.RequestReenter(_logger);
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
            case HarnessCommandKind.ApplyPendingEdits:
                _logger.Msg("DevHarness: apply-pending-edits requested.");
                try
                {
                    var applied = LiveEditPatch.ApplyPendingEdits(_logger);
                    if (applied > 0)
                    {
                        _logger.Msg($"DevHarness: applied {applied} pending edit(s)");
                    }
                    else
                    {
                        _logger.Msg("DevHarness: no pending edits or no active session");
                    }
                }
                catch (Exception ex)
                {
                    _logger.Error($"DevHarness: apply-pending-edits failed: {ex.Message}");
                }
                break;
            case HarnessCommandKind.Vulnerable:
                PlayerInvulnerability.Set(false, _logger);
                break;
            case HarnessCommandKind.Heartbeat:
                KillFloorWatcher.SetHeartbeat(command.Enabled, _logger);
                break;
            case HarnessCommandKind.Cells:
                PositionLabel.SetCellLog(command.Enabled, _logger);
                break;
            case HarnessCommandKind.Editor:
                EditorMode.Set(command.Enabled, _logger);
                break;
            case HarnessCommandKind.SteamReady:
                _logger.Msg($"DevHarness: Steamworks ready (build {GameBuildIdPatch.CurrentBuildId()}).");
                break;
            case HarnessCommandKind.State:
                return ReadState().ToJson();
            case HarnessCommandKind.Key:
                QueueKey(command.Input);
                break;
            case HarnessCommandKind.Mouse:
                QueueMouse(command.Input);
                break;
            case HarnessCommandKind.Type:
                EditorInput.Queue.EnqueueText(command.Input.Text);
                break;
            case HarnessCommandKind.Quit:
                _logger.Msg("DevHarness: quit requested, calling Application.Quit.");
                Application.Quit();
                break;
        }

        return null;
    }

    private static void QueueKey(InputArgs input)
    {
        var queue = EditorInput.Queue;
        switch (input.Action)
        {
            case "tap":
                queue.EnqueueTap(input.Key, input.Modifiers);
                break;
            case "down":
                queue.EnqueueKeyDown(input.Key);
                break;
            case "up":
                queue.EnqueueKeyUp(input.Key);
                break;
        }
    }

    private static void QueueMouse(InputArgs input)
    {
        var queue = EditorInput.Queue;
        if (input.Action == "clear")
        {
            queue.ClearMouse();
            return;
        }

        if (input.X is float x && input.Y is float y)
        {
            var (unityX, unityY) = ScreenPoint.ToUnity(x, y, Screen.height);
            queue.EnqueueMouseMove(unityX, unityY);
        }

        switch (input.Action)
        {
            case "click":
                queue.EnqueueClick(input.Button);
                break;
            case "down":
                queue.EnqueueMouseDown(input.Button);
                break;
            case "up":
                queue.EnqueueMouseUp(input.Button);
                break;
        }
    }

    private static void WarnOnUnparseableKeyNames()
    {
        foreach (var name in KeyNames.All.Where(name => !Enum.TryParse<KeyCode>(name, out _)))
        {
            _logger.Warning($"DevHarness: key name '{name}' is not a UnityEngine.KeyCode member.");
        }
    }

    private static GameStateSnapshot ReadState()
    {
        var editor = EditorMode.Active;
        var player = MyPlayer.Instance;
        PlayerSnapshot? playerSnapshot = null;
        if (player != null)
        {
            var position = player.transform.position;
            playerSnapshot = new PlayerSnapshot(position.x, position.y, position.z, PositionLabel.CellOf(position.x, position.z));
        }

        return new GameStateSnapshot(
            LevelLoaded: CustomLevelState.IsActive,
            KillFloorArmed: KillFloorWatcher.Armed,
            Editor: editor,
            Frozen: MyTime.paused,
            Invulnerable: PlayerInvulnerability.Active,
            Player: playerSnapshot,
            EditorTool: editor ? EditorTileTools.CurrentTool.ToString() : null,
            Selected: editor ? EditorObjectTools.Selected?.Serialize() : null,
            PaletteEntries: editor ? EditorPalette.Selection.Entries.Count : null,
            ScreenWidth: Screen.width,
            ScreenHeight: Screen.height);
    }

    private static void WriteResult(string commandFile, HarnessResult result)
    {
        try
        {
            var target = Path.Combine(_resultsDir, Path.GetFileName(commandFile));
            var staging = target + ".tmp";
            File.WriteAllText(staging, result.ToJson(), new UTF8Encoding(false));
            File.Move(staging, target, overwrite: true);
        }
        catch (Exception ex)
        {
            _logger.Warning($"DevHarness: could not write result for '{Path.GetFileName(commandFile)}': {ex.Message}");
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

    private static string MoveTo(string file, string dir)
    {
        var target = Path.Combine(dir, Path.GetFileName(file));
        File.Move(file, target, overwrite: true);
        return target;
    }
}
