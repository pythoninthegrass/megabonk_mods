using System.Collections.Generic;
using Il2Cpp;
using Il2CppAssets.Scripts.Managers;
using Il2CppTMPro;
using MelonLoader;
using UnityEngine;
using UnityEngine.UI;

namespace MegabonkLevels;

// See "Catalog palette" in docs/development.md.
public static class EditorPalette
{
    private const float PanelWidth = 340f;
    private const float TitleHeight = 48f;
    private const float RowHeight = 26f;
    private const float HeaderHeight = 22f;
    private const float FontSize = 16f;
    private const float ScrollPixelsPerNotch = 40f;

    private static readonly Color PanelColor = new(0f, 0f, 0f, 0.75f);
    private static readonly Color RowColor = new(1f, 1f, 1f, 0.06f);
    private static readonly Color SelectedColor = new(0.2f, 0.5f, 0.9f, 0.9f);

    private static readonly List<Row> _rows = new();
    private static MelonLogger.Instance _logger;
    private static GameObject _root;
    private static RectTransform _panel;
    private static RectTransform _viewport;
    private static RectTransform _content;
    private static TextMeshProUGUI _title;
    private static string _mapLabel = "";
    private static float _contentHeight;
    private static CursorLockMode _cursorLockBefore;
    private static bool _cursorVisibleBefore;
    private static bool _open;

    public static PaletteSelection Selection { get; } = new();

    static EditorPalette()
    {
        Selection.Changed += _ => RefreshSelection();
    }

    public static bool PointerOverPanel { get; private set; }

    private sealed class Row
    {
        public RectTransform Rect;
        public Image Background;
        public CatalogId? Id;
    }

    public static void OnEditorEntered(MelonLogger.Instance logger)
    {
        _logger = logger;
        Rebuild();
        if (_root == null)
        {
            return;
        }

        _root.SetActive(true);
        _cursorLockBefore = Cursor.lockState;
        _cursorVisibleBefore = Cursor.visible;
        Cursor.lockState = CursorLockMode.None;
        Cursor.visible = true;
        _open = true;
    }

    public static void OnEditorExited()
    {
        if (!_open)
        {
            return;
        }

        _open = false;
        PointerOverPanel = false;
        if (_root != null)
        {
            _root.SetActive(false);
        }

        Cursor.lockState = _cursorLockBefore;
        Cursor.visible = _cursorVisibleBefore;
    }

    // Clicks and scrolling are handled here rather than through an EventSystem, so the game's Rewired input module is left alone.
    public static void Tick()
    {
        if (!_open || _root == null)
        {
            PointerOverPanel = false;
            return;
        }

        var mouse = (Vector2)EditorInput.MousePosition;
        PointerOverPanel = RectTransformUtility.RectangleContainsScreenPoint(_panel, mouse, null);
        if (!PointerOverPanel)
        {
            return;
        }

        Scroll(EditorInput.MouseScrollDelta.y);
        if (EditorInput.GetMouseButtonDown(0) && RectTransformUtility.RectangleContainsScreenPoint(_viewport, mouse, null))
        {
            ClickRowAt(mouse);
        }
    }

    private static void Rebuild()
    {
        if (_root != null)
        {
            Object.Destroy(_root);
        }

        _root = null;
        _rows.Clear();

        var mapData = MapController.currentMap;
        if (mapData == null)
        {
            _logger.Warning("EditorPalette: no current map, palette not built");
            Selection.Replace(new List<PaletteEntry>());
            return;
        }

        var interactables = Object.FindObjectOfType<MapGenerationController>()?.interactablesSpawner;
        var catalog = CatalogPrefabs.Describe(mapData, interactables);
        var entries = PaletteCatalogBuilder.Build(catalog, id => PrefabName(id, interactables));
        Selection.Replace(entries);
        _mapLabel = catalog.Map.ToString();
        BuildCanvas(entries);
        _logger.Msg($"EditorPalette: built {entries.Count} entries for {_mapLabel}");
    }

    private static string PrefabName(CatalogId id, SpawnInteractables interactables)
    {
        try
        {
            return CatalogPrefabs.Resolve(CatalogRoute.Parse(id), interactables)?.name;
        }
        catch (System.Exception)
        {
            return null;
        }
    }

    private static void BuildCanvas(IReadOnlyList<PaletteEntry> entries)
    {
        _root = EditorUi.NewCanvas("MegabonkLevelsPalette");

        var font = PositionLabel.FindFontAsset(EditorUi.FontName);
        _panel = EditorUi.NewRect("Panel", _root.transform);
        _panel.anchorMin = new Vector2(0f, 0f);
        _panel.anchorMax = new Vector2(0f, 1f);
        _panel.pivot = new Vector2(0f, 0.5f);
        _panel.sizeDelta = new Vector2(PanelWidth, 0f);
        _panel.anchoredPosition = Vector2.zero;
        _panel.gameObject.AddComponent<Image>().color = PanelColor;

        var titleRect = EditorUi.NewRect("Title", _panel);
        EditorUi.Stretch(titleRect, TitleHeight);
        _title = EditorUi.NewLabel(titleRect, font, TextAlignmentOptions.TopLeft, FontSize);

        _viewport = EditorUi.NewRect("Viewport", _panel);
        _viewport.anchorMin = Vector2.zero;
        _viewport.anchorMax = Vector2.one;
        _viewport.offsetMin = Vector2.zero;
        _viewport.offsetMax = new Vector2(0f, -TitleHeight);
        _viewport.gameObject.AddComponent<RectMask2D>();

        _content = EditorUi.NewRect("Content", _viewport);
        _content.anchorMin = new Vector2(0f, 1f);
        _content.anchorMax = new Vector2(1f, 1f);
        _content.pivot = new Vector2(0f, 1f);
        _content.anchoredPosition = Vector2.zero;

        var y = 0f;
        var lastGroup = ((int Stage, PaletteCategory Category)?)null;
        foreach (var entry in entries)
        {
            var group = (entry.Stage, entry.Category);
            if (lastGroup != group)
            {
                lastGroup = group;
                AddRow(font, GroupLabel(entry), null, HeaderHeight, ref y);
            }

            AddRow(font, entry.DisplayName, entry.Id, RowHeight, ref y);
        }

        _contentHeight = y;
        _content.sizeDelta = new Vector2(0f, y);
        RefreshSelection();
    }

    private static string GroupLabel(PaletteEntry entry) => entry.Category switch
    {
        PaletteCategory.RandomObject => $"Stage {entry.Stage} random objects",
        PaletteCategory.FlatTile => $"Stage {entry.Stage} flat tiles",
        PaletteCategory.SpecificTile => $"Stage {entry.Stage} specific tiles",
        PaletteCategory.Shrine => "Shrines",
        _ => "Interactables",
    };

    private static void AddRow(TMP_FontAsset font, string text, CatalogId? id, float height, ref float y)
    {
        var rect = EditorUi.NewRect(id.HasValue ? "Entry" : "Header", _content);
        rect.anchorMin = new Vector2(0f, 1f);
        rect.anchorMax = new Vector2(1f, 1f);
        rect.pivot = new Vector2(0f, 1f);
        rect.offsetMin = new Vector2(0f, -(y + height));
        rect.offsetMax = new Vector2(0f, -y);
        y += height;

        var row = new Row { Rect = rect, Id = id };
        if (id.HasValue)
        {
            row.Background = rect.gameObject.AddComponent<Image>();
            row.Background.color = RowColor;
        }

        var labelRect = EditorUi.NewRect("Label", rect);
        labelRect.anchorMin = Vector2.zero;
        labelRect.anchorMax = Vector2.one;
        labelRect.offsetMin = new Vector2(8f, 0f);
        labelRect.offsetMax = new Vector2(-8f, 0f);
        var label = EditorUi.NewLabel(labelRect, font, TextAlignmentOptions.MidlineLeft, FontSize);
        label.text = id.HasValue ? text : $"<color=#d0b050>{text}</color>";
        _rows.Add(row);
    }

    private static void ClickRowAt(Vector2 mouse)
    {
        foreach (var row in _rows)
        {
            if (row.Id.HasValue && RectTransformUtility.RectangleContainsScreenPoint(row.Rect, mouse, null))
            {
                Selection.Select(row.Id.Value);
                return;
            }
        }
    }

    private static void RevealRow(Row row)
    {
        if (_viewport == null || _content == null)
        {
            return;
        }

        var rowTop = -row.Rect.offsetMax.y;
        var offset = PaletteScroll.OffsetToReveal(rowTop, RowHeight, _viewport.rect.height, _content.anchoredPosition.y, _contentHeight);
        _content.anchoredPosition = new Vector2(0f, offset);
    }

    private static void Scroll(float notches)
    {
        if (notches == 0f)
        {
            return;
        }

        var maxOffset = Mathf.Max(0f, _contentHeight - _viewport.rect.height);
        var offset = Mathf.Clamp(_content.anchoredPosition.y - notches * ScrollPixelsPerNotch, 0f, maxOffset);
        _content.anchoredPosition = new Vector2(0f, offset);
    }

    private static void RefreshSelection()
    {
        var current = Selection.Current;
        foreach (var row in _rows)
        {
            if (row.Background != null)
            {
                var selected = row.Id.Equals(current);
                row.Background.color = selected ? SelectedColor : RowColor;
                if (selected)
                {
                    RevealRow(row);
                }
            }
        }

        if (_title != null)
        {
            var name = "none";
            foreach (var entry in Selection.Entries)
            {
                if (current.HasValue && entry.Id.Equals(current.Value))
                {
                    name = entry.DisplayName;
                }
            }

            _title.text = $"{_mapLabel} palette\nselected: {name}";
        }
    }
}
