using Il2CppTMPro;
using UnityEngine;

namespace MegabonkLevels;

// UGUI building blocks shared by the editor overlays.
public static class EditorUi
{
    public const string FontName = "RobotoMono";

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
        return label;
    }
}
