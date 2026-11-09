using System.Collections.Generic;
using System.Linq;
using Assets.Scripts.Managers;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using static MegabonkLevels.EditorUi;

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
    private const float TabWidth = 56f;
    private const float TabHeight = 48f;
    private const float ButtonWidth = 40f;
    private const float ChevronWidth = 28f;
    private const float ChevronHeight = 48f;
    private const int MagnifierPixels = 24;
    private const int TabTargetBase = 1000;
    private const int ChevronTarget = 2000;
    private const int MagnifierTarget = 2001;
    private const float ExpandedInnerWidth = PaletteLayout.ExpandedColumns * SlotSize + (PaletteLayout.ExpandedColumns - 1) * SlotGap;
    private const float CompactInnerWidth = ButtonWidth * 2f + SlotGap;

    private static readonly Color SelectedBorder = Gray(1f);
    private static readonly Color TabFill = Gray(0.28f);
    private static readonly Color ActiveTabBorder = Gray(0.8f);
    // Opaque stand-in for the translucent PanelFill as composited over the world, so the active tab has no seam.
    private static readonly Color ActiveTabFill =Gray(95f / 255f);

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
    private static EditorTooltip _tooltip;
    private static readonly HoverDelay _tooltipDelay = EditorTooltip.NewHoverDelay();
    private static ModLogger _logger;
    private static GameObject _root;
    private static RectTransform _panel;
    private static RectTransform _tabColumn;
    private static TextMeshProUGUI _title;
    private static string _selectedName = "none";
    private static string _mapLabel = "";
    private static string _mapSummary = "";
    private static readonly PaletteThumbnailQueue _thumbnails = new();
    private static readonly System.Diagnostics.Stopwatch _thumbnailWatch = new();
    private static readonly System.Diagnostics.Stopwatch _buildWatch = new();
    private static SpawnInteractables _interactables;
    private static RandomObjectPlacer _placer;
    private static EMap _loadedMap = EMap.None;
    private static int _thumbnailBaseCount;
    private static int _thumbnailRendered;
    private static CursorLockMode _cursorLockBefore;
    private static bool _cursorVisibleBefore;
    private static bool _open;

    public static PaletteSelection Selection { get; } = new();

    static EditorPalette()
    {
        Selection.Changed += _ => RefreshSelection();
    }

    public static bool PointerOverPanel { get; private set; }

    // The map the palette was built for; every entry names the map its asset was walked from.
    public static EMap LoadedMap => _loadedMap;

    public static float Width { get; private set; }

    public static float ExpandedWidth => TabWidth + 2f * Margin + ExpandedInnerWidth + ChevronWidth;

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

    public static void OnEditorEntered(ModLogger logger)
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

        DrainThumbnails();

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
            // Choosing what to place also picks the tool that places it, the way pick-block does.
            EditorTileTools.SelectTool(EditorTool.Place);
        }
        else if (TabAt(mouse) is { } tab)
        {
            _category = tab.Category;
            ApplyFilter();
        }
    }

    // Specific widgets come before the panels that contain them, so UiWidgets.At reports the innermost one.
    public static IEnumerable<UiWidget> ListWidgets()
    {
        if (!_open || _root == null)
        {
            return Enumerable.Empty<UiWidget>();
        }

        var widgets = new List<UiWidget?>();
        foreach (var slot in _slots.Where(slot => slot.Entry.HasValue))
        {
            widgets.Add(ToWidget($"Palette:{slot.Entry.Value.Id.Serialize()}", slot.Rect));
        }

        foreach (var tab in _tabs)
        {
            widgets.Add(ToWidget($"Tab:{tab.Label}", tab.Rect));
        }

        widgets.Add(ToWidget("PaletteChevron", _chevronRect));
        widgets.Add(ToWidget("PalettePrevious", _previousRect));
        widgets.Add(ToWidget("PaletteNext", _nextRect));
        widgets.Add(ToWidget("PaletteSearch", _layout.Compact ? _magnifierRect : _searchRect));
        widgets.Add(ToWidget("PalettePanel", _panel));
        return widgets.Where(widget => widget.HasValue).Select(widget => widget.Value);
    }

    private static int PerPage => _layout.PerPage;

    private static int PageCount => PalettePager.PageCount(_filtered.Count, PerPage);

    private static float PanelWidth => 2f * Margin + (_layout.Compact ? CompactInnerWidth : ExpandedInnerWidth);

    private static void Rebuild()
    {
        _buildWatch.Restart();
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

        var controller = Object.FindObjectOfType<MapGenerationController>();
        _interactables = controller?.interactablesSpawner;
        _placer = controller?.randomObjectPlacer;
        _loadedMap = (EMap)(int)mapData.eMap;
        var catalogs = CatalogPrefabs.DescribeAll(mapData, _interactables, _placer);
        var entries = PaletteCatalogBuilder.BuildAll(catalogs, PrefabName).Concat(PackPrefabs.ListEntries()).ToList();
        Selection.Replace(entries);
        _mapLabel = _loadedMap.ToString();
        _mapSummary = catalogs.Count > 1 ? $" ({catalogs.Count} maps)" : "";
        BuildCanvas(entries);
        var buildMs = _buildWatch.ElapsedMilliseconds;
        StartThumbnails();
        var byMap = string.Join(", ", entries.GroupBy(entry => entry.Map).Select(group => $"{(group.Key == EMap.None ? "packs" : group.Key.ToString())} {group.Count()}"));
        _logger.Msg($"EditorPalette: built {entries.Count} entries for {_mapLabel} ({byMap}) in {buildMs} ms");
    }

    // Thumbnails are rendered a few per frame by Tick rather than all at once, so opening the palette
    // costs one layout pass no matter how many maps the catalog spans.
    private static void StartThumbnails()
    {
        _thumbnailBaseCount = PrefabThumbnails.Cache.Count;
        _thumbnailRendered = 0;
        _thumbnailWatch.Restart();
        RequestThumbnails();
    }

    // The page on screen first, then the rest of the filtered set, then the whole catalog.
    private static void RequestThumbnails()
    {
        if (_root == null)
        {
            return;
        }

        var page = PalettePager.Slice(_filtered, _page, PerPage).Select(entry => entry.Id);
        _thumbnails.Request(page.Concat(_filtered.Select(entry => entry.Id)).Concat(Selection.Entries.Select(entry => entry.Id)).ToArray());
    }

    private static void DrainThumbnails()
    {
        if (_thumbnails.IsEmpty)
        {
            return;
        }

        if (_thumbnails.Step(RenderThumbnail) == 0)
        {
            return;
        }

        Rebind();
        if (_thumbnails.IsEmpty)
        {
            _logger.Msg($"EditorPalette: rendered {_thumbnailRendered} thumbnails in {_thumbnailWatch.ElapsedMilliseconds} ms (cached {_thumbnailBaseCount})");
        }
    }

    private static bool RenderThumbnail(CatalogId id)
    {
        if (PrefabThumbnails.Cache.TryGet(id, out _))
        {
            return false;
        }

        PrefabThumbnails.Cache.GetOrRender(id, key => PrefabFor(key) is { } prefab ? PrefabThumbnails.Render(prefab) : null);
        _thumbnailRendered++;
        return true;
    }

    private static Texture2D TextureFor(CatalogId id) =>
        PrefabThumbnails.Cache.GetOrRender(id, key => PrefabFor(key) is { } prefab ? PrefabThumbnails.Render(prefab) : null);

    private static GameObject PrefabFor(CatalogId id)
    {
        try
        {
            if (id.Namespace == CatalogNamespace.Bundle)
            {
                return PackPrefabs.Resolve(id);
            }

            return CatalogPrefabs.Resolve(CatalogRoute.Parse(id), _interactables, _placer);
        }
        catch (System.Exception)
        {
            return null;
        }
    }

    private static string PrefabName(CatalogId id) => PrefabFor(id)?.name;

    // The catalog entries the palette would list for the loaded map, named from their prefabs, without building the UI.
    public static IReadOnlyList<PaletteEntry> CatalogEntries()
    {
        var mapData = MapController.currentMap;
        if (mapData == null) return new List<PaletteEntry>();
        var controller = Object.FindObjectOfType<MapGenerationController>();
        _interactables = controller?.interactablesSpawner;
        _placer = controller?.randomObjectPlacer;
        return PaletteCatalogBuilder.BuildAll(CatalogPrefabs.DescribeAll(mapData, _interactables, _placer), PrefabName).ToList();
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
        _panel.anchoredPosition = new Vector2(TabWidth, -EditorUi.TopInset);
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

        _tooltip = new EditorTooltip(_root.transform, font, FontSize);
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
        RequestThumbnails();
    }

    private static void BuildTabs(IReadOnlyList<PaletteEntry> entries, TMP_FontAsset font)
    {
        var categories = new List<PaletteCategory?> { null };
        categories.AddRange(PaletteFilter.Categories(entries).Select(category => (PaletteCategory?)category));
        _tabColumn = EditorUi.NewRect("Tabs", _root.transform);
        PlaceTopLeft(_tabColumn, 0f, EditorUi.TopInset, TabWidth, categories.Count * TabHeight);
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
            if (first.HasValue && TextureFor(first.Value.Id) is { } texture)
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
        _layout.Compact ? $"{_mapLabel}\n{_selectedName}" : $"{_mapLabel}{_mapSummary} palette\nselected: {_selectedName}";

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
        RequestThumbnails();
    }

    private static void SetPage(int page)
    {
        if (page == _page)
        {
            return;
        }

        _page = page;
        Rebind();
        RequestThumbnails();
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
                RequestThumbnails();
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
        string text = null;
        int? target = null;
        if (hover is { Entry: { } entry })
        {
            text = $"{entry.DisplayName}\n{entry.Id.Serialize()}\n{PaletteGroup.Of(entry).LabelFor(_loadedMap)}";
            target = _slots.IndexOf(hover);
        }
        else if (TabAt(mouse) is { } tab)
        {
            text = tab.Label;
            target = TabTargetBase + _tabs.IndexOf(tab);
        }
        else if (Contains(_chevronRect, mouse))
        {
            text = _layout.Compact ? "Expand palette" : "Collapse palette";
            target = ChevronTarget;
        }
        else if (_layout.Compact && Contains(_magnifierRect, mouse))
        {
            text = "Search";
            target = MagnifierTarget;
        }

        if (text == null || !_tooltipDelay.Update(target, Time.unscaledTime))
        {
            _tooltip.Hide();
            return;
        }

        _tooltip.Show(text, mouse);
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
