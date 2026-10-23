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
    private const float NearestPickTiles = 0.125f;
    private const int OnTopRenderQueue = 4000;
    private const float OutlineWidth = 0.8f;
    private const string CloneSuffix = "(Clone)";

    private const float GridWidth = 0.25f;
    private const float MarkerWidth = 0.6f;
    private const float MarkerRadius = 1.5f;
    private const int RingSegments = 48;

    private static readonly Color SelectionColor = new(1f, 0.15f, 0.15f, 1f);
    private static readonly Color GridColor = new(1f, 1f, 1f, 0.6f);
    private static readonly Color MarkerColor = new(1f, 0.4f, 0.2f, 1f);

    private static MelonLogger.Instance _logger;
    private static LineRenderer _selectionOutline;
    private static LineRenderer _gridLines;
    private static LineRenderer _placeMarker;
    private static ObjectTarget? _selected;
    private static ObjectTarget? _hovered;
    private static ObjectTarget? _dragging;
    private static TransformData _dragOrigin;
    private static float _dragLift;
    private static bool _dragActive;
    private static float _dragPressedAt;
    private static (float X, float Z) _dragGrab;

    public static ObjectTarget? Selected => _selected;

    public static void OnEditorEntered(MelonLogger.Instance logger)
    {
        _logger = logger;
        _selected = null;
        _hovered = null;
        _selectionOutline = BuildOutline(SelectionColor, OutlineWidth, RingSegments, loop: true, onTop: true);
        _gridLines = BuildOutline(GridColor, GridWidth, 0, loop: false);
        _placeMarker = BuildOutline(MarkerColor, MarkerWidth, RingSegments, loop: true);
    }

    public static void OnEditorExited()
    {
        CancelDrag();
        DestroyLine(ref _selectionOutline);
        DestroyLine(ref _gridLines);
        DestroyLine(ref _placeMarker);
        _selected = null;
        _hovered = null;
    }

    public static void OnToolChanged(EditorTool tool)
    {
        CancelDrag();
        _selected = null;
        _hovered = null;
    }

    // Handles clicks and keys for the Place and Select tools; returns the tool to switch to after a pick-block click.
    public static EditorTool? Tick(EditorTool tool, (int X, int Z, TileState State)? target, Vector3 point)
    {
        EditorTool? switchTo = null;
        var pointerFree = !EditorPalette.PointerOverPanel;
        pointerFree = pointerFree && !EditorTileTools.PointerOverEditorOverlay;

        _hovered = tool == EditorTool.Select && pointerFree ? PickAt()?.Target : null;

        if (pointerFree && EditorInput.GetMouseButtonDown(2))
        {
            switchTo = PickBlock();
        }

        if (pointerFree && EditorInput.GetMouseButtonDown(0))
        {
            if (tool == EditorTool.Place)
            {
                Place(target, point);
            }
            else if (tool == EditorTool.Select)
            {
                BeginDrag(target, point);
            }
        }

        if (_dragging != null)
        {
            if (EditorInput.GetMouseButtonUp(0))
            {
                EndDrag(target, point, pointerFree);
            }
            else if (EditorInput.GetMouseButton(0))
            {
                _dragActive = _dragActive || ObjectTools.DragStarted(Time.unscaledTime - _dragPressedAt);
                if (_dragActive)
                {
                    UpdateDrag(target, point);
                }
            }
        }

        if (tool == EditorTool.Select && _selected != null)
        {
            HandleSelectionKeys();
        }

        RefreshOutline(tool);
        RefreshGrid(tool, target, point);
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
        return go == null ? null : PrefabNameOf(go);
    }

    private static string PrefabNameOf(GameObject go)
    {
        var name = go.name;
        return name.EndsWith(CloneSuffix, System.StringComparison.Ordinal) ? name.Substring(0, name.Length - CloneSuffix.Length) : name;
    }

    private static bool IsStacked(string prefabName, Vector3Data position, GameObject ignore)
    {
        var others = new List<(string PrefabName, Vector3Data Position)>();
        foreach (var candidate in LiveEditPatch.PickableObjects())
        {
            if (candidate.Object != ignore)
            {
                others.Add((PrefabNameOf(candidate.Object), ToData(candidate.Object.transform.position)));
            }
        }

        return ObjectTools.IsStacked(prefabName, position, others);
    }

    private static void Place((int X, int Z, TileState State)? target, Vector3 point)
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

        var position = ObjectTools.PositionAt(cell.X, cell.Z, cell.State, grid.Width, grid.Depth, grid.Spacing, grid.TileHeight, point.x, point.z);
        if (IsStacked(prefab.name, position, null))
        {
            _logger.Msg($"EditorObjectTools: place ignored, '{prefab.name}' already stands at ({position.X:0.##}, {position.Y:0.##}, {position.Z:0.##})");
            return;
        }

        var op = ObjectTools.Place(id, position, ToData(prefab.transform.eulerAngles), ToData(prefab.transform.localScale), camera.transform.eulerAngles.y);
        Apply(op, $"place '{id.Serialize()}' at ({position.X:0.##}, {position.Z:0.##}) in cell ({cell.X},{cell.Z})");
    }

    // Pressing on an object selects it; holding picks it up. Pressing on nothing deselects.
    private static void BeginDrag((int X, int Z, TileState State)? target, Vector3 point)
    {
        if (PickAt() is not { } hit)
        {
            _selected = null;
            _logger.Msg("EditorObjectTools: deselected, nothing under the cursor");
            return;
        }

        _selected = hit.Target;
        _dragging = hit.Target;
        _dragOrigin = CurrentTransform(hit.Object);
        _dragActive = false;
        _dragPressedAt = Time.unscaledTime;
        _dragGrab = target != null ? (_dragOrigin.Position.X - point.x, _dragOrigin.Position.Z - point.z) : (0f, 0f);
        _dragLift = SurfaceYAt(_dragOrigin.Position) is { } surface ? _dragOrigin.Position.Y - surface : 0f;
        _logger.Msg($"EditorObjectTools: selected {hit.Target.Serialize()} '{hit.Object.name}' via {hit.Path}");
    }

    // The object follows the cursor as a preview; the edit is only made on release.
    private static void UpdateDrag((int X, int Z, TileState State)? target, Vector3 point)
    {
        if (_dragging is not { } dragged || LiveEditPatch.ObjectFor(dragged) is not { } go || CursorPosition(target, point, _dragGrab) is not { } position)
        {
            return;
        }

        go.transform.position = new Vector3(position.X, position.Y + _dragLift, position.Z);
    }

    private static void EndDrag((int X, int Z, TileState State)? target, Vector3 point, bool pointerFree)
    {
        var dragged = _dragging.Value;
        _dragging = null;
        if (!_dragActive)
        {
            return;
        }

        _dragActive = false;
        if (LiveEditPatch.ObjectFor(dragged) is not { } go)
        {
            return;
        }

        var final = ToData(go.transform.position);
        go.transform.position = new Vector3(_dragOrigin.Position.X, _dragOrigin.Position.Y, _dragOrigin.Position.Z);
        if (!pointerFree || target == null || !ObjectTools.HasMoved(_dragOrigin.Position, final))
        {
            return;
        }

        if (IsStacked(PrefabNameOf(go), final, go))
        {
            _logger.Msg($"EditorObjectTools: move ignored, '{PrefabNameOf(go)}' already stands at ({final.X:0.##}, {final.Y:0.##}, {final.Z:0.##})");
            return;
        }

        Apply(ObjectTools.Move(dragged, _dragOrigin, final), $"move {dragged.Serialize()} to ({final.X:0.##}, {final.Z:0.##})");
    }

    private static void CancelDrag()
    {
        if (_dragging is { } dragged && LiveEditPatch.ObjectFor(dragged) is { } go)
        {
            go.transform.position = new Vector3(_dragOrigin.Position.X, _dragOrigin.Position.Y, _dragOrigin.Position.Z);
        }

        _dragging = null;
        _dragActive = false;
    }

    // The cursor point plus the offset at which the object was grabbed, so it does not jump to the cursor.
    private static Vector3Data? CursorPosition((int X, int Z, TileState State)? target, Vector3 point, (float X, float Z) grab) =>
        target is { } cell && LiveEditPatch.Grid is { } grid
            ? ObjectTools.PositionAt(cell.X, cell.Z, cell.State, grid.Width, grid.Depth, grid.Spacing, grid.TileHeight, point.x + grab.X, point.z + grab.Z)
            : null;

    private static float? SurfaceYAt(Vector3Data world)
    {
        if (LiveEditPatch.Grid is not { } grid)
        {
            return null;
        }

        var cell = PositionReadout.CellOf(world.X, world.Z, grid.Width, grid.Depth, grid.Spacing);
        if (!cell.InGrid || LiveEditPatch.TileAt(cell.X, cell.Z) is not { } state)
        {
            return null;
        }

        var (centreX, centreZ) = PositionReadout.CellCentre(cell.X, cell.Z, grid.Width, grid.Depth, grid.Spacing);
        return ObjectTools.SurfaceY(state, world.X - centreX, world.Z - centreZ, grid.Spacing, grid.TileHeight);
    }

    private static void HandleSelectionKeys()
    {
        if (_selected is not { } selected || LiveEditPatch.ObjectFor(selected) is not { } go)
        {
            _selected = null;
            return;
        }

        if (EditorInput.GetKeyDown(KeyCode.R))
        {
            var shift = EditorInput.GetKey(KeyCode.LeftShift) || EditorInput.GetKey(KeyCode.RightShift);
            Apply(ObjectTools.Rotate(selected, CurrentTransform(go), !shift), $"rotate {selected.Serialize()} {(shift ? "counter-clockwise" : "clockwise")}");
        }
        else if (EditorInput.GetKeyDown(KeyCode.Delete) || EditorInput.GetKeyDown(KeyCode.Backspace))
        {
            Apply(ObjectTools.Remove(selected), $"remove {selected.Serialize()}");
            _selected = null;
        }
    }

    private static void Apply(EditOp op, string what)
    {
        var applied = EditorTileTools.ApplyFromObjectTools(op, what);
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

    // The nearest object the ray selects; see ObjectPicker.NearestHit for which colliders count.
    private static (ObjectTarget Target, GameObject Object)? RaycastObject(Ray ray)
    {
        var raw = Physics.RaycastAll(ray, RayLength, Physics.DefaultRaycastLayers, QueryTriggerInteraction.Collide);
        var hits = new List<RayHit>(raw.Length);
        var objects = new List<(ObjectTarget Target, GameObject Object)?>(raw.Length);
        for (var i = 0; i < raw.Length; i++)
        {
            var hit = raw[i];
            var target = LiveEditPatch.TargetOf(hit.transform);
            var go = target is { } t ? LiveEditPatch.ObjectFor(t) : null;
            objects.Add(target is { } found && go != null ? (found, go) : null);
            hits.Add(new RayHit(hit.distance, hit.collider.isTrigger, go != null, go != null && CrossesModel(ray, go)));
        }

        var index = ObjectPicker.NearestHit(hits);
        return index < 0 ? null : objects[index];
    }

    private static bool CrossesModel(Ray ray, GameObject go)
    {
        foreach (var renderer in LiveEditPatch.ModelRenderers(go))
        {
            if (renderer.bounds.IntersectRay(ray))
            {
                return true;
            }
        }

        return false;
    }

    // A physics hit on an object wins; otherwise the object nearest the cursor's ground point within an eighth of a tile.
    private static (ObjectTarget Target, GameObject Object, string Path)? PickAt()
    {
        var camera = PlayerCamera.Instance?.camera;
        if (camera == null || LiveEditPatch.Grid is not { } grid)
        {
            return null;
        }

        var ray = camera.ScreenPointToRay(EditorInput.MousePosition);
        if (RaycastObject(ray) is { } picked)
        {
            return (picked.Target, picked.Object, "raycast");
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

        var nearest = ObjectPicker.NearestIndex(positions, groundHit.point.x, groundHit.point.z, grid.Spacing * NearestPickTiles);
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
        Bounds? bounds = null;
        foreach (var renderer in go != null ? LiveEditPatch.ModelRenderers(go) : new Renderer[0])
        {
            if (bounds is { } combined)
            {
                combined.Encapsulate(renderer.bounds);
                bounds = combined;
            }
            else
            {
                bounds = renderer.bounds;
            }
        }

        if (bounds is not { } box)
        {
            _selectionOutline.enabled = false;
            return;
        }

        var origin = go.transform.position;
        var baseY = ObjectTools.RingBaseY(box.min.y, SurfaceYAt(ToData(origin)));
        SetRing(_selectionOutline, origin.x, baseY + OutlineLift, origin.z, ObjectTools.RingRadius(Mathf.Max(box.extents.x, box.extents.z)));
        _selectionOutline.enabled = true;
    }

    private static void DestroyLine(ref LineRenderer line)
    {
        if (line != null)
        {
            Object.Destroy(line.gameObject);
        }

        line = null;
    }

    // The quarter-tile grid of the targeted cell and a marker at the placement point, while Place or a selected Select can use them.
    private static void RefreshGrid(EditorTool tool, (int X, int Z, TileState State)? target, Vector3 point)
    {
        var active = tool == EditorTool.Place || (tool == EditorTool.Select && _selected != null);
        if (_gridLines == null || _placeMarker == null || !active || target is not { } cell || LiveEditPatch.Grid is not { } grid)
        {
            SetEnabled(_gridLines, false);
            SetEnabled(_placeMarker, false);
            return;
        }

        var lines = ObjectTools.GridLines(cell.X, cell.Z, cell.State, grid.Width, grid.Depth, grid.Spacing, grid.TileHeight, OutlineLift);
        _gridLines.positionCount = lines.Count;
        for (var i = 0; i < lines.Count; i++)
        {
            _gridLines.SetPosition(i, new Vector3(lines[i].X, lines[i].Y, lines[i].Z));
        }

        var marker = ObjectTools.PositionAt(cell.X, cell.Z, cell.State, grid.Width, grid.Depth, grid.Spacing, grid.TileHeight, point.x, point.z);
        SetRing(_placeMarker, marker.X, marker.Y + OutlineLift, marker.Z, MarkerRadius);
        _gridLines.enabled = true;
        _placeMarker.enabled = tool == EditorTool.Place;
    }

    private static void SetRing(LineRenderer line, float x, float y, float z, float radius)
    {
        var ring = ObjectTools.Ring(x, y, z, radius, RingSegments);
        for (var i = 0; i < ring.Count; i++)
        {
            line.SetPosition(i, new Vector3(ring[i].X, ring[i].Y, ring[i].Z));
        }
    }

    private static void SetEnabled(LineRenderer line, bool enabled)
    {
        if (line != null)
        {
            line.enabled = enabled;
        }
    }

    // onTop draws over the scene's depth, so a ring inside or behind a large mesh stays visible.
    private static LineRenderer BuildOutline(Color color, float width, int positionCount, bool loop, bool onTop = false)
    {
        var go = new GameObject("MegabonkLevelsObjectOverlay");
        Object.DontDestroyOnLoad(go);
        var line = go.AddComponent<LineRenderer>();
        line.loop = loop;
        line.useWorldSpace = true;
        line.positionCount = positionCount;
        line.startWidth = width;
        line.endWidth = width;
        line.startColor = color;
        line.endColor = color;
        line.enabled = false;

        var shader = Shader.Find("Sprites/Default") ?? Shader.Find("Hidden/Internal-Colored");
        if (shader != null)
        {
            line.material = new Material(shader) { color = color };
            if (onTop)
            {
                line.material.SetInt("unity_GUIZTestMode", (int)UnityEngine.Rendering.CompareFunction.Always);
                line.material.SetInt("_ZTest", (int)UnityEngine.Rendering.CompareFunction.Always);
                line.material.renderQueue = OnTopRenderQueue;
            }
        }

        return line;
    }
}
