using System;
using System.IO;
using UnityEditor;
using UnityEngine;

public static class PackBuilder
{
    const string BundleName = "testprop";
    const string PrefabPath = "Assets/TestProp/TestProp.prefab";
    const string MaterialPath = "Assets/TestProp/TestProp.mat";

    // Entry point for -executeMethod; the output directory comes from -packOutput.
    public static void BuildTestPack()
    {
        var output = ArgValue("-packOutput");
        CreateTestPrefab();
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

    static void Build(BuildTarget target, string directory)
    {
        Directory.CreateDirectory(directory);
        var manifest = BuildPipeline.BuildAssetBundles(directory, BuildAssetBundleOptions.ChunkBasedCompression, target);
        if (manifest == null)
            throw new Exception("BuildAssetBundles failed for " + target);
        Debug.Log("PackBuilder: built " + target + " into " + directory);
    }

    static string ArgValue(string name)
    {
        var args = Environment.GetCommandLineArgs();
        var i = Array.IndexOf(args, name);
        if (i < 0 || i + 1 >= args.Length)
            throw new ArgumentException("missing " + name);
        return args[i + 1];
    }
}
