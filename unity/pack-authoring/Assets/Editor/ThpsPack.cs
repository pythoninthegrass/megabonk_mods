using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEditorInternal;
using UnityEngine;

// The THPS Warehouse pack: the one-piece Warehouse prefab, one prefab per construction piece, and the soundtrack, all built from the extracted level mesh and textures.
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
    const string DefaultMusicSource = "tools/ost";
    const string DefaultPiecesDoc = "docs/thps-warehouse-pieces.md";
    const string PacksSourceDirectory = "unity/pack-authoring/packs/thps";

    // The PS1 transparency key in the extracted PNGs; the pack's shader is opaque, so it is baked to a dark glass colour.
    static readonly Color32 TransparencyKey = new Color32(255, 0, 255, 255);
    static readonly Color32 KeyReplacement = new Color32(24, 30, 40, 255);
    // Textures whose keyed pixels stay transparent, drawn with the game's Sprites/Default shader because the toon shader has no usable alpha-clip variant: every keyed texture.
    static readonly string[] SeeThroughTextures = { "E2BFD876-0.png", "0690EE87-0.png", "1D982D1F-0.png", "053C2AA4-0.png", "0871F61A-0.png", "0DFA7C5E-0.png", "1723B29C-0.png", "1DEE7C12-0.png", "1EE84107-0.png", "221C0004-0.png", "2BB60043-0.png", "3738824A-0.png", "5324F69B-0.png", "5C18D016-0.png", "6909A8C5-0.png", "7A0957EC-0.png", "7F6B8FF9-0.png", "7F9ACEA9-0.png", "946164AD-0.png", "DF12C866-0.png", "F2184063-0.png", "FA88F30D-0.png" };

    static readonly Color Concrete = new Color(0.6f, 0.6f, 0.58f);

    // Entry point for -executeMethod; the output directory comes from -packOutput.
    public static void Build()
    {
        var output = PackBuilder.ArgValue("-packOutput");
        AssetDatabase.DeleteAsset(PackDirectory);
        Directory.CreateDirectory(PackDirectory);
        var (prefabs, assetNames, records) = BuildWarehouseAndPieces();
        WriteManifest(assetNames);
        WritePiecesJson(records);
        prefabs.AddRange(SaveSoundtrack(MusicSource()));
        AssetDatabase.SaveAssets();
        BuildBundle(prefabs, BuildTarget.StandaloneWindows64, Path.Combine(output, "windows"));
        BuildBundle(prefabs, BuildTarget.StandaloneLinux64, Path.Combine(output, "linux"));
    }

    // The merged Warehouse prefab first (byte-identical to the shipped one), then one prefab per inventory piece and per pack-added piece; assetNames is the manifest and bundle order.
    static (List<string> Prefabs, List<string> AssetNames, List<PieceRecord> Records) BuildWarehouseAndPieces()
    {
        KitMeshes.Clear();
        var source = WarehouseSource();
        var materials = LoadWarehouseMaterials(source);
        var mesh = ParseWarehouseObj(Path.Combine(source, "warehouse.obj"), materials.Keys.ToList(), out var usedMaterials, out var vertices, out var vertexUvs, out var faces, out var floorPatches, out var posts, out var roofQuads);
        mesh = SaveAsset(mesh, PackDirectory + "/Warehouse.asset");
        var root = new GameObject("Warehouse");
        root.AddComponent<MeshFilter>().sharedMesh = mesh;
        root.AddComponent<MeshRenderer>().sharedMaterials = usedMaterials.Select(m => materials[m]).ToArray();
        root.AddComponent<MeshCollider>().sharedMesh = SaveCollisionMesh(mesh, usedMaterials);
        var prefabs = new List<string> { SavePrefab(root) };
        var assetNames = new List<string> { "Warehouse" };
        var records = new List<PieceRecord>();

        var inventory = WarehousePieces.ParseInventory(File.ReadAllText(PiecesDoc()));
        var coverage = WarehousePieces.CoverageErrors(inventory, faces.Count);
        if (coverage.Count > 0)
            throw new Exception("the piece inventory does not partition the source: " + string.Join("; ", coverage.Take(10)));
        var faceByOrdinal = faces.ToDictionary(face => face.Ordinal);
        foreach (var piece in inventory)
        {
            var groups = piece.Module == "sign"
                ? WarehouseKit.ConnectedFaces(piece.Faces.Select(n => faceByOrdinal[n].Corners.Select(index => new System.Numerics.Vector3(vertices[index].x, vertices[index].y, vertices[index].z)).ToArray()).ToArray())
                : new List<int[]> { Enumerable.Range(0, piece.Faces.Length).ToArray() };
            for (var component = 0; component < groups.Count; component++)
            {
                var asset = piece.Id + (component == 0 ? "" : "-copy-" + component);
                var ordinals = groups[component].Select(n => piece.Faces[n]).ToArray();
                var build = new PieceBuild(asset, piece.Module);
                foreach (var ordinal in ordinals) build.AddFace(faceByOrdinal[ordinal], vertices, vertexUvs);
                prefabs.Add(SavePiece(build, materials));
                records.Add(new PieceRecord
                {
                    Asset = asset, SourceId = piece.Id, CatalogAsset = LastCatalogAsset, Kind = "source", Module = piece.Module,
                    Groups = piece.Groups, Faces = ordinals, Placement = LastPlacement, Collider = LastHadCollider,
                    Rotation = LastRotation, Scale = LastScale,
                });
            }
        }

        for (var i = 0; i < floorPatches.Count; i++)
            prefabs.Add(SaveAdded(floorPatches[i], vertices, "added-floor-patch-" + i, "floor", "FloorPatches[" + i + "]", materials, assetNames, records));
        for (var i = 0; i < posts.Count; i++)
            prefabs.Add(SaveAdded(posts[i], vertices, "added-post-" + i, "prop", "RailPosts[" + i + "]", materials, assetNames, records));
        var roofs = WarehouseKit.MergeRoof(roofQuads.Select(q => q.Indices.Select(index => new System.Numerics.Vector3(vertices[index].x, vertices[index].y, vertices[index].z)).ToArray()), 1600f / (WarehouseScale * WarehouseScale));
        var sections = WarehouseKit.RoofSections(roofs, 40f / WarehouseScale);
        for (var i = 0; i < sections.Count; i++)
        {
            var asset = "added-roof-section-" + i.ToString("D3");
            var build = new PieceBuild(asset, "roof-panel");
            foreach (var polygon in sections[i])
            {
                var points = polygon.Select(v => new Vector3(v.X, v.Y, v.Z)).ToArray();
                var triangles = Enumerable.Range(1, points.Length - 2).SelectMany(n => new[] { 0, n, n + 1 }).ToArray();
                build.AddGeometry(RoofMaterial, points, Enumerable.Repeat(Vector2.zero, points.Length).ToArray(), triangles);
            }
            prefabs.Add(SavePiece(build, materials));
            records.Add(new PieceRecord { Asset = asset, CatalogAsset = LastCatalogAsset, Kind = "added", Module = "roof-panel", Source = "WarehouseRoof.Quads", Placement = LastPlacement, Collider = LastHadCollider, Rotation = LastRotation, Scale = LastScale });
        }
        prefabs = prefabs.Where(path => path != null).Distinct(StringComparer.Ordinal).ToList();
        assetNames = prefabs.Select(Path.GetFileNameWithoutExtension).ToList();
        Debug.Log("ThpsPack: " + records.Count + " instances, " + assetNames.Count + " unique assets; " + roofQuads.Count + " roof quads consolidated into " + sections.Count + " sections");
        return (prefabs, assetNames, records);
    }

    static string SaveAdded(AddedGeometry geometry, List<Vector3> vertices, string asset, string module, string origin, Dictionary<string, Material> materials, List<string> assetNames, List<PieceRecord> records)
    {
        var build = new PieceBuild(asset, module);
        build.AddGeometry(geometry.Material, geometry.Indices.Select(index => vertices[index]).ToArray(), geometry.Uvs, geometry.Tris);
        var path = SavePiece(build, materials);
        assetNames.Add(asset);
        records.Add(new PieceRecord { Asset = asset, CatalogAsset = LastCatalogAsset, Kind = "added", Module = module, Source = origin, Placement = LastPlacement, Collider = LastHadCollider, Rotation = LastRotation, Scale = LastScale });
        return path;
    }

    // Repo root paths are resolved from Assets/ so the batch-mode working directory does not matter; -piecesDoc overrides the inventory document.
    static string RepoPath(string relative) => Path.GetFullPath(Path.Combine(Application.dataPath, "../../..", relative));

    static string PiecesDoc()
    {
        var args = Environment.GetCommandLineArgs();
        var i = Array.IndexOf(args, "-piecesDoc");
        return i >= 0 && i + 1 < args.Length ? args[i + 1] : RepoPath(DefaultPiecesDoc);
    }

    // The directory holding warehouse.obj, warehouse.mtl and the PNGs; -warehouseSource overrides the default.
    static string WarehouseSource()
    {
        var args = Environment.GetCommandLineArgs();
        var i = Array.IndexOf(args, "-warehouseSource");
        return i >= 0 && i + 1 < args.Length ? args[i + 1] : Path.GetFullPath(Path.Combine(Application.dataPath, "../../..", DefaultWarehouseSource));
    }

    // The directory of soundtrack mp3s; -musicSource overrides the default.
    static string MusicSource()
    {
        var args = Environment.GetCommandLineArgs();
        var i = Array.IndexOf(args, "-musicSource");
        return i >= 0 && i + 1 < args.Length ? args[i + 1] : Path.GetFullPath(Path.Combine(Application.dataPath, "../../..", DefaultMusicSource));
    }

    // Writes the asset's .meta with a GUID derived from its path before Unity first sees the file, so every machine builds the same bundle; Unity otherwise picks a random GUID per machine.
    static string Pinned(string assetPath)
    {
        using var md5 = MD5.Create();
        var guid = string.Concat(md5.ComputeHash(Encoding.UTF8.GetBytes(assetPath)).Select(b => b.ToString("x2")));
        File.WriteAllText(assetPath + ".meta", "fileFormatVersion: 2\nguid: " + guid + "\n");
        return assetPath;
    }

    // Unity gives a new prefab's objects random file IDs on every save, and the bundle derives its object identities from them; each is renumbered to its class id times 100000 plus its position in the file.
    static void PinFileIds(string path)
    {
        var lines = File.ReadAllLines(path);
        var ids = new Dictionary<string, string>();
        foreach (var line in lines)
        {
            var header = System.Text.RegularExpressions.Regex.Match(line, @"^--- !u!(\d+) &(\d+)");
            if (header.Success)
                ids[header.Groups[2].Value] = (long.Parse(header.Groups[1].Value) * 100000 + ids.Count).ToString();
        }

        var renumbered = lines.Select(line => System.Text.RegularExpressions.Regex.Replace(line, @"(?<=&|fileID: )\d+", match => ids.TryGetValue(match.Value, out var id) ? id : match.Value));
        File.WriteAllText(path, string.Join("\n", renumbered) + "\n");
    }

    // CreateAsset ignores a pre-written .meta and picks its own GUID, so the object is serialized to the path directly and imported under the pinned one, named after the file as CreateAsset names it; the returned reference is the imported asset. A pinned .meta carries no importer settings, so an importer that defaults them badly (a PNG imports as a cubemap) has to set them explicitly.
    static T SaveAsset<T>(T asset, string path) where T : UnityEngine.Object
    {
        Pinned(path);
        asset.name = Path.GetFileNameWithoutExtension(path);
        InternalEditorUtility.SaveToSerializedFileAndForget(new UnityEngine.Object[] { asset }, path, false);
        AssetDatabase.ImportAsset(path);
        return AssetDatabase.LoadAssetAtPath<T>(path);
    }

    // Imports every mp3 in the directory as a Vorbis clip held compressed in memory, named by its file name with each run of other characters made an underscore (04 Superman.mp3 is bundle:thps/04_Superman); empty when the directory is absent so the pack still builds without music.
    static List<string> SaveSoundtrack(string source)
    {
        var saved = new List<string>();
        if (!Directory.Exists(source))
        {
            Debug.Log("ThpsPack: no music directory at " + source + "; building the pack without it.");
            return saved;
        }

        foreach (var file in Directory.GetFiles(source, "*.mp3").OrderBy(f => f, StringComparer.Ordinal))
            saved.Add(SaveClip(file));
        return saved;
    }

    static string SaveClip(string source)
    {
        var name = System.Text.RegularExpressions.Regex.Replace(Path.GetFileNameWithoutExtension(source), "[^A-Za-z0-9]+", "_").Trim('_');
        var path = Pinned(PackDirectory + "/" + name + ".mp3");
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

    // The merged collision mesh: every rendered triangle except the pass-through window faces.
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
        return SaveAsset(collision, PackDirectory + "/WarehouseCollision.asset");
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
            var assetPath = Pinned(textureDirectory + "/" + pair.Value);
            var seeThrough = SeeThroughTextures.Contains(pair.Value);
            File.WriteAllBytes(assetPath, BakeTransparencyKey(File.ReadAllBytes(Path.Combine(source, pair.Value)), seeThrough));
            AssetDatabase.ImportAsset(assetPath);
            var importer = (TextureImporter)AssetImporter.GetAtPath(assetPath);
            importer.textureShape = TextureImporterShape.Texture2D;
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
            materials[pair.Key] = SaveAsset(material, PackDirectory + "/Warehouse_" + pair.Key + ".mat");
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

    // Reads v, vt and f lines. The extracted y runs down, so y is negated and every triangle is rewound to keep its front face; quads are split into two triangles. Faces keep their f-line ordinal so the inventory's face selectors can partition them; the floor patches, posts and roof quads are also returned per piece.
    static Mesh ParseWarehouseObj(string path, List<string> knownMaterials, out List<string> usedMaterials, out List<Vector3> outVertices, out List<Vector2> outUvs, out List<WarehouseFace> outFaces, out List<AddedGeometry> floorPatches, out List<AddedGeometry> posts, out List<AddedGeometry> roofQuads)
    {
        var positions = new List<Vector3>();
        var uvs = new List<Vector2>();
        var vertices = new List<Vector3>();
        var vertexUvs = new List<Vector2>();
        var trianglesByMaterial = new Dictionary<string, List<int>>();
        var faces = new List<WarehouseFace>();
        floorPatches = new List<AddedGeometry>();
        posts = new List<AddedGeometry>();
        roofQuads = new List<AddedGeometry>();
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
                    faces.Add(new WarehouseFace(faces.Count + 1, material, corners.ToArray()));
                    break;
            }
        }

        SeparateCoplanarFaces(vertices, faces.Select(face => face.Corners).ToList());
        AddFloorPatches(vertices, vertexUvs, trianglesByMaterial, floorPatches);
        var bounds = new Bounds(positions[0], Vector3.zero);
        foreach (var p in positions)
            bounds.Encapsulate(p);
        var origin = new Vector3(bounds.center.x, 0, bounds.center.z);
        for (var i = 0; i < vertices.Count; i++)
            vertices[i] -= origin;

        RemoveRailLeftovers(vertices, trianglesByMaterial);
        AddRailPosts(vertices, vertexUvs, trianglesByMaterial, posts);
        AddRoof(vertices, vertexUvs, trianglesByMaterial, bounds.min.x - origin.x, bounds.max.x - origin.x, bounds.min.z - origin.z, bounds.max.z - origin.z, roofQuads);
        usedMaterials = trianglesByMaterial.Keys.OrderBy(k => k, StringComparer.Ordinal).ToList();
        var mesh = new Mesh { name = "Warehouse", vertices = vertices.ToArray(), uv = vertexUvs.ToArray(), subMeshCount = usedMaterials.Count };
        for (var i = 0; i < usedMaterials.Count; i++)
            mesh.SetTriangles(trianglesByMaterial[usedMaterials[i]], i);
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();
        outVertices = vertices;
        outUvs = vertexUvs;
        outFaces = faces;
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

    static void AddFloorPatches(List<Vector3> vertices, List<Vector2> vertexUvs, Dictionary<string, List<int>> trianglesByMaterial, List<AddedGeometry> added)
    {
        if (!trianglesByMaterial.TryGetValue(FloorMaterial, out var triangles))
            trianglesByMaterial[FloorMaterial] = triangles = new List<int>();
        foreach (var patch in FloorPatches)
        {
            var first = vertices.Count;
            var uvs = new List<Vector2>();
            foreach (var corner in new[] { (patch[0], patch[2]), (patch[0], patch[3]), (patch[1], patch[3]), (patch[1], patch[2]) })
            {
                vertices.Add(new Vector3(corner.Item1, -FloorPatchDepth, corner.Item2));
                var uv = new Vector2(corner.Item1 * FloorUvScaleU + FloorUvOffsetU, corner.Item2 * FloorUvScaleV + FloorUvOffsetV);
                vertexUvs.Add(uv);
                uvs.Add(uv);
            }

            var patchTriangles = new[] { 0, 1, 2, 0, 2, 3 };
            triangles.AddRange(patchTriangles.Select(index => first + index));
            added.Add(new AddedGeometry { Material = FloorMaterial, Indices = Enumerable.Range(first, 4).ToArray(), Uvs = uvs.ToArray(), Tris = patchTriangles });
        }
    }

    // Closes the shell with a dark roof that rides the tops of the walls: per grid cell, the lowest height over which a player could clear every wall around it (never below the surface there), with step faces between heights and a skirt on every edge from the wall-top line up to it, so nothing can float above a wall and no gap is left between the walls and the roof.
    static void AddRoof(List<Vector3> vertices, List<Vector2> vertexUvs, Dictionary<string, List<int>> trianglesByMaterial, float minX, float maxX, float minZ, float maxZ, List<AddedGeometry> added)
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
            added.Add(new AddedGeometry { Material = RoofMaterial, Indices = Enumerable.Range(first, 4).ToArray(), Uvs = Enumerable.Repeat(Vector2.zero, 4).ToArray(), Tris = new[] { 0, 1, 2, 0, 2, 3 } });
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

    static void AddRailPosts(List<Vector3> vertices, List<Vector2> vertexUvs, Dictionary<string, List<int>> trianglesByMaterial, List<AddedGeometry> added)
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
            var postTriangles = new List<int>();
            foreach (var face in new[] { new[] { 0, 3, 2, 1 }, new[] { 5, 6, 7, 4 }, new[] { 4, 7, 3, 0 }, new[] { 1, 2, 6, 5 }, new[] { 3, 7, 6, 2 } })
            {
                triangles.AddRange(new[] { first + face[0], first + face[1], first + face[2], first + face[0], first + face[2], first + face[3] });
                postTriangles.AddRange(new[] { face[0], face[1], face[2], face[0], face[2], face[3] });
            }

            added.Add(new AddedGeometry { Material = UntexturedMaterial, Indices = Enumerable.Range(first, 8).ToArray(), Uvs = Enumerable.Repeat(Vector2.zero, 8).ToArray(), Tris = postTriangles.ToArray() });
        }
    }

    // One parsed f line: its ordinal across the file, the mtl name in effect, and its corner vertex indices.
    sealed class WarehouseFace
    {
        public WarehouseFace(int ordinal, string material, int[] corners)
        {
            Ordinal = ordinal;
            Material = material;
            Corners = corners;
        }

        public int Ordinal { get; }
        public string Material { get; }
        public int[] Corners { get; }
    }

    // Geometry a code path added to the merged mesh, recorded as indices into the shared vertex list so the origin shift still applies.
    sealed class AddedGeometry
    {
        public string Material;
        public int[] Indices;
        public Vector2[] Uvs;
        public int[] Tris;
    }

    // One pieces.json row: where the asset came from and how it is placed, so the level generator can reassemble without re-deriving geometry.
    sealed class PieceRecord
    {
        public string CatalogAsset;
        public string SourceId;
        public Vector3 Rotation, Scale;
        public string Asset;
        public string Kind;
        public string Module;
        public string Source;
        public string[] Groups;
        public int[] Faces;
        public WarehousePieces.Placement Placement;
        public bool Collider;
    }

    // One piece's geometry before mesh creation: mesh-space vertices with UVs and triangle indices grouped by material.
    sealed class PieceBuild
    {
        public PieceBuild(string asset, string module)
        {
            Asset = asset;
            Module = module;
        }

        public string Asset { get; }
        public string Module { get; }
        public List<Vector3> Verts { get; } = new List<Vector3>();
        public List<Vector2> Uvs { get; } = new List<Vector2>();
        public Dictionary<string, List<int>> Triangles { get; } = new Dictionary<string, List<int>>(StringComparer.Ordinal);

        public void AddFace(WarehouseFace face, List<Vector3> vertices, List<Vector2> vertexUvs)
        {
            var triangles = new List<int>();
            for (var i = 1; i < face.Corners.Length - 1; i++)
                triangles.AddRange(new[] { 0, i + 1, i });
            AddGeometry(face.Material, face.Corners.Select(corner => vertices[corner]).ToArray(), face.Corners.Select(corner => vertexUvs[corner]).ToArray(), triangles.ToArray());
        }

        public void AddGeometry(string material, Vector3[] verts, Vector2[] uvs, int[] triangles)
        {
            var first = Verts.Count;
            Verts.AddRange(verts);
            Uvs.AddRange(uvs);
            if (!Triangles.TryGetValue(material, out var list))
                Triangles[material] = list = new List<int>();
            foreach (var index in triangles)
                list.Add(first + index);
        }
    }

    // Placement and collider presence of the last SavePiece call, picked up by the caller for its pieces.json record.
    static WarehousePieces.Placement LastPlacement;
    static bool LastHadCollider;
    static string LastCatalogAsset;
    static Vector3 LastRotation, LastScale;
    static readonly Dictionary<string, (string Asset, Vector3 Size)> KitMeshes = new Dictionary<string, (string, Vector3)>(StringComparer.Ordinal);

    // Builds one construction piece: vertices folded into its convention pivot frame, submeshes per material in ordinal order sharing the Warehouse materials, and a collision mesh without the pass-through faces (no MeshCollider at all when nothing solid is left).
    static string SavePiece(PieceBuild build, Dictionary<string, Material> materials)
    {
        var meshVerts = build.Verts.Select(v => new System.Numerics.Vector3(v.x, v.y, v.z)).ToList();
        var placement = WarehousePieces.ComputePlacement(WarehousePieces.RuleFor(build.Module == "roof-panel" ? "roof" : build.Module), meshVerts);
        var vertices = WarehousePieces.ToLocal(meshVerts, placement).Select(v => new Vector3(v.X, v.Y, v.Z)).ToArray();
        var ordered = build.Triangles.Keys.OrderBy(k => k, StringComparer.Ordinal).ToList();
        var kept = PieceCollisionTriangles(build, ordered);
        LastHadCollider = kept.Any(list => list.Count > 0);
        LastPlacement = placement;
        LastRotation = new Vector3(0, placement.YawDegrees, 0);
        LastScale = Vector3.one * WarehouseScale;
        LastCatalogAsset = build.Asset;
        if (build.Module == "suppressed-post")
        {
            LastCatalogAsset = "";
            return null;
        }
        var reusable = new[] { "sign", "prop", "kicker", "roof-panel" }.Contains(build.Module);
        if (reusable)
        {
            var triangles = ordered.SelectMany(material => build.Triangles[material]).ToArray();
            var signatures = new List<string>();
            for (var m = 0; m < ordered.Count; m++)
                for (var t = 0; t < build.Triangles[ordered[m]].Count; t += 3)
                {
                    var indices = build.Triangles[ordered[m]].Skip(t).Take(3).ToArray();
                    var solid = Enumerable.Range(0, kept[m].Count / 3).Any(n => kept[m].Skip(n*3).Take(3).SequenceEqual(indices));
                    signatures.Add(ordered[m] + (solid ? ":solid" : ":open"));
                }
            var normalized = WarehouseKit.Normalize(meshVerts.ToArray(), build.Uvs.Select(uv => new System.Numerics.Vector2(uv.x, uv.y)).ToArray(), triangles, signatures.ToArray(), LastHadCollider, build.Module == "sign", build.Module != "kicker", build.Module == "roof-panel", build.Module == "prop" && build.Asset.Contains("board"));
            var family = build.Module == "roof-panel" ? "added-roof-panel" : build.Asset.Contains("board") ? "piece-board" : build.Module == "kicker" ? "piece-kicker-frame" : build.Asset.StartsWith("added-post-", StringComparison.Ordinal) ? "added-post" : "piece-" + build.Module;
            var key = family + ":" + normalized.Key;
            var size = new Vector3(normalized.Scale.X, normalized.Scale.Y, normalized.Scale.Z);
            var exists = KitMeshes.TryGetValue(key, out var canonical);
            if (!exists)
            {
                using var sha = SHA256.Create();
                var hash = string.Concat(sha.ComputeHash(Encoding.UTF8.GetBytes(key)).Take(5).Select(b => b.ToString("x2")));
                var rectangleArea = (build.Verts.Max(v => v.x)-build.Verts.Min(v => v.x))*(build.Verts.Max(v => v.z)-build.Verts.Min(v => v.z));
                var flatRoof = build.Module == "roof-panel" && build.Verts.Count == 4 && build.Verts.All(v => Mathf.Abs(v.y - build.Verts[0].y) < 1e-7f)
                    && Mathf.Abs(WarehouseKit.Area(meshVerts.ToArray())-rectangleArea)<rectangleArea*1e-5f;
                canonical = (flatRoof ? "added-roof-panel-flat" : family + "-" + hash, flatRoof ? new Vector3(40f/WarehouseScale,1,40f/WarehouseScale) : size);
                KitMeshes.Add(key, canonical);
            }
            LastCatalogAsset = canonical.Asset;
            var z = new Vector3(normalized.Z.X, normalized.Z.Y, normalized.Z.Z);
            var y = new Vector3(normalized.Y.X, normalized.Y.Y, normalized.Y.Z);
            LastRotation = Quaternion.LookRotation(z, y).eulerAngles;
            LastScale = new Vector3(size.x/canonical.Size.x, size.y/canonical.Size.y, size.z/canonical.Size.z) * WarehouseScale;
            LastPlacement = new WarehousePieces.Placement(normalized.Origin, LastRotation.y);
            if (exists) return PackDirectory + "/" + LastCatalogAsset + ".prefab";
            vertices = normalized.Vertices.Select(v => new Vector3(v.X*canonical.Size.x, v.Y*canonical.Size.y, v.Z*canonical.Size.z)).ToArray();
        }
        var mesh = new Mesh { name = LastCatalogAsset, vertices = vertices, uv = build.Uvs.ToArray(), subMeshCount = ordered.Count };
        for (var i = 0; i < ordered.Count; i++)
            mesh.SetTriangles(build.Triangles[ordered[i]], i);
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();

        var root = new GameObject(LastCatalogAsset);
        root.transform.localScale = Vector3.one * WarehouseScale;
        root.AddComponent<MeshFilter>().sharedMesh = SaveAsset(mesh, PackDirectory + "/" + LastCatalogAsset + ".asset");
        root.AddComponent<MeshRenderer>().sharedMaterials = ordered.Select(material => materials[material]).ToArray();
        var collision = SavePieceCollisionMesh(LastCatalogAsset, kept, vertices, build.Uvs.ToArray());
        LastHadCollider = collision != null;
        if (collision != null)
            root.AddComponent<MeshCollider>().sharedMesh = collision;
        return SavePrefab(root);
    }

    static List<List<int>> PieceCollisionTriangles(PieceBuild build, List<string> ordered)
    {
        var kept = new List<List<int>>();
        for (var i = 0; i < ordered.Count; i++)
        {
            var material = ordered[i];
            if (PassThroughMaterials.Contains(material))
            {
                kept.Add(new List<int>());
                continue;
            }
            var triangles = build.Triangles[material];
            if (PassThroughInRoomMaterials.Contains(material))
                triangles = WithoutTrianglesInOpenedWindows(triangles.ToArray(), build.Verts.ToArray()).ToList();
            kept.Add(triangles);
        }

        return kept;
    }

    static Mesh SavePieceCollisionMesh(string asset, List<List<int>> triangles, Vector3[] vertices, Vector2[] uvs)
    {
        var kept = triangles.Where(list => list.Count > 0).ToList();
        if (kept.Count == 0)
            return null;
        var collision = new Mesh { name = asset + "Collision", vertices = vertices, uv = uvs, subMeshCount = kept.Count };
        for (var i = 0; i < kept.Count; i++)
            collision.SetTriangles(kept[i], i);
        collision.RecalculateBounds();
        return SaveAsset(collision, PackDirectory + "/" + asset + "Collision.asset");
    }

    // Rewrites the committed manifest with the built asset list; id, name, author and version are kept from the existing file, whose version the shipped level pins, so adding pieces never bumps it.
    static void WriteManifest(List<string> assetNames)
    {
        var path = Path.Combine(RepoPath(PacksSourceDirectory), "manifest.json");
        if (!File.Exists(path))
            throw new Exception("missing pack manifest " + path);
        var text = File.ReadAllText(path);
        string Field(string name) => System.Text.RegularExpressions.Regex.Match(text, "\"" + name + "\": \"([^\"]*)\"").Groups[1].Value;
        var json = "{\n  \"id\": \"" + Field("id") + "\",\n  \"name\": \"" + Field("name") + "\",\n  \"author\": \"" + Field("author") + "\",\n  \"version\": \"" + Field("version") + "\",\n  \"kitVersion\": \"" + Field("kitVersion") + "\",\n  \"kitAssetPrefixes\": [\"piece-\", \"added-\"],\n  \"assets\": [\n"
            + string.Join(",\n", assetNames.Select(name => "    \"" + name + "\"")) + "\n  ]\n}\n";
        if (File.ReadAllText(path) != json)
            File.WriteAllText(path, json);
    }

    // Writes the committed pieces.json sidecar: every piece asset's convention pivot, placement yaw, world position and collider presence, in manifest order.
    static void WritePiecesJson(List<PieceRecord> records)
    {
        var json = new StringBuilder();
        json.Append("{\n  \"schema\": \"thps-pieces/1\",\n  \"meshToWorld\": { \"scale\": ").Append(Number(WarehouseScale))
            .Append(", \"position\": [").Append(Number(WarehouseWorldX)).Append(", ").Append(Number(WarehouseLift)).Append(", ").Append(Number(WarehouseWorldZ)).Append("] },\n  \"pieces\": [\n");
        for (var i = 0; i < records.Count; i++)
        {
            var record = records[i];
            json.Append("    { \"asset\": \"").Append(record.Asset).Append("\", \"kind\": \"").Append(record.Kind)
                .Append("\", \"module\": \"").Append(record.Module).Append("\"");
            json.Append(", \"catalogAsset\": \"").Append(record.CatalogAsset).Append("\"");
            if (record.Kind == "source")
            {
                json.Append(", \"sourceId\": \"").Append(record.SourceId).Append("\"");
                json.Append(", \"groups\": [").Append(string.Join(", ", record.Groups.Select(group => "\"" + group + "\"")))
                    .Append("], \"faces\": [").Append(string.Join(", ", record.Faces)).Append("]");
            }
            else
                json.Append(", \"source\": \"").Append(record.Source).Append("\"");
            var pivot = record.Placement.Pivot;
            json.Append(", \"pivot\": [").Append(Number(pivot.X)).Append(", ").Append(Number(pivot.Y)).Append(", ").Append(Number(pivot.Z)).Append("]");
            json.Append(", \"yaw\": ").Append(Number(record.Placement.YawDegrees));
            json.Append(", \"rotation\": [").Append(Number(record.Rotation.x)).Append(", ").Append(Number(record.Rotation.y)).Append(", ").Append(Number(record.Rotation.z)).Append("]");
            json.Append(", \"scale\": [").Append(Number(record.Scale.x)).Append(", ").Append(Number(record.Scale.y)).Append(", ").Append(Number(record.Scale.z)).Append("]");
            json.Append(", \"position\": [").Append(Number(pivot.X * WarehouseScale + WarehouseWorldX)).Append(", ")
                .Append(Number(pivot.Y * WarehouseScale + WarehouseLift)).Append(", ").Append(Number(pivot.Z * WarehouseScale + WarehouseWorldZ)).Append("]");
            json.Append(", \"collider\": ").Append(record.Collider ? "true" : "false").Append(" }").Append(i + 1 < records.Count ? ",\n" : "\n");
        }

        json.Append("  ]\n}\n");
        var path = Path.Combine(RepoPath(PacksSourceDirectory), "pieces.json");
        File.WriteAllText(path, json.ToString());
    }

    static string Number(float value) => value.ToString("R", CultureInfo.InvariantCulture);

    static float Parse(string value) => float.Parse(value, CultureInfo.InvariantCulture);

    static Material SaveMaterial(string name, Color color)
    {
        var material = new Material(Shader.Find("Standard")) { color = color };
        return SaveAsset(material, PackDirectory + "/" + name + ".mat");
    }

    // Puts the prefab on the layer the player grounds against, the same as the tile ground.
    static string SavePrefab(GameObject root)
    {
        foreach (var t in root.GetComponentsInChildren<Transform>(true))
            t.gameObject.layer = GroundLayer;

        var path = Pinned(PackDirectory + "/" + root.name + ".prefab");
        PrefabUtility.SaveAsPrefabAsset(root, path);
        PinFileIds(path);
        AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
        UnityEngine.Object.DestroyImmediate(root);
        return path;
    }

    static void BuildBundle(List<string> prefabPaths, BuildTarget target, string directory) =>
        PackBuilder.BuildNamedBundle(BundleName, prefabPaths, target, directory);
}
