using System;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace MegabonkLevels;

public static class EditorSettingsPanel
{
    private static GameObject _root;
    private static RectTransform _panel;
    private static RectTransform _input;
    private static TextMeshProUGUI _title;
    private static TextMeshProUGUI _message;
    private static TextFieldView _view;
    private static readonly TextFieldModel _field = new(2048);
    private static readonly EditorCaretInput _caret = new();
    private static readonly List<(string Name, RectTransform Rect, Action Click)> _buttons = new();
    private static readonly List<LineRenderer> _markers = new();
    private static LevelSettingsHistory _history;
    private static int _generation = -1;
    private static int _index;
    private static int _capturedFrame = -1;
    private static ModLogger _logger;

    public static bool Focused { get; private set; }
    public static bool CapturedThisFrame => _capturedFrame == Time.frameCount;
    public static bool Dirty => _history?.Dirty == true;
    public static bool PointerOver => _panel != null && RectTransformUtility.RectangleContainsScreenPoint(_panel, EditorInput.MousePosition, null);
    private static string Field => LevelSettings.Fields[_index];

    public static void Synchronize(IReadOnlyList<EditOp> edits, bool force = false)
    {
        if (!force && _generation == LiveEditPatch.RunGeneration && _history != null) return;
        if (LiveEditPatch.SnapshotLevelFile(edits) is not { } level) return;
        _history = new LevelSettingsHistory(level);
        _generation = LiveEditPatch.RunGeneration;
        ResetInput();
    }

    public static LevelFile ForSave(LevelFile level) => _history == null ? level : LevelSettings.CopyTo(_history.Current, level);
    public static void MarkSaved() => _history?.MarkSaved();

    public static void Enter(ModLogger logger)
    {
        _logger = logger;
        _root = EditorUi.NewCanvas("MegabonkLevelsSettings");
        _panel = EditorUi.Bordered("LevelSettings", _root.transform, EditorUi.PanelBorder, EditorUi.PanelFill).Outer;
        _panel.anchorMin = _panel.anchorMax = new Vector2(1, 1);
        _panel.pivot = new Vector2(1, 1);
        _panel.anchoredPosition = new Vector2(0, -160);
        _panel.sizeDelta = new Vector2(450, 238);
        _title = Label("SettingName", 8, 8, 434, 28);
        Button("PreviousSetting", "<", 8, 40, 32, () => Step(-1));
        Button("NextSetting", ">", 408, 40, 32, () => Step(1));
        var parts = EditorUi.Bordered("SettingInput", _panel, EditorUi.SlotBorder, EditorUi.SearchFill);
        _input = parts.Outer;
        EditorUi.PlaceTopLeft(_input, 46, 40, 356, 32);
        var text = EditorUi.NewRect("Text", _input);
        text.anchorMin = Vector2.zero;
        text.anchorMax = Vector2.one;
        text.offsetMin = new Vector2(8, 0);
        text.offsetMax = new Vector2(-8, 0);
        var label = EditorUi.NewLabel(text, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.MidlineLeft, 16);
        EditorUi.FixInputBaseline(label);
        _view = new TextFieldView(label);
        Button("ApplySetting", "Apply", 8, 80, 80, Apply);
        Button("CancelSetting", "Cancel", 94, 80, 80, ResetInput);
        Button("ClearSetting", "Clear", 180, 80, 80, () => { _field.Clear(); Focused = true; });
        Button("UndoSetting", "Undo", 266, 80, 80, () => History(false));
        Button("RedoSetting", "Redo", 352, 80, 88, () => History(true));
        Button("LocateMarker", "Locate marker", 8, 120, 208, Locate);
        Button("MoveMarkerToCamera", "Marker to camera", 222, 120, 218, MoveToCamera);
        _message = Label("SettingsHelp", 8, 158, 434, 74);
        _message.enableWordWrapping = true;
        _message.text = "Vectors [x,y,z]; flags true/false; null=default.\nPlayer Y=body; boss Y=floor.\nSettings Undo/Redo is separate from objects.";
        for (var i = 0; i < 2; i++) _markers.Add(NewMarker(i == 0 ? Color.cyan : Color.magenta));
        ResetInput();
    }

    public static void Exit()
    {
        if (_root != null) UnityEngine.Object.Destroy(_root);
        foreach (var marker in _markers)
        {
            if (marker != null)
            {
                if (marker.material != null) UnityEngine.Object.Destroy(marker.material);
                UnityEngine.Object.Destroy(marker.gameObject);
            }
        }
        _markers.Clear();
        _buttons.Clear();
        _panel = _input = null;
        _root = null;
        _title = _message = null;
        _view = null;
        Focused = false;
    }

    public static void Cancel()
    {
        _capturedFrame = Time.frameCount;
        ResetInput();
    }

    public static void Tick()
    {
        if (_panel == null || _history == null) return;
        if (Focused)
        {
            _capturedFrame = Time.frameCount;
            if (!EditorInput.GetKey(KeyCode.LeftControl) && !EditorInput.GetKey(KeyCode.RightControl))
            {
                if (_field.Type(EditorInput.InputString)) Apply();
                _field.Navigate(_caret.Read());
            }
        }
        if (EditorInput.GetMouseButtonDown(0))
        {
            var wasFocused = Focused;
            Focused = RectTransformUtility.RectangleContainsScreenPoint(_input, EditorInput.MousePosition, null);
            if (Focused)
            {
                EditorTileTools.BlurSaveInput();
                EditorPalette.BlurSearch();
                if (!wasFocused) _field.Navigate(new CaretKeys(End: true));
            }
            foreach (var button in _buttons)
            {
                if (RectTransformUtility.RectangleContainsScreenPoint(button.Rect, EditorInput.MousePosition, null))
                {
                    button.Click();
                    break;
                }
            }
        }
        _title.text = $"Level: {Field} ({_index + 1}/{LevelSettings.Fields.Length}){(Dirty ? " *" : "")}";
        _view.Render(_field, Focused, null);
        DrawMarker(0, _history.Current.PlayerStart);
        DrawMarker(1, _history.Current.BossSpawnPosition);
    }

    private static void Step(int direction)
    {
        _index = (_index + direction + LevelSettings.Fields.Length) % LevelSettings.Fields.Length;
        ResetInput();
    }

    private static void ResetInput()
    {
        Focused = false;
        if (_history != null) _field.Set(LevelSettings.Read(_history.Current, Field));
    }

    private static void Apply()
    {
        try
        {
            _history.Apply(Field, _field.Text, LiveEditPatch.CurrentState()?.Objects.Count > 0 || LiveEditPatch.SeedEdits.Count > 0);
            LiveEditPatch.ApplySettings(_history.Current, _logger);
            _message.text = Field.StartsWith("randomize", StringComparison.Ordinal) || Field.StartsWith("extra", StringComparison.Ordinal)
                ? $"Applied {Field}. Takes effect next run; save to keep it."
                : $"Applied {Field}. Save to keep it across relaunch.";
            _logger.Msg($"EditorSettings: applied {Field}={_field.Text}");
            ResetInput();
        }
        catch (ArgumentException ex)
        {
            _message.text = ex.Message;
            _logger.Warning($"EditorSettings: {ex.Message}");
        }
    }

    private static void History(bool redo)
    {
        if (_history == null || !(redo ? _history.Redo() : _history.Undo())) return;
        LiveEditPatch.ApplySettings(_history.Current, _logger);
        ResetInput();
        _message.text = redo ? "Settings redone." : "Settings undone.";
    }

    private static IReadOnlyList<float> SelectedMarker => Field == "playerStart" ? _history.Current.PlayerStart : Field == "bossSpawnPosition" ? _history.Current.BossSpawnPosition : null;

    private static void Locate()
    {
        if (SelectedMarker is not { Count: 3 } position) return;
        EditorMode.LocateMarker(position[0], position[1], position[2]);
    }

    private static void MoveToCamera()
    {
        if (Field != "playerStart" && Field != "bossSpawnPosition" || PlayerCamera.Instance?.camera is not { } camera) return;
        var p = camera.transform.position;
        _field.Set(System.Text.Json.JsonSerializer.Serialize(new[] { p.x, p.y, p.z }));
        Apply();
    }

    public static IEnumerable<UiWidget> Widgets() => _buttons.Select(button => EditorUi.ToWidget(button.Name, button.Rect))
        .Concat(new[] { EditorUi.ToWidget("SettingInput", _input), EditorUi.ToWidget("LevelSettings", _panel) })
        .Where(widget => widget.HasValue).Select(widget => widget.Value);

    private static TextMeshProUGUI Label(string name, float x, float y, float width, float height)
    {
        var rect = EditorUi.NewRect(name, _panel);
        EditorUi.PlaceTopLeft(rect, x, y, width, height);
        return EditorUi.NewLabel(rect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.TopLeft, 15);
    }

    private static void Button(string name, string text, float x, float y, float width, Action click)
    {
        var rect = EditorUi.Bordered(name, _panel, EditorUi.SlotBorder, EditorUi.SlotFill).Outer;
        EditorUi.PlaceTopLeft(rect, x, y, width, 30);
        var labelRect = EditorUi.NewRect("Text", rect);
        labelRect.anchorMin = Vector2.zero;
        labelRect.anchorMax = Vector2.one;
        labelRect.offsetMin = labelRect.offsetMax = Vector2.zero;
        EditorUi.NewLabel(labelRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.Center, 14).text = text;
        _buttons.Add((name, rect, click));
    }

    private static LineRenderer NewMarker(Color color)
    {
        var go = new GameObject("MegabonkLevelsStartMarker");
        UnityEngine.Object.DontDestroyOnLoad(go);
        var line = go.AddComponent<LineRenderer>();
        line.useWorldSpace = true;
        line.positionCount = 6;
        line.startWidth = line.endWidth = 0.2f;
        line.startColor = line.endColor = color;
        line.material = new Material(Shader.Find("Sprites/Default")) { color = color };
        return line;
    }

    private static void DrawMarker(int index, IReadOnlyList<float> position)
    {
        var line = _markers[index];
        line.enabled = position is { Count: 3 };
        if (!line.enabled) return;
        var p = new Vector3(position[0], position[1], position[2]);
        var offsets = new[] { Vector3.left * 2, Vector3.right * 2, Vector3.zero, Vector3.up * 4, Vector3.zero, Vector3.forward * 2 };
        for (var i = 0; i < offsets.Length; i++) line.SetPosition(i, p + offsets[i]);
    }
}
