using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Player;
using Il2CppAssets.Scripts.Managers;
using Il2CppAssets.Scripts.MapGeneration.ProceduralTiles;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// LowestLevel is the lowest tile level the generator produced, the floor for the editor's Lower tool.
public readonly record struct LiveGrid(int Width, int Depth, float Spacing, float TileHeight, int LowestLevel);

// On A_GenerationComplete, indexes the live spawned tiles/objects by genId and, when a level file
// started the run, applies that file's edits through LiveEditPlan. See docs/runtime-map-structure.md
// for the genId scheme and where each category lives in the scene.
public static class LiveEditPatch
{
    private const string TileObjectsParentName = "TileObjectsParent";

    private static IReadOnlyList<EditOp> _pendingEdits;
    private static IReadOnlyList<EditOp> _levelEdits;
    private static bool _noGrass;
    private static IReadOnlyList<float> _playerStart;
    private static float? _maxSlopeAngle;
    private static float? _killFloorY;
    private static IReadOnlyList<float> _bossSpawnPosition;
    private static bool _grindRequiresSlide;
    private static string _fallDamageCharacter;
    private static IReadOnlyDictionary<string, string> _packKitVersions;
    private static LevelFile _randomizationSettings;
    private static Session _session;
    private static int _runGeneration;

    // Increments each time a new map generation completes. EditorTileTools uses this to detect
    // when the level has changed and the undo/redo session should be reset.
    public static int RunGeneration => _runGeneration;

    // Where the level authors the boss appearing when its boss portal is activated, or null to let the game spawn the
    // boss at the portal itself. See BossSpawnRedirectPatch.
    public static IReadOnlyList<float> BossSpawnPosition => _bossSpawnPosition;

    // Whether a rail touch on this level needs the slide button held. See GrindGatePatch.
    public static bool GrindRequiresSlide => _grindRequiresSlide;

    // Name of the character whose fall damage this level scores landings with, or null. See FallDamagePatch.
    public static string FallDamageCharacter => _fallDamageCharacter;

    // Set by LevelLoaderPatch right before it starts a run, consumed (and cleared) by the next
    // generation so a later vanilla run is never edited.
    public static void SetPendingEdits(IReadOnlyList<EditOp> edits, bool noGrass = false, IReadOnlyList<float> playerStart = null, float? maxSlopeAngle = null, float? killFloorY = null, IReadOnlyList<float> bossSpawnPosition = null, bool grindRequiresSlide = false, IReadOnlyDictionary<string, string> packKitVersions = null, string fallDamageCharacter = null, LevelFile randomizationSettings = default)
    {
        _pendingEdits = edits;
        _levelEdits = edits;
        _noGrass = noGrass;
        _playerStart = playerStart;
        _maxSlopeAngle = maxSlopeAngle;
        _killFloorY = killFloorY;
        _bossSpawnPosition = bossSpawnPosition;
        _grindRequiresSlide = grindRequiresSlide;
        _fallDamageCharacter = fallDamageCharacter;
        _packKitVersions = packKitVersions;
        _randomizationSettings = randomizationSettings;
    }

    public static void ApplySettings(LevelFile settings, MelonLogger.Instance logger)
    {
        LevelSettings.Validate(settings);
        _noGrass = settings.NoGrass;
        _playerStart = settings.PlayerStart;
        _bossSpawnPosition = settings.BossSpawnPosition;
        _killFloorY = settings.KillFloorY;
        _maxSlopeAngle = settings.MaxSlopeAngle;
        _grindRequiresSlide = settings.GrindRequiresSlide;
        _fallDamageCharacter = settings.FallDamageCharacter;
        _packKitVersions = settings.PackKitVersions;
        _randomizationSettings = settings;
        LevelLoaderPatch.ApplyMetadata(settings);
        LevelTitle.Prepare(settings.Title, settings.Description, logger);
        if (LevelMusic.Reference != settings.Music) LevelMusic.Prepare(settings.Music, logger);
        if (LiveSession is { } session)
        {
            if (session.Controller.grassRenderer != null) session.Controller.grassRenderer.enabled = !_noGrass;
            if (session.TileGen != null) KillFloorWatcher.Arm(session.TileGen, logger, _killFloorY);
        }
        TickMaxSlopeAngle(logger);
    }

    // Queues the loaded level's edits again for the next generation, which a native restart runs without going through LevelLoaderPatch.
    public static void RearmLevelEdits()
    {
        _pendingEdits = _levelEdits;
    }

    // Apply pending edits immediately to the current session if present. Returns the number of edits applied.
    public static int ApplyPendingEdits(MelonLogger.Instance logger)
    {
        if (_pendingEdits == null || _pendingEdits.Count == 0)
        {
            return 0;
        }

        var session = _session;
        if (session == null)
        {
            // No active session; they will be applied on next generation.
            return 0;
        }

        try
        {
            ApplyEdits(session, session.Planner.State, _pendingEdits);
            var count = _pendingEdits.Count;
            _pendingEdits = null;
            return count;
        }
        catch (Exception ex)
        {
            logger.Error($"LiveEdit: ApplyPendingEdits failed: {ex.Message}");
            return 0;
        }
    }

    public static void Install(MelonLogger.Instance logger)
    {
        MapGenerationController.A_PreGeneration += (Il2CppSystem.Action)StartupCover.OnGenerationStarting;
        SpawnPlayerPortal.A_PortalClosed += (Il2CppSystem.Action)StartupCover.OnPortalClosed;
        MapGenerationController.A_GenerationComplete += (Il2CppSystem.Action)(() => OnGenerationComplete(logger));
    }

    // The session is kept until the next generation completes, so its tile generator is destroyed while a reloaded level generates.
    private static Session LiveSession => _session is { } session && session.Controller != null ? session : null;

    public static LiveGrid? Grid => LiveSession?.Grid;

    // True on a ProceduralMesh map, where there is no tile grid and only objects can be edited.
    public static bool IsTerrainMap => LiveSession is { } session && session.TileGen == null;

    public static IReadOnlyList<EditOp> SeedEdits => LiveSession?.SeedEdits ?? Array.Empty<EditOp>();

    // The tile's current state: the generated grid with every applied edit on top, null for an empty cell.
    public static TileState? TileAt(int x, int z) => LiveSession?.Planner.State.GetTile(x, z);

    public static LevelState CurrentState() => LiveSession?.Planner.State;

    // The baked ground collision, replaced after every terrain edit.
    public static MeshCollider GroundCollider() => LiveSession?.GroundCollider();

    // The editor-pickable object whose hierarchy contains hit, or null: tiles, walls and fill pieces never resolve.
    public static ObjectTarget? TargetOf(Transform hit) => LiveSession?.Applier.TargetOf(hit);

    // The live object for a target, null when it is gone.
    public static GameObject ObjectFor(ObjectTarget target) => LiveSession?.Applier.FindActive(target);

    public static ObjectTarget SelectionTarget(ObjectTarget target, bool selectHidden) =>
        LiveSession?.Planner.State.SelectionTarget(target, selectHidden) ?? target;

    public static IEnumerable<Renderer> ModelRenderers(GameObject go) => Applier.ModelRenderers(go);

    public static IReadOnlyList<(ObjectTarget Target, GameObject Object)> PickableObjects() =>
        LiveSession?.Applier.PickableObjects() ?? new List<(ObjectTarget, GameObject)>();

    // The catalogId an editor-placed object was spawned from, null for a generator-spawned object.
    public static CatalogId? CatalogIdOf(ObjectTarget target) => LiveSession?.Applier.CatalogIdOf(target);

    public static GameObject PrefabFor(CatalogId id) => LiveSession?.Applier.PrefabFor(id);

    public static bool TryBuildPlan(EditOp op, out EditCommandPlan plan)
    {
        var session = _session;
        if (session == null)
        {
            plan = default;
            return false;
        }

        TransformData? fallback = null;
        if (op.OpType == RemoveObject.OpType || op.OpType == MoveObject.OpType)
        {
            var target = op.OpType == RemoveObject.OpType
                ? RemoveObject.FromEditOp(op).Target
                : MoveObject.FromEditOp(op).Target;
            var go = ObjectFor(target);
            if (go != null)
            {
                fallback = new TransformData(ToData(go.transform.position), ToData(go.transform.eulerAngles), ToData(go.transform.localScale));
            }
        }

        try
        {
            if (op.OpType == PlaceObject.OpType)
            {
                var place = PlaceObject.FromEditOp(op);
                op = new PlaceObject(place.CatalogId, place.Position, place.Rotation, place.Scale, place.Hidden,
                    place.Attachments, place.PlacementId ?? session.Planner.NextPlacementId).ToEditOp();
            }
            plan = EditCommandPlanner.Plan(op, session.Planner.State, session.Planner.NextPlacementId, fallback);
            return true;
        }
        catch (ArgumentException ex)
        {
            session.Logger.Error($"LiveEdit: plan failed for {op.OpType}: {ex.Message}");
            plan = default;
            return false;
        }
    }

    public static bool ApplySequence(IReadOnlyList<EditOp> ops)
    {
        var session = _session;
        if (session == null)
        {
            return false;
        }

        var actions = new List<LiveAction>(ops.Count);
        foreach (var op in ops)
        {
            try
            {
                actions.Add(session.Planner.Apply(op));
            }
            catch (ArgumentException ex)
            {
                session.Logger.Error($"LiveEdit: invalid edit {op.OpType}: {ex.Message}");
                return false;
            }
        }

        ApplyPlan(session, actions);
        return true;
    }

    public static LevelFile? SnapshotLevelFile(IReadOnlyList<EditOp> edits)
    {
        var session = _session;
        if (session == null)
        {
            return null;
        }

        var map = MapController.currentMap;
        var stage = MapController.currentStage;
        if (map == null || stage == null)
        {
            return null;
        }

        var stageIndex = -1;
        for (var i = 0; i < map.stages.Length; i++)
        {
            if (map.stages[i] != null && map.stages[i].Pointer == stage.Pointer)
            {
                stageIndex = i;
                break;
            }
        }

        if (stageIndex < 0)
        {
            return null;
        }

        return new LevelFile(
            SchemaVersion: LevelFile.CurrentSchemaVersion,
            GameBuildId: GameBuildIdPatch.CurrentBuildId() ?? "",
            Map: (EMap)(int)map.eMap,
            StageIndex: stageIndex,
            Tier: MapController.runConfig?.mapTierIndex ?? 0,
            Seed: session.TileGen?.debugSeed ?? 0,
            Packs: BuildPacks(edits),
            Edits: edits.ToList(),
            NoGrass: _noGrass,
            PlayerStart: _playerStart,
            MaxSlopeAngle: _maxSlopeAngle,
            KillFloorY: _killFloorY,
            BossSpawnPosition: _bossSpawnPosition,
            GrindRequiresSlide: _grindRequiresSlide,
            FallDamageCharacter: _fallDamageCharacter,
            Music: LevelMusic.Reference,
            Title: LevelTitle.Title,
            Description: LevelTitle.Description,
            AllowedCharacters: LevelLoaderPatch.AllowedCharacters,
            MapDescription: LevelLoaderPatch.MapDescription,
            PackKitVersions: BuildKitVersions(edits),
            RandomizeShadyGuy: _randomizationSettings.RandomizeShadyGuy,
            RandomizeChests: _randomizationSettings.RandomizeChests,
            RandomizeMoai: _randomizationSettings.RandomizeMoai,
            ExtraShrines: _randomizationSettings.ExtraShrines,
            ExtraShrineKinds: _randomizationSettings.ExtraShrineKinds);
    }

    private static IReadOnlyDictionary<string, string> BuildKitVersions(IReadOnlyList<EditOp> edits)
    {
        var versions = _packKitVersions == null ? new Dictionary<string, string>() : new Dictionary<string, string>(_packKitVersions);
        var manifests = new Dictionary<string, PackManifest?>();
        foreach (var op in edits.Where(op => op.OpType == PlaceObject.OpType))
        {
            var place = PlaceObject.FromEditOp(op);
            foreach (var raw in new[] { place.CatalogId }.Concat(place.Attachments.Select(child => child.CatalogId)))
            {
                if (CatalogId.TryParse(raw, out var id, out _) && id.Namespace == CatalogNamespace.Bundle)
                {
                    var pack = id.Segments[0];
                    var asset = string.Join("/", id.Segments.Skip(1));
                    if (!manifests.TryGetValue(pack, out var manifest))
                    {
                        manifest = PackPrefabs.Manifest(pack);
                        manifests[pack] = manifest;
                    }
                    if (manifest is { } found && found.IsKitAsset(asset) && found.KitVersion is { } revision)
                    {
                        versions[pack] = revision;
                    }
                }
            }
        }
        return versions.Count == 0 ? null : versions;
    }

    // The packs referenced by the level's edits, mapped to the version recorded in each installed
    // manifest (a pack with no manifest is skipped). Editor save writes this so the level-side version
    // check can warn when a pack was updated since the level was saved.
    private static IReadOnlyDictionary<string, string> BuildPacks(IReadOnlyList<EditOp> edits)
    {
        var referenced = new Dictionary<string, string>();
        foreach (var op in edits)
        {
            if (op.OpType != PlaceObject.OpType)
            {
                continue;
            }

            var place = PlaceObject.FromEditOp(op);
            foreach (var catalogId in new[] { place.CatalogId }.Concat(place.Attachments.Select(child => child.CatalogId)))
            {
                if (CatalogId.TryParse(catalogId, out var id, out _) && id.Namespace == CatalogNamespace.Bundle)
                {
                    var pack = id.Segments[0];
                    if (!referenced.ContainsKey(pack))
                    {
                        var version = PackPrefabs.ManifestVersion(pack);
                        if (version != null)
                        {
                            referenced[pack] = version;
                        }
                    }
                }
            }
        }

        return referenced;
    }

    public static string LevelsDirectoryPath()
    {
        var path = Path.Combine(MelonLoader.Utils.MelonEnvironment.GameRootDirectory, "UserData", "Levels");
        Directory.CreateDirectory(path);
        return path;
    }

    public static IReadOnlyList<string> ListLevelFiles()
    {
        var path = LevelsDirectoryPath();
        var names = Directory.GetFiles(path, "*.mblevel.json").Select(Path.GetFileName);
        return EditorFileNaming.SortLevelNames(names);
    }

    public static string BossPortalTargetName()
    {
        var session = _session;
        if (session == null)
        {
            return null;
        }

        foreach (var pair in session.Applier.PickableObjects())
        {
            if (pair.Object != null && EditorValidationTargets.IsBossPortalName(pair.Object.name))
            {
                return pair.Object.name;
            }
        }

        return null;
    }

    public static (int X, int Z)? BossPortalCell()
    {
        var grid = Grid;
        var session = _session;
        if (grid == null || session == null)
        {
            return null;
        }

        foreach (var pair in session.Applier.PickableObjects())
        {
            var go = pair.Object;
            if (go == null || !EditorValidationTargets.IsBossPortalName(go.name))
            {
                continue;
            }

            var cell = PositionReadout.CellOf(go.transform.position.x, go.transform.position.z, grid.Value.Width, grid.Value.Depth, grid.Value.Spacing);
            if (cell.InGrid)
            {
                return (cell.X, cell.Z);
            }
        }

        return null;
    }

    // Index of the run's stage in the current map's stage list, -1 when unknown.
    public static int CurrentStageIndex()
    {
        var stages = MapController.currentMap?.stages;
        var current = MapController.currentStage;
        for (var i = 0; current != null && stages != null && i < stages.Length; i++)
        {
            if (stages[i] != null && stages[i].Pointer == current.Pointer)
            {
                return i;
            }
        }

        return -1;
    }

    // Applies one edit to the running level the same way a level file's edits are applied at load.
    public static bool ApplyLive(EditOp op)
    {
        var session = _session;
        if (session == null)
        {
            return false;
        }

        LiveAction action;
        try
        {
            action = session.Planner.Apply(op);
        }
        catch (ArgumentException ex)
        {
            session.Logger.Error($"LiveEdit: invalid edit {op.OpType}: {ex.Message}");
            return false;
        }

        var plan = new[] { action };
        ApplyPlan(session, plan);
        return true;
    }

    // Resets the live level to its generation baseline then applies newEdits in place, without
    // relaunching the game. Tile differences are computed and applied via InPlaceLoadTileReset;
    // gen-id objects are restored from a pre-edit transform snapshot; placed objects are destroyed.
    // Returns false when there is no active session (no level is running).
    public static bool ResetAndApplyEdits(IReadOnlyList<EditOp> newEdits, MelonLogger.Instance logger)
    {
        var session = _session;
        if (session == null)
        {
            return false;
        }

        var baseline = session.Baseline;
        // Capture object state before resetting the planner.
        var modifiedObjects = session.Planner.State.Objects;

        // Reset tiles: compute diff from current back to baseline and apply each action.
        var tileResets = InPlaceLoadTileReset.ComputeTileResets(baseline, session.Planner.State);
        if (tileResets.Count > 0)
        {
            ApplyPlan(session, tileResets);
        }

        // Reset objects: restore gen-id objects to baseline transforms, destroy placed objects.
        session.Applier.ResetToGenBaseline(modifiedObjects);

        // Re-initialize the planner to a clean baseline before applying new edits.
        session.Planner = new LiveEditPlanner(baseline);

        // Apply the loaded edits.
        var edits = newEdits ?? Array.Empty<EditOp>();
        if (edits.Count > 0)
        {
            ApplyEdits(session, baseline, edits);
        }

        session.SeedEdits = edits.ToList();
        logger.Msg($"LiveEdit: in-place load applied {edits.Count} edit(s) after baseline reset");
        return true;
    }

    private static void OnGenerationComplete(MelonLogger.Instance logger)
    {
        StartupCover.OnProgress();
        var edits = _pendingEdits;
        _pendingEdits = null;
        if (edits == null) _randomizationSettings = default;
        _runGeneration++;
        _session = null;
        BossSpawnRedirectPatch.Disarm();
        ExtraShrinesPatch.ClearStale();

        var controller = UnityEngine.Object.FindObjectOfType<MapGenerationController>();
        if (controller == null)
        {
            return;
        }

        var index = BuildIndex(controller);
        logger.Msg($"LiveEdit: indexed {index.Count} objects: {SummarizeCategories(index)}");
        DisableGrassIfRequested(controller, logger);

        var tileGen = controller.proceduralTileGeneration;
        if (tileGen?.proceduralTiles == null)
        {
            OnTerrainGenerationComplete(logger, controller, index, edits);
            if (edits != null && InteractableRandomization.Enabled(_randomizationSettings))
                logger.Warning("InteractableRandomization: no tile ground available; keeping original placements");
            if (edits != null && ExtraShrines.Enabled(_randomizationSettings))
                logger.Warning("ExtraShrines: no tile ground available; no extra shrines spawned");
            StartupCover.OnContentReady();
            return;
        }

        var baseline = SnapshotGrid(tileGen);
        var seedEdits = edits != null ? edits.ToList() : new List<EditOp>();
        var session = new Session(logger, controller, index, baseline, seedEdits);
        if (edits != null && edits.Count > 0)
        {
            ApplyEdits(session, baseline, edits);
        }

        _session = session;
        if (edits != null && (InteractableRandomization.Enabled(_randomizationSettings) || ExtraShrines.Enabled(_randomizationSettings)))
        {
            MelonCoroutines.Start(FinishRandomizedGeneration(session, index, edits, _randomizationSettings));
            return;
        }
        StartupCover.OnContentReady();
        if (edits == null)
        {
            KillFloorWatcher.Disarm();
            _grindRequiresSlide = false;
            _fallDamageCharacter = null;
            return;
        }

        KillFloorWatcher.Arm(tileGen, logger, _killFloorY);
    }

    // Chest.Start adds random tilt, so relocate after native Start callbacks but before releasing the startup cover.
    private static System.Collections.IEnumerator FinishRandomizedGeneration(Session session, Dictionary<string, GameObject> index,
        IReadOnlyList<EditOp> edits, LevelFile settings)
    {
        yield return null;
        if (_session != session || session.Controller == null) yield break;
        var ground = session.GroundCollider();
        InteractableRandomizationPatch.Apply(settings, index, edits, session.Planner.State,
            session.TileGen, ground, settings.PlayerStart, session.Logger);
        ExtraShrinesPatch.Spawn(settings, index, session.Planner.State, session.TileGen, ground, session.Controller, session.Logger);
        StartupCover.OnContentReady();
        KillFloorWatcher.Arm(session.TileGen, session.Logger, settings.KillFloorY);
    }

    // The grass manager raycasts onto the ground layer, so it would grow through a level's placed floor meshes.
    private static void DisableGrassIfRequested(MapGenerationController controller, MelonLogger.Instance logger)
    {
        if (!_noGrass || controller.grassRenderer == null)
        {
            return;
        }

        controller.grassRenderer.enabled = false;
        logger.Msg("LiveEdit: grass disabled by the level");
    }

    // Where the level authors the player starting at, or null to leave the player where the game put it.
    public static IReadOnlyList<float> PlayerStart => _playerStart;

    private static float? _defaultMaxSlopeAngle;

    // Raises the player's slope limit for the length of a custom level run and puts the game's value back afterwards, so vanilla runs keep their movement.
    public static void TickMaxSlopeAngle(MelonLogger.Instance logger)
    {
        var player = MyPlayer.Instance;
        if (player == null || player.playerMovement == null)
        {
            return;
        }

        var movement = player.playerMovement;
        var wanted = CustomLevelState.IsActive ? _maxSlopeAngle : null;
        if (wanted == null)
        {
            if (_defaultMaxSlopeAngle != null)
            {
                movement.maxSlopeAngle = _defaultMaxSlopeAngle.Value;
                _defaultMaxSlopeAngle = null;
            }

            return;
        }

        if (_defaultMaxSlopeAngle == null)
        {
            _defaultMaxSlopeAngle = movement.maxSlopeAngle;
            logger.Msg($"LiveEdit: max slope angle {movement.maxSlopeAngle} -> {wanted.Value}");
        }

        movement.maxSlopeAngle = wanted.Value;
    }

    // A ProceduralMesh map: the session holds only objects, over an empty tile baseline.
    private static void OnTerrainGenerationComplete(MelonLogger.Instance logger, MapGenerationController controller, Dictionary<string, GameObject> index, IReadOnlyList<EditOp> edits)
    {
        var baseline = LevelState.FromTiles(new Dictionary<(int X, int Z), TileState>());
        var session = new Session(logger, controller, index, baseline, edits != null ? edits.ToList() : new List<EditOp>());
        if (edits != null && edits.Count > 0)
        {
            ApplyEdits(session, baseline, edits);
        }

        _session = session;
        if (edits == null || session.GroundCollider() is not { } ground)
        {
            KillFloorWatcher.Disarm();
            return;
        }

        KillFloorWatcher.ArmTerrain(ground.bounds.min.y, logger);
    }

    private static void ApplyEdits(Session session, LevelState baseline, IReadOnlyList<EditOp> edits)
    {
        if (session.TileGen == null)
        {
            var (kept, rejected) = TerrainEdits.Split(edits);
            if (rejected.Count > 0)
            {
                session.Logger.Warning($"LiveEdit: {rejected.Count} tile edit(s) skipped, a terrain map has no tile grid");
            }

            edits = kept;
        }

        IReadOnlyList<LiveAction> plan;
        try
        {
            plan = LiveEditPlan.Build(edits, baseline);
        }
        catch (ArgumentException ex)
        {
            session.Logger.Error($"LiveEdit: invalid edit list: {ex.Message}");
            return;
        }

        foreach (var op in edits)
        {
            session.Planner.Apply(op);
        }

        ApplyPlan(session, plan);
    }

    private static void ApplyPlan(Session session, IReadOnlyList<LiveAction> plan)
    {
        foreach (var action in plan)
        {
            try
            {
                session.Applier.Apply(action);
                StartupCover.OnProgress();
            }
            catch (Exception ex)
            {
                session.Logger.Error($"LiveEdit: {action.Kind} failed: {ex}");
            }
        }

        session.Logger.Msg($"LiveEdit: applied {plan.Count} edit(s)");

        if (LiveEditPlan.ChangesTerrain(plan))
        {
            var touched = plan.Where(a => a.Kind is LiveActionKind.SetTile or LiveActionKind.RemoveTile).Select(a => (a.X, a.Z));
            FillRegeneration.Regenerate(session.TileGen, session.Grid.Value.Spacing, touched, session.Logger);
            CollisionRebuild.Replace(session.TileGen, session.Logger);
        }
    }

    // The generated grid before any edit, read from the live tiles.
    private static LevelState SnapshotGrid(ProceduralTileGeneration tileGen)
    {
        var tiles = new Dictionary<(int X, int Z), TileState>();
        var grid = tileGen.proceduralTiles;
        for (var x = 0; x < grid.Length; x++)
        {
            for (var z = 0; grid[x] != null && z < grid[x].Length; z++)
            {
                var tile = grid[x][z];
                if (tile != null)
                {
                    tiles[(x, z)] = new TileState(tile.posY, SlopeOf(tile));
                }
            }
        }

        return LevelState.FromTiles(tiles);
    }

    private static SlopeDirection SlopeOf(ProceduralTile tile) =>
        tile == null || tile.isFlat
            ? SlopeDirection.None
            : TilePlacement.SlopeFromVector(Mathf.RoundToInt(tile.dir.x), Mathf.RoundToInt(tile.dir.z));

    private static Dictionary<string, GameObject> BuildIndex(MapGenerationController controller)
    {
        var sources = new Dictionary<string, IReadOnlyList<GameObject>>();
        var tileGen = controller.proceduralTileGeneration;
        sources["tile"] = ToList(tileGen?.tiles);
        sources["flatTile"] = ToList(tileGen?.flatTiles);
        sources["fillTile"] = ToList(tileGen?.fillTiles);
        sources["tileObject"] = Children(controller.RandomTileObjects?.tileObjectsParent?.transform);

        // Random objects, chests, shrines, pots, rails etc. are all instantiated as scene roots named
        // "<prefab>(Clone)", after the TileObjectsParent root; root order is spawn order.
        var spawned = new Dictionary<string, List<GameObject>>();
        var seenTileObjectsParent = false;
        foreach (var root in controller.gameObject.scene.GetRootGameObjects())
        {
            if (root.name == TileObjectsParentName)
            {
                seenTileObjectsParent = true;
                continue;
            }

            var category = seenTileObjectsParent ? SceneRootCategory.Of(root.name) : null;
            if (category == null)
            {
                continue;
            }

            if (!spawned.TryGetValue(category, out var list))
            {
                spawned[category] = list = new List<GameObject>();
            }

            list.Add(root);
        }

        foreach (var (category, list) in spawned)
        {
            sources[category] = list;
        }

        return GenIdAssigner.Index(sources);
    }

    private static string SummarizeCategories(Dictionary<string, GameObject> index) =>
        string.Join(", ", index.Keys
            .GroupBy(k => k.Substring(0, k.LastIndexOf(':')))
            .Select(g => $"{g.Key}x{g.Count()}"));

    private static IReadOnlyList<GameObject> ToList(Il2CppSystem.Collections.Generic.List<GameObject> source)
    {
        var result = new List<GameObject>();
        for (var i = 0; source != null && i < source.Count; i++)
        {
            result.Add(source[i]);
        }

        return result;
    }

    private static IReadOnlyList<GameObject> Children(Transform parent)
    {
        var result = new List<GameObject>();
        for (var i = 0; parent != null && i < parent.childCount; i++)
        {
            result.Add(parent.GetChild(i).gameObject);
        }

        return result;
    }

    // Everything needed to keep editing the level generated last: the planner holds the generated grid plus every edit.
    private sealed class Session
    {
        public readonly MelonLogger.Instance Logger;
        public readonly MapGenerationController Controller;
        // Both are null on a ProceduralMesh map.
        public readonly ProceduralTileGeneration TileGen;
        public readonly LiveGrid? Grid;
        public readonly Applier Applier;
        public LiveEditPlanner Planner;
        public IReadOnlyList<EditOp> SeedEdits;
        // Generation baseline before any edits; used by ResetAndApplyEdits for in-place load.
        public readonly LevelState Baseline;

        public Session(MelonLogger.Instance logger, MapGenerationController controller, Dictionary<string, GameObject> index, LevelState baseline, IReadOnlyList<EditOp> seedEdits)
        {
            Logger = logger;
            Controller = controller;
            var tileGen = controller.proceduralTileGeneration;
            if (tileGen?.proceduralTiles != null)
            {
                TileGen = tileGen;
                var columns = TileGen.proceduralTiles;
                var mapParameters = TileGen.currentMapParameters ?? TileGen.currentStage?.mapParameters;
                var lowestLevel = baseline.Tiles.Count == 0 ? 0 : baseline.Tiles.Values.Min(t => t.Height);
                Grid = new LiveGrid(columns.Length, columns[0].Length, mapParameters.scaledTileWidth, mapParameters.scaledTileHeight, lowestLevel);
            }

            Baseline = baseline;
            Applier = new Applier(logger, controller, index);
            Planner = new LiveEditPlanner(baseline);
            SeedEdits = seedEdits;
        }

        // The baked tile collision, or the heightmap mesh's collider on a ProceduralMesh map.
        public MeshCollider GroundCollider() => TileGen != null
            ? TileGen.collider?.GetComponent<MeshCollider>()
            : Controller.proceduralMapMeshGenerator?.mesh?.GetComponentInChildren<MeshCollider>();
    }

    private sealed class Applier
    {
        private readonly MelonLogger.Instance _logger;
        private readonly MapGenerationController _controller;
        private readonly ProceduralTileGeneration _tileGen;
        private readonly MapParameters _mapParameters;
        private readonly Dictionary<string, GameObject> _index;
        private readonly Dictionary<int, GameObject> _placed = new();
        private readonly Dictionary<int, string> _placedCatalogIds = new();
        private readonly Dictionary<int, ObjectTarget> _targetsByInstanceId = new();
        // Snapshots of generator object transforms taken before any edits, keyed by genId.
        private readonly Dictionary<string, TransformData> _genIdBaselineTransforms = new();

        public Applier(MelonLogger.Instance logger, MapGenerationController controller, Dictionary<string, GameObject> index)
        {
            _logger = logger;
            _controller = controller;
            _tileGen = controller.proceduralTileGeneration;
            _mapParameters = _tileGen?.currentMapParameters ?? _tileGen?.currentStage?.mapParameters;
            _index = index;
            foreach (var (genId, go) in index)
            {
                if (ObjectTools.IsPickableGenId(genId) && HasMeshRenderer(go))
                {
                    _targetsByInstanceId[go.GetInstanceID()] = ObjectTarget.FromGenId(genId);
                }
            }
            foreach (var (genId, go) in index)
            {
                if (ObjectTools.IsPickableGenId(genId) && go != null)
                {
                    _genIdBaselineTransforms[genId] = new TransformData(
                        ToData(go.transform.position),
                        ToData(go.transform.eulerAngles),
                        ToData(go.transform.localScale));
                }
            }
        }

        // Effect-only roots such as ForestParticles span the map and are not objects to edit.
        public static bool HasMeshRenderer(GameObject go) => ModelRenderers(go).Any();

        public static IEnumerable<Renderer> ModelRenderers(GameObject go) =>
            go.GetComponentsInChildren<Renderer>()
                .Where(r => ObjectTools.IsModelRenderer(r.name, r.enabled, r.TryCast<ParticleSystemRenderer>() != null));

        public ObjectTarget? TargetOf(Transform hit)
        {
            for (var t = hit; t != null; t = t.parent)
            {
                if (_targetsByInstanceId.TryGetValue(t.gameObject.GetInstanceID(), out var target))
                {
                    return target;
                }
            }

            return null;
        }

        public GameObject FindActive(ObjectTarget target)
        {
            var found = FindAny(target);
            return found != null && found.activeInHierarchy ? found : null;
        }

        private GameObject FindAny(ObjectTarget target)
        {
            var found = target.Kind == ObjectTargetKind.GenId
                ? _index.GetValueOrDefault(target.GenId)
                : _placed.GetValueOrDefault(target.PlacementId);
            return found != null ? found : null;
        }

        public IReadOnlyList<(ObjectTarget Target, GameObject Object)> PickableObjects()
        {
            var result = new List<(ObjectTarget, GameObject)>();
            foreach (var (genId, go) in _index)
            {
                if (ObjectTools.IsPickableGenId(genId) && go != null && go.activeInHierarchy && HasMeshRenderer(go))
                {
                    result.Add((ObjectTarget.FromGenId(genId), go));
                }
            }

            foreach (var (id, go) in _placed)
            {
                if (go != null && go.activeInHierarchy)
                {
                    result.Add((ObjectTarget.FromPlacementId(id), go));
                }
            }

            return result;
        }

        public CatalogId? CatalogIdOf(ObjectTarget target) =>
            target.Kind == ObjectTargetKind.PlacementId && _placedCatalogIds.TryGetValue(target.PlacementId, out var id)
                ? CatalogId.Parse(id)
                : null;

        public GameObject PrefabFor(CatalogId id) => ResolvePrefab(id);

        public void Apply(LiveAction action)
        {
            switch (action.Kind)
            {
                case LiveActionKind.SetTile:
                    SetTile(action);
                    break;
                case LiveActionKind.RemoveTile:
                    RemoveTile(action);
                    break;
                case LiveActionKind.SpawnObject:
                    SpawnObject(action);
                    break;
                case LiveActionKind.MoveObject:
                    MoveObject(action);
                    break;
                case LiveActionKind.RemoveObject:
                    RemoveObject(action);
                    break;
            }
        }

        private ProceduralTile TileAt(int x, int z)
        {
            var grid = _tileGen.proceduralTiles;
            return x < grid.Length && grid[x] != null && z < grid[x].Length ? grid[x][z] : null;
        }

        private bool InGrid(int x, int z)
        {
            var grid = _tileGen.proceduralTiles;
            return x >= 0 && x < grid.Length && grid[x] != null && z >= 0 && z < grid[x].Length;
        }

        private void SetTile(LiveAction action)
        {
            var (x, z) = (action.X, action.Z);
            if (!InGrid(x, z))
            {
                _logger.Warning($"LiveEdit: ({x},{z}) is outside the {_tileGen.proceduralTiles.Length}-wide tile grid; adding tiles beyond the grid is not supported");
                return;
            }

            var state = action.Tile.Value;
            var live = TileAt(x, z);
            var batched = live != null && live.GetComponentsInChildren<Renderer>().Any(renderer => renderer.isPartOfStaticBatch);
            var kind = TilePlacement.Decide(live != null, SlopeOf(live), state, liveIsStaticBatch: batched);

            if (kind == TilePlacementKind.MoveOnly)
            {
                var before = live.transform.position;
                var y = state.Height * _mapParameters.scaledTileHeight;
                live.transform.position = new Vector3(before.x, y, before.z);
                live.posY = state.Height;
                _logger.Msg($"LiveEdit: tile ({x},{z}) height {before.y} -> {y} (level {state.Height})");
                return;
            }

            var slope = kind is TilePlacementKind.AddSlope or TilePlacementKind.ReplaceWithSlope;
            var direction = slope
                ? ToDirection(TilePlacement.UphillVector(state.Slope))
                : live != null ? live.dir : Vector3.forward;
            var prefab = slope ? _tileGen.slopeTile : _tileGen.flatTile;
            var created = _tileGen.InstantiateTile(new Vector2Int(x, z), state.Height, prefab, direction, direction);
            var tile = created.GetComponent<ProceduralTile>();

            if (live != null)
            {
                _tileGen.tiles.Remove(live.gameObject);
                _tileGen.flatTiles.Remove(live.gameObject);
                live.gameObject.SetActive(false);
                UnityEngine.Object.Destroy(live.gameObject);
            }

            if (!_tileGen.tiles.Contains(created))
            {
                _tileGen.tiles.Add(created);
            }

            _tileGen.proceduralTiles[x][z] = tile;
            _logger.Msg($"LiveEdit: {kind} at ({x},{z}) prefab '{prefab.name}' level {state.Height} slope {state.Slope} -> {created.transform.position} euler {created.transform.eulerAngles}");
        }

        private static Vector3 ToDirection((int Dx, int Dz) step) => new(step.Dx, 0, step.Dz);

        private void RemoveTile(LiveAction action)
        {
            var tile = TileAt(action.X, action.Z);
            if (tile == null)
            {
                _logger.Warning($"LiveEdit: no live tile at ({action.X},{action.Z}) to remove");
                return;
            }

            _tileGen.tiles.Remove(tile.gameObject);
            _tileGen.flatTiles.Remove(tile.gameObject);
            tile.gameObject.SetActive(false);
            UnityEngine.Object.Destroy(tile.gameObject);
            _tileGen.proceduralTiles[action.X][action.Z] = null;
            _logger.Msg($"LiveEdit: removed tile ({action.X},{action.Z})");
        }

        private void SpawnObject(LiveAction action)
        {
            var prefab = ResolvePrefab(CatalogId.Parse(action.CatalogId));
            var t = action.Transform.Value;
            var spawned = UnityEngine.Object.Instantiate(prefab, ToVector(t.Position), Quaternion.Euler(ToVector(t.Rotation)));
            spawned.transform.localScale = ToVector(t.Scale);
            if (action.Hidden)
            {
                foreach (var renderer in spawned.GetComponentsInChildren<Renderer>(true))
                {
                    renderer.enabled = false;
                }
            }

            _placed[action.Target.PlacementId] = spawned;
            _placedCatalogIds[action.Target.PlacementId] = action.CatalogId;
            _targetsByInstanceId[spawned.GetInstanceID()] = action.Target;
            for (var i = 0; i < (action.Attachments?.Count ?? 0); i++)
            {
                var attachment = action.Attachments[i];
                var target = ObjectTarget.FromPlacementId(action.Target.PlacementId + i + 1);
                var childPrefab = ResolvePrefab(CatalogId.Parse(attachment.CatalogId));
                var child = UnityEngine.Object.Instantiate(childPrefab);
                child.name = attachment.Name;
                child.transform.SetParent(spawned.transform, false);
                var local = attachment.LocalTransform;
                child.transform.localPosition = ToVector(local.Position);
                child.transform.localRotation = Quaternion.Euler(ToVector(local.Rotation));
                child.transform.localScale = ToVector(local.Scale);
                if (attachment.Hidden || action.Hidden)
                {
                    foreach (var renderer in child.GetComponentsInChildren<Renderer>(true))
                    {
                        renderer.enabled = false;
                    }
                }
                _placed[target.PlacementId] = child;
                _placedCatalogIds[target.PlacementId] = attachment.CatalogId;
                _targetsByInstanceId[child.GetInstanceID()] = target;
                _logger.Msg($"LiveEdit: attached '{attachment.Name}' as {target.Serialize()} to {action.Target.Serialize()}");
            }
            _logger.Msg($"LiveEdit: spawned '{action.CatalogId}' (prefab '{prefab.name}') as placement:{action.Target.PlacementId} at {spawned.transform.position}");
        }

        private void MoveObject(LiveAction action)
        {
            var go = Resolve(action.Target);
            if (go == null)
            {
                return;
            }

            var t = action.Transform.Value;
            if (!go.activeSelf)
            {
                go.SetActive(true);
            }

            if (action.Owner != null)
            {
                go.transform.localPosition = ToVector(t.Position);
                go.transform.localRotation = Quaternion.Euler(ToVector(t.Rotation));
            }
            else
            {
                go.transform.position = ToVector(t.Position);
                go.transform.rotation = Quaternion.Euler(ToVector(t.Rotation));
            }
            go.transform.localScale = ToVector(t.Scale);
            HideChildren(go, action.HiddenChildren);
            _logger.Msg($"LiveEdit: moved {action.Target.Serialize()} '{go.name}' to {go.transform.position}");
        }

        private void HideChildren(GameObject go, IReadOnlyList<string> names)
        {
            if (names == null || names.Count == 0)
            {
                return;
            }

            foreach (var child in go.GetComponentsInChildren<Transform>(true))
            {
                if (!names.Contains(child.name))
                {
                    continue;
                }

                foreach (var renderer in child.GetComponents<Renderer>())
                {
                    renderer.enabled = false;
                }

                foreach (var collider in child.GetComponents<Collider>())
                {
                    collider.enabled = false;
                }

                _logger.Msg($"LiveEdit: hid child '{child.name}' of '{go.name}'");
            }
        }

        private void RemoveObject(LiveAction action)
        {
            var go = Resolve(action.Target);
            if (go == null)
            {
                return;
            }

            var name = go.name;
            go.SetActive(false);
            var player = MyPlayer.Instance?.playerMovement;
            if (player != null && player.IsGrinding() && player.rail != null && player.rail.transform.IsChildOf(go.transform))
            {
                player.StopRail();
            }
            _logger.Msg($"LiveEdit: removed {action.Target.Serialize()} '{name}'");
        }

        private GameObject Resolve(ObjectTarget target)
        {
            var found = FindAny(target);
            if (found == null)
            {
                _logger.Warning($"LiveEdit: no live object for {target.Serialize()}");
            }

            return found;
        }

        private GameObject ResolvePrefab(CatalogId id) =>
            id.Namespace == CatalogNamespace.Bundle
                ? PackPrefabs.Resolve(id)
                : CatalogPrefabs.Resolve(CatalogRoute.Parse(id), _controller.interactablesSpawner);

        private static Vector3 ToVector(Vector3Data v) => new(v.X, v.Y, v.Z);

        private static Vector3Data ToData(Vector3 v) => new(v.x, v.y, v.z);

        // Restores all editor-modified objects to their pre-edit state: placed objects are destroyed,
        // gen-id objects that were moved or removed are restored to their baseline transform.
        public void ResetToGenBaseline(IReadOnlyDictionary<ObjectTarget, ObjectState> modifiedObjects)
        {
            foreach (var (target, _) in modifiedObjects)
            {
                if (target.Kind == ObjectTargetKind.GenId)
                {
                    if (!_index.TryGetValue(target.GenId, out var go) || go == null)
                    {
                        _logger.Warning($"LiveEdit reset: gen-id object '{target.GenId}' not found in index");
                        continue;
                    }

                    if (!_genIdBaselineTransforms.TryGetValue(target.GenId, out var t))
                    {
                        _logger.Warning($"LiveEdit reset: no baseline transform snapshot for '{target.GenId}'");
                        continue;
                    }

                    go.SetActive(true);
                    go.transform.position = ToVector(t.Position);
                    go.transform.rotation = Quaternion.Euler(ToVector(t.Rotation));
                    go.transform.localScale = ToVector(t.Scale);
                    _logger.Msg($"LiveEdit reset: restored gen-id '{target.GenId}' to baseline transform");
                }
                else if (target.Kind == ObjectTargetKind.PlacementId)
                {
                    if (_placed.TryGetValue(target.PlacementId, out var go) && go != null)
                    {
                        var instanceId = go.GetInstanceID();
                        go.SetActive(false);
                        UnityEngine.Object.Destroy(go);
                        _targetsByInstanceId.Remove(instanceId);
                        _logger.Msg($"LiveEdit reset: destroyed placement:{target.PlacementId} '{go.name}'");
                    }

                    _placed.Remove(target.PlacementId);
                    _placedCatalogIds.Remove(target.PlacementId);
                }
            }
        }
    }

    private static Vector3Data ToData(Vector3 v) => new(v.x, v.y, v.z);
}
