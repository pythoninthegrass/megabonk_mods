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
    private const float Margin = 8f;
    private const float LabelMargin = 8f;
    private const float TitleHeight = 48f;
    private const float ControlHeight = 30f;
    private const float FontSize = 16f;
    private const float SlotFontSize = 12f;
    private const float SlotSize = 61.6f;
    private const float SlotGap = 4f;
    private const float Border = 2f;
    private const float TabWidth = 56f;
    private const float TabHeight = 48f;
    private const float ButtonWidth = 40f;
    private const float ChevronWidth = 28f;
    private const float ChevronHeight = 48f;
    private const int MagnifierPixels = 24;
    private const float ExpandedInnerWidth = PaletteLayout.ExpandedColumns * SlotSize + (PaletteLayout.ExpandedColumns - 1) * SlotGap;
    private const float CompactInnerWidth = ButtonWidth * 2f + SlotGap;

    private static readonly Color PanelBorder = Gray(0.55f);
    private static readonly Color PanelFill = Gray(0.36f, 0.95f);
    private static readonly Color SlotBorder = Gray(0.15f);
    private static readonly Color SlotFill = Gray(0.22f);
    private static readonly Color HoverFill = Gray(0.30f);
    private static readonly Color SelectedBorder = Gray(1f);
    private static readonly Color SelectedFill = Gray(0.42f);
    private static readonly Color TabFill = Gray(0.28f);
    private static readonly Color ActiveTabBorder = Gray(0.8f);
    // Opaque stand-in for the translucent PanelFill as composited over the world, so the active tab has no seam.
    private static readonly Color ActiveTabFill =Gray(95f / 255f);
    private static readonly Color SearchFill = Gray(0.12f);

    private static readonly List<Slot> _slots = new();
    private static readonly List<Tab> _tabs = new();
    private static readonly PaletteLayout _layout = new();
    private static readonly PaletteSearchInput _search = new();
    private static readonly EditorCaretInput _caretInput = new();
    private static TextFieldView _searchView;
    private static IReadOnlyList<PaletteEntry> _filtered = new List<PaletteEntry>();
    private static PaletteCategory? _category;
    private static int _page;
    private static RectTransform _searchRect;
    private static TextMeshProUGUI _searchLabel;
    private static Image _searchFill;
    private static RectTransform _titleRect;
    private static RectTransform _pageRect;
    private static RectTransform _emptyRect;
    private static RectTransform _chevronRect;
    private static TextMeshProUGUI _chevronLabel;
    private static RectTransform _magnifierRect;
    private static Texture2D _magnifierTexture;
    private static RectTransform _previousRect;
    private static RectTransform _nextRect;
    private static TextMeshProUGUI _pageLabel;
    private static TextMeshProUGUI _emptyLabel;
    private static RectTransform _tooltip;
    private static TextMeshProUGUI _tooltipLabel;
    private static MelonLogger.Instance _logger;
    private static GameObject _root;
    private static RectTransform _panel;
    private static RectTransform _tabColumn;
    private static TextMeshProUGUI _title;
    private static string _selectedName = "none";
    private static string _mapLabel = "";
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

    private sealed class Slot
    {
        public RectTransform Rect;
        public Image Border;
        public Image Fill;
        public RawImage Thumb;
        public TextMeshProUGUI Name;
        public PaletteEntry? Entry;
    }

    private sealed class Tab
    {
        public RectTransform Rect;
        public Image Border;
        public Image Fill;
        public Image Seam;
        public PaletteCategory? Category;
        public string Label;
    }

    private static Color Gray(float value, float alpha = 1f) => new(value, value, value, alpha);

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
        PointerOverPanel = Contains(_panel, mouse) || Contains(_tabColumn, mouse) || Contains(_chevronRect, mouse);
        var clicked = EditorInput.GetMouseButtonDown(0);
        var queryBefore = _search.Query;
        var overSearch = _layout.Compact ? Contains(_magnifierRect, mouse) : Contains(_searchRect, mouse);
        _search.Step(clicked, overSearch, EditorInput.GetKeyDown(KeyCode.Escape), EditorInput.InputString,
            EditorInput.GetKey(KeyCode.LeftControl) || EditorInput.GetKey(KeyCode.RightControl), _caretInput.Read());
        if (queryBefore != _search.Query)
        {
            ApplyFilter();
        }

        _searchView.Render(_search.Field, _search.Focused, "Search name or id...");
        _searchLabel.color = Color.white;
        _searchFill.color = _search.Focused ? SelectedFill : SearchFill;
        var hover = SlotAt(mouse);
        UpdateSlotColors(hover);
        UpdateTooltip(mouse, hover);
        if (!PointerOverPanel)
        {
            return;
        }

        if (Contains(_panel, mouse))
        {
            SetPage(PalettePager.Step(_page, -EditorInput.MouseScrollDelta.y, PageCount));
        }

        if (!clicked)
        {
            return;
        }

        if (Contains(_chevronRect, mouse) || (_layout.Compact && Contains(_magnifierRect, mouse)))
        {
            SetCompact(!_layout.Compact);
        }
        else if (Contains(_previousRect, mouse))
        {
            SetPage(PalettePager.Step(_page, -1f, PageCount));
        }
        else if (Contains(_nextRect, mouse))
        {
            SetPage(PalettePager.Step(_page, 1f, PageCount));
        }
        else if (hover is { Entry: { } entry })
        {
            Selection.Select(entry.Id);
        }
        else if (TabAt(mouse) is { } tab)
        {
            _category = tab.Category;
            ApplyFilter();
        }
    }

    private static int PerPage => _layout.PerPage;

    private static int PageCount => PalettePager.PageCount(_filtered.Count, PerPage);

    private static float PanelWidth => 2f * Margin + (_layout.Compact ? CompactInnerWidth : ExpandedInnerWidth);

    private static void Rebuild()
    {
        if (_root != null)
        {
            Object.Destroy(_root);
        }

        _root = null;
        _slots.Clear();
        _tabs.Clear();
        _search.Reset();
        _category = null;
        _page = 0;
        _layout.Reset();

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
        RenderThumbnails(entries, interactables);
        BuildCanvas(entries);
        _logger.Msg($"EditorPalette: built {entries.Count} entries for {_mapLabel}");
    }

    private static void RenderThumbnails(IReadOnlyList<PaletteEntry> entries, SpawnInteractables interactables)
    {
        var cachedBefore = PrefabThumbnails.Cache.Count;
        var watch = System.Diagnostics.Stopwatch.StartNew();
        foreach (var entry in entries)
        {
            PrefabThumbnails.Cache.GetOrRender(entry.Id, id => PrefabFor(id, interactables) is { } prefab ? PrefabThumbnails.Render(prefab) : null);
        }

        var rendered = PrefabThumbnails.Cache.Count - cachedBefore;
        _logger.Msg($"EditorPalette: rendered {rendered} thumbnails in {watch.ElapsedMilliseconds} ms (cached {cachedBefore})");
    }

    private static GameObject PrefabFor(CatalogId id, SpawnInteractables interactables)
    {
        try
        {
            return CatalogPrefabs.Resolve(CatalogRoute.Parse(id), interactables);
        }
        catch (System.Exception)
        {
            return null;
        }
    }

    private static string PrefabName(CatalogId id, SpawnInteractables interactables) => PrefabFor(id, interactables)?.name;

    private static (RectTransform Outer, Image Border, Image Fill) Bordered(string name, Transform parent, Color border, Color fill)
    {
        var outer = EditorUi.NewRect(name, parent);
        var borderImage = outer.gameObject.AddComponent<Image>();
        borderImage.color = border;
        var inner = EditorUi.NewRect("Fill", outer);
        inner.anchorMin = Vector2.zero;
        inner.anchorMax = Vector2.one;
        inner.offsetMin = new Vector2(Border, Border);
        inner.offsetMax = new Vector2(-Border, -Border);
        var fillImage = inner.gameObject.AddComponent<Image>();
        fillImage.color = fill;
        return (outer, borderImage, fillImage);
    }

    private static void PlaceTopLeft(RectTransform rect, float x, float y, float width, float height)
    {
        rect.anchorMin = new Vector2(0f, 1f);
        rect.anchorMax = new Vector2(0f, 1f);
        rect.pivot = new Vector2(0f, 1f);
        rect.anchoredPosition = new Vector2(x, -y);
        rect.sizeDelta = new Vector2(width, height);
    }

    private static RawImage AddThumb(RectTransform parent)
    {
        var rect = EditorUi.NewRect("Thumb", parent);
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = new Vector2(Border, Border);
        rect.offsetMax = new Vector2(-Border, -Border);
        var thumb = rect.gameObject.AddComponent<RawImage>();
        thumb.raycastTarget = false;
        thumb.enabled = false;
        return thumb;
    }

    private static TextMeshProUGUI CenteredLabel(RectTransform parent, TMP_FontAsset font, float size)
    {
        var rect = EditorUi.NewRect("Label", parent);
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = new Vector2(2f, 2f);
        rect.offsetMax = new Vector2(-2f, -2f);
        var label = EditorUi.NewLabel(rect, font, TextAlignmentOptions.Center, size);
        label.richText = false;
        label.enableWordWrapping = true;
        return label;
    }

    private static void BuildCanvas(IReadOnlyList<PaletteEntry> entries)
    {
        _root = EditorUi.NewCanvas("MegabonkLevelsPalette");
        var font = PositionLabel.FindFontAsset(EditorUi.FontName);
        var gridTop = TitleHeight + ControlHeight + Margin;
        var footerTop = gridTop + PaletteLayout.Rows * (SlotSize + SlotGap);
        var panelHeight = footerTop + ControlHeight + Margin;

        var panel = Bordered("Panel", _root.transform, PanelBorder, PanelFill);
        _panel = panel.Outer;
        _panel.anchorMin = new Vector2(0f, 1f);
        _panel.anchorMax = new Vector2(0f, 1f);
        _panel.pivot = new Vector2(0f, 1f);
        _panel.anchoredPosition = new Vector2(TabWidth, -Margin);
        _panel.sizeDelta = new Vector2(0f, panelHeight);

        _titleRect = EditorUi.NewRect("Title", _panel);
        _title = EditorUi.NewLabel(_titleRect, font, TextAlignmentOptions.TopLeft, FontSize);

        var search = Bordered("Search", _panel, SlotBorder, SearchFill);
        _searchRect = search.Outer;
        _searchFill = search.Fill;
        _searchLabel = ControlLabel(_searchRect, font, "Search name or id...");
        EditorUi.FixInputBaseline(_searchLabel);
        _searchView = new TextFieldView(_searchLabel);

        var magnifier = Bordered("Magnifier", _panel, SlotBorder, SearchFill);
        _magnifierRect = magnifier.Outer;
        var magnifierImage = AddThumb(magnifier.Fill.rectTransform);
        magnifierImage.texture = MagnifierTexture();
        magnifierImage.enabled = true;
        var iconRect = magnifierImage.rectTransform;
        iconRect.anchorMin = iconRect.anchorMax = iconRect.pivot = new Vector2(0.5f, 0.5f);
        iconRect.anchoredPosition = Vector2.zero;
        iconRect.sizeDelta = new Vector2(MagnifierPixels, MagnifierPixels);

        _chevronRect = BuildButton("Chevron", "<<", font);
        _chevronLabel = _chevronRect.GetComponentInChildren<TextMeshProUGUI>();

        BuildTabs(entries, font);
        for (var i = 0; i < PaletteLayout.ExpandedColumns * PaletteLayout.Rows; i++)
        {
            BuildSlot(font);
        }

        _previousRect = BuildButton("PreviousPage", "<", font);
        _nextRect = BuildButton("NextPage", ">", font);
        _pageRect = EditorUi.NewRect("Page", _panel);
        _pageLabel = ControlLabel(_pageRect, font, "1/1");
        _pageLabel.alignment = TextAlignmentOptions.Center;

        _emptyRect = EditorUi.NewRect("NoResults", _panel);
        _emptyLabel = ControlLabel(_emptyRect, font, "No matching entries");

        _tooltip = EditorUi.NewRect("Tooltip", _root.transform);
        _tooltip.anchorMin = new Vector2(0f, 1f);
        _tooltip.anchorMax = new Vector2(0f, 1f);
        _tooltip.pivot = new Vector2(0f, 1f);
        _tooltip.gameObject.AddComponent<Image>().color = Gray(0.08f, 0.95f);
        _tooltipLabel = ControlLabel(_tooltip, font, "");
        _tooltip.gameObject.SetActive(false);
        ApplyLayout();
        ApplyFilter();
    }

    private static Texture2D MagnifierTexture()
    {
        if (_magnifierTexture != null)
        {
            return _magnifierTexture;
        }

        var mask = MagnifierIcon.Mask(MagnifierPixels);
        var texture = new Texture2D(MagnifierPixels, MagnifierPixels, TextureFormat.RGBA32, false) { filterMode = FilterMode.Point };
        for (var row = 0; row < MagnifierPixels; row++)
        {
            for (var column = 0; column < MagnifierPixels; column++)
            {
                texture.SetPixel(column, MagnifierPixels - 1 - row, mask[row, column] ? Color.white : Color.clear);
            }
        }

        texture.Apply();
        _magnifierTexture = texture;
        return texture;
    }

    // Positions every panel-width dependent element for the current compact state and republishes Width.
    private static void ApplyLayout()
    {
        var compact = _layout.Compact;
        var panelWidth = PanelWidth;
        var innerWidth = panelWidth - Margin * 2f;
        var gridTop = TitleHeight + ControlHeight + Margin;
        var slotSize = compact ? CompactInnerWidth : SlotSize;
        var footerTop = gridTop + PaletteLayout.Rows * (slotSize + SlotGap);
        Width = TabWidth + panelWidth + ChevronWidth;
        _panel.sizeDelta = new Vector2(panelWidth, footerTop + ControlHeight + Margin);

        PlaceTopLeft(_titleRect, Margin, 4f, innerWidth, TitleHeight - 4f);
        _searchRect.gameObject.SetActive(!compact);
        PlaceTopLeft(_searchRect, Margin, TitleHeight, innerWidth, ControlHeight);
        _magnifierRect.gameObject.SetActive(compact);
        PlaceTopLeft(_magnifierRect, Margin + (innerWidth - slotSize) / 2f, TitleHeight, slotSize, ControlHeight);
        PlaceTopLeft(_chevronRect, panelWidth, (_panel.sizeDelta.y - ChevronHeight) / 2f, ChevronWidth, ChevronHeight);
        _chevronLabel.text = compact ? ">>" : "<<";

        var columns = _layout.Columns;
        var slotsWidth = columns * slotSize + (columns - 1) * SlotGap;
        var slotsLeft = Margin + (innerWidth - slotsWidth) / 2f;
        for (var i = 0; i < _slots.Count; i++)
        {
            PlaceTopLeft(_slots[i].Rect, slotsLeft + i % columns * (slotSize + SlotGap), gridTop + i / columns * (slotSize + SlotGap), slotSize, slotSize);
        }

        PlaceTopLeft(_previousRect, Margin, footerTop, ButtonWidth, ControlHeight);
        PlaceTopLeft(_nextRect, panelWidth - Margin - ButtonWidth, footerTop, ButtonWidth, ControlHeight);
        _pageRect.gameObject.SetActive(!compact);
        PlaceTopLeft(_pageRect, Margin + ButtonWidth + SlotGap, footerTop, innerWidth - (ButtonWidth + SlotGap) * 2f, ControlHeight);
        PlaceTopLeft(_emptyRect, Margin, gridTop, innerWidth, ControlHeight);
        _emptyLabel.text = compact ? "None" : "No matching entries";
        _title.text = TitleText();
    }

    private static void SetCompact(bool compact)
    {
        if (compact == _layout.Compact)
        {
            return;
        }

        if (compact)
        {
            _search.Blur();
        }

        _page = _layout.SetCompact(compact, _page);
        ApplyLayout();
        RefreshSelection();
    }

    private static void BuildTabs(IReadOnlyList<PaletteEntry> entries, TMP_FontAsset font)
    {
        var categories = new List<PaletteCategory?> { null };
        categories.AddRange(PaletteFilter.Categories(entries).Select(category => (PaletteCategory?)category));
        _tabColumn = EditorUi.NewRect("Tabs", _root.transform);
        PlaceTopLeft(_tabColumn, 0f, Margin, TabWidth, categories.Count * TabHeight);
        for (var i = 0; i < categories.Count; i++)
        {
            var category = categories[i];
            var parts = Bordered("Tab", _tabColumn, PanelBorder, TabFill);
            PlaceTopLeft(parts.Outer, 0f, i * TabHeight, TabWidth + Border, TabHeight - 4f);
            parts.Fill.rectTransform.offsetMax = new Vector2(-2f * Border, -Border);
            var seam = EditorUi.NewRect("Seam", parts.Outer);
            seam.anchorMin = new Vector2(1f, 0f);
            seam.anchorMax = Vector2.one;
            seam.offsetMin = new Vector2(-2f * Border, Border);
            seam.offsetMax = new Vector2(0f, -Border);
            var seamImage = seam.gameObject.AddComponent<Image>();
            seamImage.raycastTarget = false;
            var first = category.HasValue ? entries.First(entry => entry.Category == category.Value) : (PaletteEntry?)null;
            var thumb = AddThumb(parts.Fill.rectTransform);
            if (first.HasValue && PrefabThumbnails.Cache.TryGet(first.Value.Id, out var texture) && texture != null)
            {
                thumb.texture = texture;
                thumb.enabled = true;
            }
            else
            {
                CenteredLabel(parts.Fill.rectTransform, font, FontSize).text = category?.ShortLabel() ?? "All";
            }

            _tabs.Add(new Tab { Rect = parts.Outer, Border = parts.Border, Fill = parts.Fill, Seam = seamImage, Category = category, Label = category?.Label() ?? "All" });
        }
    }

    private static void BuildSlot(TMP_FontAsset font)
    {
        var parts = Bordered("Slot", _panel, SlotBorder, SlotFill);
        _slots.Add(new Slot
        {
            Rect = parts.Outer,
            Border = parts.Border,
            Fill = parts.Fill,
            Thumb = AddThumb(parts.Fill.rectTransform),
            Name = CenteredLabel(parts.Fill.rectTransform, font, SlotFontSize),
        });
    }

    private static RectTransform BuildButton(string name, string text, TMP_FontAsset font)
    {
        var parts = Bordered(name, _panel, SlotBorder, SlotFill);
        CenteredLabel(parts.Fill.rectTransform, font, FontSize).text = text;
        return parts.Outer;
    }

    private static RectTransform ControlRect(string name, float top, float left, float right)
    {
        var rect = EditorUi.NewRect(name, _panel);
        rect.anchorMin = new Vector2(0f, 1f);
        rect.anchorMax = new Vector2(1f, 1f);
        rect.pivot = new Vector2(0f, 1f);
        rect.offsetMin = new Vector2(left, -(top + ControlHeight));
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

    private static string TitleText() =>
        _layout.Compact ? $"{_mapLabel}\n{_selectedName}" : $"{_mapLabel} palette\nselected: {_selectedName}";

    private static bool Contains(RectTransform rect, Vector2 mouse) =>
        rect != null && RectTransformUtility.RectangleContainsScreenPoint(rect, mouse, null);

    private static Slot SlotAt(Vector2 mouse) =>
        _slots.FirstOrDefault(slot => slot.Entry.HasValue && Contains(slot.Rect, mouse));

    private static Tab TabAt(Vector2 mouse) => _tabs.FirstOrDefault(tab => Contains(tab.Rect, mouse));

    private static void ApplyFilter()
    {
        _filtered = PaletteFilter.Apply(Selection.Entries, _search.Query, _category);
        _page = 0;
        _emptyLabel.gameObject.SetActive(_filtered.Count == 0);
        RefreshSelection();
        Rebind();
    }

    private static void SetPage(int page)
    {
        if (page == _page)
        {
            return;
        }

        _page = page;
        Rebind();
    }

    // Shows the page that holds the current selection, when the active filters leave it visible.
    private static void RevealSelection()
    {
        if (Selection.Current is not { } current)
        {
            return;
        }

        for (var i = 0; i < _filtered.Count; i++)
        {
            if (_filtered[i].Id.Equals(current))
            {
                _page = PalettePager.PageOf(i, PerPage);
                return;
            }
        }
    }

    private static void Rebind()
    {
        var pageEntries = PalettePager.Slice(_filtered, _page, PerPage);
        for (var i = 0; i < _slots.Count; i++)
        {
            var slot = _slots[i];
            slot.Entry = i < pageEntries.Count ? pageEntries[i] : null;
            slot.Rect.gameObject.SetActive(slot.Entry.HasValue);
            if (!slot.Entry.HasValue)
            {
                continue;
            }

            var hasThumb = PrefabThumbnails.Cache.TryGet(slot.Entry.Value.Id, out var texture) && texture != null;
            slot.Thumb.texture = hasThumb ? texture : null;
            slot.Thumb.enabled = hasThumb;
            slot.Name.gameObject.SetActive(!hasThumb);
            slot.Name.text = slot.Entry.Value.DisplayName;
        }

        _pageLabel.text = $"{_page + 1}/{PageCount}";
        foreach (var tab in _tabs)
        {
            tab.Border.color = tab.Category == _category ? ActiveTabBorder : PanelBorder;
            tab.Fill.color = tab.Category == _category ? ActiveTabFill : TabFill;
            tab.Seam.color = tab.Category == _category ? ActiveTabFill : PanelBorder;
        }

        UpdateSlotColors(null);
    }

    private static void UpdateSlotColors(Slot hover)
    {
        var current = Selection.Current;
        foreach (var slot in _slots)
        {
            if (!slot.Entry.HasValue)
            {
                continue;
            }

            var selected = current.HasValue && slot.Entry.Value.Id.Equals(current.Value);
            slot.Border.color = selected ? SelectedBorder : SlotBorder;
            slot.Fill.color = selected ? SelectedFill : slot == hover ? HoverFill : SlotFill;
        }
    }

    private static void UpdateTooltip(Vector2 mouse, Slot hover)
    {
        _tooltip.gameObject.SetActive(false);
        string text = null;
        if (hover is { Entry: { } entry })
        {
            text = $"{hover.Name.text}\n{entry.Id.Serialize()}\n{PaletteGroup.Of(entry).Label}";
        }
        else if (TabAt(mouse) is { } tab)
        {
            text = tab.Label;
        }
        else if (Contains(_chevronRect, mouse))
        {
            text = _layout.Compact ? "Expand palette" : "Collapse palette";
        }
        else if (_layout.Compact && Contains(_magnifierRect, mouse))
        {
            text = "Search";
        }

        if (text == null)
        {
            return;
        }

        _tooltipLabel.text = text;
        var size = _tooltipLabel.GetPreferredValues(text) + new Vector2(LabelMargin * 2f, 12f);
        size.x = Mathf.Min(size.x, Screen.width);
        _tooltip.sizeDelta = size;
        var x = Mathf.Clamp(mouse.x + 16f, 0f, Screen.width - size.x);
        var top = Mathf.Clamp(Screen.height - mouse.y + 16f, 0f, Mathf.Max(0f, Screen.height - size.y));
        _tooltip.anchoredPosition = new Vector2(x, -top);
        _tooltip.gameObject.SetActive(true);
    }

    private static void RefreshSelection()
    {
        if (_slots.Count == 0)
        {
            return;
        }

        RevealSelection();
        Rebind();
        if (_title != null)
        {
            _selectedName = "none";
            var current = Selection.Current;
            foreach (var entry in Selection.Entries)
            {
                if (current.HasValue && entry.Id.Equals(current.Value))
                {
                    _selectedName = entry.DisplayName;
                }
            }

            _title.text = TitleText();
        }
    }
}
