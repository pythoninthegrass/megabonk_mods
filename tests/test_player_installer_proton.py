"""
Self-test for scripts/player_installer/proton.py.

Covers the Proton-side pieces the installer needs: where the .NET 6 runtime
goes in a prefix, the Wine DllOverrides entry the loader's version.dll needs,
the Proton tool pick, and the launch option the fallback path prints.
"""

import player_installer.proton as proton
import zipfile
from pathlib import Path


def _prefix(tmp_path: Path) -> Path:
    prefix = tmp_path / "compatdata" / "3405340" / "pfx"
    (prefix / "drive_c").mkdir(parents=True)
    return prefix


def test_windows_path_maps_a_unix_path_onto_the_wine_z_drive(tmp_path: Path) -> None:
    got = proton.windows_path(Path("/media/sdcard/SteamLibrary/steamapps/common/Megabonk/dotnet6-win"))
    assert got == "Z:\\media\\sdcard\\SteamLibrary\\steamapps\\common\\Megabonk\\dotnet6-win"


def test_runtime_target_is_the_standard_dotnet_folder_in_the_prefix(tmp_path: Path) -> None:
    prefix = _prefix(tmp_path)
    assert proton.runtime_target(prefix) == prefix / "drive_c" / "Program Files" / "dotnet"


def test_runtime_installed_false_until_the_marker_and_host_exist(tmp_path: Path) -> None:
    target = proton.runtime_target(_prefix(tmp_path))
    assert proton.runtime_installed(target, "6.0.36") is False
    (target / "host" / "fxr" / "6.0.36").mkdir(parents=True)
    (target / "host" / "fxr" / "6.0.36" / "hostfxr.dll").write_bytes(b"MZ")
    assert proton.runtime_installed(target, "6.0.36") is False
    (target / proton.RUNTIME_MARKER_NAME).write_text("6.0.36")
    assert proton.runtime_installed(target, "6.0.36") is True


def test_runtime_installed_false_for_a_different_version(tmp_path: Path) -> None:
    target = proton.runtime_target(_prefix(tmp_path))
    (target / "host" / "fxr" / "6.0.36" / "hostfxr.dll").parent.mkdir(parents=True)
    (target / "host" / "fxr" / "6.0.36" / "hostfxr.dll").write_bytes(b"MZ")
    (target / proton.RUNTIME_MARKER_NAME).write_text("6.0.30")
    assert proton.runtime_installed(target, "6.0.36") is False


def test_extract_runtime_lays_out_dotnet_and_writes_the_marker(tmp_path: Path) -> None:
    archive = tmp_path / "dotnet.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("dotnet.exe", "MZ")
        zf.writestr("host/fxr/6.0.36/hostfxr.dll", "MZ")
        zf.writestr("shared/Microsoft.NETCore.App/6.0.36/System.Private.CoreLib.dll", "MZ")
    target = proton.runtime_target(_prefix(tmp_path))
    proton.extract_runtime(archive, target, version="6.0.36")
    assert (target / "dotnet.exe").is_file()
    assert (target / "host" / "fxr" / "6.0.36" / "hostfxr.dll").is_file()
    assert proton.runtime_installed(target, "6.0.36") is True


def test_read_dll_override_none_when_user_reg_has_no_section(tmp_path: Path) -> None:
    prefix = _prefix(tmp_path)
    (prefix / "user.reg").write_text('REGEDIT4\n\n[Software\\\\Wine\\\\AppDefaults]\n"foo"="bar"\n')
    assert proton.read_dll_override(prefix, "version") is None


def test_read_dll_override_reads_an_existing_entry(tmp_path: Path) -> None:
    prefix = _prefix(tmp_path)
    (prefix / "user.reg").write_text('REGEDIT4\n\n[Software\\\\Wine\\\\DllOverrides]\n"version"="native,builtin"\n"winedlloverrides"="native"\n')
    assert proton.read_dll_override(prefix, "version") == "native,builtin"


def test_set_dll_override_creates_the_section_and_entry(tmp_path: Path) -> None:
    prefix = _prefix(tmp_path)
    (prefix / "user.reg").write_text('REGEDIT4\n\n[Software\\\\Wine\\\\AppDefaults]\n"foo"="bar"\n')
    assert proton.set_dll_override(prefix, "version", "native,builtin") == "registry"
    text = (prefix / "user.reg").read_text()
    assert '[Software\\Wine\\DllOverrides]' in text
    assert proton.read_dll_override(prefix, "version") == "native,builtin"
    assert '"foo"="bar"' in text


def test_set_dll_override_replaces_an_existing_entry_without_duplicating(tmp_path: Path) -> None:
    prefix = _prefix(tmp_path)
    (prefix / "user.reg").write_text('REGEDIT4\n\n[Software\\\\Wine\\\\DllOverrides]\n"version"="builtin"\n')
    proton.set_dll_override(prefix, "version", "native,builtin")
    text = (prefix / "user.reg").read_text()
    assert text.count('"version"=') == 1
    assert proton.read_dll_override(prefix, "version") == "native,builtin"


def test_set_dll_override_creates_user_reg_when_absent(tmp_path: Path) -> None:
    prefix = _prefix(tmp_path)
    assert proton.set_dll_override(prefix, "version", "native,builtin") == "registry"
    assert proton.read_dll_override(prefix, "version") == "native,builtin"


def test_set_dll_override_prefers_the_wine_binary_when_it_works(tmp_path: Path) -> None:
    prefix = _prefix(tmp_path)
    calls: list[tuple[list[str], dict[str, str]]] = []

    def runner(argv, env):
        calls.append((argv, env))
        return 0

    wine = tmp_path / "wine"
    result = proton.set_dll_override(prefix, "version", "native,builtin", wine_bin=wine, runner=runner)
    assert result == "wine"
    argv, env = calls[0]
    assert argv[0] == str(wine)
    assert argv[1:3] == ["reg", "add"]
    assert "version" in argv and "native,builtin" in argv
    assert env["WINEPREFIX"] == str(prefix)


def test_set_dll_override_falls_back_to_the_registry_when_wine_fails(tmp_path: Path) -> None:
    prefix = _prefix(tmp_path)

    def failing_runner(argv, env):
        return 1

    result = proton.set_dll_override(prefix, "version", "native,builtin", wine_bin=tmp_path / "wine", runner=failing_runner)
    assert result == "registry"
    assert proton.read_dll_override(prefix, "version") == "native,builtin"


def test_clear_dll_override_removes_the_entry(tmp_path: Path) -> None:
    prefix = _prefix(tmp_path)
    proton.set_dll_override(prefix, "version", "native,builtin")
    proton.clear_dll_override(prefix, "version")
    assert proton.read_dll_override(prefix, "version") is None


def test_proton_roots_lists_installed_and_user_tools(tmp_path: Path) -> None:
    library = tmp_path / "lib"
    (library / "steamapps" / "common" / "Proton 10.0").mkdir(parents=True)
    (library / "steamapps" / "common" / "Proton 9.0 (Beta)").mkdir(parents=True)
    (library / "steamapps" / "common" / "SteamLinuxRuntime").mkdir()
    (library / "compatibilitytools.d" / "Proton-GE").mkdir(parents=True)
    names = [p.name for p in proton.proton_roots(library)]
    assert "Proton 10.0" in names and "Proton 9.0 (Beta)" in names and "Proton-GE" in names
    assert "SteamLinuxRuntime" not in names


def test_pick_proton_prefers_the_highest_numbered_tool(tmp_path: Path) -> None:
    library = tmp_path / "lib"
    (library / "steamapps" / "common" / "Proton 9.0").mkdir(parents=True)
    (library / "steamapps" / "common" / "Proton 10.0").mkdir(parents=True)
    assert proton.pick_proton(library).name == "Proton 10.0"


def test_pick_proton_honours_the_forced_tool_name(tmp_path: Path) -> None:
    library = tmp_path / "lib"
    (library / "steamapps" / "common" / "Proton 10.0").mkdir(parents=True)
    (library / "compatibilitytools.d" / "Proton-GE-10-2").mkdir(parents=True)
    assert proton.pick_proton(library, forced="proton_ge_10").name == "Proton-GE-10-2"


def test_pick_proton_none_when_no_tool_exists(tmp_path: Path) -> None:
    (tmp_path / "lib" / "steamapps" / "common").mkdir(parents=True)
    assert proton.pick_proton(tmp_path / "lib") is None


def test_proton_wine_binary_is_found_inside_the_tool(tmp_path: Path) -> None:
    tool = tmp_path / "Proton 10.0"
    (tool / "files" / "bin").mkdir(parents=True)
    (tool / "files" / "bin" / "wine").write_text("#!/bin/sh\n")
    assert proton.proton_wine_bin(tool).name == "wine"


def test_proton_wine_binary_none_when_the_tool_lacks_it(tmp_path: Path) -> None:
    (tmp_path / "Proton 10.0").mkdir()
    assert proton.proton_wine_bin(tmp_path / "Proton 10.0") is None


def test_launch_option_sets_dotnet_root_and_keeps_the_command_placeholder(tmp_path: Path) -> None:
    got = proton.launch_option(Path("/media/sdcard/SteamLibrary/steamapps/common/Megabonk/dotnet6-win"))
    assert got == 'DOTNET_ROOT=Z:\\media\\sdcard\\SteamLibrary\\steamapps\\common\\Megabonk\\dotnet6-win %command%'
