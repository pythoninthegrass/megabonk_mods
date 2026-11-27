import kf2_package_info as info
import pytest
import struct

PACKAGE_TAG = 0x9E2A83C1


def header(
    *, file_version=868, licensee=0, size=1234, folder="None", flags=0x8, names=(5, 100), exports=(7, 200), imports=(3, 300)
):
    folder_bytes = folder.encode("ascii") + b"\0"
    return (
        struct.pack("<IHHi", PACKAGE_TAG, file_version, licensee, size)
        + struct.pack("<i", len(folder_bytes))
        + folder_bytes
        + struct.pack("<I6i", flags, *names, *exports, *imports)
    )


def test_reads_versions_flags_and_table_counts():
    data = header()
    parsed = info.read_header(data)
    assert parsed.file_version == 868
    assert parsed.licensee_version == 0
    assert parsed.header_size == 1234
    assert parsed.folder == "None"
    assert parsed.package_flags == 0x8
    assert (parsed.name_count, parsed.name_offset) == (5, 100)
    assert (parsed.export_count, parsed.export_offset) == (7, 200)
    assert (parsed.import_count, parsed.import_offset) == (3, 300)


def test_cooked_flag_distinguishes_brewed_from_unbrewed():
    assert info.read_header(header(flags=0x8)).cooked is True
    assert info.read_header(header(flags=0x0)).cooked is False


def test_rejects_a_file_without_the_package_tag():
    with pytest.raises(ValueError, match="not an Unreal package"):
        info.read_header(b"\x00" * 64)


def test_rejects_a_truncated_header():
    with pytest.raises(ValueError, match="truncated"):
        info.read_header(header()[:10])


def name_entry(text):
    raw = text.encode("ascii") + b"\0"
    return struct.pack("<i", len(raw)) + raw + struct.pack("<Q", 0)


def import_entry(class_package, class_name, outer, object_name):
    return struct.pack("<2i2i i2i", class_package, 0, class_name, 0, outer, object_name, 0)


def build_package(names, imports):
    prefix_size = len(header())
    name_blob = b"".join(name_entry(n) for n in names)
    import_blob = b"".join(imports)
    data = bytearray(
        header(names=(len(names), prefix_size), exports=(0, 0), imports=(len(imports), prefix_size + len(name_blob)))
    )
    return bytes(data + name_blob + import_blob)


def test_reads_the_name_table():
    data = build_package(["None", "Core", "Package"], [])
    assert info.read_names(data, info.read_header(data)) == ["None", "Core", "Package"]


def test_lists_stock_packages_the_map_imports_from():
    names = ["None", "Core", "Package", "StaticMesh", "KFEnvironment", "Rock01"]
    imports = [
        import_entry(1, 2, 0, 4),  # Core.Package KFEnvironment, top level
        import_entry(1, 3, -1, 5),  # Core.StaticMesh Rock01, inside KFEnvironment
        import_entry(1, 2, 0, 1),  # Core.Package Core, top level
    ]
    data = build_package(names, imports)
    parsed = info.read_header(data)
    assert info.import_packages(data, parsed) == ["Core", "KFEnvironment"]


def test_rejects_names_beyond_the_data():
    data = build_package(["None"], [])
    with pytest.raises(ValueError, match="truncated"):
        info.read_names(data[:-4], info.read_header(data))
