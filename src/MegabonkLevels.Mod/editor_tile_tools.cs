using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Il2Cpp;
using Il2CppTMPro;
using MelonLoader;
using UnityEngine;
using UnityEngine.UI;

namespace MegabonkLevels;

// See "Tile tools" in docs/development.md.
public static class EditorTileTools
{
    private const float ToolbarWidth = 960f;
    private const float ToolbarHeight = 144f;
    private const float FontSize = 18f;
    private const float OverlayFontSize = 16f;
    private const float RayLength = 5000f;
    private const float WallNudge = 0.01f;
    private const float OutlineLift = 0.5f;
    private const float OutlineWidth = 0.8f;
    private const float OverlayWidth = 300f;
    private const float OverlayRowHeight = 30f;
    private const float OverlayPadding = 8f;
    private const int MaxListedLevels = 8;
    private const float UndoRedoCtrlHoldSeconds = 0.2f;
    private const int SaveNameMaxChars = 80;

    private static readonly Color PanelColor = new(0f, 0f, 0f, 0.75f);
    private static readonly Color HighlightColor = new(1f, 0.85f, 0.3f, 1f);
    private static readonly Color WarnColor = new(1f, 0.7f, 0.2f, 1f);
    private static readonly Color ErrorColor = new(1f, 0.4f, 0.4f, 1f);

    private static MelonLogger.Instance _logger;
    private static GameObject _root;
    private static TextMeshProUGUI _label;
    private static TextMeshProUGUI _status;
    private static TextMeshProUGUI _loadList;
    private static TextMeshProUGUI _saveInputText;
    private static TextMeshProUGUI _savePlaceholderText;
    private static RectTransform _saveInputRect;
    private static Image _undoButtonBg;
    private static Image _redoButtonBg;
    private static LineRenderer _outline;
    private static readonly List<LineRenderer> _unreachable = new();
    private static readonly List<ClickRegion> _clickRegions = new();
    private static readonly List<string> _levelFiles = new();
    private static EditorTool _tool = EditorTools.Default;
    private static (int X, int Z, TileState State)? _target;
    private static Vector3 _targetPoint;
    private static RectTransform _toolbarRect;
    private static RectTransform _loadRect;
    private static TextMeshProUGUI _loadStatusText;
    private static float _loadStatusExpiry = -1f;
    private static EditorEditSession _session;
    private static ReachabilityResult _reachability;
    private static string _validateSummary = "validate: not run";
    private static int _selectedLevel;
    private static float _ctrlHeldSince = -1f;
    private static bool _saveInputFocused;
    private static string _saveName = "";
    private static int _lastSavedEditCount;

    private sealed class ClickRegion
    {
        public RectTransform Rect;
        public Action OnClick;
        public Func<bool> Enabled;
    }

    public static bool PointerOverEditorOverlay => PointerOverOverlay();

    public static bool TextInputFocused => _saveInputFocused;

    public static void OnEditorEntered(MelonLogger.Instance logger)
    {
        _logger = logger;
        _tool = EditorTools.Default;
        _session = new EditorEditSession(LiveEditPatch.SeedEdits);
        _reachability = null;
        _validateSummary = "validate: not run";
        EditorObjectTools.OnEditorEntered(logger);
        BuildToolbar();
        BuildOutline();
        _target = null;
        RefreshLoadList();
        Refresh();
    }

    public static void OnEditorExited()
    {
        EditorObjectTools.OnEditorExited();
        if (_root != null)
        {
            UnityEngine.Object.Destroy(_root);
        }

        if (_outline != null)
        {
            UnityEngine.Object.Destroy(_outline.gameObject);
        }

        _root = null;
        _label = null;
        _status = null;
        _loadList = null;
        _saveInputText = null;
        _savePlaceholderText = null;
        _saveInputRect = null;
        _undoButtonBg = null;
        _redoButtonBg = null;
        _outline = null;
        _loadStatusText = null;
        _loadStatusExpiry = -1f;
        _target = null;
        _toolbarRect = null;
        _loadRect = null;
        _session = null;
        _reachability = null;
        _levelFiles.Clear();
        _selectedLevel = 0;
        _ctrlHeldSince = -1f;
        _saveInputFocused = false;
        _saveName = "";
        _lastSavedEditCount = LiveEditPatch.SeedEdits.Count;
        _clickRegions.Clear();
        ClearUnreachable();
    }

    public static void Tick()
    {
        HandleUndoRedoHotkeys();
        HandleOverlayInput();

        for (var digit = 1; digit <= 9; digit++)
        {
            if (Input.GetKeyDown(KeyCode.Alpha0 + digit) && EditorTools.FromHotkey(digit) is { } tool)
            {
                SetTool(tool);
            }
        }

        var pointerOverToolbar = PointerOverOverlay();
        _target = EditorPalette.PointerOverPanel || pointerOverToolbar ? null : FindTarget();
        if (EditorTools.IsObjectTool(_tool) && !pointerOverToolbar)
        {
            if (EditorObjectTools.Tick(_tool, _target, _targetPoint) is { } requested)
            {
                SetTool(requested);
            }
        }
        else if (_target is { } target && Input.GetMouseButtonDown(0))
        {
            Use(target.X, target.Z, target.State);
            _target = FindTarget();
        }

        Refresh();
    }

    private static void SetTool(EditorTool tool)
    {
        if (tool != _tool)
        {
            EditorObjectTools.OnToolChanged(tool);
        }

        _tool = tool;
    }

    private static (int X, int Z, TileState State)? FindTarget()
    {
        var camera = PlayerCamera.Instance?.camera;
        var ground = LiveEditPatch.GroundCollider();
        if (camera == null || ground == null || LiveEditPatch.Grid is not { } grid)
        {
            return null;
        }

        if (!ground.Raycast(camera.ScreenPointToRay(Input.mousePosition), out var hit, RayLength))
        {
            return null;
        }

        // Stepping just inside the surface puts a hit on a side wall in the cell the wall belongs to.
        var point = hit.point - hit.normal * WallNudge;
        _targetPoint = point;
        var cell = PositionReadout.CellOf(point.x, point.z, grid.Width, grid.Depth, grid.Spacing);
        if (!cell.InGrid || LiveEditPatch.TileAt(cell.X, cell.Z) is not { } state)
        {
            return null;
        }

        return (cell.X, cell.Z, state);
    }

    private static void Use(int x, int z, TileState state)
    {
        var lowestLevel = LiveEditPatch.Grid?.LowestLevel ?? 0;
        if (TileTools.Build(_tool, x, z, state, lowestLevel) is not { } op)
        {
            _logger.Msg($"EditorTileTools: {_tool} ({x},{z}) nothing to do at level {state.Height}");
            return;
        }

        ApplyFromTool(op, $"{_tool} ({x},{z})");
    }

    private static void Refresh()
    {
        if (_label != null)
        {
            var detail = EditorTools.IsObjectTool(_tool) ? EditorObjectTools.Detail(_tool, _target) : EditorTools.TileDetail(_target);
            _label.text = EditorTools.ToolbarText(_tool, detail);
        }

        if (_status != null)
        {
            var undo = _session?.CanUndo == true ? "ready" : "empty";
            var redo = _session?.CanRedo == true ? "ready" : "empty";
            var currentEdits = _session?.CurrentEdits.Count ?? 0;
            var dirty = _session != null && currentEdits != _lastSavedEditCount;
            var saveState = dirty ? "dirty" : "saved";
            _status.text = $"undo: {undo}  redo: {redo}  save: {saveState} ({currentEdits} edits)\n{_validateSummary}";
            _status.color = _reachability == null ? WarnColor : Color.white;
        }

        if (_loadList != null)
        {
            _loadList.text = RenderLoadList();
            _loadList.overflowMode = TextOverflowModes.Ellipsis;
        }

        if (_undoButtonBg != null)
        {
            _undoButtonBg.color = _session?.CanUndo == true ? new Color(0.15f, 0.15f, 0.15f, 0.95f) : new Color(0.1f, 0.1f, 0.1f, 0.55f);
        }

        if (_redoButtonBg != null)
        {
            _redoButtonBg.color = _session?.CanRedo == true ? new Color(0.15f, 0.15f, 0.15f, 0.95f) : new Color(0.1f, 0.1f, 0.1f, 0.55f);
        }

        if (_saveInputText != null)
        {
            _saveInputText.text = _saveName;
            _saveInputText.color = _saveInputFocused ? Color.white : new Color(0.85f, 0.85f, 0.85f, 1f);
        }

        if (_savePlaceholderText != null)
        {
            _savePlaceholderText.enabled = EditorInputModel.PlaceholderVisible(_saveName);
        }

        if (_loadStatusText != null && _loadStatusExpiry >= 0f && Time.unscaledTime >= _loadStatusExpiry)
        {
            _loadStatusText.text = "";
            _loadStatusExpiry = -1f;
        }

        if (_outline == null)
        {
            return;
        }

        if (_target is not { } target || LiveEditPatch.Grid is not { } grid)
        {
            _outline.enabled = false;
            return;
        }

        var corners = TileOutline.Corners(target.X, target.Z, target.State, grid.Width, grid.Depth, grid.Spacing, grid.TileHeight, OutlineLift);
        for (var i = 0; i < corners.Count; i++)
        {
            _outline.SetPosition(i, new Vector3(corners[i].X, corners[i].Y, corners[i].Z));
        }

        _outline.enabled = true;
    }

    private static void BuildToolbar()
    {
        _root = EditorUi.NewCanvas("MegabonkLevelsTileTools");
        var panel = EditorUi.NewRect("Toolbar", _root.transform);
        _toolbarRect = panel;
        panel.anchorMin = new Vector2(0.5f, 1f);
        panel.anchorMax = new Vector2(0.5f, 1f);
        panel.pivot = new Vector2(0.5f, 1f);
        panel.sizeDelta = new Vector2(ToolbarWidth, ToolbarHeight);
        panel.anchoredPosition = Vector2.zero;
        panel.gameObject.AddComponent<Image>().color = PanelColor;

        var labelRect = EditorUi.NewRect("Label", panel);
        labelRect.anchorMin = new Vector2(0f, 1f);
        labelRect.anchorMax = new Vector2(1f, 1f);
        labelRect.pivot = new Vector2(0f, 1f);
        labelRect.offsetMin = new Vector2(8f, -58f);
        labelRect.offsetMax = new Vector2(-8f, -4f);
        _label = EditorUi.NewLabel(labelRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.Center, FontSize);

        var actionsRect = EditorUi.NewRect("Actions", panel);
        actionsRect.anchorMin = new Vector2(0f, 1f);
        actionsRect.anchorMax = new Vector2(1f, 1f);
        actionsRect.pivot = new Vector2(0f, 1f);
        actionsRect.offsetMin = new Vector2(8f, -96f);
        actionsRect.offsetMax = new Vector2(-8f, -62f);

        _undoButtonBg = NewButton(actionsRect, "Undo", "Undo", 0f, 88f, Undo, () => _session?.CanUndo == true);
        _redoButtonBg = NewButton(actionsRect, "Redo", "Redo", 94f, 88f, Redo, () => _session?.CanRedo == true);
        NewButton(actionsRect, "Validate", "Validate", 188f, 110f, Validate);

        var saveX = 304f;
        NewInput(actionsRect, "SaveInput", saveX, 200f, "level");
        NewButton(actionsRect, "Save", "Save", saveX + 206f, 70f, () => { Save(); });
        NewButton(actionsRect, "Load", "Load", saveX + 282f, 70f, LoadSelected);

        var statusRect = EditorUi.NewRect("Status", panel);
        statusRect.anchorMin = new Vector2(0f, 1f);
        statusRect.anchorMax = new Vector2(1f, 1f);
        statusRect.pivot = new Vector2(0f, 1f);
        statusRect.offsetMin = new Vector2(8f, -138f);
        statusRect.offsetMax = new Vector2(-8f, -100f);
        _status = EditorUi.NewLabel(statusRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.Left, OverlayFontSize);

        var loadRect = EditorUi.NewRect("LoadList", _root.transform);
        _loadRect = loadRect;
        loadRect.anchorMin = new Vector2(1f, 1f);
        loadRect.anchorMax = new Vector2(1f, 1f);
        loadRect.pivot = new Vector2(1f, 1f);
        loadRect.sizeDelta = new Vector2(OverlayWidth, OverlayRowHeight * (MaxListedLevels + 1) + OverlayPadding * 2);
        loadRect.anchoredPosition = new Vector2(-8f, -8f);
        loadRect.gameObject.AddComponent<Image>().color = PanelColor;

        var loadLabelRect = EditorUi.NewRect("LoadText", loadRect);
        loadLabelRect.anchorMin = Vector2.zero;
        loadLabelRect.anchorMax = Vector2.one;
        loadLabelRect.offsetMin = new Vector2(OverlayPadding, OverlayPadding);
        loadLabelRect.offsetMax = new Vector2(-OverlayPadding, -OverlayPadding);
        _loadList = EditorUi.NewLabel(loadLabelRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.TopLeft, OverlayFontSize);
        _loadList.enableWordWrapping = true;
        _loadList.overflowMode = TextOverflowModes.Overflow;

        // Transient save/load status: bottom-right of the toolbar, orange, disappears after 3s.
        var lsRect = EditorUi.NewRect("LoadStatus", panel);
        lsRect.anchorMin = new Vector2(1f, 0f);
        lsRect.anchorMax = new Vector2(1f, 0f);
        lsRect.pivot = new Vector2(1f, 0f);
        lsRect.sizeDelta = new Vector2(420f, OverlayRowHeight);
        lsRect.anchoredPosition = new Vector2(-8f, 4f);
        _loadStatusText = EditorUi.NewLabel(lsRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.MidlineRight, OverlayFontSize);
        _loadStatusText.color = WarnColor;
        _loadStatusText.text = "";
    }

    private static void BuildOutline()
    {
        var go = new GameObject("MegabonkLevelsTileHighlight");
        UnityEngine.Object.DontDestroyOnLoad(go);
        _outline = go.AddComponent<LineRenderer>();
        _outline.loop = true;
        _outline.useWorldSpace = true;
        _outline.positionCount = 4;
        _outline.startWidth = OutlineWidth;
        _outline.endWidth = OutlineWidth;
        _outline.startColor = HighlightColor;
        _outline.endColor = HighlightColor;
        _outline.enabled = false;

        var shader = Shader.Find("Sprites/Default");
        if (shader == null)
        {
            shader = Shader.Find("Hidden/Internal-Colored");
        }

        if (shader == null)
        {
            _logger.Warning("EditorTileTools: no line shader found, the highlight may not render");
            return;
        }

        _outline.material = new Material(shader) { color = HighlightColor };
        _logger.Msg($"EditorTileTools: highlight shader '{shader.name}'");
    }

    public static bool ApplyFromObjectTools(EditOp op, string what)
    {
        var ok = ApplyFromTool(op, what);
        if (!ok)
        {
            _logger.Msg($"EditorObjectTools: {what} -> {op.OpType} not applied");
        }

        return ok;
    }

    private static bool ApplyFromTool(EditOp op, string what)
    {
        if (_session == null || !LiveEditPatch.TryBuildPlan(op, out var plan))
        {
            return false;
        }

        var applied = _session.Apply(plan, LiveEditPatch.ApplyLive);
        _logger.Msg($"EditorTileTools: {what} -> {op.OpType}{(applied ? "" : " not applied")}");
        if (applied)
        {
            InvalidateValidation();
        }

        return applied;
    }

    private static void HandleUndoRedoHotkeys()
    {
        var ctrl = Input.GetKey(KeyCode.LeftControl) || Input.GetKey(KeyCode.RightControl);
        if (!ctrl)
        {
            _ctrlHeldSince = -1f;
            return;
        }

        if (_ctrlHeldSince < 0f)
        {
            _ctrlHeldSince = Time.unscaledTime;
        }

        if (!EditorHotkeys.CtrlChordReady(_ctrlHeldSince, Time.unscaledTime, UndoRedoCtrlHoldSeconds))
        {
            return;
        }

        if (Input.GetKeyDown(KeyCode.Z))
        {
            Undo();
        }
        else if (Input.GetKeyDown(KeyCode.Y))
        {
            Redo();
        }
    }

    private static void Undo()
    {
        var undone = _session?.Undo(LiveEditPatch.ApplyLive) == true;
        _logger.Msg($"EditorTileTools: undo{(undone ? "" : " not applied")}");
        if (undone)
        {
            InvalidateValidation();
        }
    }

    private static void Redo()
    {
        var redone = _session?.Redo(LiveEditPatch.ApplyLive) == true;
        _logger.Msg($"EditorTileTools: redo{(redone ? "" : " not applied")}");
        if (redone)
        {
            InvalidateValidation();
        }
    }

    private static void Validate()
    {
        if (LiveEditPatch.CurrentState() is not { } state || LiveEditPatch.Grid is not { } grid)
        {
            _validateSummary = "validate: no live level";
            _reachability = null;
            ClearUnreachable();
            return;
        }

        var spawn = SpawnCell(grid);
        if (spawn == null)
        {
            _validateSummary = "validate: no spawn portal found";
            _reachability = null;
            ClearUnreachable();
            return;
        }

        try
        {
            _reachability = ReachabilityValidator.Validate(state, spawn.Value);
        }
        catch (ArgumentException ex)
        {
            _validateSummary = $"validate failed: {ex.Message}";
            _reachability = null;
            ClearUnreachable();
            return;
        }

        RenderUnreachable(_reachability.Unreachable, grid, state);
        var portal = LiveEditPatch.BossPortalCell();
        var portalText = portal is { } target
            ? (_reachability.IsReachable(target) ? "reachable" : "unreachable")
            : "not found";
        _validateSummary = $"validate: {_reachability.Unreachable.Count} unreachable, boss portal {portalText}";
    }

    private static (int X, int Z)? SpawnCell(LiveGrid grid)
    {
        foreach (var pair in LiveEditPatch.PickableObjects())
        {
            if (pair.Object == null)
            {
                continue;
            }

            var name = pair.Object.name.ToLowerInvariant();
            if (!name.Contains("portal") || !name.Contains("spawn") || name.Contains("boss"))
            {
                continue;
            }

            var cell = PositionReadout.CellOf(pair.Object.transform.position.x, pair.Object.transform.position.z, grid.Width, grid.Depth, grid.Spacing);
            if (cell.InGrid)
            {
                return (cell.X, cell.Z);
            }
        }

        return null;
    }

    private static bool Save()
    {
        if (_session == null)
        {
            return false;
        }

        var level = LiveEditPatch.SnapshotLevelFile(_session.CurrentEdits);
        if (level == null)
        {
            _validateSummary = "save failed: no active run";
            return false;
        }

        var fileName = EditorFileNaming.NormalizeLevelFileName(_saveName);
        var path = Path.Combine(LiveEditPatch.LevelsDirectoryPath(), fileName);
        try
        {
            File.WriteAllText(path, LevelFileSerializer.Serialize(level.Value));
        }
        catch (Exception ex)
        {
            _validateSummary = $"save failed: {ex.Message}";
            return false;
        }

        _lastSavedEditCount = _session.CurrentEdits.Count;
        _validateSummary = $"saved {fileName}";
        ShowTransientStatus($"saved: {fileName}");
        _saveName = fileName.Substring(0, fileName.Length - ".mblevel.json".Length);

        RefreshLoadList(fileName);
        return true;
    }

    private static void LoadSelected()
    {
        if (_levelFiles.Count == 0)
        {
            _validateSummary = "load failed: no files";
            return;
        }

        var name = _levelFiles[Mathf.Clamp(_selectedLevel, 0, _levelFiles.Count - 1)];
        var path = Path.Combine(LiveEditPatch.LevelsDirectoryPath(), name);

        LevelFile level;
        try
        {
            level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(path));
        }
        catch (Exception ex)
        {
            _validateSummary = $"load failed: {ex.Message}";
            return;
        }

        var warning = GameBuildIdCheck.MismatchWarning(level.GameBuildId, GameBuildIdPatch.CurrentBuildId());
        if (warning != null)
        {
            _logger.Warning(warning);
        }

        if (!LiveEditPatch.ResetAndApplyEdits(level.Edits, _logger))
        {
            _validateSummary = "load failed: no active run";
            return;
        }

        _session = new EditorEditSession(level.Edits);
        _lastSavedEditCount = level.Edits.Count;
        InvalidateValidation();
        _validateSummary = $"loaded {name}";
        ShowTransientStatus($"loaded: {name}");
    }

    // Load applies the selected file's edits in-place (resets live tiles/objects to baseline, then replays the file's edits) without relaunching.

    private static void RefreshLoadList(string selectName = null)
    {
        _levelFiles.Clear();
        _levelFiles.AddRange(LiveEditPatch.ListLevelFiles());
        if (_levelFiles.Count == 0)
        {
            _selectedLevel = 0;
            return;
        }

        if (selectName != null)
        {
            var index = _levelFiles.FindIndex(n => n.Equals(selectName, StringComparison.OrdinalIgnoreCase));
            _selectedLevel = index >= 0 ? index : 0;
        }
        else
        {
            _selectedLevel = Mathf.Clamp(_selectedLevel, 0, _levelFiles.Count - 1);
        }
    }

    private static string RenderLoadList()
    {
        if (_levelFiles.Count == 0)
        {
            return "levels/UserData\n(no .mblevel.json files)";
        }

        var start = Mathf.Max(0, _selectedLevel - MaxListedLevels / 2);
        if (start + MaxListedLevels > _levelFiles.Count)
        {
            start = Mathf.Max(0, _levelFiles.Count - MaxListedLevels);
        }

        var lines = new List<string> { "levels/UserData" };
        for (var i = start; i < _levelFiles.Count && i < start + MaxListedLevels; i++)
        {
            lines.Add((i == _selectedLevel ? "<color=#ffd84d>> </color>" : "  ") + _levelFiles[i]);
        }

        return string.Join("\n", lines);
    }

    private static void InvalidateValidation()
    {
        _reachability = null;
        _validateSummary = "validate: stale (run validate)";
        ClearUnreachable();
    }

    private static void RenderUnreachable(IReadOnlyList<(int X, int Z)> cells, LiveGrid grid, LevelState state)
    {
        ClearUnreachable();
        foreach (var (x, z) in cells)
        {
            if (state.GetTile(x, z) is not { } tile)
            {
                continue;
            }

            var line = NewOverlayLine(new Color(1f, 0.3f, 0.3f, 1f), 0.5f, true, 4);
            var corners = TileOutline.Corners(x, z, tile, grid.Width, grid.Depth, grid.Spacing, grid.TileHeight, OutlineLift + 0.15f);
            for (var i = 0; i < corners.Count; i++)
            {
                line.SetPosition(i, new Vector3(corners[i].X, corners[i].Y, corners[i].Z));
            }

            line.enabled = true;
            _unreachable.Add(line);
        }
    }

    private static void ClearUnreachable()
    {
        foreach (var line in _unreachable)
        {
            if (line != null)
            {
                UnityEngine.Object.Destroy(line.gameObject);
            }
        }

        _unreachable.Clear();
    }

    private static void ShowTransientStatus(string text)
    {
        if (_loadStatusText != null) _loadStatusText.text = text;
        _loadStatusExpiry = Time.unscaledTime + 3f;
    }

    private static bool PointerOverOverlay() =>
        (_toolbarRect != null && RectTransformUtility.RectangleContainsScreenPoint(_toolbarRect, Input.mousePosition, null))
        || (_loadRect != null && RectTransformUtility.RectangleContainsScreenPoint(_loadRect, Input.mousePosition, null));

    private static void HandleOverlayInput()
    {
        if (_saveInputFocused)
        {
            HandleSaveTyping();
        }

        ScrollLoadList();

        if (!Input.GetMouseButtonDown(0))
        {
            return;
        }

        var mouse = (Vector2)Input.mousePosition;
        var handled = false;
        foreach (var region in _clickRegions)
        {
            if (region.Rect != null
                && RectTransformUtility.RectangleContainsScreenPoint(region.Rect, mouse, null)
                && (region.Enabled == null || region.Enabled()))
            {
                region.OnClick();
                handled = true;
                break;
            }
        }

        if (!handled)
        {
            handled = TrySelectLoadRow(mouse);
        }

        _saveInputFocused = _saveInputRect != null && RectTransformUtility.RectangleContainsScreenPoint(_saveInputRect, mouse, null);
    }

    private static void ScrollLoadList()
    {
        if (_loadRect == null || !RectTransformUtility.RectangleContainsScreenPoint(_loadRect, Input.mousePosition, null))
        {
            return;
        }

        var selected = EditorOverlayModel.SelectedIndexAfterScroll(_selectedLevel, _levelFiles.Count, Input.mouseScrollDelta.y);
        if (selected == _selectedLevel)
        {
            return;
        }

        _selectedLevel = selected;
        _saveName = EditorFileNaming.StemForForm(_levelFiles[selected], SaveNameMaxChars);
    }

    private static void HandleSaveTyping()
    {
        if (Input.GetKey(KeyCode.LeftControl) || Input.GetKey(KeyCode.RightControl))
        {
            return;
        }

        foreach (var c in Input.inputString)
        {
            if (c == '\b')
            {
                if (_saveName.Length > 0)
                {
                    _saveName = _saveName.Substring(0, _saveName.Length - 1);
                }
            }
            else if (c == '\n' || c == '\r')
            {
                Save();
            }
            else if (!char.IsControl(c) && _saveName.Length < SaveNameMaxChars)
            {
                _saveName += c;
            }
        }

        if (Input.GetKeyDown(KeyCode.Escape))
        {
            _saveInputFocused = false;
        }
    }

    private static bool TrySelectLoadRow(Vector2 mouse)
    {
        if (_loadRect == null || _levelFiles.Count == 0 || !RectTransformUtility.RectangleContainsScreenPoint(_loadRect, mouse, null))
        {
            return false;
        }

        if (!RectTransformUtility.ScreenPointToLocalPointInRectangle(_loadRect, mouse, null, out var local))
        {
            return false;
        }

        var top = _loadRect.rect.yMax - OverlayPadding;
        var line = Mathf.FloorToInt((top - local.y) / OverlayRowHeight);
        if (line <= 0)
        {
            return false;
        }

        var maybeIndex = EditorOverlayModel.LoadIndexAtRow(_selectedLevel, _levelFiles.Count, MaxListedLevels, line - 1);
        if (maybeIndex is not { } index)
        {
            return false;
        }

        _selectedLevel = index;
        _saveName = EditorFileNaming.StemForForm(_levelFiles[index], SaveNameMaxChars);
        return true;
    }

    private static Image NewButton(RectTransform parent, string name, string text, float x, float width, Action onClick, Func<bool> enabled = null)
    {
        var rect = EditorUi.NewRect(name, parent);
        rect.anchorMin = new Vector2(0f, 1f);
        rect.anchorMax = new Vector2(0f, 1f);
        rect.pivot = new Vector2(0f, 1f);
        rect.sizeDelta = new Vector2(width, OverlayRowHeight);
        rect.anchoredPosition = new Vector2(x, 0f);

        var image = rect.gameObject.AddComponent<Image>();
        image.color = new Color(0.15f, 0.15f, 0.15f, 0.95f);
        _clickRegions.Add(new ClickRegion { Rect = rect, OnClick = onClick, Enabled = enabled });

        var labelRect = EditorUi.NewRect("Text", rect);
        labelRect.anchorMin = Vector2.zero;
        labelRect.anchorMax = Vector2.one;
        labelRect.offsetMin = Vector2.zero;
        labelRect.offsetMax = Vector2.zero;
        var label = EditorUi.NewLabel(labelRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.Center, OverlayFontSize);
        label.text = text;
        return image;
    }

    private static void NewInput(RectTransform parent, string name, float x, float width, string placeholder)
    {
        var rect = EditorUi.NewRect(name, parent);
        _saveInputRect = rect;
        rect.anchorMin = new Vector2(0f, 1f);
        rect.anchorMax = new Vector2(0f, 1f);
        rect.pivot = new Vector2(0f, 1f);
        rect.sizeDelta = new Vector2(width, OverlayRowHeight);
        rect.anchoredPosition = new Vector2(x, 0f);
        rect.gameObject.AddComponent<Image>().color = new Color(0.1f, 0.1f, 0.1f, 0.95f);

        var textRect = EditorUi.NewRect("Text", rect);
        textRect.anchorMin = Vector2.zero;
        textRect.anchorMax = Vector2.one;
        textRect.offsetMin = new Vector2(8f, 0f);
        textRect.offsetMax = new Vector2(-8f, 0f);
        _saveInputText = EditorUi.NewLabel(textRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.MidlineLeft, OverlayFontSize);
        _saveInputText.text = placeholder;

        var phRect = EditorUi.NewRect("Placeholder", rect);
        phRect.anchorMin = Vector2.zero;
        phRect.anchorMax = Vector2.one;
        phRect.offsetMin = new Vector2(8f, 0f);
        phRect.offsetMax = new Vector2(-8f, 0f);
        _savePlaceholderText = EditorUi.NewLabel(phRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.MidlineLeft, OverlayFontSize);
        _savePlaceholderText.text = placeholder;
        _savePlaceholderText.color = new Color(0.6f, 0.6f, 0.6f, 1f);
        _saveName = "";
    }

    private static LineRenderer NewOverlayLine(Color color, float width, bool loop, int points)
    {
        var go = new GameObject("MegabonkLevelsValidationOverlay");
        UnityEngine.Object.DontDestroyOnLoad(go);
        var line = go.AddComponent<LineRenderer>();
        line.loop = loop;
        line.useWorldSpace = true;
        line.positionCount = points;
        line.startWidth = width;
        line.endWidth = width;
        line.startColor = color;
        line.endColor = color;
        line.enabled = false;

        var shader = Shader.Find("Sprites/Default") ?? Shader.Find("Hidden/Internal-Colored");
        if (shader == null)
        {
            _logger.Warning("EditorTileTools: no line shader found for validation overlay");
            return line;
        }

        line.material = new Material(shader) { color = color };
        return line;
    }
}
