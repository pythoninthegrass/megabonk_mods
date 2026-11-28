using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

public static class Kf1MountainPassPack
{
    const string PackDirectory = "Assets/Kf1MountainPass";
    const string BundleName = "kf1";
    const string AssetName = "MountainPass";
    const int GroundLayer = 8;

    public static void Build()
    {
        var output = PackBuilder.ArgValue("-packOutput");
        var source = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../.tools/kf1"));
        var data = JsonUtility.FromJson<PackData>(File.ReadAllText(Path.Combine(source, "mesh.json")));
        AssetDatabase.DeleteAsset(PackDirectory);
        Directory.CreateDirectory(PackDirectory);
        AssetDatabase.Refresh();

        var shader = Shader.Find("MegabonkLevels/Colors Vertex Tint");
        if (shader == null)
            throw new InvalidOperationException("Colors vertex tint shader is missing");
        var materials = new List<Material>();
        var textures = new Dictionary<(string, int, int, int), Texture2D>();
        foreach (var spec in data.materials)
        {
            var material = new Material(shader);
            if (!string.IsNullOrEmpty(spec.texture))
                material.mainTexture = LoadTexture(source, spec, textures);
            material.SetFloat("_Cull", (float)(spec.doubleSided ? CullMode.Off : CullMode.Back));
            if (spec.alphaMode == "MASK")
            {
                material.SetFloat("_UseAlpha", 1);
                material.SetFloat("_Cutoff", spec.alphaCutoff);
                material.renderQueue = (int)RenderQueue.AlphaTest;
            }
            if (spec.alphaMode == "BLEND")
            {
                material.SetFloat("_UseAlpha", 1);
                material.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                material.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                material.SetFloat("_DepthWrite", 0);
                material.renderQueue = (int)RenderQueue.Transparent;
            }
            AssetDatabase.CreateAsset(material, $"{PackDirectory}/Material{materials.Count}.mat");
            materials.Add(material);
        }

        var root = new GameObject(AssetName) { layer = GroundLayer };
        var prefab = $"{PackDirectory}/{AssetName}.prefab";
        try
        {
            var collider = root.AddComponent<MeshCollider>();
            collider.sharedMesh = SaveMesh(data.collision, "Collision");
            foreach (var wall in data.perimeter)
            {
                var part = new GameObject("ArenaBoundary") { layer = GroundLayer };
                part.transform.SetParent(root.transform, false);
                part.transform.localPosition = new Vector3(wall.center[0], wall.center[1], wall.center[2]);
                part.transform.localRotation = Quaternion.Euler(0, wall.yaw, 0);
                part.AddComponent<BoxCollider>().size = new Vector3(wall.size[0], wall.size[1], wall.size[2]);
            }
            var meshId = 0;
            foreach (var node in data.meshes)
            {
                var group = new GameObject(node.name);
                group.transform.SetParent(root.transform, false);
                foreach (var primitive in node.primitives)
                {
                    var part = new GameObject($"Material{primitive.material}");
                    part.transform.SetParent(group.transform, false);
                    part.AddComponent<MeshFilter>().sharedMesh = SaveMesh(primitive, $"Mesh{meshId++}");
                    part.AddComponent<MeshRenderer>().sharedMaterial = materials[primitive.material];
                }
            }
            PrefabUtility.SaveAsPrefabAsset(root, prefab, out var success);
            if (!success)
                throw new InvalidOperationException($"Failed to save the {AssetName} prefab");
        }
        finally
        {
            UnityEngine.Object.DestroyImmediate(root);
        }

        AssetDatabase.SaveAssets();
        var assets = new List<string> { prefab };
        PackBuilder.BuildNamedBundle(BundleName, assets, BuildTarget.StandaloneWindows64, Path.Combine(output, "windows"));
        PackBuilder.BuildNamedBundle(BundleName, assets, BuildTarget.StandaloneLinux64, Path.Combine(output, "linux"));
    }

    static Texture2D LoadTexture(string source, MaterialData spec, Dictionary<(string, int, int, int), Texture2D> textures)
    {
        var key = (spec.texture, spec.wrapS, spec.wrapT, spec.magFilter);
        if (textures.TryGetValue(key, out var texture))
            return texture;
        var file = Path.Combine(source, spec.texture);
        if (!File.Exists(file))
            throw new FileNotFoundException($"Material '{spec.name}' needs texture '{spec.texture}', which is not under {source}", file);
        var path = $"{PackDirectory}/Texture{textures.Count}{Path.GetExtension(file)}";
        File.Copy(file, path, true);
        AssetDatabase.ImportAsset(path);
        var importer = (TextureImporter)AssetImporter.GetAtPath(path);
        importer.mipmapEnabled = false;
        importer.textureCompression = TextureImporterCompression.Uncompressed;
        importer.npotScale = TextureImporterNPOTScale.None;
        importer.filterMode = spec.magFilter == 9728 ? FilterMode.Point : FilterMode.Bilinear;
        importer.wrapModeU = Wrap(spec.wrapS);
        importer.wrapModeV = Wrap(spec.wrapT);
        importer.SaveAndReimport();
        texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        textures.Add(key, texture);
        return texture;
    }

    static TextureWrapMode Wrap(int mode) => mode switch
    {
        33071 => TextureWrapMode.Clamp,
        33648 => TextureWrapMode.Mirror,
        _ => TextureWrapMode.Repeat,
    };

    static Mesh SaveMesh(Geometry data, string name)
    {
        var vertices = new Vector3[data.positions.Length / 3];
        for (var i = 0; i < vertices.Length; i++)
            vertices[i] = new Vector3(data.positions[3 * i], data.positions[3 * i + 1], data.positions[3 * i + 2]);
        var mesh = new Mesh { name = name, indexFormat = vertices.Length > 65535 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
        mesh.vertices = vertices;
        mesh.triangles = data.indices;
        if (data.uv?.Length > 0)
        {
            var uv = new Vector2[vertices.Length];
            for (var i = 0; i < uv.Length; i++)
                uv[i] = new Vector2(data.uv[2 * i], data.uv[2 * i + 1]);
            mesh.uv = uv;
        }
        if (data.rgba?.Length > 0)
        {
            var colors = new Color32[vertices.Length];
            for (var i = 0; i < colors.Length; i++)
                colors[i] = new Color32((byte)data.rgba[4 * i], (byte)data.rgba[4 * i + 1], (byte)data.rgba[4 * i + 2], (byte)data.rgba[4 * i + 3]);
            mesh.colors32 = colors;
        }
        AssetDatabase.CreateAsset(mesh, $"{PackDirectory}/{name}.asset");
        return mesh;
    }

    [Serializable]
    class PackData
    {
        public Node[] meshes;
        public MaterialData[] materials;
        public Geometry collision;
        public Barrier[] perimeter;
    }

    [Serializable]
    class Barrier
    {
        public float[] center;
        public float[] size;
        public float yaw;
    }

    [Serializable]
    class Node
    {
        public string name;
        public Geometry[] primitives;
    }

    [Serializable]
    class Geometry
    {
        public float[] positions;
        public int[] indices;
        public float[] uv;
        public int[] rgba;
        public int material;
    }

    [Serializable]
    class MaterialData
    {
        public string name;
        public string texture;
        public string alphaMode;
        public float alphaCutoff;
        public bool doubleSided;
        public int wrapS;
        public int wrapT;
        public int magFilter;
    }
}
