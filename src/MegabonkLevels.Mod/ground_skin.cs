using System.Collections.Generic;
using System.Linq;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Draws a ground tile with a biome's terrain material where the level's ground zones say so; cliff and fill pieces keep their own look.
public static class GroundSkin
{
    private const string GroundMaterialPrefix = "m_topGrass";
    private static readonly HashSet<string> s_missing = new();
    private static Dictionary<string, Material> s_materials;
    private static readonly List<Mesh> s_generatedSurfaces = new();
    private static Mesh s_nativeLava;
    private static Vector3Data[] s_nativeVertices;

    public static void ClearSurfaces()
    {
        foreach (var mesh in s_generatedSurfaces)
            if (mesh != null) UnityEngine.Object.Destroy(mesh);
        s_generatedSurfaces.Clear();
    }

    public static void Apply(GameObject tile, int x, int z, IReadOnlyList<GroundZone> zones, MelonLogger.Instance logger)
    {
        var name = GroundZones.MaterialAt(zones, x, z);
        if (name == null) return;
        var material = Find(name);
        if (material == null)
        {
            if (s_missing.Add(name)) logger.Warning($"GroundSkin: no material named '{name}'; ground zone left as it was");
            return;
        }

        foreach (var renderer in tile.GetComponentsInChildren<MeshRenderer>(true))
        {
            var current = renderer.sharedMaterial;
            if (current == null || !current.name.StartsWith(GroundMaterialPrefix)) continue;
            if (name == "LavaCrypt" && !ApplyNativeLava(renderer, logger) && s_missing.Add("native:LavaCrypt"))
                logger.Warning("GroundSkin: no readable native Graveyard lava surface found; using material-only lava");
            renderer.sharedMaterial = material;
        }
    }

    private static bool ApplyNativeLava(MeshRenderer target, MelonLogger.Instance logger)
    {
        var targetFilter = target.GetComponent<MeshFilter>();
        if (targetFilter == null) return false;
        if (s_nativeLava == null)
        {
            var candidates = Resources.FindObjectsOfTypeAll<MeshRenderer>()
                .Where(r => r != null && r.sharedMaterial != null && r.sharedMaterial.name == "LavaCrypt")
                .Select(r => r.GetComponent<MeshFilter>()).Where(f => f != null && f.sharedMesh != null)
                .OrderBy(f => f.sharedMesh.name, System.StringComparer.Ordinal);
            foreach (var source in candidates)
            {
                var mesh = source.sharedMesh;
                if (!mesh.name.StartsWith("pb_Mesh") || !mesh.isReadable || mesh.vertexCount > 6 || mesh.triangles.Length != 6) continue;
                var uv = mesh.uv;
                if (uv.Length != mesh.vertexCount || uv.Any(v => !float.IsFinite(v.x) || !float.IsFinite(v.y))) continue;
                var vertices = mesh.vertices.Select(v => source.transform.TransformPoint(v)).Select(v => new Vector3Data(v.x, v.y, v.z)).ToArray();
                if (!NativeLavaGeometry.CanFit(vertices)) continue;
                s_nativeLava = mesh;
                s_nativeVertices = vertices;
                logger.Msg($"GroundSkin: native Graveyard lava mesh={mesh.name} vertices={mesh.vertexCount} uv={uv.Length}");
                break;
            }
        }
        if (s_nativeLava == null) return false;
        var bounds = target.bounds;
        var fitted = NativeLavaGeometry.Fit(s_nativeVertices,
            new Vector3Data(bounds.center.x, bounds.center.y + 0.02f, bounds.center.z), bounds.size.x, bounds.size.z);
        var surface = UnityEngine.Object.Instantiate(s_nativeLava);
        surface.name = "NativeGraveyardLavaSurface";
        surface.vertices = fitted.Select(v => target.transform.InverseTransformPoint(new Vector3(v.X, v.Y, v.Z))).ToArray();
        surface.triangles = NativeLavaGeometry.FaceUp(fitted, s_nativeLava.triangles.ToArray()).ToArray();
        surface.RecalculateBounds();
        surface.RecalculateNormals();
        logger.Msg($"GroundSkin: lava surface normal={surface.normals[0].ToString("F3")}");
        targetFilter.sharedMesh = surface;
        s_generatedSurfaces.Add(surface);
        return true;
    }

    private static Material Find(string name)
    {
        if (s_materials == null || !s_materials.TryGetValue(name, out var cached) || cached == null)
        {
            s_materials = new Dictionary<string, Material>();
            foreach (var material in Resources.FindObjectsOfTypeAll<Material>())
            {
                if (material != null && !s_materials.ContainsKey(material.name)) s_materials[material.name] = material;
            }
        }

        return s_materials.TryGetValue(name, out var found) ? found : null;
    }
}
