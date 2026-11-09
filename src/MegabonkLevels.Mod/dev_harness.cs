using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Text.Json.Nodes;
using Assets.Scripts.Actors.Player;
using Assets.Scripts.Managers;
using Assets.Scripts.UI.InGame.Levelup;
using Assets.Scripts.UI.InGame.Rewards;
using Assets.Scripts.Utility;
using Il2CppInterop.Runtime;
using UnityEngine;

namespace MegabonkLevels;

// Development-only command channel: scripts/run.py drops JSON command files into <game dir>/harness/commands.
// Inert unless <game dir>/harness/enabled exists when the game starts; see docs/development.md.
public static class DevHarness
{
    private const float PollIntervalSeconds = 0.5f;
    private const float PlayerBodyOffsetY = TeleportTarget.PlayerBodyOffsetY;
    private const float TeleportCameraPitch = 20f;

    private static ModLogger _logger;
    private static string _commandsDir;
    private static string _processingDir;
    private static string _doneDir;
    private static string _rejectedDir;
    private static string _resultsDir;
    private static bool _enabled;
    private static float _nextPoll;

    public static bool Enabled => _enabled;

    public static void Install(ModLogger logger)
    {
        _logger = logger;
        var root = ModPaths.HarnessDirectory;
        if (!File.Exists(Path.Combine(root, "enabled")))
        {
            return;
        }

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
        var result = Run(command);
        WriteResult(file, result);
        MoveTo(processingFile, result.Ok ? _doneDir : _rejectedDir);
    }

    // In-process entry point; call from the main thread. Works without the harness/enabled marker, which gates only the file queue.
    public static HarnessResult Run(HarnessCommand command)
    {
        var result = HarnessRunner.Run(command, Execute);
        if (!result.Ok)
        {
            _logger.Error($"DevHarness: '{command.Kind}' failed: {result.Error}");
        }

        return result;
    }

    private static JsonObject Execute(HarnessCommand command)
    {
        switch (command.Kind)
        {
            case HarnessCommandKind.Console:
                var plan = ConsoleOverlay.SubmitLine(command.Line);
                var lines = new JsonArray();
                foreach (var printed in plan.PrintLines)
                {
                    foreach (var line in ConsoleScrollback.Split(printed))
                    {
                        lines.Add(line);
                    }
                }

                return new JsonObject { ["ok"] = plan.Ok, ["lines"] = lines };
            case HarnessCommandKind.LoadLevel:
                _logger.Msg($"DevHarness: load-level '{command.Path}'.");
                // Always resolve relative paths from the repo workspace into the game's Z: mount.
                // run.py already rewrites host paths when invoked, but accept both repo-relative and absolute paths.
                var path = command.Path;
                if (!Path.IsPathRooted(path) && File.Exists(Path.Combine(Environment.CurrentDirectory, path)))
                {
                    path = Path.Combine(Environment.CurrentDirectory, path);
                }
                LevelLoaderPatch.LoadAndStart(path, _logger, command.Overrides);
                // After loading, request editor auto-reenter so the run starts in editor mode for Forest.
                EditorMode.RequestReenter(_logger);
                break;
            case HarnessCommandKind.LoadBundle:
                return LoadBundle(command.Path);
            case HarnessCommandKind.ShaderReport:
                return ShaderReport.Build();
            case HarnessCommandKind.MaterialDump:
                return MaterialDump.Build(command.Path);
            case HarnessCommandKind.Screenshot:
                var target = ScreenshotPath.Resolve(command.Path, Environment.GetEnvironmentVariable(ScreenshotPath.EvidenceVariable), File.Exists);
                if (target.Error != null)
                {
                    throw new InvalidOperationException(target.Error);
                }

                _logger.Msg($"DevHarness: screenshot '{target.Path}'.");
                ModTick.Run(CaptureAtEndOfFrame(target.Path));
                return new JsonObject { ["message"] = $"screenshot: {target.Path}" };
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
            case HarnessCommandKind.Kill:
                KillPlayer();
                break;
            case HarnessCommandKind.RestartRun:
                RestartRun();
                break;
            case HarnessCommandKind.PressDeathConfirm:
                return DeathScreenPress.PressConfirm();
            case HarnessCommandKind.PressSummaryRestart:
                return DeathScreenPress.PressSummaryRestart();
            case HarnessCommandKind.Damage:
                return PlayerDamage.Apply(command.Damage);
            case HarnessCommandKind.KillEnemies:
                return EnemyKiller.Kill(command.KillTarget);
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
            case HarnessCommandKind.Spawns:
                EnemySpawns.Set(command.Enabled, _logger);
                break;
            case HarnessCommandKind.CharacterScreen:
                CharacterScreenPatch.SetRestricted(command.Enabled);
                if (!command.Enabled)
                {
                    LevelLoaderPatch.CancelAwaitingCharacter();
                }
                break;
            case HarnessCommandKind.Heartbeat:
                KillFloorWatcher.SetHeartbeat(command.Enabled, _logger);
                break;
            case HarnessCommandKind.Cells:
                PositionLabel.SetCellLog(command.Enabled, _logger);
                break;
            case HarnessCommandKind.Hud:
                HudControl.Set(command.Enabled, _logger);
                break;
            case HarnessCommandKind.Music:
                return LevelMusic.Transport(command.Music);
            case HarnessCommandKind.Coordinates:
                PositionLabel.SetVisible(command.Enabled, _logger);
                return new JsonObject { ["enabled"] = PositionLabel.Enabled, ["visible"] = PositionLabel.Visible };
            case HarnessCommandKind.Editor:
                if (command.Enabled && EditorMode.CurrentMapSupport() is { Supported: false } unsupported)
                {
                    throw new InvalidOperationException(unsupported.Reason);
                }

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
            case HarnessCommandKind.UiTree:
                return UiTree(command.Input);
            case HarnessCommandKind.ClickWidget:
                return ClickWidget(command.Input.Text);
            case HarnessCommandKind.SaveLevel:
                return EditorTileTools.SaveLevel(command.Path);
            case HarnessCommandKind.EditorLoad:
                return EditorTileTools.LoadLevel(command.Path);
            case HarnessCommandKind.NewLevel:
                return NewLevel.Create(command.Path, command.NewLevel.Value, _logger);
            case HarnessCommandKind.ListLevels:
                return ListLevels();
            case HarnessCommandKind.Palette:
                return PaletteRows();
            case HarnessCommandKind.QueryObjects:
                return QueryObjects(command.Query);
            case HarnessCommandKind.Teleport:
                return Teleport(command.Teleport);
            case HarnessCommandKind.Item:
                return PlayerItems.Apply(command.Item);
            case HarnessCommandKind.GrindSlide:
                return GrindSlide(command.Held);
            case HarnessCommandKind.FallDamage:
                return FallDamage.Read();
            case HarnessCommandKind.MusicProbe:
                return MusicProbe.Run(command.Input.Action, command.Path, command.Input.Variant, command.Input.Value, _logger);
            case HarnessCommandKind.Perf:
                return RunPerf(command.Perf);
            case HarnessCommandKind.DismissLevelUp:
                return DismissLevelUp(command.Choice);
            case HarnessCommandKind.DismissOffers:
                return DismissOffers(command.Offer, command.Skip);
            case HarnessCommandKind.Interact:
                return Interact(command.Interact);
            case HarnessCommandKind.Quit:
                _logger.Msg("DevHarness: quit requested, calling Application.Quit.");
                Application.Quit();
                break;
        }

        return null;
    }

    // The frame profiler's verbs: a measurement window, its report, live enemy counts and a held time scale. See docs/development.md.
    private static JsonObject RunPerf(PerfArgs args)
    {
        return args.Action switch
        {
            "start" => PerfMonitor.StartWindow(),
            "report" => PerfMonitor.Report(),
            "status" => PerfMonitor.Status(),
            "reset" => PerfMonitor.Reset(),
            "spawn" => PerfMonitor.Spawn(args.Count),
            "timescale" => PerfMonitor.SetTimeScale(args.Value),
            "toggle" => PerfMonitor.Toggle(args.Target, args.Enabled),
            "vsync" => PerfMonitor.SetVSync(args.Enabled),
            "render" => PerfMonitor.SetEnemyRenderers(args.Enabled),
            "physics" => PerfMonitor.SetEnemyPhysics(args.Enabled),
            "animation" => PerfMonitor.SetEnemyAnimation(args.Enabled),
            "health" => PerfMonitor.SetPlayerHealth(args.Hp ?? PerfLimits.DefaultPlayerHp),
            "census" => PerfMonitor.Census(),
            _ => throw new InvalidOperationException($"unknown perf action '{args.Action}'"),
        };
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

    private static List<UiWidget> EditorWidgets()
    {
        // Outside the editor the console is the only overlay with widgets, so it is the only one ui-tree can report there.
        if (!EditorMode.Active)
        {
            var outside = ConsoleOverlay.ListWidgets().ToList();
            if (outside.Count > 0)
            {
                return outside;
            }

            throw new InvalidOperationException("editor mode is off: the widgets only exist inside the editor or while the console is open");
        }

        return EditorTileTools.ListWidgets().Concat(EditorPalette.ListWidgets()).Concat(ConsoleOverlay.ListWidgets()).ToList();
    }

    private static JsonObject WidgetJson(UiWidget widget) =>
        new() { ["name"] = widget.Name, ["x"] = widget.X, ["y"] = widget.Y, ["width"] = widget.Width, ["height"] = widget.Height, ["enabled"] = widget.Enabled };

    private static JsonObject UiTree(InputArgs input)
    {
        var widgets = EditorWidgets();
        var result = new JsonObject { ["widgets"] = new JsonArray(widgets.Select(widget => (JsonNode)WidgetJson(widget)).ToArray()) };
        if (input.X is float x && input.Y is float y)
        {
            result["at"] = UiWidgets.At(widgets, x, y)?.Name;
        }

        return result;
    }

    private static JsonObject ClickWidget(string name)
    {
        if (!UiWidgets.TryFind(EditorWidgets(), name, out var widget, out var error))
        {
            throw new InvalidOperationException(error);
        }

        if (!widget.Enabled)
        {
            throw new InvalidOperationException($"widget '{widget.Name}' is disabled");
        }

        var (x, y) = widget.Centre;
        QueueMouse(new InputArgs { Action = "click", X = x, Y = y });
        _logger.Msg($"DevHarness: click-widget '{widget.Name}' at ({x}, {y}).");
        return WidgetJson(widget);
    }

    private static JsonObject ListLevels()
    {
        var levels = new JsonArray();
        foreach (var name in LiveEditPatch.ListLevelFiles())
        {
            levels.Add(name);
        }

        return new JsonObject { ["directory"] = LiveEditPatch.LevelsDirectoryPath(), ["levels"] = levels };
    }

    // Every entry the editor palette lists for the loaded map, as [id, display name, category, map] rows, without needing the editor open.
    private static JsonObject PaletteRows()
    {
        var rows = new JsonArray();
        foreach (var entry in EditorPalette.CatalogEntries())
        {
            rows.Add(new JsonArray(entry.Id.Serialize(), entry.DisplayName, entry.Category.ToString(), entry.Map.ToString()));
        }

        return new JsonObject { ["count"] = rows.Count, ["entries"] = rows };
    }

    private static JsonObject QueryObjects(QueryArgs args)
    {
        if (args.TypeName == nameof(MapController) || args.TypeName == typeof(MapController).FullName)
        {
            return ObjectQuery.ReadStatics(typeof(MapController), args.Fields, args.Depth);
        }

        var type = ObjectQuery.ResolveType(UnityObjectTypes(), args.TypeName);
        var items = Resources.FindObjectsOfTypeAll(Il2CppType.From(type)).Select(found => Activator.CreateInstance(type, found.Pointer)).ToList();
        return ObjectQuery.Read(type, items, args.Fields, args.Depth);
    }

    private static IEnumerable<Type> UnityObjectTypes()
    {
        foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            Type[] types;
            try
            {
                types = assembly.GetTypes();
            }
            catch (System.Reflection.ReflectionTypeLoadException ex)
            {
                types = ex.Types.Where(type => type != null).ToArray();
            }

            foreach (var type in types)
            {
                if (typeof(UnityEngine.Object).IsAssignableFrom(type))
                {
                    yield return type;
                }
            }
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
        StartupCover.OnHarnessTeleported();
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

    // Holds the slide button the grind gate reads so a scripted check needs no keyboard; with no value the read
    // goes back to the real device. slideHeld is what the gate sees afterwards, forced or not.
    private static JsonObject GrindSlide(bool? held)
    {
        GrindInput.Force(held, _logger);
        return new JsonObject
        {
            ["held"] = held is bool value ? JsonValue.Create(value) : null,
            ["slideHeld"] = JsonValue.Create(GrindInput.IsSlideHeld()),
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

    // Closes, skips or picks the visible reward window (level-up, shrine offers, chest, microwave).
    // The windows are BaseEncounterWindow subclasses sharing Open/OnClose/ChooseOffer; see docs/development.md.
    private static JsonObject DismissOffers(int? offer, bool skip)
    {
        // The game's own gate: EncounterWindows.encounterInProgress is true while a reward window is up, and false once it closed,
        // which is what keeps a LevelupScreen whose GameObject lingers active from being read as an open window.
        var encounterWindows = FindAll<EncounterWindows>().FirstOrDefault();
        var encounterInProgress = encounterWindows?.encounterInProgress ?? false;
        var levelingUp = LevelupScreen.isLevelingUp;

        var activeLevelup = FindAll<LevelupScreen>().FirstOrDefault(w => w.gameObject.activeInHierarchy && (levelingUp || encounterInProgress));
        var window = (BaseEncounterWindow)activeLevelup
            ?? (BaseEncounterWindow)FindAll<EncounterUi>().FirstOrDefault(w => w.gameObject.activeInHierarchy)
            ?? (BaseEncounterWindow)FindAll<ChestWindowUi>().FirstOrDefault(w => w.gameObject.activeInHierarchy)
            ?? (BaseEncounterWindow)FindAll<MicrowaveUi>().FirstOrDefault(w => w.gameObject.activeInHierarchy);
        if (window == null)
        {
            _logger.Msg($"DevHarness: dismiss-offers found no active reward window (levelup={levelingUp}, encounterInProgress={encounterInProgress}, " +
                $"encounterUis=[{string.Join(", ", FindAll<EncounterUi>().Select(w => $"{w.gameObject.name}:{w.gameObject.activeInHierarchy}"))}]).");
            return new JsonObject { ["windowWasOpen"] = false, ["window"] = null };
        }

        var label = $"{window.GetIl2CppType().Name} ({window.gameObject.name})";
        string action;
        bool closed;
        string reason = null;

        // Detection uses either flag. Skip and choose clear LevelupScreen.isLevelingUp in the same call, which is the only
        // signal for them; a close clears EncounterWindows.encounterInProgress synchronously, and isLevelingUp is already
        // false on a shrine offer window, so closing has to read the encounter flag to mean anything.
        bool LevelupClosed() => !LevelupScreen.isLevelingUp;
        bool LevelupClosedByClose() => !(encounterWindows?.encounterInProgress ?? false);

        if (skip)
        {
            if (window is not LevelupScreen skipScreen)
            {
                throw new InvalidOperationException($"'{label}' is not the level-up window; skip only applies there");
            }

            skipScreen.Skip();
            closed = LevelupClosed();
            action = "skip";
            if (!closed)
            {
                reason = SkipRefusal(skipScreen);
            }
        }
        else if (offer is int index)
        {
            if (window is LevelupScreen levelup)
            {
                // LevelupScreen.ChooseOffer is an empty override; its picks go through the UpgradeButton, as in dismiss-levelup.
                var buttons = levelup.upgradePicker.buttons;
                if (index >= buttons.Length)
                {
                    throw new InvalidOperationException($"choice {index} is out of range; the window offers {buttons.Length} upgrades");
                }

                if (buttons[index].upgradable == null)
                {
                    throw new InvalidOperationException($"offer {index} on '{label}' has no upgrade to select; a shrine reward window is dismissed with the default close, not chosen");
                }

                buttons[index].SelectUpgrade();
                closed = LevelupClosed();
            }
            else
            {
                window.ChooseOffer(index);
                closed = !window.gameObject.activeInHierarchy;
            }

            action = $"choose {index}";
        }
        else
        {
            if (window is LevelupScreen levelupScreen)
            {
                levelupScreen.CloseLevelupScreen();
            }
            else
            {
                window.OnClose();
            }

            closed = window is LevelupScreen ? LevelupClosedByClose() : !window.gameObject.activeInHierarchy;
            action = "close";
        }

        // Closing the window unpauses the run, which would end an editor session's freeze.
        if (closed && EditorMode.Active)
        {
            MyTime.Pause();
        }

        _logger.Msg($"DevHarness: dismiss-offers {action} on {label}, closed={closed}" + (reason is null ? "." : $", reason={reason}."));
        return new JsonObject
        {
            ["windowWasOpen"] = true,
            ["window"] = label,
            ["action"] = action,
            ["closed"] = closed,
            ["reason"] = reason,
        };
    }

    // Activates the nearest interactable through the game's own CanInteract/Interact, bypassing DetectInteractables'
    // hover gate, which no harness key press can reach because harness input never enters Rewired gameplay UI.
    private static JsonObject Interact(InteractArgs args)
    {
        var player = MyPlayer.Instance;
        if (player == null)
        {
            throw new InvalidOperationException("no player: start a run first");
        }

        var origin = player.transform.position;
        BaseInteractable target = null;
        var targetType = (Type)null;
        var targetDistance = 0f;
        var candidates = 0;
        var seen = new HashSet<IntPtr>();
        foreach (var type in InteractableTypes())
        {
            foreach (var found in Resources.FindObjectsOfTypeAll(Il2CppType.From(type)))
            {
                if (found == null) continue;

                BaseInteractable item;
                try
                {
                    item = (BaseInteractable)Activator.CreateInstance(type, found.Pointer);
                }
                catch (Exception)
                {
                    continue;
                }

                // Prefab assets and inactive copies report a useless origin and must never be activated; the base-type
                // sweep returns every subclass, so also drop instances an earlier sweep already recorded.
                if (item?.gameObject == null || !item.gameObject.activeInHierarchy || !seen.Add(found.Pointer)) continue;

                if (args.Type is { } filter
                    && !type.Name.Contains(filter, StringComparison.OrdinalIgnoreCase)
                    && !item.gameObject.name.Contains(filter, StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                var distance = Vector3.Distance(item.transform.position, origin);
                if (args.MaxDistance is { } max && distance > max) continue;

                candidates++;
                if (target == null || distance < targetDistance)
                {
                    target = item;
                    targetType = type;
                    targetDistance = distance;
                }
            }
        }

        if (target == null)
        {
            throw new InvalidOperationException(
                $"no interactable matched (type={args.Type ?? "any"}, maxDistance={args.MaxDistance?.ToString(System.Globalization.CultureInfo.InvariantCulture) ?? "any"})");
        }

        var name = target.gameObject.name;
        var canInteract = target.CanInteract();
        if (!canInteract && !args.Force)
        {
            _logger.Msg($"DevHarness: interact refused on {name} ({targetType.Name}), CanInteract returned false.");
            return new JsonObject
            {
                ["interacted"] = false,
                ["reason"] = "CanInteract returned false; pass force to call Interact anyway",
                ["name"] = name,
                ["type"] = targetType.Name,
                ["distance"] = targetDistance,
                ["candidates"] = candidates,
            };
        }

        string prompt;
        try
        {
            prompt = target.GetInteractString();
        }
        catch (Exception)
        {
            prompt = null;
        }

        var result = target.Interact();
        _logger.Msg($"DevHarness: interact with {name} ({targetType.Name}) at {targetDistance:F1}, prompt '{prompt}', result {result}.");
        return new JsonObject
        {
            ["interacted"] = true,
            ["name"] = name,
            ["type"] = targetType.Name,
            ["distance"] = targetDistance,
            ["prompt"] = prompt,
            ["canInteract"] = canInteract,
            ["result"] = result,
            ["candidates"] = candidates,
        };
    }

    private static List<Type> _interactableTypes;

    // Derived wrappers first so a candidate reports its real class; the abstract base's non-abstract wrapper
    // runs last as the fallback that still sees subclasses whose own wrapper failed to load.
    private static List<Type> InteractableTypes()
    {
        if (_interactableTypes == null)
        {
            _interactableTypes = UnityObjectTypes()
                .Where(type => typeof(BaseInteractable).IsAssignableFrom(type) && !type.IsAbstract)
                .OrderByDescending(type => type != typeof(BaseInteractable))
                .ToList();
        }

        return _interactableTypes;
    }

    // Why the game kept the level-up window open after Skip(): its own private skip counters and utility price.
    private static string SkipRefusal(LevelupScreen screen)
    {
        var hasSkips = typeof(LevelupScreen).GetField("hasSkips", BindingFlags.Static | BindingFlags.NonPublic | BindingFlags.Public)?.GetValue(null) as bool?;
        if (hasSkips == false)
        {
            return "no skips left";
        }

        var used = InvokeLevelupInt(screen, "GetSkipsUsed");
        var price = used is int spent ? InvokeLevelupInt(screen, "GetShopToolPrice", spent) : null;
        return price is int cost
            ? $"the game refused the skip; skip price {cost}, skips used {used}"
            : "the game refused the skip and left the window open";
    }

    private static int? InvokeLevelupInt(LevelupScreen screen, string name, params object[] args)
    {
        var method = typeof(LevelupScreen).GetMethod(name, BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public);
        if (method is null)
        {
            return null;
        }

        try
        {
            return Convert.ToInt32(method.Invoke(screen, args));
        }
        catch (Exception e)
        {
            _logger.Msg($"DevHarness: LevelupScreen.{name} failed: {e.GetBaseException().Message}");
            return null;
        }
    }

    // Instance wrappers built from Resources.FindObjectsOfTypeAll, the one sweep proven to see the UI objects;
    // generic FindObjectsOfType and C# type filters over MonoBehaviour sweeps both miss them under interop.
    private static List<T> FindAll<T>()
        where T : class
    {
        var items = new List<T>();
        foreach (var found in Resources.FindObjectsOfTypeAll(Il2CppType.From(typeof(T))))
        {
            if (found != null)
            {
                items.Add((T)Activator.CreateInstance(typeof(T), found.Pointer));
            }
        }

        return items;
    }

    // Ends the run through PlayerHealth.KillPlayer, the same call the kill floor uses, so it ignores invulnerability.
    private static void KillPlayer()
    {
        var health = MyPlayer.Instance?.inventory?.playerHealth;
        if (health == null)
        {
            _logger.Warning("DevHarness: kill ignored, no player in the scene.");
            return;
        }

        health.KillPlayer();
        _logger.Msg("DevHarness: player killed.");
    }

    // Runs the game's own restart, the death screen's Retry button, without OS-level input on the Rewired menu.
    private static void RestartRun()
    {
        Assets.Scripts.Managers.MapController.RestartRun();
        _logger.Msg("DevHarness: restart-run requested.");
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
            case "scroll":
                queue.EnqueueScroll(input.Value ?? 0f);
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
            SpawnsOff: EnemySpawns.Off,
            Player: playerSnapshot,
            EditorTool: editor ? EditorTileTools.CurrentTool.ToString() : null,
            Selected: editor ? EditorObjectTools.Selected?.Serialize() : null,
            PaletteEntries: editor ? EditorPalette.Selection.Entries.Count : null,
            Edits: editor ? EditorTileTools.ReadEdits() : null,
            ScreenWidth: Screen.width,
            ScreenHeight: Screen.height,
            CoordinatesEnabled: PositionLabel.Enabled,
            CoordinatesVisible: PositionLabel.Visible,
            CursorVisible: Cursor.visible,
            CursorLocked: Cursor.lockState != CursorLockMode.None);
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

            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path)));
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
