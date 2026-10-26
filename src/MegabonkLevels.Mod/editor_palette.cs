using System.Collections.Generic;
using System.Linq;
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
    private const float LabelMargin = 8f;
    private const float TitleHeight = 48f;
    private const float ControlsHeight = 60f;
    private const float RowHeight = 26f;
    private const float HeaderHeight = 22f;
    private const float FontSize = 16f;
    private const float ScrollPixelsPerNotch = 40f;

    private static readonly Color PanelColor = new(0f, 0f, 0f, 0.75f);
    private static readonly Color HeaderColor = new(0f, 0f, 0f, 0.95f);
    private static readonly Color SearchColor = new(0.1f, 0.1f, 0.1f, 0.98f);
    private static readonly Color RowColor = new(1f, 1f, 1f, 0.06f);
    private static readonly Color SelectedColor = new(0.2f, 0.5f, 0.9f, 0.9f);

    private static readonly List<Row> _rows = new();
    private static readonly PaletteSearchInput _search = new();
    private static IReadOnlyList<PaletteGroup> _groups;
    private static int _groupIndex = -1;
    private static RectTransform _searchRect;
    private static TextMeshProUGUI _searchLabel;
    private static Image _searchBackground;
    private static RectTransform _allRect;
    private static RectTransform _previousRect;
    private static RectTransform _nextRect;
    private static TextMeshProUGUI _groupLabel;
    private static TextMeshProUGUI _emptyLabel;
    private static RectTransform _tooltip;
    private static TextMeshProUGUI _tooltipLabel;
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

    public static float Width { get; private set; }

    public static bool TextInputCaptured => _search.CapturesKeyboard;

    public static bool SearchFocused => _search.Focused;

    public static bool SearchHasText => _search.Query.Length > 0;

    public static void BlurSearch() => _search.Blur();

    public static void ClearSearch()
    {
        _search.Reset();
        ApplyFilter();
    }

    private sealed class Row
    {
        public RectTransform Rect;
        public Image Background;
        public CatalogId? Id;
        public PaletteGroup Group;
        public string Name;
        public float Height;
        public bool Visible;
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
        _search.Reset();
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
        var clicked = EditorInput.GetMouseButtonDown(0);
        var queryBefore = _search.Query;
        _search.Step(clicked, Contains(_searchRect, mouse), EditorInput.GetKeyDown(KeyCode.Escape), EditorInput.InputString,
            EditorInput.GetKey(KeyCode.LeftControl) || EditorInput.GetKey(KeyCode.RightControl));
        if (queryBefore != _search.Query)
        {
            ApplyFilter();
        }

        _searchLabel.text = _search.Query.Length == 0 ? "Search name or id..." : _search.Query;
        _searchLabel.color = Color.white;
        _searchBackground.color = _search.Focused ? SelectedColor : SearchColor;
        UpdateTooltip(mouse);
        if (!PointerOverPanel)
        {
            return;
        }

        if (Contains(_viewport, mouse))
        {
            Scroll(EditorInput.MouseScrollDelta.y);
        }

        if (clicked && Contains(_allRect, mouse))
        {
            _groupIndex = -1;
            ApplyFilter();
        }
        else if (clicked && (Contains(_previousRect, mouse) || Contains(_nextRect, mouse)))
        {
            var direction = Contains(_previousRect, mouse) ? -1 : 1;
            _groupIndex = (_groupIndex + 1 + direction + _groups.Count + 1) % (_groups.Count + 1) - 1;
            ApplyFilter();
        }
        else if (clicked && Contains(_viewport, mouse))
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
        _search.Reset();
        _groupIndex = -1;

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
        _groups = PaletteFilter.Groups(entries);
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
        _panel.sizeDelta = new Vector2(0f, 0f);
        _panel.anchoredPosition = Vector2.zero;
        _panel.gameObject.AddComponent<Image>().color = PanelColor;

        var headerRect = EditorUi.NewRect("HeaderBackground", _panel);
        EditorUi.Stretch(headerRect, TitleHeight + ControlsHeight);
        headerRect.offsetMin = new Vector2(0f, -(TitleHeight + ControlsHeight));
        headerRect.offsetMax = Vector2.zero;
        headerRect.gameObject.AddComponent<Image>().color = HeaderColor;

        var titleRect = EditorUi.NewRect("Title", _panel);
        EditorUi.Stretch(titleRect, TitleHeight);
        _title = EditorUi.NewLabel(titleRect, font, TextAlignmentOptions.TopLeft, FontSize);

        _searchRect = ControlRect("Search", TitleHeight, 0f, 0f);
        _searchBackground = _searchRect.gameObject.AddComponent<Image>();
        _searchBackground.color = SearchColor;
        _searchLabel = ControlLabel(_searchRect, font, "Search name or id...");
        EditorUi.FixInputBaseline(_searchLabel);
        _allRect = ControlRect("All", TitleHeight + 30f, 0f, 0f);
        _allRect.anchorMax = new Vector2(0f, 1f);
        _allRect.offsetMax = new Vector2(48f, -(TitleHeight + 30f));
        ControlLabel(_allRect, font, "All");
        _previousRect = ControlRect("PreviousGroup", TitleHeight + 30f, 48f, 0f);
        _previousRect.anchorMax = new Vector2(0f, 1f);
        _previousRect.offsetMax = new Vector2(76f, -(TitleHeight + 30f));
        ControlLabel(_previousRect, font, "<");
        _nextRect = ControlRect("NextGroup", TitleHeight + 30f, 0f, 0f);
        _nextRect.anchorMin = new Vector2(1f, 1f);
        _nextRect.offsetMin = new Vector2(-28f, -(TitleHeight + ControlsHeight));
        ControlLabel(_nextRect, font, ">");
        var groupRect = ControlRect("Group", TitleHeight + 30f, 76f, 28f);
        _groupLabel = ControlLabel(groupRect, font, "All");

        _viewport = EditorUi.NewRect("Viewport", _panel);
        _viewport.anchorMin = Vector2.zero;
        _viewport.anchorMax = Vector2.one;
        _viewport.offsetMin = Vector2.zero;
        _viewport.offsetMax = new Vector2(0f, -(TitleHeight + ControlsHeight));
        _viewport.gameObject.AddComponent<RectMask2D>();

        _content = EditorUi.NewRect("Content", _viewport);
        _content.anchorMin = new Vector2(0f, 1f);
        _content.anchorMax = new Vector2(1f, 1f);
        _content.pivot = new Vector2(0f, 1f);
        _content.anchoredPosition = Vector2.zero;

        var y = 0f;
        var widestLabel = 0f;
        var lastGroup = ((int Stage, PaletteCategory Category)?)null;
        foreach (var entry in entries)
        {
            var group = (entry.Stage, entry.Category);
            if (lastGroup != group)
            {
                lastGroup = group;
                AddRow(font, PaletteGroup.Of(entry).Label, null, PaletteGroup.Of(entry), HeaderHeight, ref y, ref widestLabel);
            }

            AddRow(font, entry.DisplayName, entry.Id, PaletteGroup.Of(entry), RowHeight, ref y, ref widestLabel);
        }

        _contentHeight = y;
        widestLabel = Mathf.Max(widestLabel, WidestTitleWidth(entries));
        foreach (var group in _groups)
        {
            widestLabel = Mathf.Max(widestLabel, _groupLabel.GetPreferredValues(group.Label).x + 104f);
        }
        Width = widestLabel + LabelMargin * 2f;
        _panel.sizeDelta = new Vector2(Width, 0f);
        _content.sizeDelta = new Vector2(0f, y);
        var emptyRect = EditorUi.NewRect("NoResults", _viewport);
        EditorUi.Stretch(emptyRect, RowHeight);
        _emptyLabel = ControlLabel(emptyRect, font, "No matching entries");
        _tooltip = EditorUi.NewRect("Tooltip", _root.transform);
        _tooltip.anchorMin = new Vector2(0f, 1f);
        _tooltip.anchorMax = new Vector2(0f, 1f);
        _tooltip.pivot = new Vector2(0f, 1f);
        _tooltip.gameObject.AddComponent<Image>().color = new Color(0f, 0f, 0f, 0.95f);
        _tooltipLabel = ControlLabel(_tooltip, font, "");
        _tooltip.gameObject.SetActive(false);
        ApplyFilter();
    }

    private static float WidestTitleWidth(IReadOnlyList<PaletteEntry> entries)
    {
        var widest = 0f;
        foreach (var entry in entries)
        {
            widest = Mathf.Max(widest, _title.GetPreferredValues(TitleText(entry.DisplayName)).x);
        }

        return widest;
    }

    private static string TitleText(string selectedName) => $"{_mapLabel} palette\nselected: {selectedName}";

    private static RectTransform ControlRect(string name, float top, float left, float right)
    {
        var rect = EditorUi.NewRect(name, _panel);
        rect.anchorMin = new Vector2(0f, 1f);
        rect.anchorMax = new Vector2(1f, 1f);
        rect.pivot = new Vector2(0f, 1f);
        rect.offsetMin = new Vector2(left, -(top + 30f));
        rect.offsetMax = new Vector2(-right, -top);
        return rect;
    }

    private static TextMeshProUGUI ControlLabel(RectTransform parent, TMP_FontAsset font, string text)
    {
        var rect = EditorUi.NewRect("Label", parent);
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = new Vector2(LabelMargin, 0f);
        rect.offsetMax = new Vector2(-LabelMargin, 0f);
        var label = EditorUi.NewLabel(rect, font, TextAlignmentOptions.MidlineLeft, FontSize);
        label.richText = false;
        label.text = text;
        return label;
    }

    private static bool Contains(RectTransform rect, Vector2 mouse) =>
        RectTransformUtility.RectangleContainsScreenPoint(rect, mouse, null);

    private static void ApplyFilter()
    {
        PaletteGroup? group = _groupIndex < 0 ? null : _groups[_groupIndex];
        var entries = PaletteFilter.Apply(Selection.Entries, _search.Query, group);
        var ids = new HashSet<CatalogId>(entries.Select(entry => entry.Id));
        var groups = new HashSet<PaletteGroup>(entries.Select(PaletteGroup.Of));
        var y = 0f;
        foreach (var row in _rows)
        {
            row.Visible = row.Id is { } id ? ids.Contains(id) : groups.Contains(row.Group);
            row.Rect.gameObject.SetActive(row.Visible);
            if (!row.Visible)
            {
                continue;
            }

            row.Rect.offsetMin = new Vector2(0f, -(y + row.Height));
            row.Rect.offsetMax = new Vector2(0f, -y);
            y += row.Height;
        }

        _contentHeight = y;
        _content.sizeDelta = new Vector2(0f, y);
        _groupLabel.text = group?.Label ?? "All";
        _emptyLabel.gameObject.SetActive(entries.Count == 0);
        RefreshSelection();
        _content.anchoredPosition = Vector2.zero;
    }

    private static void UpdateTooltip(Vector2 mouse)
    {
        _tooltip.gameObject.SetActive(false);
        if (!Contains(_viewport, mouse))
        {
            return;
        }

        foreach (var row in _rows)
        {
            if (!row.Visible || row.Id is not { } id || !Contains(row.Rect, mouse))
            {
                continue;
            }

            _tooltipLabel.text = $"{row.Name}\n{id.Serialize()}";
            var size = _tooltipLabel.GetPreferredValues(_tooltipLabel.text) + new Vector2(LabelMargin * 2f, 12f);
            size.x = Mathf.Min(size.x, Screen.width);
            _tooltip.sizeDelta = size;
            var x = Mathf.Clamp(mouse.x + 16f, 0f, Screen.width - size.x);
            var top = Mathf.Clamp(Screen.height - mouse.y + 16f, 0f, Mathf.Max(0f, Screen.height - size.y));
            _tooltip.anchoredPosition = new Vector2(x, -top);
            _tooltip.gameObject.SetActive(true);
            return;
        }
    }

    private static void AddRow(TMP_FontAsset font, string text, CatalogId? id, PaletteGroup group, float height, ref float y, ref float widestLabel)
    {
        var rect = EditorUi.NewRect(id.HasValue ? "Entry" : "Header", _content);
        rect.anchorMin = new Vector2(0f, 1f);
        rect.anchorMax = new Vector2(1f, 1f);
        rect.pivot = new Vector2(0f, 1f);
        rect.offsetMin = new Vector2(0f, -(y + height));
        rect.offsetMax = new Vector2(0f, -y);
        y += height;

        var row = new Row { Rect = rect, Id = id, Name = text, Group = group, Height = height };
        if (id.HasValue)
        {
            row.Background = rect.gameObject.AddComponent<Image>();
            row.Background.color = RowColor;
        }

        var labelRect = EditorUi.NewRect("Label", rect);
        labelRect.anchorMin = Vector2.zero;
        labelRect.anchorMax = Vector2.one;
        labelRect.offsetMin = new Vector2(LabelMargin, 0f);
        labelRect.offsetMax = new Vector2(-LabelMargin, 0f);
        var label = EditorUi.NewLabel(labelRect, font, TextAlignmentOptions.MidlineLeft, FontSize);
        label.richText = !id.HasValue;
        label.text = id.HasValue ? text : $"<color=#d0b050>{text}</color>";
        widestLabel = Mathf.Max(widestLabel, label.GetPreferredValues(label.text).x);
        _rows.Add(row);
    }

    private static void ClickRowAt(Vector2 mouse)
    {
        foreach (var row in _rows)
        {
            if (row.Visible && row.Id.HasValue && RectTransformUtility.RectangleContainsScreenPoint(row.Rect, mouse, null))
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
                if (selected && row.Visible)
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

            _title.text = TitleText(name);
        }
    }
}
