using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

public static class PackBuilder
{
    const string BundleName = "testprop";
    const string PrefabPath = "Assets/TestProp/TestProp.prefab";
    const string MaterialPath = "Assets/TestProp/TestProp.mat";
    const string ModelBundleName = "testmodel";
    const string ModelDirectory = "Assets/TestModel";

    // Entry point for -executeMethod; the output directory comes from -packOutput.
    public static void BuildTestPack()
    {
        var output = ArgValue("-packOutput");
        CreateTestPrefab();
        CreateTestModel();
        Build(BuildTarget.StandaloneWindows64, Path.Combine(output, "windows"));
        Build(BuildTarget.StandaloneLinux64, Path.Combine(output, "linux"));
    }

    static void CreateTestPrefab()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(PrefabPath));

        var material = new Material(Shader.Find("Standard")) { color = new Color(0.9f, 0.4f, 0.1f) };
        AssetDatabase.CreateAsset(material, MaterialPath);

        var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
        cube.name = "TestProp";
        cube.GetComponent<MeshRenderer>().sharedMaterial = material;
        PrefabUtility.SaveAsPrefabAsset(cube, PrefabPath);
        UnityEngine.Object.DestroyImmediate(cube);

        AssetImporter.GetAtPath(PrefabPath).assetBundleName = BundleName;
        AssetDatabase.SaveAssets();
    }

    // A multi-part model with a textured Standard material, a plain-colored Legacy shader material and an emissive Standard material, to exercise the shader remap.
    static void CreateTestModel()
    {
        Directory.CreateDirectory(ModelDirectory);

        var texture = CreateBrickTexture(ModelDirectory + "/Brick.png");
        var brick = CreateMaterial("Brick", "Standard", Color.white, texture);
        var tower = CreateMaterial("Tower", "Legacy Shaders/Diffuse", new Color(0.25f, 0.5f, 0.85f), null);
        var glow = CreateMaterial("Glow", "Standard", new Color(0.2f, 0.9f, 0.3f), null);
        glow.EnableKeyword("_EMISSION");
        glow.SetColor("_EmissionColor", new Color(0.2f, 1.2f, 0.3f));
        var roof = CreateMaterial("Roof", "Standard", new Color(0.55f, 0.15f, 0.1f), null);

        var root = new GameObject("TestModel");
        AddPart(root, PrimitiveType.Cube, "Body", new Vector3(0, 1.0f, 0), new Vector3(3, 2, 3), brick);
        AddPart(root, PrimitiveType.Cylinder, "Tower", new Vector3(2.2f, 1.5f, 0), new Vector3(1.2f, 1.5f, 1.2f), tower);
        AddPart(root, PrimitiveType.Sphere, "Beacon", new Vector3(2.2f, 3.5f, 0), new Vector3(0.9f, 0.9f, 0.9f), glow);
        AddPart(root, PrimitiveType.Cube, "Roof", new Vector3(0, 2.2f, 0), new Vector3(3.6f, 0.4f, 3.6f), roof);

        var prefabPath = ModelDirectory + "/TestModel.prefab";
        PrefabUtility.SaveAsPrefabAsset(root, prefabPath);
        UnityEngine.Object.DestroyImmediate(root);

        AssetImporter.GetAtPath(prefabPath).assetBundleName = ModelBundleName;
        AssetDatabase.SaveAssets();
    }

    static Material CreateMaterial(string name, string shader, Color color, Texture2D texture)
    {
        var material = new Material(Shader.Find(shader)) { color = color, mainTexture = texture };
        AssetDatabase.CreateAsset(material, ModelDirectory + "/" + name + ".mat");
        return material;
    }

    static void AddPart(GameObject root, PrimitiveType type, string name, Vector3 position, Vector3 scale, Material material)
    {
        var part = GameObject.CreatePrimitive(type);
        part.name = name;
        part.transform.SetParent(root.transform, false);
        part.transform.localPosition = position;
        part.transform.localScale = scale;
        part.GetComponent<Renderer>().sharedMaterial = material;
    }

    static Texture2D CreateBrickTexture(string path)
    {
        const int size = 64;
        var texture = new Texture2D(size, size);
        for (var y = 0; y < size; y++)
        {
            for (var x = 0; x < size; x++)
            {
                var row = y / 16;
                var mortar = y % 16 < 2 || (x + (row % 2) * 16) % 32 < 2;
                texture.SetPixel(x, y, mortar ? new Color(0.75f, 0.75f, 0.7f) : new Color(0.7f, 0.3f, 0.2f));
            }
        }

        File.WriteAllBytes(path, texture.EncodeToPNG());
        UnityEngine.Object.DestroyImmediate(texture);
        AssetDatabase.ImportAsset(path);
        return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
    }

    static void Build(BuildTarget target, string directory)
    {
        Directory.CreateDirectory(directory);
        var manifest = BuildPipeline.BuildAssetBundles(directory, BuildAssetBundleOptions.ChunkBasedCompression, target);
        if (manifest == null)
            throw new Exception("BuildAssetBundles failed for " + target);
        Debug.Log("PackBuilder: built " + target + " into " + directory);
    }

    internal static void BuildNamedBundle(string bundleName, List<string> assetPaths, BuildTarget target, string directory)
    {
        Directory.CreateDirectory(directory);
        var builds = new[] { new AssetBundleBuild { assetBundleName = bundleName, assetNames = assetPaths.ToArray() } };
        var manifest = BuildPipeline.BuildAssetBundles(directory, builds, BuildAssetBundleOptions.ChunkBasedCompression, target);
        if (manifest == null)
            throw new Exception("BuildAssetBundles failed for " + target);
        Debug.Log("PackBuilder: built " + bundleName + " for " + target + " into " + directory);
    }

    internal static string ArgValue(string name)
    {
        var args = Environment.GetCommandLineArgs();
        var i = Array.IndexOf(args, name);
        if (i < 0 || i + 1 >= args.Length)
            throw new ArgumentException("missing " + name);
        return args[i + 1];
    }
}
