using System;
using System.Collections;
using BepInEx.Unity.IL2CPP.Utils.Collections;
using Il2CppInterop.Runtime.Attributes;
using UnityEngine;

namespace MegabonkLevels;

public class ModTick : MonoBehaviour
{
    public ModTick(IntPtr ptr) : base(ptr) { }

    internal static ModTick Instance;

    private void Update() => MegabonkLevelsMod.Tick();
    private void LateUpdate() => CameraOverride.Apply();
    private void OnApplicationQuit() => LevelMusic.Clear();

    [HideFromIl2Cpp]
    internal static void Run(IEnumerator routine) => Instance.StartCoroutine(routine.WrapToIl2Cpp());
}
