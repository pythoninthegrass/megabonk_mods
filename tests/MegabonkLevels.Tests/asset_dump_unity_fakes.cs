// Minimal stand-ins for the Unity base types AssetDump keys its field-only rule off, so the walker can be tested without the game assemblies.
namespace UnityEngine
{
    public class Object
    {
        public string name { get; set; } = "";
    }

    public class GameObject : Object
    {
    }

    public class ScriptableObject : Object
    {
    }
}
