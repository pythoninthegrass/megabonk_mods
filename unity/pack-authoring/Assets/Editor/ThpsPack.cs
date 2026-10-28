using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

// The THPS Warehouse pack: one prefab built from the extracted level mesh and textures.
public static class ThpsPack
{
    const string BundleName = "thps";
    const string PackDirectory = "Assets/Thps";
    const int GroundLayer = 8;
    // The mtl name the extractor gives faces that have no texture.
    const string UntexturedMaterial = "None";
    const string FloorMaterial = "F051E515";
    // The secret room's three window sections: rendered, but left out of the collision mesh so the player flies through them.
    static readonly string[] PassThroughMaterials = { "FA88F30D" };
    // The intact window sections share a material with solid windows elsewhere, so only the faces inside the world bounds below (x, y, z min and max) are opened.
    static readonly string[] PassThroughInRoomMaterials = { "F2184063" };
    static readonly float[] SecretRoomBounds = { 149f, 179f, 15f, 26f, 20f, 32f };
    // The two windows at the top of the starting slope, with the half pipe behind them.
    static readonly float[] StartSlopeWindowBounds = { 80f, 140f, 27f, 38f, -75f, -72f };
    static readonly float[][] OpenedWindowBounds = { SecretRoomBounds, StartSlopeWindowBounds };
    // Roof grid cell width, how far the seal over an open footprint edge sits above the tallest vertex, how low a boundary cell must be to count as open, and how close to the footprint edge a face counts as the wall there, in world units, plus how far the roof edges sit inside the footprint in mesh space so they do not overlap the original outer faces.
    const float RoofCell = 1.5f, RoofMargin = 2f, RoofOpenBelow = 15f, RoofEdgeBand = 1.5f, RoofInset = 0.003f;
    const string RoofMaterial = "Roof";
    static readonly Color DarkRoof = new Color(0.07f, 0.07f, 0.08f);
    const string DefaultWarehouseSource = ".tools/thps1/warehouse";
    const string DefaultMusicSource = "tools/Goldfinger - Superman.mp3";
    // The clip's name in the bundle, which a level's music id names as bundle:thps/Superman.
    const string MusicAssetName = "Superman";

    // The PS1 transparency key in the extracted PNGs; the pack's shader is opaque, so it is baked to a dark glass colour.
    static readonly Color32 TransparencyKey = new Color32(255, 0, 255, 255);
    static readonly Color32 KeyReplacement = new Color32(24, 30, 40, 255);
    // Textures whose keyed pixels stay transparent, drawn with the game's Sprites/Default shader because the toon shader has no usable alpha-clip variant: the ceiling chains and the two crane hook textures.
    static readonly string[] SeeThroughTextures = { "E2BFD876-0.png", "0690EE87-0.png", "1D982D1F-0.png" };

    static readonly Color Concrete = new Color(0.6f, 0.6f, 0.58f);

    // Entry point for -executeMethod; the output directory comes from -packOutput.
    public static void Build()
    {
        var output = PackBuilder.ArgValue("-packOutput");
        Directory.CreateDirectory(PackDirectory);
        var prefabs = new List<string>
        {
            SaveWarehouse(WarehouseSource()),
        };
        var music = SaveMusic(MusicSource());
        if (music != null)
            prefabs.Add(music);
        AssetDatabase.SaveAssets();
        BuildBundle(prefabs, BuildTarget.StandaloneWindows64, Path.Combine(output, "windows"));
        BuildBundle(prefabs, BuildTarget.StandaloneLinux64, Path.Combine(output, "linux"));
    }

    // The directory holding warehouse.obj, warehouse.mtl and the PNGs; -warehouseSource overrides the default.
    static string WarehouseSource()
    {
        var args = Environment.GetCommandLineArgs();
        var i = Array.IndexOf(args, "-warehouseSource");
        return i >= 0 && i + 1 < args.Length ? args[i + 1] : Path.GetFullPath(Path.Combine(Application.dataPath, "../../..", DefaultWarehouseSource));
    }

    // The soundtrack file; -musicSource overrides the default.
    static string MusicSource()
    {
        var args = Environment.GetCommandLineArgs();
        var i = Array.IndexOf(args, "-musicSource");
        return i >= 0 && i + 1 < args.Length ? args[i + 1] : Path.GetFullPath(Path.Combine(Application.dataPath, "../../..", DefaultMusicSource));
    }

    // Imports the soundtrack as a Vorbis clip held compressed in memory; returns null when the file is absent so the pack still builds without it.
    static string SaveMusic(string source)
    {
        if (!File.Exists(source))
        {
            Debug.Log("ThpsPack: no music at " + source + "; building the pack without it.");
            return null;
        }

        var path = PackDirectory + "/" + MusicAssetName + ".mp3";
        File.Copy(source, path, true);
        AssetDatabase.ImportAsset(path);
        var importer = (AudioImporter)AssetImporter.GetAtPath(path);
        importer.defaultSampleSettings = new AudioImporterSampleSettings
        {
            loadType = AudioClipLoadType.CompressedInMemory,
            compressionFormat = AudioCompressionFormat.Vorbis,
            quality = 0.7f,
            sampleRateSetting = AudioSampleRateSetting.PreserveSampleRate,
        };
        importer.SaveAndReimport();
        return path;
    }

    // The extracted level at OBJ scale, centred on its footprint with y = 0 at the floor and y up; the level placement applies the scale.
    static string SaveWarehouse(string source)
    {
        var materials = LoadWarehouseMaterials(source);
        var mesh = ParseWarehouseObj(Path.Combine(source, "warehouse.obj"), materials.Keys.ToList(), out var usedMaterials);
        AssetDatabase.CreateAsset(mesh, PackDirectory + "/Warehouse.asset");
        var root = new GameObject("Warehouse");
        root.AddComponent<MeshFilter>().sharedMesh = mesh;
        root.AddComponent<MeshRenderer>().sharedMaterials = usedMaterials.Select(m => materials[m]).ToArray();
        root.AddComponent<MeshCollider>().sharedMesh = SaveCollisionMesh(mesh, usedMaterials);
        return SavePrefab(root);
    }

    static Mesh SaveCollisionMesh(Mesh mesh, List<string> usedMaterials)
    {
        var collision = new Mesh { name = "WarehouseCollision", vertices = mesh.vertices, uv = mesh.uv };
        var vertices = mesh.vertices;
        var kept = Enumerable.Range(0, usedMaterials.Count).Where(i => !PassThroughMaterials.Contains(usedMaterials[i])).ToList();
        collision.subMeshCount = kept.Count;
        for (var i = 0; i < kept.Count; i++)
        {
            var triangles = mesh.GetTriangles(kept[i]);
            if (PassThroughInRoomMaterials.Contains(usedMaterials[kept[i]]))
                triangles = WithoutTrianglesInOpenedWindows(triangles, vertices);
            collision.SetTriangles(triangles, i);
        }

        collision.RecalculateBounds();
        AssetDatabase.CreateAsset(collision, PackDirectory + "/WarehouseCollision.asset");
        return collision;
    }

    static int[] WithoutTrianglesInOpenedWindows(int[] triangles, Vector3[] vertices)
    {
        var kept = new List<int>();
        for (var i = 0; i < triangles.Length; i += 3)
        {
            var inWindows = Enumerable.Range(i, 3).All(k => InOpenedWindows(vertices[triangles[k]]));
            if (!inWindows)
                kept.AddRange(new[] { triangles[i], triangles[i + 1], triangles[i + 2] });
        }

        return kept.ToArray();
    }

    static bool InOpenedWindows(Vector3 meshPoint)
    {
        var x = meshPoint.x * WarehouseScale + WarehouseWorldX;
        var y = meshPoint.y * WarehouseScale + WarehouseLift;
        var z = meshPoint.z * WarehouseScale + WarehouseWorldZ;
        return OpenedWindowBounds.Any(b => x >= b[0] && x <= b[1] && y >= b[2] && y <= b[3] && z >= b[4] && z <= b[5]);
    }

    // One point-filtered, mipmap-free, repeating Standard material per mtl entry, plus a flat one for untextured faces, keyed by material name.
    static Dictionary<string, Material> LoadWarehouseMaterials(string source)
    {
        var textureDirectory = PackDirectory + "/WarehouseTextures";
        Directory.CreateDirectory(textureDirectory);
        var textureFiles = new Dictionary<string, string>();
        string current = null;
        foreach (var line in File.ReadAllLines(Path.Combine(source, "warehouse.mtl")))
        {
            var parts = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < 2)
                continue;
            if (parts[0] == "newmtl")
                current = parts[1];
            else if (parts[0] == "map_Kd" && current != null)
                textureFiles[current] = parts[1];
        }

        var materials = new Dictionary<string, Material>();
        foreach (var pair in textureFiles)
        {
            var assetPath = textureDirectory + "/" + pair.Value;
            var seeThrough = SeeThroughTextures.Contains(pair.Value);
            File.WriteAllBytes(assetPath, BakeTransparencyKey(File.ReadAllBytes(Path.Combine(source, pair.Value)), seeThrough));
            AssetDatabase.ImportAsset(assetPath);
            var importer = (TextureImporter)AssetImporter.GetAtPath(assetPath);
            importer.filterMode = FilterMode.Point;
            importer.mipmapEnabled = false;
            importer.wrapMode = TextureWrapMode.Repeat;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.textureCompression = TextureImporterCompression.Uncompressed;
            importer.alphaSource = seeThrough ? TextureImporterAlphaSource.FromInput : TextureImporterAlphaSource.None;
            importer.alphaIsTransparency = seeThrough;
            importer.SaveAndReimport();
            var material = new Material(Shader.Find(seeThrough ? "Sprites/Default" : "Standard")) { color = Color.white };
            material.mainTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
            if (!seeThrough)
                material.SetFloat("_Glossiness", 0);
            AssetDatabase.CreateAsset(material, PackDirectory + "/Warehouse_" + pair.Key + ".mat");
            materials[pair.Key] = material;
        }

        materials[UntexturedMaterial] = SaveMaterial("Warehouse_" + UntexturedMaterial, Concrete);
        materials[RoofMaterial] = SaveMaterial("Warehouse_" + RoofMaterial, DarkRoof);
        return materials;
    }

    static byte[] BakeTransparencyKey(byte[] png, bool seeThrough)
    {
        var texture = new Texture2D(2, 2, TextureFormat.RGBA32, false);
        texture.LoadImage(png);
        var pixels = texture.GetPixels32();
        for (var i = 0; i < pixels.Length; i++)
        {
            var p = pixels[i];
            var isKey = p.r == TransparencyKey.r && p.g == TransparencyKey.g && p.b == TransparencyKey.b;
            pixels[i] = isKey ? (seeThrough ? new Color32(0, 0, 0, 0) : KeyReplacement) : new Color32(p.r, p.g, p.b, 255);
        }

        texture.SetPixels32(pixels);
        var baked = texture.EncodeToPNG();
        UnityEngine.Object.DestroyImmediate(texture);
        return baked;
    }

    // Flat patches (minX, maxX, minZ, maxZ in OBJ units) over gaps the extraction left in the floor; they sit just under the floor plane so the surrounding grime decals stay on top.
    static readonly float[][] FloorPatches = { new[] { 0.52f, 0.76f, 2.58f, 3.04f } };
    const float FloorPatchDepth = 0.003f;
    // The floor material's UVs per OBJ unit and offset, fitted to the extracted floor faces so a patch continues the same texture.
    const float FloorUvScaleU = 7.5f, FloorUvOffsetU = -10.91f, FloorUvScaleV = 7.95f, FloorUvOffsetV = -24.07f;

    // Posts under the mesh's rail bars, which the extraction left floating: world (x, z) of each post and the height of the bar's underside, then the post width.
    const float RailPostWidth = 0.5f;
    static readonly Vector3[] RailPosts =
    {
        new Vector3(75, 3.17f, 4), new Vector3(75, 3.17f, 16), new Vector3(75, 3.17f, 28), new Vector3(75, 3.17f, 40), new Vector3(75, 3.17f, 52), new Vector3(78.3f, 3.17f, 56.8f), new Vector3(81.4f, 3.17f, 60.5f),
        new Vector3(175.66f, 8.31f, 49.1f), new Vector3(175.66f, 8.31f, 61.3f), new Vector3(175.66f, 8.31f, 73.45f),
    };
    // Small plates the extraction left floating where the posts should be, as world bounds (x, y, z min and max) on the rail material.
    const string RailMaterial = "A53322CF";
    static readonly float[][] RailLeftoverBounds = { new[] { 74.9f, 82f, 1.4f, 1.95f, 3f, 61f }, new[] { 175.5f, 176.3f, 5.6f, 6.2f, 48f, 74.5f } };
    // The Warehouse is placed at this world centre, lift and scale, which turns a world position into mesh space.
    const float WarehouseWorldX = 100f, WarehouseWorldZ = 0f, WarehouseLift = 0.5f, WarehouseScale = 79.2f;

    // Reads v, vt and f lines. The extracted y runs down, so y is negated and every triangle is rewound to keep its front face; quads are split into two triangles.
    static Mesh ParseWarehouseObj(string path, List<string> knownMaterials, out List<string> usedMaterials)
    {
        var positions = new List<Vector3>();
        var uvs = new List<Vector2>();
        var vertices = new List<Vector3>();
        var vertexUvs = new List<Vector2>();
        var trianglesByMaterial = new Dictionary<string, List<int>>();
        var faces = new List<int[]>();
        string material = null;
        foreach (var line in File.ReadLines(path))
        {
            var parts = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length == 0)
                continue;
            switch (parts[0])
            {
                case "v":
                    positions.Add(new Vector3(Parse(parts[1]), -Parse(parts[2]), Parse(parts[3])));
                    break;
                case "vt":
                    uvs.Add(new Vector2(Parse(parts[1]), Parse(parts[2])));
                    break;
                case "usemtl":
                    material = parts[1];
                    break;
                case "f":
                    if (material == null || !knownMaterials.Contains(material))
                        throw new Exception("face without a known material in " + path);
                    if (!trianglesByMaterial.TryGetValue(material, out var triangles))
                        trianglesByMaterial[material] = triangles = new List<int>();
                    var corners = new List<int>();
                    foreach (var token in parts.Skip(1))
                    {
                        var indices = token.Split('/');
                        corners.Add(vertices.Count);
                        vertices.Add(positions[int.Parse(indices[0], CultureInfo.InvariantCulture) - 1]);
                        vertexUvs.Add(indices[1].Length == 0 ? Vector2.zero : uvs[int.Parse(indices[1], CultureInfo.InvariantCulture) - 1]);
                    }

                    for (var i = 1; i < corners.Count - 1; i++)
                        triangles.AddRange(new[] { corners[0], corners[i + 1], corners[i] });
                    faces.Add(corners.ToArray());
                    break;
            }
        }

        SeparateCoplanarFaces(vertices, faces);
        AddFloorPatches(vertices, vertexUvs, trianglesByMaterial);
        var bounds = new Bounds(positions[0], Vector3.zero);
        foreach (var p in positions)
            bounds.Encapsulate(p);
        var origin = new Vector3(bounds.center.x, 0, bounds.center.z);
        for (var i = 0; i < vertices.Count; i++)
            vertices[i] -= origin;

        RemoveRailLeftovers(vertices, trianglesByMaterial);
        AddRailPosts(vertices, vertexUvs, trianglesByMaterial);
        AddRoof(vertices, vertexUvs, trianglesByMaterial, bounds.min.x - origin.x, bounds.max.x - origin.x, bounds.min.z - origin.z, bounds.max.z - origin.z);
        usedMaterials = trianglesByMaterial.Keys.OrderBy(k => k, StringComparer.Ordinal).ToList();
        var mesh = new Mesh { name = "Warehouse", vertices = vertices.ToArray(), uv = vertexUvs.ToArray(), subMeshCount = usedMaterials.Count };
        for (var i = 0; i < usedMaterials.Count; i++)
            mesh.SetTriangles(trianglesByMaterial[usedMaterials[i]], i);
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();
        return mesh;
    }

    // Lifts the top face of each coplanar overlap (posters over walls, stacked planks) so the depth buffer no longer ties.
    static void SeparateCoplanarFaces(List<Vector3> vertices, List<int[]> faces)
    {
        var points = vertices.Select(v => new System.Numerics.Vector3(v.x, v.y, v.z)).ToList();
        CoplanarLayering.Separate(points, faces);
        for (var i = 0; i < vertices.Count; i++)
            vertices[i] = new Vector3(points[i].X, points[i].Y, points[i].Z);
    }

    static void AddFloorPatches(List<Vector3> vertices, List<Vector2> vertexUvs, Dictionary<string, List<int>> trianglesByMaterial)
    {
        if (!trianglesByMaterial.TryGetValue(FloorMaterial, out var triangles))
            trianglesByMaterial[FloorMaterial] = triangles = new List<int>();
        foreach (var patch in FloorPatches)
        {
            var first = vertices.Count;
            foreach (var corner in new[] { (patch[0], patch[2]), (patch[0], patch[3]), (patch[1], patch[3]), (patch[1], patch[2]) })
            {
                vertices.Add(new Vector3(corner.Item1, -FloorPatchDepth, corner.Item2));
                vertexUvs.Add(new Vector2(corner.Item1 * FloorUvScaleU + FloorUvOffsetU, corner.Item2 * FloorUvScaleV + FloorUvOffsetV));
            }

            triangles.AddRange(new[] { first, first + 1, first + 2, first, first + 2, first + 3 });
        }
    }

    // Closes the shell with a dark roof that rides the tops of the walls: per grid cell, the lowest height over which a player could clear every wall around it (never below the surface there), with step faces between heights and a skirt on every edge from the wall-top line up to it, so nothing can float above a wall and no gap is left between the walls and the roof.
    static void AddRoof(List<Vector3> vertices, List<Vector2> vertexUvs, Dictionary<string, List<int>> trianglesByMaterial, float minX, float maxX, float minZ, float maxZ)
    {
        var standing = new List<System.Numerics.Vector3[]>();
        foreach (var triangles in trianglesByMaterial.Values)
            for (var i = 0; i < triangles.Count; i += 3)
                standing.Add(Enumerable.Range(i, 3).Select(k => new System.Numerics.Vector3(vertices[triangles[k]].x, vertices[triangles[k]].y, vertices[triangles[k]].z)).ToArray());
        var sealY = standing.SelectMany(t => t).Max(p => p.Y) + RoofMargin / WarehouseScale;
        var cell = RoofCell / WarehouseScale;
        int cellsX = Mathf.CeilToInt((maxX - minX) / cell), cellsZ = Mathf.CeilToInt((maxZ - minZ) / cell);
        var tops = WarehouseRoof.ColumnTops(standing, minX, minZ, cell, cellsX, cellsZ);
        var ceiling = WarehouseRoof.SpillLevels(tops, RoofOpenBelow / WarehouseScale, sealY);
        var band = RoofEdgeBand / WarehouseScale;
        var profiles = new[]
        {
            WarehouseRoof.EdgeWallProfile(standing, WarehouseRoof.Side.West, minZ, maxZ, minX, band, 0),
            WarehouseRoof.EdgeWallProfile(standing, WarehouseRoof.Side.East, minZ, maxZ, maxX, band, 0),
            WarehouseRoof.EdgeWallProfile(standing, WarehouseRoof.Side.South, minX, maxX, minZ, band, 0),
            WarehouseRoof.EdgeWallProfile(standing, WarehouseRoof.Side.North, minX, maxX, maxZ, band, 0),
        };
        if (!trianglesByMaterial.TryGetValue(RoofMaterial, out var roofTriangles))
            trianglesByMaterial[RoofMaterial] = roofTriangles = new List<int>();
        foreach (var quad in WarehouseRoof.Quads(ceiling, minX, minZ, maxX, maxZ, cell, RoofInset, profiles))
        {
            var first = vertices.Count;
            foreach (var corner in quad)
            {
                vertices.Add(new Vector3(corner.X, corner.Y, corner.Z));
                vertexUvs.Add(Vector2.zero);
            }

            roofTriangles.AddRange(new[] { first, first + 1, first + 2, first, first + 2, first + 3 });
        }

        if (vertices.Count > 65000)
            throw new Exception("the Warehouse mesh has " + vertices.Count + " vertices; a Unity mesh holds 65535 with 16-bit indices, so use a larger RoofCell");
    }

    static void RemoveRailLeftovers(List<Vector3> vertices, Dictionary<string, List<int>> trianglesByMaterial)
    {
        if (!trianglesByMaterial.TryGetValue(RailMaterial, out var triangles))
            return;
        var kept = new List<int>();
        for (var i = 0; i < triangles.Count; i += 3)
        {
            if (!Enumerable.Range(i, 3).All(k => InRailLeftovers(vertices[triangles[k]])))
                kept.AddRange(new[] { triangles[i], triangles[i + 1], triangles[i + 2] });
        }

        trianglesByMaterial[RailMaterial] = kept;
    }

    static bool InRailLeftovers(Vector3 meshPoint)
    {
        var x = meshPoint.x * WarehouseScale + WarehouseWorldX;
        var y = meshPoint.y * WarehouseScale + WarehouseLift;
        var z = meshPoint.z * WarehouseScale + WarehouseWorldZ;
        return RailLeftoverBounds.Any(b => x >= b[0] && x <= b[1] && y >= b[2] && y <= b[3] && z >= b[4] && z <= b[5]);
    }

    static void AddRailPosts(List<Vector3> vertices, List<Vector2> vertexUvs, Dictionary<string, List<int>> trianglesByMaterial)
    {
        if (!trianglesByMaterial.TryGetValue(UntexturedMaterial, out var triangles))
            trianglesByMaterial[UntexturedMaterial] = triangles = new List<int>();
        var half = RailPostWidth / 2 / WarehouseScale;
        foreach (var post in RailPosts)
        {
            var top = (post.y - WarehouseLift) / WarehouseScale;
            var x = (post.x - WarehouseWorldX) / WarehouseScale;
            var z = (post.z - WarehouseWorldZ) / WarehouseScale;
            var first = vertices.Count;
            foreach (var corner in new[]
            {
                new Vector3(x - half, 0, z - half), new Vector3(x + half, 0, z - half), new Vector3(x + half, top, z - half), new Vector3(x - half, top, z - half),
                new Vector3(x - half, 0, z + half), new Vector3(x + half, 0, z + half), new Vector3(x + half, top, z + half), new Vector3(x - half, top, z + half),
            })
            {
                vertices.Add(corner);
                vertexUvs.Add(Vector2.zero);
            }

            // Corner indices of each side face, clockwise seen from outside, then the top.
            foreach (var face in new[] { new[] { 0, 3, 2, 1 }, new[] { 5, 6, 7, 4 }, new[] { 4, 7, 3, 0 }, new[] { 1, 2, 6, 5 }, new[] { 3, 7, 6, 2 } })
                triangles.AddRange(new[] { first + face[0], first + face[1], first + face[2], first + face[0], first + face[2], first + face[3] });
        }
    }

    static float Parse(string value) => float.Parse(value, CultureInfo.InvariantCulture);

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
        UnityEngine.Object.DestroyImmediate(root);
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
