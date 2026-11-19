"""
Self-test for scripts/lift_names.py.

Joins Il2CppDumper's dump.cs to the scored body map. Uses synthetic dumps so
no real GameAssembly.so or global-metadata.dat is needed.
"""

import json
import lift_names
from pathlib import Path

DUMP = """// Image 0: mscorlib.dll - 0
// Image 1: Assembly-CSharp.dll - 1200

public enum EItem // TypeDefIndex: 1300
{
	public const EItem CageKey = 69;
}

public class InventoryUtility // TypeDefIndex: 1301
{
	// Fields
	public const int MAX_WEAPON_LEVEL_BASE = 40;

	// Methods

	// RVA: 0x225B7C0 Offset: 0x225B7C0 VA: 0x225B7C0
	public static int GetNumMaxTomeSlots() { }

	// RVA: 0x225B7D0 Offset: 0x225B7D0 VA: 0x225B7D0
	public static int GetWeaponMaxLevel() { }

	// RVA: 0x225B7E0 Offset: 0x225B7E0 VA: 0x225B7E0
	private static int ComputeMax(int level) { }

	// RVA: 0x225B7F0 Offset: 0x225B7F0 VA: 0x225B7F0
	public InventoryUtility() { }

	// RVA: 0x225B800 Offset: 0x225B800 VA: 0x225B800
	public static T Read<T>(Stream s) { }

	// RVA: 0x225B810 Offset: 0x225B810 VA: 0x225B810
	public int Width { get { } set { } }
}

public class ItemFactory // TypeDefIndex: 4570
{
	// Methods

	// RVA: 0x227E020 Offset: 0x227E020 VA: 0x227E020
	internal static Item CreateItem(EItem item) { }
}
"""


def test_rva_map_names_methods_with_image_and_class() -> None:
    names = lift_names.rva_map(DUMP)
    assert names[0x225B7D0] == ["Assembly-CSharp.dll:InventoryUtility::GetWeaponMaxLevel"]
    assert names[0x225B7E0] == ["Assembly-CSharp.dll:InventoryUtility::ComputeMax"]


def test_rva_map_uses_the_image_owning_the_type_index() -> None:
    names = lift_names.rva_map(DUMP)
    # TypeDefIndex 1301 is past Assembly-CSharp's start of 1200; 4570 too.
    assert names[0x225B7C0][0].startswith("Assembly-CSharp.dll:InventoryUtility::")
    assert names[0x227E020] == ["Assembly-CSharp.dll:ItemFactory::CreateItem"]


def test_rva_map_handles_constructors_and_generics() -> None:
    names = lift_names.rva_map(DUMP)
    assert names[0x225B7F0] == ["Assembly-CSharp.dll:InventoryUtility::InventoryUtility"]
    assert names[0x225B800] == ["Assembly-CSharp.dll:InventoryUtility::Read"]


def test_rva_map_skips_property_declarations_without_a_signature() -> None:
    names = lift_names.rva_map(DUMP)
    assert 0x225B810 not in names


def test_rva_map_ignores_enum_fields() -> None:
    names = lift_names.rva_map(DUMP)
    assert all("CageKey" not in n for group in names.values() for n in group)


def test_rva_map_precedes_the_first_image_start_with_unknown() -> None:
    dump = "public class Early // TypeDefIndex: 5\n{\n\t// RVA: 0x10 Offset: 0x10 VA: 0x10\n\tpublic int Run() { }\n}\n"
    names = lift_names.rva_map(dump)
    assert names[0x10] == ["?:Early::Run"]


def test_name_bodies_joins_on_body_start(tmp_path: Path) -> None:
    bodies = tmp_path / "bodies.jsonl"
    rows = [
        {"start": 0x225B7D0, "size": 11, "stages": {"clean": True}, "unproven_branchind": []},
        {"start": 0x227E020, "size": 4521, "stages": {"clean": False}, "unproven_branchind": [{}] * 3},
    ]
    bodies.write_text("\n".join(json.dumps(r) for r in rows))
    named = lift_names.name_bodies(DUMP, bodies)
    assert named[0]["start"] == "0x225b7d0"
    assert named[0]["clean"] is True
    assert named[0]["names"] == ["Assembly-CSharp.dll:InventoryUtility::GetWeaponMaxLevel"]
    assert named[1]["sites"] == 3
    assert named[1]["names"] == ["Assembly-CSharp.dll:ItemFactory::CreateItem"]


def test_rva_map_keeps_the_constructor_dot() -> None:
    dump = (
        "// Image 0: UnityEngine.CoreModule.dll - 0\n\n"
        "public class RenderTexture // TypeDefIndex: 5\n"
        "{\n"
        "\t// RVA: 0x4AA7EC0 Offset: 0x4AA7EC0 VA: 0x4AA7EC0\n"
        "\tpublic void .ctor(IntPtr jobject) { }\n"
        "}\n"
    )
    names = lift_names.rva_map(dump)
    assert names[0x4AA7EC0] == ["UnityEngine.CoreModule.dll:RenderTexture::.ctor"]


def test_summarise_counts_named_and_unnamed() -> None:
    named = [
        {"names": ["a.dll:C::M"], "clean": True},
        {"names": [], "clean": False},
        {"names": ["b.dll:C::M"], "clean": False},
    ]
    assert lift_names.summarise(named) == {
        "bodies": 3,
        "named": 2,
        "clean": 1,
        "blocked": 2,
        "blocked_named": 1,
    }
