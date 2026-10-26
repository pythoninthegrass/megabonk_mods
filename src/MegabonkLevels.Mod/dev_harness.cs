using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json.Nodes;
using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Player;
using Il2CppAssets.Scripts.Utility;
using Il2CppInterop.Runtime;
using MelonLoader;
using MelonLoader.Utils;
using UnityEngine;

namespace MegabonkLevels;

// Development-only command channel: scripts/run.py drops JSON command files into <game dir>/harness/commands.
// Inert unless <game dir>/harness/enabled exists when the game starts; see docs/development.md.
public static class DevHarness
{
    private const float PollIntervalSeconds = 0.5f;
    private const float PlayerBodyOffsetY = 1.925f;
    private const float TeleportCameraPitch = 20f;

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
            case HarnessCommandKind.LoadBundle:
                return LoadBundle(command.Path);
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
                var readiness = SteamReadiness.Probe(GameBuildIdPatch.CurrentBuildId);
                if (readiness.Ready)
                {
                    _logger.Msg($"DevHarness: Steamworks ready (build {readiness.BuildId}).");
                }

                return readiness.ToJson();
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
            case HarnessCommandKind.Teleport:
                return Teleport(command.Teleport);
            case HarnessCommandKind.DismissLevelUp:
                return DismissLevelUp(command.Choice);
            case HarnessCommandKind.Quit:
                _logger.Msg("DevHarness: quit requested, calling Application.Quit.");
                Application.Quit();
                break;
        }

        return null;
    }

    // The interop wrappers for the synchronous AssetBundle loaders fail on Il2CppSystem span types, so this uses the async API (the parameterless LoadAllAssetsAsync has no native body, hence the Type overload); reading .assetBundle and .allAssets blocks until the load completes.
    private static JsonObject LoadBundle(string path)
    {
        var bundle = AssetBundle.LoadFromFileAsync(path).assetBundle;
        if (bundle == null)
        {
            throw new InvalidOperationException($"no AssetBundle loaded from '{path}'");
        }

        try
        {
            var assets = new JsonArray();
            GameObject prefab = null;
            foreach (var asset in bundle.LoadAllAssetsAsync(Il2CppType.Of<UnityEngine.Object>()).allAssets)
            {
                assets.Add($"{asset.name}:{asset.GetIl2CppType().Name}");
                prefab ??= asset.TryCast<GameObject>();
            }

            if (prefab == null)
            {
                throw new InvalidOperationException($"bundle '{path}' holds no GameObject asset");
            }

            _logger.Msg($"DevHarness: load-bundle '{path}' loaded prefab '{prefab.name}' among {assets.Count} asset(s).");
            return new JsonObject { ["assets"] = assets, ["prefab"] = prefab.name };
        }
        finally
        {
            bundle.Unload(true);
        }
    }

    private static JsonObject Teleport(TeleportArgs args)
    {
        var player = MyPlayer.Instance;
        if (player == null)
        {
            throw new InvalidOperationException("no player: start a run first");
        }

        var target = args.Cell is { } cell ? CellFeetPoint(cell[0], cell[1], player.transform.position.y - PlayerBodyOffsetY) : new Vector3(args.Position[0], args.Position[1], args.Position[2]);
        if (KillFloor.ShouldKill(target.y, KillFloorWatcher.FloorY))
        {
            throw new InvalidOperationException($"target y={target.y} is below the kill floor y={KillFloorWatcher.FloorY}");
        }

        var facing = player.transform.forward;
        player.TeleportPlayerImmediate(target, facing, facing, TeleportCameraPitch);
        _logger.Msg($"DevHarness: teleport to {target}.");

        // The transform only follows the Rigidbody on the next physics sync, so read the body itself.
        var reached = player.playerMovement.rb.position;
        return new JsonObject
        {
            ["position"] = new JsonArray(reached.x, reached.y, reached.z),
            ["cell"] = PositionLabel.CellOf(reached.x, reached.z) is { } c ? new JsonArray(c.X, c.Z) : null,
        };
    }

    private static Vector3 CellFeetPoint(int cellX, int cellZ, float currentFeetY)
    {
        if (LiveEditPatch.Grid is not { } grid)
        {
            throw new InvalidOperationException("no level grid: a cell teleport needs a loaded custom level");
        }

        if (cellX < 0 || cellX >= grid.Width || cellZ < 0 || cellZ >= grid.Depth)
        {
            throw new InvalidOperationException($"cell ({cellX},{cellZ}) is outside the {grid.Width}x{grid.Depth} grid");
        }

        var (x, y, z) = TeleportTarget.CellStandingPoint(cellX, cellZ, LiveEditPatch.TileAt(cellX, cellZ), grid.Width, grid.Depth, grid.Spacing, grid.TileHeight, currentFeetY);
        return new Vector3(x, y, z);
    }

    private static JsonObject DismissLevelUp(int choice)
    {
        if (!LevelupScreen.isLevelingUp)
        {
            return new JsonObject { ["dialogWasOpen"] = false, ["chosen"] = null };
        }

        var buttons = UnityEngine.Object.FindObjectOfType<LevelupScreen>().upgradePicker.buttons;
        if (choice >= buttons.Length)
        {
            throw new InvalidOperationException($"choice {choice} is out of range; the dialog offers {buttons.Length} upgrades");
        }

        var button = buttons[choice];
        var chosen = button.upgradable.GetName();
        button.SelectUpgrade();

        // Closing the dialog unpauses the run, which would end an editor session's freeze.
        if (EditorMode.Active)
        {
            MyTime.Pause();
        }

        _logger.Msg($"DevHarness: dismiss-levelup chose {choice} '{chosen}'.");
        return new JsonObject { ["dialogWasOpen"] = true, ["chosen"] = chosen };
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
