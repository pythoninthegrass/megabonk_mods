using System.Collections.Generic;
using Il2Cpp;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// See "Object tools" in docs/development.md.
public static class EditorObjectTools
{
    private const float RayLength = 5000f;
    private const float OutlineLift = 0.5f;
    private const float OutlineWidth = 0.8f;
    private const string CloneSuffix = "(Clone)";

    private static readonly Color SelectionColor = new(0.3f, 0.9f, 1f, 1f);

    private static MelonLogger.Instance _logger;
    private static LineRenderer _selectionOutline;
    private static ObjectTarget? _selected;
    private static ObjectTarget? _hovered;

    public static void OnEditorEntered(MelonLogger.Instance logger)
    {
        _logger = logger;
        _selected = null;
        _hovered = null;
        _selectionOutline = BuildOutline();
    }

    public static void OnEditorExited()
    {
        if (_selectionOutline != null)
        {
            Object.Destroy(_selectionOutline.gameObject);
        }

        _selectionOutline = null;
        _selected = null;
        _hovered = null;
    }

    public static void OnToolChanged(EditorTool tool)
    {
        _selected = null;
        _hovered = null;
    }

    // Handles clicks and keys for the Place and Select tools; returns the tool to switch to after a pick-block click.
    public static EditorTool? Tick(EditorTool tool, (int X, int Z, TileState State)? target)
    {
        EditorTool? switchTo = null;
        var pointerFree = !EditorPalette.PointerOverPanel;

        _hovered = tool == EditorTool.Select && pointerFree ? PickAt()?.Target : null;

        if (pointerFree && Input.GetMouseButtonDown(2))
        {
            switchTo = PickBlock();
        }

        if (pointerFree && Input.GetMouseButtonDown(0))
        {
            if (tool == EditorTool.Place)
            {
                Place(target);
            }
            else if (tool == EditorTool.Select)
            {
                Select(target);
            }
        }

        if (tool == EditorTool.Select && _selected != null)
        {
            HandleSelectionKeys();
        }

        RefreshOutline(tool);
        return switchTo;
    }

    public static string Detail(EditorTool tool, (int X, int Z, TileState State)? target)
    {
        var cell = target is { } t ? (t.X, t.Z) : ((int X, int Z)?)null;
        if (tool == EditorTool.Place)
        {
            return EditorTools.PlaceDetail(cell, SelectedPaletteName());
        }

        return EditorTools.SelectDetail(NameOf(_selected), NameOf(_hovered), cell);
    }

    private static string SelectedPaletteName()
    {
        var current = EditorPalette.Selection.Current;
        foreach (var entry in EditorPalette.Selection.Entries)
        {
            if (current.HasValue && entry.Id.Equals(current.Value))
            {
                return entry.DisplayName;
            }
        }

        return null;
    }

    private static string NameOf(ObjectTarget? target)
    {
        var go = target is { } t ? LiveEditPatch.ObjectFor(t) : null;
        if (go == null)
        {
            return null;
        }

        var name = go.name;
        return name.EndsWith(CloneSuffix, System.StringComparison.Ordinal) ? name.Substring(0, name.Length - CloneSuffix.Length) : name;
    }

    private static void Place((int X, int Z, TileState State)? target)
    {
        if (target is not { } cell || LiveEditPatch.Grid is not { } grid)
        {
            return;
        }

        if (EditorPalette.Selection.Current is not { } id)
        {
            _logger.Msg("EditorObjectTools: place ignored, no palette item selected");
            return;
        }

        var prefab = LiveEditPatch.PrefabFor(id);
        var camera = PlayerCamera.Instance?.camera;
        if (prefab == null || camera == null)
        {
            _logger.Warning($"EditorObjectTools: place ignored, no prefab or camera for '{id.Serialize()}'");
            return;
        }

        var position = ObjectTools.SnapPosition(cell.X, cell.Z, cell.State, grid.Width, grid.Depth, grid.Spacing, grid.TileHeight);
        var op = ObjectTools.Place(id, position, ToData(prefab.transform.eulerAngles), ToData(prefab.transform.localScale), camera.transform.eulerAngles.y);
        Apply(op, $"place '{id.Serialize()}' at ({cell.X},{cell.Z})");
    }

    private static void Select((int X, int Z, TileState State)? cell)
    {
        var picked = PickAt();
        if (picked is { } hit)
        {
            _selected = _selected is { } current && current.Equals(hit.Target) ? null : hit.Target;
            _logger.Msg($"EditorObjectTools: {(_selected == null ? "deselected" : "selected")} {hit.Target.Serialize()} '{hit.Object.name}' via {hit.Path}");
            return;
        }

        if (_selected is { } selected && cell is { } target && LiveEditPatch.Grid is { } grid && LiveEditPatch.ObjectFor(selected) is { } go)
        {
            var position = ObjectTools.SnapPosition(target.X, target.Z, target.State, grid.Width, grid.Depth, grid.Spacing, grid.TileHeight);
            Apply(ObjectTools.Move(selected, CurrentTransform(go), position), $"move {selected.Serialize()} to ({target.X},{target.Z})");
        }
    }

    private static void HandleSelectionKeys()
    {
        if (_selected is not { } selected || LiveEditPatch.ObjectFor(selected) is not { } go)
        {
            _selected = null;
            return;
        }

        if (Input.GetKeyDown(KeyCode.R))
        {
            var shift = Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift);
            Apply(ObjectTools.Rotate(selected, CurrentTransform(go), !shift), $"rotate {selected.Serialize()} {(shift ? "counter-clockwise" : "clockwise")}");
        }
        else if (Input.GetKeyDown(KeyCode.Delete) || Input.GetKeyDown(KeyCode.Backspace))
        {
            Apply(ObjectTools.Remove(selected), $"remove {selected.Serialize()}");
            _selected = null;
        }
    }

    private static void Apply(EditOp op, string what)
    {
        var applied = LiveEditPatch.ApplyLive(op);
        _logger.Msg($"EditorObjectTools: {what} -> {op.OpType}{(applied ? "" : " not applied")}");
    }

    private static EditorTool? PickBlock()
    {
        if (PickAt() is not { } hit)
        {
            return null;
        }

        var entries = EditorPalette.Selection.Entries;
        var entry = LiveEditPatch.CatalogIdOf(hit.Target) is { } placedId
            ? PalettePick.FindByCatalogId(entries, placedId)
            : PalettePick.PrefabNameOf(hit.Target.GenId) is { } name
                ? PalettePick.FindByPrefabName(entries, name, LiveEditPatch.CurrentStageIndex())
                : null;

        if (entry is not { } found)
        {
            _logger.Msg($"EditorObjectTools: pick block found no palette entry for {hit.Target.Serialize()} '{hit.Object.name}'");
            return null;
        }

        EditorPalette.Selection.Select(found.Id);
        _logger.Msg($"EditorObjectTools: pick block {hit.Target.Serialize()} -> '{found.Id.Serialize()}' ({found.DisplayName})");
        return EditorTool.Place;
    }

    // A physics hit on an object wins; otherwise the object nearest the cursor's ground point within half a tile.
    private static (ObjectTarget Target, GameObject Object, string Path)? PickAt()
    {
        var camera = PlayerCamera.Instance?.camera;
        if (camera == null || LiveEditPatch.Grid is not { } grid)
        {
            return null;
        }

        var ray = camera.ScreenPointToRay(Input.mousePosition);
        if (Physics.Raycast(ray, out var physicsHit, RayLength)
            && LiveEditPatch.TargetOf(physicsHit.transform) is { } target
            && LiveEditPatch.ObjectFor(target) is { } hitObject)
        {
            return (target, hitObject, "raycast");
        }

        var ground = LiveEditPatch.GroundCollider();
        if (ground == null || !ground.Raycast(ray, out var groundHit, RayLength))
        {
            return null;
        }

        var candidates = LiveEditPatch.PickableObjects();
        var positions = new List<(float X, float Z)>(candidates.Count);
        foreach (var candidate in candidates)
        {
            var p = candidate.Object.transform.position;
            positions.Add((p.x, p.z));
        }

        var nearest = ObjectPicker.NearestIndex(positions, groundHit.point.x, groundHit.point.z, grid.Spacing / 2f);
        return nearest < 0 ? null : (candidates[nearest].Target, candidates[nearest].Object, "nearest");
    }

    private static TransformData CurrentTransform(GameObject go) =>
        new(ToData(go.transform.position), ToData(go.transform.eulerAngles), ToData(go.transform.localScale));

    private static Vector3Data ToData(Vector3 v) => new(v.x, v.y, v.z);

    private static void RefreshOutline(EditorTool tool)
    {
        if (_selectionOutline == null)
        {
            return;
        }

        var go = tool == EditorTool.Select && _selected is { } selected ? LiveEditPatch.ObjectFor(selected) : null;
        var renderers = go != null ? go.GetComponentsInChildren<Renderer>() : null;
        if (renderers == null || renderers.Length == 0)
        {
            _selectionOutline.enabled = false;
            return;
        }

        var bounds = renderers[0].bounds;
        for (var i = 1; i < renderers.Length; i++)
        {
            bounds.Encapsulate(renderers[i].bounds);
        }

        var y = bounds.min.y + OutlineLift;
        _selectionOutline.SetPosition(0, new Vector3(bounds.min.x, y, bounds.min.z));
        _selectionOutline.SetPosition(1, new Vector3(bounds.max.x, y, bounds.min.z));
        _selectionOutline.SetPosition(2, new Vector3(bounds.max.x, y, bounds.max.z));
        _selectionOutline.SetPosition(3, new Vector3(bounds.min.x, y, bounds.max.z));
        _selectionOutline.enabled = true;
    }

    private static LineRenderer BuildOutline()
    {
        var go = new GameObject("MegabonkLevelsObjectSelection");
        Object.DontDestroyOnLoad(go);
        var line = go.AddComponent<LineRenderer>();
        line.loop = true;
        line.useWorldSpace = true;
        line.positionCount = 4;
        line.startWidth = OutlineWidth;
        line.endWidth = OutlineWidth;
        line.startColor = SelectionColor;
        line.endColor = SelectionColor;
        line.enabled = false;

        var shader = Shader.Find("Sprites/Default") ?? Shader.Find("Hidden/Internal-Colored");
        if (shader != null)
        {
            line.material = new Material(shader) { color = SelectionColor };
        }

        return line;
    }
}
