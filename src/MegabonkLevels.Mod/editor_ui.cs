using Il2CppTMPro;
using UnityEngine;
using UnityEngine.UI;

namespace MegabonkLevels;

// UGUI building blocks shared by the editor overlays.
public static class EditorUi
{
    public const string FontName = "RobotoMono";

    // Distance from the top of the window to the first overlay row, clearing the viewport border and the screen notch.
    public const float TopInset = 26f;

    public const float Border = 2f;

    public static readonly Color PanelBorder = Gray(0.55f);
    public static readonly Color PanelFill = Gray(0.36f, 0.95f);
    public static readonly Color SlotBorder = Gray(0.15f);
    public static readonly Color SlotFill = Gray(0.22f);
    public static readonly Color HoverFill = Gray(0.30f);
    public static readonly Color SelectedFill = Gray(0.42f);
    public static readonly Color SearchFill = Gray(0.12f);

    public static Color Gray(float value, float alpha = 1f) => new(value, value, value, alpha);

    public static GameObject NewCanvas(string name)
    {
        var root = new GameObject(name);
        Object.DontDestroyOnLoad(root);
        var canvas = root.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        canvas.sortingOrder = 1000;
        return root;
    }

    public static RectTransform NewRect(string name, Transform parent)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        return go.AddComponent<RectTransform>();
    }

    public static (RectTransform Outer, Image Border, Image Fill) Bordered(string name, Transform parent, Color border, Color fill)
    {
        var outer = NewRect(name, parent);
        var borderImage = outer.gameObject.AddComponent<Image>();
        borderImage.color = border;
        var inner = NewRect("Fill", outer);
        inner.anchorMin = Vector2.zero;
        inner.anchorMax = Vector2.one;
        inner.offsetMin = new Vector2(Border, Border);
        inner.offsetMax = new Vector2(-Border, -Border);
        var fillImage = inner.gameObject.AddComponent<Image>();
        fillImage.color = fill;
        return (outer, borderImage, fillImage);
    }

    public static void PlaceTopLeft(RectTransform rect, float x, float y, float width, float height)
    {
        rect.anchorMin = new Vector2(0f, 1f);
        rect.anchorMax = new Vector2(0f, 1f);
        rect.pivot = new Vector2(0f, 1f);
        rect.anchoredPosition = new Vector2(x, -y);
        rect.sizeDelta = new Vector2(width, height);
    }

    // Anchors rect to the top of its parent, full width less an 8-pixel margin, height pixels tall.
    public static void Stretch(RectTransform rect, float height)
    {
        rect.anchorMin = new Vector2(0f, 1f);
        rect.anchorMax = new Vector2(1f, 1f);
        rect.pivot = new Vector2(0f, 1f);
        rect.offsetMin = new Vector2(8f, -height);
        rect.offsetMax = new Vector2(-8f, 0f);
    }

    public static TextMeshProUGUI NewLabel(RectTransform rect, TMP_FontAsset font, TextAlignmentOptions alignment, float fontSize)
    {
        var label = rect.gameObject.AddComponent<TextMeshProUGUI>();
        if (font != null)
        {
            label.font = font;
        }

        label.fontSize = fontSize;
        label.alignment = alignment;
        label.enableWordWrapping = false;
        label.overflowMode = TextOverflowModes.Ellipsis;
        label.color = Color.white;
        label.raycastTarget = false;
        StripEffects(label);
        return label;
    }

    // The game's font material has underlay (drop shadow) on and zero sharpness, which draws gray boxes behind small glyphs.
    private static void StripEffects(TextMeshProUGUI label)
    {
        var material = label.fontMaterial;
        material.DisableKeyword("UNDERLAY_ON");
        material.DisableKeyword("OUTLINE_ON");
        foreach (var property in new[] { "_OutlineWidth", "_UnderlaySoftness", "_UnderlayDilate", "_FaceDilate" })
        {
            if (material.HasProperty(property))
            {
                material.SetFloat(property, 0f);
            }
        }

        if (material.HasProperty("_UnderlayColor"))
        {
            material.SetColor("_UnderlayColor", Color.clear);
        }

        material.SetFloat("_Sharpness", 1f);
    }

    public static void FixInputBaseline(TextMeshProUGUI label)
    {
        label.alignment = TextAlignmentOptions.BaselineLeft;
        label.rectTransform.anchoredPosition += new Vector2(0f, -label.fontSize * 0.3f);
    }
}
