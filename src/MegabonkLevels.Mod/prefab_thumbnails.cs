using System;
using UnityEngine;

namespace MegabonkLevels;

// Renders a prefab's meshes to a texture from a proxy copy, so the prefab's own scripts never run. See "Catalog palette" in docs/development.md.
public static class PrefabThumbnails
{
    public const int Size = 128;
    private const int Layer = 31;
    private static readonly Vector3 Far = new(0f, -5000f, 0f);
    private static readonly Vector3 ViewDirection = new Vector3(1f, 0.8f, -1f).normalized;

    public static readonly ThumbnailCache<Texture2D> Cache = new();

    // Returns null when the prefab has no mesh to draw or the render throws; the palette then shows the name.
    public static Texture2D Render(GameObject prefab)
    {
        GameObject proxy = null;
        GameObject rig = null;
        var fogBefore = RenderSettings.fog;
        try
        {
            proxy = BuildProxy(prefab);
            if (proxy == null)
            {
                return null;
            }

            var bounds = ProxyBounds(proxy);
            if (bounds.size.sqrMagnitude < 1e-6f)
            {
                return null;
            }

            rig = new GameObject("MegabonkLevelsThumbnailRig");
            rig.transform.position = Far;
            RenderSettings.fog = false;
            return Capture(rig, bounds);
        }
        catch (Exception)
        {
            return null;
        }
        finally
        {
            RenderSettings.fog = fogBefore;
            if (proxy != null)
            {
                UnityEngine.Object.DestroyImmediate(proxy);
            }

            if (rig != null)
            {
                UnityEngine.Object.DestroyImmediate(rig);
            }
        }
    }

    private static GameObject BuildProxy(GameObject prefab)
    {
        var root = new GameObject("MegabonkLevelsThumbnailProxy");
        root.transform.position = Far;
        var drawn = 0;
        foreach (var filter in prefab.GetComponentsInChildren<MeshFilter>(true))
        {
            var renderer = filter.GetComponent<MeshRenderer>();
            if (renderer == null || filter.sharedMesh == null || IsLowerLod(filter.name))
            {
                continue;
            }

            AddPart(root.transform, prefab.transform, filter.transform, filter.sharedMesh, renderer.sharedMaterials);
            drawn++;
        }

        foreach (var skinned in prefab.GetComponentsInChildren<SkinnedMeshRenderer>(true))
        {
            if (skinned.sharedMesh == null || IsLowerLod(skinned.name))
            {
                continue;
            }

            AddPart(root.transform, prefab.transform, skinned.transform, skinned.sharedMesh, skinned.sharedMaterials);
            drawn++;
        }

        if (drawn > 0)
        {
            return root;
        }

        UnityEngine.Object.DestroyImmediate(root);
        return null;
    }

    // LODGroup.GetLODs is not exposed by the interop assemblies, so lower detail levels are recognised by name.
    private static bool IsLowerLod(string name) => name.Contains("LOD", StringComparison.OrdinalIgnoreCase)
        && !name.Contains("LOD0", StringComparison.OrdinalIgnoreCase);

    private static void AddPart(Transform proxyRoot, Transform prefabRoot, Transform source, Mesh mesh, Material[] materials)
    {
        var part = new GameObject("Part");
        part.layer = Layer;
        part.transform.SetParent(proxyRoot, false);
        part.transform.localPosition = prefabRoot.InverseTransformPoint(source.position);
        part.transform.localRotation = Quaternion.Inverse(prefabRoot.rotation) * source.rotation;
        part.transform.localScale = source.lossyScale;
        part.AddComponent<MeshFilter>().sharedMesh = mesh;
        part.AddComponent<MeshRenderer>().sharedMaterials = materials;
    }

    private static Bounds ProxyBounds(GameObject proxy)
    {
        var renderers = proxy.GetComponentsInChildren<Renderer>();
        var bounds = renderers[0].bounds;
        foreach (var renderer in renderers)
        {
            bounds.Encapsulate(renderer.bounds);
        }

        return bounds;
    }

    private static Texture2D Capture(GameObject rig, Bounds bounds)
    {
        var lightObject = new GameObject("Light");
        lightObject.transform.SetParent(rig.transform, false);
        lightObject.transform.rotation = Quaternion.Euler(50f, -30f, 0f);
        var light = lightObject.AddComponent<Light>();
        light.type = LightType.Directional;
        light.cullingMask = 1 << Layer;
        light.intensity = 1.1f;

        var cameraObject = new GameObject("Camera");
        cameraObject.transform.SetParent(rig.transform, false);
        var camera = cameraObject.AddComponent<Camera>();
        camera.enabled = false;
        camera.cullingMask = 1 << Layer;
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = new Color(0f, 0f, 0f, 0f);
        camera.fieldOfView = 30f;
        var radius = bounds.extents.magnitude;
        var distance = radius / Mathf.Sin(camera.fieldOfView * 0.5f * Mathf.Deg2Rad) * 1.05f;
        camera.nearClipPlane = Mathf.Max(0.01f, distance - radius * 1.5f);
        camera.farClipPlane = distance + radius * 2f;
        cameraObject.transform.position = bounds.center + ViewDirection * distance;
        cameraObject.transform.LookAt(bounds.center);

        var target = RenderTexture.GetTemporary(Size, Size, 24, RenderTextureFormat.ARGB32);
        var previous = RenderTexture.active;
        try
        {
            camera.targetTexture = target;
            camera.Render();
            RenderTexture.active = target;
            var texture = new Texture2D(Size, Size, TextureFormat.RGBA32, false);
            texture.ReadPixels(new Rect(0, 0, Size, Size), 0, 0);
            texture.Apply();
            texture.hideFlags = HideFlags.HideAndDontSave;
            return texture;
        }
        finally
        {
            camera.targetTexture = null;
            RenderTexture.active = previous;
            RenderTexture.ReleaseTemporary(target);
        }
    }
}
