using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

public static class SqueakerPack
{
    const string BundleName = "squeaker";
    const string AssetDirectory = "Assets/Squeaker";
    const string ControllerPath = AssetDirectory + "/Squeaker.controller";
    static readonly string[] LoopingClips = { "Idle", "Run", "Falling", "Grind" };
    static readonly string[] ClipNames = { "Idle", "Run", "Jump", "Falling", "Grind" };

    // Entry point for -executeMethod; the output directory comes from -packOutput.
    public static void Build()
    {
        var output = PackBuilder.ArgValue("-packOutput");
        ConfigureImporter(AssetDirectory + "/Squeaker.fbx", true);
        ConfigureImporter(AssetDirectory + "/StaleCookie.fbx", false);
        var controller = BuildController();
        var prefabs = new List<string>
        {
            SavePrefab(AssetDirectory + "/Squeaker.fbx", "Squeaker", controller),
            SavePrefab(AssetDirectory + "/StaleCookie.fbx", "StaleCookie", null),
        };
        AssetDatabase.SaveAssets();
        PackBuilder.BuildNamedBundle(BundleName, prefabs, BuildTarget.StandaloneWindows64, Path.Combine(output, "windows"));
        PackBuilder.BuildNamedBundle(BundleName, prefabs, BuildTarget.StandaloneLinux64, Path.Combine(output, "linux"));
    }

    // The character gets a Generic rig and one clip per Blender take, named after the stock Animator clips; the cookie is a static mesh.
    static void ConfigureImporter(string path, bool animated)
    {
        var importer = (ModelImporter)AssetImporter.GetAtPath(path);
        importer.animationType = animated ? ModelImporterAnimationType.Generic : ModelImporterAnimationType.None;
        importer.importAnimation = animated;
        if (animated)
            importer.clipAnimations = importer.defaultClipAnimations.Select(ClipNamedAfterTake).ToArray();
        importer.SaveAndReimport();
    }

    static ModelImporterClipAnimation ClipNamedAfterTake(ModelImporterClipAnimation clip)
    {
        clip.name = clip.takeName.Split('|').Last();
        clip.loopTime = LoopingClips.Contains(clip.name);
        return clip;
    }

    static AnimatorController BuildController()
    {
        AssetDatabase.DeleteAsset(ControllerPath);
        var controller = AnimatorController.CreateAnimatorControllerAtPath(ControllerPath);
        var clips = AssetDatabase.LoadAllAssetsAtPath(AssetDirectory + "/Squeaker.fbx").OfType<AnimationClip>().ToDictionary(c => c.name);
        foreach (var name in ClipNames)
        {
            if (!clips.TryGetValue(name, out var clip))
                throw new System.Exception("Squeaker.fbx has no clip named " + name + "; found " + string.Join(", ", clips.Keys));
            var state = controller.layers[0].stateMachine.AddState(name);
            state.motion = clip;
            if (name == "Idle")
                controller.layers[0].stateMachine.defaultState = state;
        }

        return controller;
    }

    // Unpacked so the prefab holds its own hierarchy (hips, torso, renderer) rather than a link into the FBX.
    static string SavePrefab(string fbxPath, string name, AnimatorController controller)
    {
        var path = AssetDirectory + "/" + name + ".prefab";
        var instance = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(fbxPath));
        PrefabUtility.UnpackPrefabInstance(instance, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
        instance.name = name;
        if (controller != null)
        {
            var animator = instance.GetComponent<Animator>();
            if (animator == null)
                animator = instance.AddComponent<Animator>();
            animator.runtimeAnimatorController = controller;
            animator.avatar = AssetDatabase.LoadAllAssetsAtPath(fbxPath).OfType<Avatar>().FirstOrDefault();
        }

        PrefabUtility.SaveAsPrefabAsset(instance, path);
        Object.DestroyImmediate(instance);
        AssetImporter.GetAtPath(path).assetBundleName = BundleName;
        return path;
    }
}
