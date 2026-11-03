"""
Self-test for scripts/player_installer/plan.py and content.py.

Covers the idempotence plan (no-op versus repair), level and pack placement,
and what uninstall takes back out of the game directory.
"""

import hashlib
import json
import player_installer.content as content
import player_installer.manifest as mf
import player_installer.plan as plan
import player_installer.proton as proton
import pytest
import zipfile
from pathlib import Path


def _zip(path: Path, entries: dict[str, bytes]) -> bytes:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return path.read_bytes()


def _package(tmp_path: Path, *, mod_dll: bytes = b"mod dll", nlayer: bytes = b"nlayer") -> Path:
    package = tmp_path / "package"
    (package / "vendor").mkdir(parents=True)
    (package / "mod").mkdir(parents=True)
    loader = _zip(
        package / "vendor" / "MelonLoader.x64.zip",
        {"version.dll": b"MZ", "MelonLoader/net6/MelonLoader.dll": b"MZ", "MelonLoader/net6/MelonLoader.runtimeconfig.json": b"{}"},
    )
    runtime = _zip(
        package / "vendor" / "dotnet-runtime-6.0.36-win-x64.zip",
        {
            "dotnet.exe": b"MZ",
            "host/fxr/6.0.36/hostfxr.dll": b"MZ",
            "shared/Microsoft.NETCore.App/6.0.36/System.Private.CoreLib.dll": b"MZ",
        },
    )
    (package / "mod" / "MegabonkLevels.Mod.dll").write_bytes(mod_dll)
    (package / "mod" / "MegabonkLevels.Mod.pdb").write_bytes(b"pdb")
    (package / "mod" / "NLayer.dll").write_bytes(nlayer)
    doc = {
        "schema": mf.PACKAGE_SCHEMA,
        "platform": "linux",
        "package_id": "megabonk-levels-0.0.1-ml0.7.3-linux",
        "mod_version": "0.0.1",
        "melonloader_version": "0.7.3",
        "game_buildid": "21750826",
        "generated": "2026-10-31T03:30:00Z",
        "verified_on": [],
        "vendors": [
            {
                "name": "MelonLoader.x64.zip",
                "url": "u",
                "sha256": hashlib.sha256(loader).hexdigest(),
                "kind": "melonloader",
                "version": "0.7.3",
            },
            {
                "name": "dotnet-runtime-6.0.36-win-x64.zip",
                "url": "u",
                "sha256": hashlib.sha256(runtime).hexdigest(),
                "kind": "dotnet",
                "version": "6.0.36",
            },
        ],
        "files": [
            {"path": "mod/MegabonkLevels.Mod.dll", "sha256": hashlib.sha256(mod_dll).hexdigest(), "dest": "Mods/MegabonkLevels.Mod.dll"},
            {"path": "mod/MegabonkLevels.Mod.pdb", "sha256": hashlib.sha256(b"pdb").hexdigest(), "dest": "Mods/MegabonkLevels.Mod.pdb"},
            {"path": "mod/NLayer.dll", "sha256": hashlib.sha256(nlayer).hexdigest(), "dest": "Mods/NLayer.dll"},
            {"path": "mod/NLayer.dll", "sha256": hashlib.sha256(nlayer).hexdigest(), "dest": "UserLibs/NLayer.dll"},
        ],
    }
    (package / "manifest.json").write_text(json.dumps(doc))
    return package


def _game(tmp_path: Path) -> Path:
    game = tmp_path / "Megabonk"
    (game / "Megabonk_Data").mkdir(parents=True)
    (game / "Megabonk.exe").write_bytes(b"MZ")
    return game


def _prefix(tmp_path: Path) -> Path:
    prefix = tmp_path / "compatdata" / "3405340" / "pfx"
    (prefix / "drive_c").mkdir(parents=True)
    return prefix


def _kinds(actions) -> list[str]:
    return [a.kind for a in actions]


def test_fresh_install_plans_every_piece(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    result = plan.build_plan(package, manifest, game, build="windows", prefix=prefix)
    kinds = _kinds(result.actions)
    assert "install-loader" in kinds
    assert kinds.count("install-file") == 4
    assert "install-runtime" in kinds
    assert "enable-dll-override" in kinds
    assert "create-levels-dir" in kinds
    assert result.is_noop is False


def test_complete_install_is_a_no_op(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix)
    again = plan.build_plan(package, manifest, game, build="windows", prefix=prefix)
    assert again.is_noop is True
    assert again.actions == ()


def test_repair_replaces_only_a_stale_mod_dll(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix)
    (game / "Mods" / "MegabonkLevels.Mod.dll").write_bytes(b"old version")
    result = plan.build_plan(package, manifest, game, build="windows", prefix=prefix)
    repairs = [a for a in result.actions if a.kind == "install-file"]
    assert [a.path.name for a in repairs] == ["MegabonkLevels.Mod.dll"]
    assert "install-loader" not in _kinds(result.actions)
    assert "install-runtime" not in _kinds(result.actions)


def test_repair_reinstalls_the_loader_when_its_marker_is_gone(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix)
    (game / "MelonLoader" / "MegabonkLevels.melonloader_version").unlink()
    result = plan.build_plan(package, manifest, game, build="windows", prefix=prefix)
    assert "install-loader" in _kinds(result.actions)


def test_repair_reinstalls_the_runtime_when_the_prefix_was_wiped(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix)
    import shutil

    shutil.rmtree(prefix / "drive_c" / "Program Files")
    result = plan.build_plan(package, manifest, game, build="windows", prefix=prefix)
    assert _kinds(result.actions) == ["install-runtime", "enable-dll-override"]


def test_game_dir_runtime_mode_targets_the_game_folder(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    result = plan.build_plan(package, manifest, game, build="windows", prefix=prefix, runtime_mode="gamedir")
    runtime = next(a for a in result.actions if a.kind == "install-runtime")
    assert runtime.path == game / content.RUNTIME_SUBDIR
    assert "DOTNET_ROOT" in runtime.detail


def test_native_build_is_refused_before_anything_is_planned(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    (game / "Megabonk.x86_64").write_bytes(b"\x7fELF")
    (game / "Megabonk.exe").unlink()
    manifest = mf.load_manifest(package / "manifest.json")
    with pytest.raises(plan.PlanError, match="Megabonk.x86_64"):
        plan.build_plan(package, manifest, game, build="native-linux", prefix=prefix)


def test_missing_package_file_is_reported(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    (package / "mod" / "NLayer.dll").unlink()
    manifest = mf.load_manifest(package / "manifest.json")
    with pytest.raises(plan.PlanError, match="NLayer.dll"):
        plan.build_plan(package, manifest, game, build="windows", prefix=prefix)


def test_dll_override_can_be_declined(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    result = plan.build_plan(package, manifest, game, build="windows", prefix=prefix, dll_override=False)
    assert "enable-dll-override" not in _kinds(result.actions)


def test_level_file_lands_in_user_data_levels(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    level = tmp_path / "my-level.mblevel.json"
    level.write_text('{"schema":2}')
    manifest = mf.load_manifest(package / "manifest.json")
    result = plan.build_plan(package, manifest, game, build="windows", prefix=prefix, level=level)
    target = next(a for a in result.actions if a.kind == "install-file" and a.path.parent.name == "Levels")
    assert target.path == game / "UserData" / "Levels" / "my-level.mblevel.json"
    plan.apply(package, manifest, game, build="windows", prefix=prefix, level=level)
    assert (game / "UserData" / "Levels" / "my-level.mblevel.json").read_text() == '{"schema":2}'


def test_an_identical_level_file_is_not_recopied(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    level = tmp_path / "my-level.mblevel.json"
    level.write_text('{"schema":2}')
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix, level=level)
    result = plan.build_plan(package, manifest, game, build="windows", prefix=prefix, level=level)
    assert all(a.kind != "install-file" or a.path.name != "my-level.mblevel.json" for a in result.actions)


def test_levels_directory_is_created_when_absent(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix)
    assert content.levels_dir(game).is_dir()


def _pack_source(tmp_path: Path, pack_id: str = "thps") -> Path:
    source = tmp_path / "packsrc" / pack_id
    source.mkdir(parents=True)
    (source / pack_id).write_bytes(b"bundle bytes")
    (source / "manifest.json").write_text(
        json.dumps({"id": pack_id, "name": "THPS", "author": "user", "version": "1", "assets": ["a"]})
    )
    (source / "attachments.json").write_text('{"schema":"pack-attachments/1"}')
    return source


def test_pack_bundle_and_manifest_land_in_level_packs(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    source = _pack_source(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix, pack=source)
    dest = content.pack_dest(game, "thps")
    assert sorted(p.name for p in dest.iterdir()) == ["attachments.json", "manifest.json", "thps"]
    assert (dest / "thps").read_bytes() == b"bundle bytes"


def test_a_stale_pack_file_is_replaced(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    source = _pack_source(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix, pack=source)
    (content.pack_dest(game, "thps") / "thps").write_bytes(b"stale")
    result = plan.build_plan(package, manifest, game, build="windows", prefix=prefix, pack=source)
    repaired = [a for a in result.actions if a.kind == "install-file"]
    assert [a.path for a in repaired] == [content.pack_dest(game, "thps") / "thps"]


def test_a_pack_whose_manifest_id_mismatches_its_folder_is_refused(tmp_path: Path) -> None:
    source = _pack_source(tmp_path)
    (source / "manifest.json").write_text(json.dumps({"id": "other", "name": "n", "author": "a", "version": "1", "assets": []}))
    problems = content.validate_pack_source(source)
    assert any("does not match" in p for p in problems)


def test_a_pack_missing_manifest_fields_is_refused(tmp_path: Path) -> None:
    source = _pack_source(tmp_path)
    (source / "manifest.json").write_text(json.dumps({"id": "thps", "name": "n"}))
    problems = content.validate_pack_source(source)
    assert any("author" in p for p in problems) and any("assets" in p for p in problems)


def test_a_pack_with_no_bundle_is_refused(tmp_path: Path) -> None:
    source = _pack_source(tmp_path)
    (source / "thps").unlink()
    assert any("bundle" in p for p in content.validate_pack_source(source))


def test_a_directory_that_is_not_a_pack_is_refused(tmp_path: Path) -> None:
    empty = tmp_path / "notapack"
    empty.mkdir()
    assert content.validate_pack_source(empty) != []


def test_uninstall_removes_everything_the_installer_placed(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    source = _pack_source(tmp_path)
    level = tmp_path / "level.mblevel.json"
    level.write_text("{}")
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix, pack=source, level=level)
    removed = plan.uninstall(game)
    for path in (
        game / "MelonLoader",
        game / "version.dll",
        game / "Mods" / "MegabonkLevels.Mod.dll",
        game / "Mods" / "NLayer.dll",
        game / "UserLibs" / "NLayer.dll",
        content.pack_dest(game, "thps"),
        game / "UserData" / "Levels" / "level.mblevel.json",
        prefix / "drive_c" / "Program Files" / "dotnet",
    ):
        assert path in removed
        assert not path.exists()
    assert (game / "Mods").exists() is False


def test_uninstall_keeps_player_files_the_installer_did_not_place(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix)
    (game / "UserData" / "Levels" / "mine.mblevel.json").write_text("{}")
    plan.uninstall(game)
    assert (game / "UserData" / "Levels" / "mine.mblevel.json").exists()


def test_uninstall_on_a_vanilla_directory_is_a_no_op(tmp_path: Path) -> None:
    game = _game(tmp_path)
    assert plan.uninstall(game) == []
    assert content.load_record(game) is None


def test_record_round_trips_and_names_what_was_installed(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix)
    record = content.load_record(game)
    assert record["package_id"] == manifest.package_id
    assert "Mods/MegabonkLevels.Mod.dll" in record["files"]
    assert record["runtime"]["mode"] == "prefix"
    assert record["dll_override"]["applied"] is True


def test_apply_reports_each_action_it_took(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    done = plan.apply(package, manifest, game, build="windows", prefix=prefix)
    assert "install-loader" in _kinds(done)
    assert all(isinstance(a.path, Path) for a in done)


def test_a_tampered_vendor_archive_is_refused_before_extraction(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    (package / "vendor" / "MelonLoader.x64.zip").write_bytes(b"not the loader")
    manifest = mf.load_manifest(package / "manifest.json")
    with pytest.raises(plan.PlanError, match="MelonLoader.x64.zip"):
        plan.build_plan(package, manifest, game, build="windows", prefix=prefix)


def test_the_loader_is_extracted_into_the_game_directory(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix)
    assert (game / "version.dll").is_file()
    assert (game / "MelonLoader" / "net6" / "MelonLoader.dll").is_file()
    assert (game / "MelonLoader" / "MegabonkLevels.melonloader_version").read_text() == "0.7.3"


def test_the_runtime_lands_in_the_prefix_by_default(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix)
    assert proton.runtime_installed(proton.runtime_target(prefix), "6.0.36") is True
    assert (prefix / "drive_c" / "Program Files" / "dotnet" / "dotnet.exe").is_file()


def test_the_dll_override_is_written_to_the_prefix(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix)
    assert proton.read_dll_override(prefix, "version") == "native,builtin"


def test_a_record_is_written_only_after_a_successful_apply(tmp_path: Path) -> None:
    package, game, prefix = _package(tmp_path), _game(tmp_path), _prefix(tmp_path)
    assert content.load_record(game) is None
    manifest = mf.load_manifest(package / "manifest.json")
    plan.apply(package, manifest, game, build="windows", prefix=prefix)
    assert content.load_record(game)["melonloader_version"] == "0.7.3"
