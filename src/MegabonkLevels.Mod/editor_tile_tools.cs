using Il2Cpp;
using Il2CppTMPro;
using MelonLoader;
using UnityEngine;
using UnityEngine.UI;

namespace MegabonkLevels;

// See "Tile tools" in docs/development.md.
public static class EditorTileTools
{
    private const float ToolbarWidth = 640f;
    private const float ToolbarHeight = 56f;
    private const float FontSize = 18f;
    private const float RayLength = 5000f;
    private const float WallNudge = 0.01f;
    private const float OutlineLift = 0.5f;
    private const float OutlineWidth = 0.8f;

    private static readonly Color PanelColor = new(0f, 0f, 0f, 0.75f);
    private static readonly Color HighlightColor = new(1f, 0.85f, 0.3f, 1f);

    private static MelonLogger.Instance _logger;
    private static GameObject _root;
    private static TextMeshProUGUI _label;
    private static LineRenderer _outline;
    private static EditorTool _tool = EditorTool.Raise;
    private static (int X, int Z, TileState State)? _target;

    public static void OnEditorEntered(MelonLogger.Instance logger)
    {
        _logger = logger;
        EditorObjectTools.OnEditorEntered(logger);
        BuildToolbar();
        BuildOutline();
        _target = null;
        Refresh();
    }

    public static void OnEditorExited()
    {
        EditorObjectTools.OnEditorExited();
        if (_root != null)
        {
            Object.Destroy(_root);
        }

        if (_outline != null)
        {
            Object.Destroy(_outline.gameObject);
        }

        _root = null;
        _label = null;
        _outline = null;
        _target = null;
    }

    public static void Tick()
    {
        for (var digit = 1; digit <= 9; digit++)
        {
            if (Input.GetKeyDown(KeyCode.Alpha0 + digit) && EditorTools.FromHotkey(digit) is { } tool)
            {
                SetTool(tool);
            }
        }

        _target = EditorPalette.PointerOverPanel ? null : FindTarget();
        if (EditorTools.IsObjectTool(_tool))
        {
            if (EditorObjectTools.Tick(_tool, _target) is { } requested)
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

        var applied = LiveEditPatch.ApplyLive(op);
        _logger.Msg($"EditorTileTools: {_tool} ({x},{z}) -> {op.OpType}{(applied ? "" : " not applied")}");
    }

    private static void Refresh()
    {
        if (_label != null)
        {
            var detail = EditorTools.IsObjectTool(_tool) ? EditorObjectTools.Detail(_tool, _target) : EditorTools.TileDetail(_target);
            _label.text = EditorTools.ToolbarText(_tool, detail);
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
        panel.anchorMin = new Vector2(0.5f, 1f);
        panel.anchorMax = new Vector2(0.5f, 1f);
        panel.pivot = new Vector2(0.5f, 1f);
        panel.sizeDelta = new Vector2(ToolbarWidth, ToolbarHeight);
        panel.anchoredPosition = Vector2.zero;
        panel.gameObject.AddComponent<Image>().color = PanelColor;

        var labelRect = EditorUi.NewRect("Label", panel);
        EditorUi.Stretch(labelRect, ToolbarHeight);
        _label = EditorUi.NewLabel(labelRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.Center, FontSize);
    }

    private static void BuildOutline()
    {
        var go = new GameObject("MegabonkLevelsTileHighlight");
        Object.DontDestroyOnLoad(go);
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
}
