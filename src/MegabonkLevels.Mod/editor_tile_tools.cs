using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json.Nodes;
using Il2Cpp;
using Il2CppTMPro;
using MelonLoader;
using UnityEngine;
using UnityEngine.UI;
using static MegabonkLevels.EditorUi;

namespace MegabonkLevels;

// See "Tile tools" in docs/development.md.
public static class EditorTileTools
{
    private const float ToolbarMargin = 8f;
    private const float ToastSeconds = 3f;
    private const float ToastGap = 4f;
    private const int MaxToasts = 5;
    private const float ToolbarHeight = 116f;
    private const float FontSize = 18f;
    private const float OverlayFontSize = 16f;
    private const float ToolGap = 8f;
    private const float RayLength = 5000f;
    private const float WallNudge = 0.01f;
    private const float OutlineLift = 0.5f;
    private const float OutlineWidth = 0.8f;
    private const float OverlayWidth = 300f;
    private const float OverlayRowHeight = 30f;
    private const float OverlayPadding = 8f;
    private const int ListedLevels = 4;
    private const float ListTitleHeight = 24f;
    private const float ListRowHeight = 19f;
    // The 16 pt line is taller than a list row, and an ellipsis label hides lines that overflow its rect.
    private const float ListRowTextOverhang = 4f;
    private const float ListPagerButtonWidth = 28f;
    private const float ListPageLabelWidth = 48f;
    private const float UndoRedoCtrlHoldSeconds = 0.2f;
    private const int SaveNameMaxChars = 80;

    private static readonly Color PanelColor = new(0f, 0f, 0f, 0.75f);
    private static readonly Color HighlightColor = new(1f, 0.85f, 0.3f, 1f);
    private static readonly Color WarnColor = new(1f, 0.7f, 0.2f, 1f);
    private static readonly Color ErrorColor = new(1f, 0.4f, 0.4f, 1f);

    private static MelonLogger.Instance _logger;
    private static GameObject _root;
    private static readonly List<ToolSlot> _toolSlots = new();
    private static TextMeshProUGUI _status;
    private static TextMeshProUGUI _loadPageLabel;
    private static readonly List<LoadRow> _loadRows = new();
    private static EditorTooltip _hint;
    private static readonly HoverDelay _hintDelay = EditorTooltip.NewHoverDelay();
    private static TextMeshProUGUI _saveInputText;
    private static TextMeshProUGUI _savePlaceholderText;
    private static RectTransform _saveInputRect;
    private static Image _saveInputFill;
    private static Image _undoButtonBg;
    private static Image _redoButtonBg;
    private static LineRenderer _outline;
    private static readonly List<LineRenderer> _unreachable = new();
    private static readonly List<ClickRegion> _clickRegions = new();
    private static readonly List<string> _levelFiles = new();
    private static EditorTool _tool = EditorTools.Default;
    private static (int X, int Z, TileState State)? _target;
    private static Vector3 _targetPoint;
    private static bool _terrainHit;
    private static RectTransform _toolbarRect;
    private static RectTransform _loadRect;
    private static readonly ToastStack _toasts = new(ToastSeconds, MaxToasts);
    private static readonly List<ToastSlot> _toastSlots = new();
    private static EditorEditSession _session;
    private static int _sessionRunGeneration = -1;
    private static ReachabilityResult _reachability;
    private static string _validateSummary = "validate: not run";
    private static int _selectedLevel;
    private static int _loadPage;
    private static float _ctrlHeldSince = -1f;
    private static bool _saveInputFocused;
    private static bool _textInputCaptured;
    private static readonly TextFieldModel _saveField = new(SaveNameMaxChars);
    private static readonly EditorCaretInput _saveCaretInput = new();
    private static TextFieldView _saveView;
    private static int _lastSavedEditCount;
    private static string _lastSavedName;
    private static string _saveStatus = "none";

    private sealed class ToastSlot
    {
        public RectTransform Rect;
        public Image Background;
        public TextMeshProUGUI Text;
    }

    private sealed class ToolSlot
    {
        public RectTransform Rect;
        public TextMeshProUGUI Text;
    }

    private sealed class LoadRow
    {
        public RectTransform Rect;
        public Image Fill;
        public TextMeshProUGUI Text;
    }

    private sealed class ClickRegion
    {
        public string Name;
        public RectTransform Rect;
        public Action OnClick;
        public Func<bool> Enabled;
        public bool OmitWhenDisabled;
    }

    public static bool PointerOverEditorOverlay => PointerOverOverlay();

    public static bool TextInputFocused => _saveInputFocused || _textInputCaptured || EditorPalette.TextInputCaptured || EditorEscapeInput.CapturedThisFrame;

    public static bool SaveInputFocused => _saveInputFocused;

    public static bool SaveInputHasText => _saveField.Text.Length > 0;

    public static void BlurSaveInput() => _saveInputFocused = false;

    public static void ClearSaveInput() => _saveField.Clear();

    public static void OnEditorEntered(MelonLogger.Instance logger)
    {
        _logger = logger;
        _tool = EditorTools.Default;
        SynchronizeSession();

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
        _toolSlots.Clear();
        _status = null;
        _loadPageLabel = null;
        _loadRows.Clear();
        _hint = null;
        _saveInputFill = null;
        _saveInputText = null;
        _saveView = null;
        _savePlaceholderText = null;
        _saveInputRect = null;
        _undoButtonBg = null;
        _redoButtonBg = null;
        _outline = null;
        _toasts.Clear();
        _toastSlots.Clear();
        _target = null;
        _toolbarRect = null;
        _loadRect = null;
        _reachability = null;
        _levelFiles.Clear();
        _selectedLevel = 0;
        _loadPage = 0;
        _ctrlHeldSince = -1f;
        _saveInputFocused = false;
        _textInputCaptured = false;
        _saveField.Clear();
        _clickRegions.Clear();
        ClearUnreachable();
    }

    public static void Tick()
    {
        if (SynchronizeSession())
        {
            InvalidateValidation();
        }

        if (_toolbarRect != null)
        {
            CentreToolbar();
        }

        _textInputCaptured = _saveInputFocused || EditorPalette.TextInputCaptured;
        HandleOverlayInput();
        _textInputCaptured |= _saveInputFocused;
        if (TextInputFocused)
        {
            _ctrlHeldSince = -1f;
            _target = null;
            Refresh();
            return;
        }

        HandleUndoRedoHotkeys();

        for (var digit = 1; digit <= 9; digit++)
        {
            if (EditorInput.GetKeyDown(KeyCode.Alpha0 + digit) && EditorTools.FromHotkey(digit) is { } tool)
            {
                SetTool(tool);
            }
        }

        var pointerOverToolbar = PointerOverOverlay();
        _target = EditorPalette.PointerOverPanel || pointerOverToolbar ? null : FindTarget();
        if (EditorTools.IsObjectTool(_tool) && !pointerOverToolbar)
        {
            if (EditorObjectTools.Tick(_tool, _target, _terrainHit, _targetPoint) is { } requested)
            {
                SetTool(requested);
            }
        }
        else if (_target is { } target && EditorInput.GetMouseButtonDown(0))
        {
            Use(target.X, target.Z, target.State);
            _target = FindTarget();
        }

        Refresh();
    }

    private static void SetTool(EditorTool tool)
    {
        if (!EditorTools.IsAvailable(tool, tileTools: !LiveEditPatch.IsTerrainMap))
        {
            Warn(EditorTools.UnavailableMessage(tool));
            return;
        }

        if (tool != _tool)
        {
            EditorObjectTools.OnToolChanged(tool);
        }

        _tool = tool;
    }

    private static (int X, int Z, TileState State)? FindTarget()
    {
        _terrainHit = false;
        var camera = PlayerCamera.Instance?.camera;
        var ground = LiveEditPatch.GroundCollider();
        if (camera == null || ground == null)
        {
            return null;
        }

        if (!ground.Raycast(camera.ScreenPointToRay(EditorInput.MousePosition), out var hit, RayLength))
        {
            return null;
        }

        if (LiveEditPatch.Grid is not { } grid)
        {
            _targetPoint = hit.point;
            _terrainHit = LiveEditPatch.IsTerrainMap;
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
        for (var i = 0; i < _toolSlots.Count; i++)
        {
            _toolSlots[i].Text.text = EditorTools.ToolLabel(EditorTools.All[i], _tool);
        }

        if (_hint != null)
        {
            RefreshHint();
        }

        if (_status != null)
        {
            var undo = _session?.CanUndo == true ? "ready" : "empty";
            var redo = _session?.CanRedo == true ? "ready" : "empty";
            var currentEdits = _session?.CurrentEdits.Count ?? 0;
            var dirty = IsDirty();
            var saveState = dirty ? "dirty" : "saved";
            _status.text = $"undo: {undo}  redo: {redo}  save: {saveState} ({currentEdits} edits)\n{_validateSummary}";
            _status.color = _reachability == null ? WarnColor : Color.white;
        }

        if (_loadPageLabel != null)
        {
            RenderLoadList();
        }

        if (_undoButtonBg != null)
        {
            _undoButtonBg.color = _session?.CanUndo == true ? SlotFill : SearchFill;
        }

        if (_redoButtonBg != null)
        {
            _redoButtonBg.color = _session?.CanRedo == true ? SlotFill : SearchFill;
        }

        if (_saveInputText != null)
        {
            _saveView?.Render(_saveField, _saveInputFocused, null);
            _saveInputText.color = _saveInputFocused ? Color.white : new Color(0.85f, 0.85f, 0.85f, 1f);
            _saveInputFill.color = _saveInputFocused ? SelectedFill : SearchFill;
        }

        if (_savePlaceholderText != null)
        {
            _savePlaceholderText.enabled = EditorInputModel.PlaceholderVisible(_saveField.Text);
        }

        if (_toastSlots.Count > 0)
        {
            _toasts.Expire(Time.unscaledTime);
            RenderToasts();
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

    private static void RefreshHint()
    {
        var mouse = (Vector2)EditorInput.MousePosition;
        int? hovered = null;
        for (var i = 0; i < _toolSlots.Count; i++)
        {
            if (RectTransformUtility.RectangleContainsScreenPoint(_toolSlots[i].Rect, mouse, null))
            {
                hovered = i;
                break;
            }
        }

        if (!_hintDelay.Update(hovered, Time.unscaledTime) || hovered is not { } tool)
        {
            _hint.Hide();
            return;
        }

        var belowToolbar = new Vector2(mouse.x, Screen.height - EditorUi.TopInset - ToolbarHeight);
        _hint.Show(EditorTools.Description(EditorTools.All[tool]), belowToolbar);
    }

    // The toolbar sits centred between the expanded palette and the load overlay, so collapsing the palette does not move it.
    private static void CentreToolbar()
    {
        var freeWidth = Screen.width - EditorPalette.ExpandedWidth - OverlayWidth;
        _toolbarRect.anchoredPosition = new Vector2(EditorPalette.ExpandedWidth + freeWidth / 2f - Screen.width / 2f, -EditorUi.TopInset);
    }

    private static void BuildToolbar()
    {
        _root = EditorUi.NewCanvas("MegabonkLevelsTileTools");
        var font = PositionLabel.FindFontAsset(EditorUi.FontName);
        var panel = Bordered("Toolbar", _root.transform, PanelBorder, PanelFill).Outer;
        _toolbarRect = panel;
        panel.anchorMin = new Vector2(0.5f, 1f);
        panel.anchorMax = new Vector2(0.5f, 1f);
        panel.pivot = new Vector2(0.5f, 1f);
        CentreToolbar();

        var toolWidths = new List<float>();
        foreach (var tool in EditorTools.All)
        {
            var toolRect = EditorUi.NewRect($"Tool{tool}", panel);
            var toolText = EditorUi.NewLabel(toolRect, font, TextAlignmentOptions.Center, FontSize);
            toolText.text = EditorTools.ToolLabel(tool, tool);
            toolText.ForceMeshUpdate();
            toolWidths.Add(toolText.preferredWidth);
            _toolSlots.Add(new ToolSlot { Rect = toolRect, Text = toolText });
            var selected = tool;
            _clickRegions.Add(new ClickRegion { Name = EditorTools.WidgetName(tool), Rect = toolRect, OnClick = () => SetTool(selected) });
        }


        var actionsRect = EditorUi.NewRect("Actions", panel);
        actionsRect.anchorMin = new Vector2(0f, 1f);
        actionsRect.anchorMax = new Vector2(1f, 1f);
        actionsRect.pivot = new Vector2(0f, 1f);
        actionsRect.offsetMin = new Vector2(8f, -68f);
        actionsRect.offsetMax = new Vector2(-8f, -38f);

        _undoButtonBg = NewButton(actionsRect, "Undo", "Undo", 0f, 88f, Undo, () => _session?.CanUndo == true);
        _redoButtonBg = NewButton(actionsRect, "Redo", "Redo", 94f, 88f, Redo, () => _session?.CanRedo == true);
        NewButton(actionsRect, "Validate", "Validate", 188f, 110f, Validate);

        var saveX = 304f;
        NewInput(actionsRect, "SaveInput", saveX, 200f, "level");
        NewButton(actionsRect, "Save", "Save", saveX + 206f, 70f, () => { Save(); });
        NewButton(actionsRect, "Load", "Load", saveX + 282f, 70f, LoadSelected);

        var actionsWidth = saveX + 282f + 70f;
        var toolsWidth = toolWidths.Sum() + ToolGap * (toolWidths.Count - 1);
        var toolbarWidth = Mathf.Max(actionsWidth, toolsWidth) + ToolbarMargin * 2f;
        panel.sizeDelta = new Vector2(toolbarWidth, ToolbarHeight);
        var toolX = (toolbarWidth - toolsWidth) / 2f;
        for (var i = 0; i < _toolSlots.Count; i++)
        {
            PlaceTopLeft(_toolSlots[i].Rect, toolX - ToolGap / 2f, 6f, toolWidths[i] + ToolGap, 28f);
            toolX += toolWidths[i] + ToolGap;
        }

        var statusRect = EditorUi.NewRect("Status", panel);
        statusRect.anchorMin = new Vector2(0f, 1f);
        statusRect.anchorMax = new Vector2(1f, 1f);
        statusRect.pivot = new Vector2(0f, 1f);
        statusRect.offsetMin = new Vector2(8f, -110f);
        statusRect.offsetMax = new Vector2(-8f, -72f);
        _status = EditorUi.NewLabel(statusRect, font, TextAlignmentOptions.Left, OverlayFontSize);

        BuildLoadList(font);

        // Toasts stack under the toolbar, newest nearest it: orange for success, red for failures, each cleared after ToastSeconds or on click.
        for (var i = 0; i < MaxToasts; i++)
        {
            _toastSlots.Add(BuildToastSlot(i, toolbarWidth, panel.anchoredPosition.x));
        }

        _hint = new EditorTooltip(_root.transform, font, OverlayFontSize);
    }

    private static void BuildLoadList(TMP_FontAsset font)
    {
        var loadRect = Bordered("LoadList", _root.transform, PanelBorder, PanelFill).Outer;
        _loadRect = loadRect;
        loadRect.anchorMin = new Vector2(1f, 1f);
        loadRect.anchorMax = new Vector2(1f, 1f);
        loadRect.pivot = new Vector2(1f, 1f);
        loadRect.sizeDelta = new Vector2(OverlayWidth, ToolbarHeight);
        loadRect.anchoredPosition = new Vector2(0f, -EditorUi.TopInset);

        var pagerLeft = OverlayWidth - OverlayPadding - ListPagerButtonWidth * 2f - ListPageLabelWidth;
        var titleRect = EditorUi.NewRect("LoadTitle", loadRect);
        PlaceTopLeft(titleRect, OverlayPadding, OverlayPadding, pagerLeft - OverlayPadding, ListTitleHeight);
        EditorUi.NewLabel(titleRect, font, TextAlignmentOptions.MidlineLeft, OverlayFontSize).text = "levels/UserData";

        NewButton(loadRect, "PreviousLevels", "<", pagerLeft, ListPagerButtonWidth, () => StepLoadPage(-1f), null, OverlayPadding, ListTitleHeight);
        var pageRect = EditorUi.NewRect("LoadPage", loadRect);
        PlaceTopLeft(pageRect, pagerLeft + ListPagerButtonWidth, OverlayPadding, ListPageLabelWidth, ListTitleHeight);
        _loadPageLabel = EditorUi.NewLabel(pageRect, font, TextAlignmentOptions.Center, OverlayFontSize);
        NewButton(loadRect, "NextLevels", ">", pagerLeft + ListPagerButtonWidth + ListPageLabelWidth, ListPagerButtonWidth, () => StepLoadPage(1f), null, OverlayPadding, ListTitleHeight);

        for (var i = 0; i < ListedLevels; i++)
        {
            var row = EditorUi.NewRect($"LoadRow{i}", loadRect);
            PlaceTopLeft(row, OverlayPadding, OverlayPadding + ListTitleHeight + i * ListRowHeight, OverlayWidth - OverlayPadding * 2f, ListRowHeight);
            var fill = row.gameObject.AddComponent<Image>();
            fill.color = Color.clear;
            var textRect = EditorUi.NewRect("Text", row);
            textRect.anchorMin = Vector2.zero;
            textRect.anchorMax = Vector2.one;
            textRect.offsetMin = new Vector2(4f, -ListRowTextOverhang);
            textRect.offsetMax = new Vector2(-4f, ListRowTextOverhang);
            _loadRows.Add(new LoadRow { Rect = row, Fill = fill, Text = EditorUi.NewLabel(textRect, font, TextAlignmentOptions.MidlineLeft, OverlayFontSize) });
        }
    }

    private static ToastSlot BuildToastSlot(int index, float width, float x)
    {
        var rect = EditorUi.NewRect($"Toast{index}", _root.transform);
        rect.anchorMin = new Vector2(0.5f, 1f);
        rect.anchorMax = new Vector2(0.5f, 1f);
        rect.pivot = new Vector2(0.5f, 1f);
        rect.sizeDelta = new Vector2(width, OverlayRowHeight);
        rect.anchoredPosition = new Vector2(x, -(EditorUi.TopInset + ToolbarHeight + ToastGap + index * (OverlayRowHeight + ToastGap)));
        _clickRegions.Add(new ClickRegion { Name = $"Toast{index}", Rect = rect, OnClick = () => _toasts.Dismiss(index), Enabled = () => index < _toasts.Items.Count, OmitWhenDisabled = true });

        var background = rect.gameObject.AddComponent<Image>();
        background.color = PanelColor;
        background.enabled = false;

        var textRect = EditorUi.NewRect($"Toast{index}Text", rect);
        textRect.anchorMin = Vector2.zero;
        textRect.anchorMax = Vector2.one;
        textRect.offsetMin = new Vector2(ToolbarMargin, 0f);
        textRect.offsetMax = new Vector2(-ToolbarMargin, 0f);
        var text = EditorUi.NewLabel(textRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.Center, OverlayFontSize);
        text.text = "";
        return new ToastSlot { Rect = rect, Background = background, Text = text };
    }

    private static void RenderToasts()
    {
        for (var i = 0; i < _toastSlots.Count; i++)
        {
            var slot = _toastSlots[i];
            var shown = i < _toasts.Items.Count;
            slot.Background.enabled = shown;
            slot.Text.text = shown ? _toasts.Items[i].Text : "";
            if (shown)
            {
                slot.Text.color = _toasts.Items[i].IsError ? ErrorColor : WarnColor;
            }
        }
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

    public static EditorTool CurrentTool => _tool;

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

    // Editor re-entry may happen before the map's generation-complete callback.
    private static bool SynchronizeSession()
    {
        if (!EditorSessionPick.Pick(LiveEditPatch.RunGeneration, _session, _sessionRunGeneration, _lastSavedEditCount, LiveEditPatch.SeedEdits, out var session, out var generation, out var saved))
        {
            return false;
        }

        _session = session;
        _sessionRunGeneration = generation;
        _lastSavedEditCount = saved;
        return true;
    }

    private static void HandleUndoRedoHotkeys()
    {
        var ctrl = EditorInput.GetKey(KeyCode.LeftControl) || EditorInput.GetKey(KeyCode.RightControl);
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

        if (EditorInput.GetKeyDown(KeyCode.Z))
        {
            Undo();
        }
        else if (EditorInput.GetKeyDown(KeyCode.Y))
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
            Fail("validate: no live level");
            _reachability = null;
            ClearUnreachable();
            return;
        }

        var spawn = SpawnCell(grid);
        if (spawn == null)
        {
            Fail("validate: no spawn portal found");
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
            Fail($"validate failed: {ex.Message}");
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

    private static bool IsDirty() => _session != null && _session.CurrentEdits.Count != _lastSavedEditCount;

    public static EditsSnapshot ReadEdits() =>
        new(_session?.CurrentEdits.Count ?? 0, IsDirty(), _lastSavedName, _saveStatus);

    // Saves like the Save button; a non-null rawName replaces the save field's text, and a failure throws so the harness reports it.
    public static JsonObject SaveLevel(string rawName)
    {
        if (!EditorMode.Active)
        {
            throw new InvalidOperationException("editor mode is off");
        }

        if (rawName != null)
        {
            _saveField.Set(rawName);
        }

        if (!Save())
        {
            throw new InvalidOperationException(_validateSummary ?? "save failed");
        }

        return new JsonObject
        {
            ["name"] = _lastSavedName,
            ["path"] = Path.Combine(LiveEditPatch.LevelsDirectoryPath(), _lastSavedName),
            ["edits"] = _lastSavedEditCount,
        };
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
            Fail("save failed: no active run");
            return false;
        }

        var fileName = EditorFileNaming.NormalizeLevelFileName(_saveField.Text);
        var path = Path.Combine(LiveEditPatch.LevelsDirectoryPath(), fileName);
        try
        {
            File.WriteAllText(path, LevelFileSerializer.Serialize(level.Value));
        }
        catch (Exception ex)
        {
            _saveStatus = "failed";
            Fail($"save failed: {ex.Message}");
            return false;
        }

        _lastSavedEditCount = _session.CurrentEdits.Count;
        _lastSavedName = fileName;
        _saveStatus = "saved";
        _validateSummary = $"saved {fileName}";
        ShowTransientStatus($"saved: {fileName}");
        _saveField.Set(fileName.Substring(0, fileName.Length - ".mblevel.json".Length));

        RefreshLoadList(fileName);
        return true;
    }

    private static void LoadSelected()
    {
        if (_levelFiles.Count == 0)
        {
            Fail("load failed: no files");
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
            Fail($"load failed: {ex.Message}");
            return;
        }

        var warning = GameBuildIdCheck.MismatchWarning(level.GameBuildId, GameBuildIdPatch.CurrentBuildId());
        if (warning != null)
        {
            _logger.Warning(warning);
        }

        foreach (var (packId, recordedVersion) in level.Packs)
        {
            var packWarning = GamePackVersionCheck.MismatchWarning(packId, recordedVersion, PackPrefabs.ManifestVersion(packId));
            if (packWarning != null)
            {
                _logger.Warning(packWarning);
            }
        }

        if (!LiveEditPatch.ResetAndApplyEdits(level.Edits, _logger))
        {
            Fail("load failed: no active run");
            return;
        }

        _session = new EditorEditSession(level.Edits);
        _sessionRunGeneration = LiveEditPatch.RunGeneration;
        _lastSavedEditCount = level.Edits.Count;
        _lastSavedName = name;
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
            _loadPage = 0;
            return;
        }

        if (selectName != null)
        {
            var index = _levelFiles.FindIndex(n => n.Equals(selectName, StringComparison.OrdinalIgnoreCase));
            _selectedLevel = index >= 0 ? index : 0;
            _loadPage = PalettePager.PageOf(_selectedLevel, ListedLevels);
        }
        else
        {
            _selectedLevel = Mathf.Clamp(_selectedLevel, 0, _levelFiles.Count - 1);
            _loadPage = PalettePager.Clamp(_loadPage, _levelFiles.Count, ListedLevels);
        }
    }

    private static int LoadPageCount => PalettePager.PageCount(_levelFiles.Count, ListedLevels);

    private static void StepLoadPage(float notches) => _loadPage = PalettePager.Step(_loadPage, notches, LoadPageCount);

    private static void RenderLoadList()
    {
        _loadPage = PalettePager.Clamp(_loadPage, _levelFiles.Count, ListedLevels);
        _loadPageLabel.text = $"{_loadPage + 1}/{LoadPageCount}";
        var mouse = (Vector2)EditorInput.MousePosition;
        for (var i = 0; i < _loadRows.Count; i++)
        {
            var row = _loadRows[i];
            var index = PalettePager.IndexAt(_loadPage, i, ListedLevels, _levelFiles.Count);
            row.Text.text = index is { } n ? _levelFiles[n] : i == 0 && _levelFiles.Count == 0 ? "(no .mblevel.json files)" : "";
            var selected = index == _selectedLevel;
            row.Text.color = selected ? HighlightColor : Color.white;
            var hovered = index.HasValue && RectTransformUtility.RectangleContainsScreenPoint(row.Rect, mouse, null);
            row.Fill.color = selected ? SelectedFill : hovered ? HoverFill : Color.clear;
        }
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

    private static void Fail(string message)
    {
        _validateSummary = message;
        _toasts.Push(message, true, Time.unscaledTime);
    }

    public static void Warn(string message) => _toasts.Push(message, true, Time.unscaledTime);

    private static void ShowTransientStatus(string text) => _toasts.Push(text, false, Time.unscaledTime);

    // Specific widgets come before the panels that contain them, so UiWidgets.At reports the innermost one.
    public static IEnumerable<UiWidget> ListWidgets()
    {
        var widgets = new List<UiWidget?>();
        foreach (var region in _clickRegions)
        {
            var enabled = region.Enabled == null || region.Enabled();
            if (enabled || !region.OmitWhenDisabled)
            {
                widgets.Add(ToWidget(region.Name, region.Rect, enabled));
            }
        }

        widgets.Add(ToWidget("SaveInput", _saveInputRect));
        for (var i = 0; i < _loadRows.Count; i++)
        {
            widgets.Add(ToWidget($"LoadRow{i}", _loadRows[i].Rect));
        }

        widgets.Add(ToWidget("Toolbar", _toolbarRect));
        widgets.Add(ToWidget("LoadPanel", _loadRect));
        return widgets.Where(widget => widget.HasValue).Select(widget => widget.Value);
    }

    private static bool PointerOverOverlay() =>
        (_toolbarRect != null && RectTransformUtility.RectangleContainsScreenPoint(_toolbarRect, EditorInput.MousePosition, null))
        || PointerOverToast()
        || (_loadRect != null && RectTransformUtility.RectangleContainsScreenPoint(_loadRect, EditorInput.MousePosition, null));

    private static bool PointerOverToast()
    {
        for (var i = 0; i < _toasts.Items.Count && i < _toastSlots.Count; i++)
        {
            if (RectTransformUtility.RectangleContainsScreenPoint(_toastSlots[i].Rect, EditorInput.MousePosition, null))
            {
                return true;
            }
        }

        return false;
    }

    private static void HandleOverlayInput()
    {
        if (_saveInputFocused)
        {
            HandleSaveTyping();
        }

        ScrollLoadList();

        if (!EditorInput.GetMouseButtonDown(0))
        {
            return;
        }

        var mouse = (Vector2)EditorInput.MousePosition;
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

        var wasSaveFocused = _saveInputFocused;
        _saveInputFocused = _saveInputRect != null && RectTransformUtility.RectangleContainsScreenPoint(_saveInputRect, mouse, null);
        if (_saveInputFocused && !wasSaveFocused)
        {
            _saveField.Navigate(new CaretKeys(End: true));
        }
    }

    private static void ScrollLoadList()
    {
        if (_loadRect == null || !RectTransformUtility.RectangleContainsScreenPoint(_loadRect, EditorInput.MousePosition, null))
        {
            return;
        }

        StepLoadPage(-EditorInput.MouseScrollDelta.y);
    }

    private static void HandleSaveTyping()
    {
        if (EditorInput.GetKey(KeyCode.LeftControl) || EditorInput.GetKey(KeyCode.RightControl))
        {
            return;
        }

        if (_saveField.Type(EditorInput.InputString))
        {
            Save();
        }

        _saveField.Navigate(_saveCaretInput.Read());

        if (EditorInput.GetKeyDown(KeyCode.Escape))
        {
            _saveInputFocused = false;
        }
    }

    private static bool TrySelectLoadRow(Vector2 mouse)
    {
        for (var i = 0; i < _loadRows.Count; i++)
        {
            if (!RectTransformUtility.RectangleContainsScreenPoint(_loadRows[i].Rect, mouse, null))
            {
                continue;
            }

            if (PalettePager.IndexAt(_loadPage, i, ListedLevels, _levelFiles.Count) is not { } index)
            {
                return false;
            }

            _selectedLevel = index;
            _saveField.Set(EditorFileNaming.StemForForm(_levelFiles[index], SaveNameMaxChars));
            return true;
        }

        return false;
    }

    private static Image NewButton(RectTransform parent, string name, string text, float x, float width, Action onClick, Func<bool> enabled = null, float y = 0f, float height = OverlayRowHeight)
    {
        var parts = Bordered(name, parent, SlotBorder, SlotFill);
        var rect = parts.Outer;
        PlaceTopLeft(rect, x, y, width, height);
        _clickRegions.Add(new ClickRegion { Name = name, Rect = rect, OnClick = onClick, Enabled = enabled });

        var labelRect = EditorUi.NewRect("Text", rect);
        labelRect.anchorMin = Vector2.zero;
        labelRect.anchorMax = Vector2.one;
        labelRect.offsetMin = Vector2.zero;
        labelRect.offsetMax = Vector2.zero;
        var label = EditorUi.NewLabel(labelRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.Center, OverlayFontSize);
        label.text = text;
        return parts.Fill;
    }

    private static void NewInput(RectTransform parent, string name, float x, float width, string placeholder)
    {
        var parts = Bordered(name, parent, SlotBorder, SearchFill);
        var rect = parts.Outer;
        _saveInputRect = rect;
        _saveInputFill = parts.Fill;
        PlaceTopLeft(rect, x, 0f, width, OverlayRowHeight);

        var textRect = EditorUi.NewRect("Text", rect);
        textRect.anchorMin = Vector2.zero;
        textRect.anchorMax = Vector2.one;
        textRect.offsetMin = new Vector2(8f, 0f);
        textRect.offsetMax = new Vector2(-8f, 0f);
        _saveInputText = EditorUi.NewLabel(textRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.MidlineLeft, OverlayFontSize);
        EditorUi.FixInputBaseline(_saveInputText);
        _saveView = new TextFieldView(_saveInputText);
        _saveInputText.text = placeholder;

        var phRect = EditorUi.NewRect("Placeholder", rect);
        phRect.anchorMin = Vector2.zero;
        phRect.anchorMax = Vector2.one;
        phRect.offsetMin = new Vector2(8f, 0f);
        phRect.offsetMax = new Vector2(-8f, 0f);
        _savePlaceholderText = EditorUi.NewLabel(phRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.MidlineLeft, OverlayFontSize);
        EditorUi.FixInputBaseline(_savePlaceholderText);
        _savePlaceholderText.text = placeholder;
        _savePlaceholderText.color = new Color(0.6f, 0.6f, 0.6f, 1f);
        _saveField.Clear();
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
