using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

// Procedural THPS Warehouse structures. Every prefab is authored at unit size with its origin at the bottom centre of the footprint, so a level placement scales it to width (x), height (y) and depth (z).
public static class ThpsPack
{
    const string BundleName = "thps";
    const string PackDirectory = "Assets/Thps";
    const int GroundLayer = 8;
    const int ProfileSegments = 20;

    // Fraction of a quarter pipe's run that is the curved transition; the rest is a straight slope. Mirrors QUARTER_PIPE_TRANSITION in scripts/build_thps_level.py.
    const float TransitionFraction = 0.4f;

    static readonly Color Plywood = new Color(0.72f, 0.5f, 0.28f);
    static readonly Color LightPlywood = new Color(0.8f, 0.62f, 0.38f);
    static readonly Color Concrete = new Color(0.6f, 0.6f, 0.58f);
    static readonly Color TaxiYellow = new Color(0.95f, 0.8f, 0.1f);
    static readonly Color Glass = new Color(0.12f, 0.15f, 0.2f);
    static readonly Color PaleWood = new Color(0.75f, 0.62f, 0.45f);

    // Entry point for -executeMethod; the output directory comes from -packOutput.
    public static void Build()
    {
        var output = PackBuilder.ArgValue("-packOutput");
        Directory.CreateDirectory(PackDirectory);
        var prefabs = new List<string>
        {
            SaveMeshPrefab("QuarterPipe", ExtrudeProfile(QuarterPipeProfile()), Plywood),
            SaveMeshPrefab("Kicker", ExtrudeProfile(new List<Vector2> { new Vector2(-0.5f, 0), new Vector2(0.5f, 1) }), LightPlywood),
            SaveMeshPrefab("Block", ExtrudeProfile(new List<Vector2> { new Vector2(-0.5f, 1), new Vector2(0.5f, 1) }), Concrete),
            SaveTaxi(),
            SaveCorridor(),
        };
        AssetDatabase.SaveAssets();
        BuildBundle(prefabs, BuildTarget.StandaloneWindows64, Path.Combine(output, "windows"));
        BuildBundle(prefabs, BuildTarget.StandaloneLinux64, Path.Combine(output, "linux"));
    }

    // (z, y) points rising toward +z: a curved transition that eases into a straight slope, normalised to a rise of 1.
    static List<Vector2> QuarterPipeProfile()
    {
        var rise = 1 - TransitionFraction / 2;
        var points = new List<Vector2>();
        for (var i = 0; i <= ProfileSegments; i++)
        {
            var t = (float)i / ProfileSegments;
            var y = t < TransitionFraction ? t * t / (2 * TransitionFraction) : t - TransitionFraction / 2;
            points.Add(new Vector2(t - 0.5f, y / rise));
        }

        return points;
    }

    // Closed solid under a (z, y) profile, extruded over x in [-0.5, 0.5]; the base is y = 0.
    static Mesh ExtrudeProfile(List<Vector2> profile)
    {
        var vertices = new List<Vector3>();
        var triangles = new List<int>();
        foreach (var p in profile)
        {
            vertices.Add(new Vector3(-0.5f, p.y, p.x));
            vertices.Add(new Vector3(0.5f, p.y, p.x));
        }

        for (var i = 0; i < profile.Count - 1; i++)
        {
            var a = i * 2;
            AddQuad(vertices, triangles, a, a + 1, a + 3, a + 2, Vector3.up);
        }

        var first = profile[0];
        var last = profile[profile.Count - 1];
        AddFlatQuad(vertices, triangles, new Vector3(-0.5f, 0, first.x), new Vector3(0.5f, 0, first.x), new Vector3(0.5f, 0, last.x), new Vector3(-0.5f, 0, last.x), Vector3.down);
        AddFlatQuad(vertices, triangles, new Vector3(-0.5f, 0, last.x), new Vector3(0.5f, 0, last.x), new Vector3(0.5f, last.y, last.x), new Vector3(-0.5f, last.y, last.x), Vector3.forward);
        if (first.y > 0)
            AddFlatQuad(vertices, triangles, new Vector3(-0.5f, 0, first.x), new Vector3(0.5f, 0, first.x), new Vector3(0.5f, first.y, first.x), new Vector3(-0.5f, first.y, first.x), Vector3.back);

        foreach (var side in new[] { -0.5f, 0.5f })
        {
            var outward = side < 0 ? Vector3.left : Vector3.right;
            for (var i = 0; i < profile.Count - 1; i++)
            {
                AddFlatQuad(
                    vertices,
                    triangles,
                    new Vector3(side, 0, profile[i].x),
                    new Vector3(side, 0, profile[i + 1].x),
                    new Vector3(side, profile[i + 1].y, profile[i + 1].x),
                    new Vector3(side, profile[i].y, profile[i].x),
                    outward);
            }
        }

        var mesh = new Mesh { vertices = vertices.ToArray(), triangles = triangles.ToArray() };
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();
        return mesh;
    }

    static void AddFlatQuad(List<Vector3> vertices, List<int> triangles, Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 outward)
    {
        var start = vertices.Count;
        vertices.AddRange(new[] { a, b, c, d });
        AddQuad(vertices, triangles, start, start + 1, start + 2, start + 3, outward);
    }

    // Winds the quad clockwise as seen from the side `outward` points to, which Unity treats as the front face.
    static void AddQuad(List<Vector3> vertices, List<int> triangles, int a, int b, int c, int d, Vector3 outward)
    {
        var normal = Vector3.Cross(vertices[b] - vertices[a], vertices[c] - vertices[a]);
        if (Vector3.Dot(normal, outward) < 0)
            (b, d) = (d, b);
        triangles.AddRange(new[] { a, b, c, a, c, d });
    }

    static string SaveMeshPrefab(string name, Mesh mesh, Color color)
    {
        AssetDatabase.CreateAsset(mesh, PackDirectory + "/" + name + ".asset");
        var root = new GameObject(name);
        root.AddComponent<MeshFilter>().sharedMesh = mesh;
        root.AddComponent<MeshRenderer>().sharedMaterial = SaveMaterial(name, color);
        root.AddComponent<MeshCollider>().sharedMesh = mesh;
        return SavePrefab(root);
    }

    // A yellow hull with a cabin on top, all box colliders; the dark window band has no collider.
    static string SaveTaxi()
    {
        var yellow = SaveMaterial("Taxi", TaxiYellow);
        var glass = SaveMaterial("TaxiGlass", Glass);
        var root = new GameObject("Taxi");
        AddBox(root, "Body", new Vector3(0, 0.275f, 0), new Vector3(1, 0.55f, 1), yellow, true);
        AddBox(root, "Cabin", new Vector3(0, 0.775f, -0.05f), new Vector3(0.8f, 0.45f, 0.5f), yellow, true);
        AddBox(root, "Windows", new Vector3(0, 0.82f, -0.05f), new Vector3(0.82f, 0.2f, 0.52f), glass, false);
        return SavePrefab(root);
    }

    // A box room with a walkable floor, side walls and a roof; both ends are open.
    static string SaveCorridor()
    {
        var wood = SaveMaterial("Corridor", PaleWood);
        var root = new GameObject("Corridor");
        AddBox(root, "Floor", new Vector3(0, 0.04f, 0), new Vector3(1, 0.08f, 1), wood, true);
        AddBox(root, "Roof", new Vector3(0, 0.96f, 0), new Vector3(1, 0.08f, 1), wood, true);
        AddBox(root, "WallWest", new Vector3(-0.48f, 0.5f, 0), new Vector3(0.04f, 1, 1), wood, true);
        AddBox(root, "WallEast", new Vector3(0.48f, 0.5f, 0), new Vector3(0.04f, 1, 1), wood, true);
        return SavePrefab(root);
    }

    static void AddBox(GameObject root, string name, Vector3 position, Vector3 scale, Material material, bool solid)
    {
        var part = GameObject.CreatePrimitive(PrimitiveType.Cube);
        part.name = name;
        part.transform.SetParent(root.transform, false);
        part.transform.localPosition = position;
        part.transform.localScale = scale;
        part.GetComponent<Renderer>().sharedMaterial = material;
        if (!solid)
            Object.DestroyImmediate(part.GetComponent<Collider>());
    }

    static Material SaveMaterial(string name, Color color)
    {
        var material = new Material(Shader.Find("Standard")) { color = color };
        AssetDatabase.CreateAsset(material, PackDirectory + "/" + name + ".mat");
        return material;
    }

    // Puts the prefab on the layer the player grounds against, the same as the tile ground.
    static string SavePrefab(GameObject root)
    {
        foreach (var t in root.GetComponentsInChildren<Transform>(true))
            t.gameObject.layer = GroundLayer;

        var path = PackDirectory + "/" + root.name + ".prefab";
        PrefabUtility.SaveAsPrefabAsset(root, path);
        Object.DestroyImmediate(root);
        return path;
    }

    static void BuildBundle(List<string> prefabPaths, BuildTarget target, string directory)
    {
        Directory.CreateDirectory(directory);
        var builds = new[] { new AssetBundleBuild { assetBundleName = BundleName, assetNames = prefabPaths.ToArray() } };
        var manifest = BuildPipeline.BuildAssetBundles(directory, builds, BuildAssetBundleOptions.ChunkBasedCompression, target);
        if (manifest == null)
            throw new System.Exception("BuildAssetBundles failed for " + target);
        Debug.Log("ThpsPack: built " + target + " into " + directory);
    }
}
