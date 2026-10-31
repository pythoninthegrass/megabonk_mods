"""
Self-test for scripts/player_installer/gamebuild.py and manifest.py.

Covers telling the native Linux build from the Windows build, and reading and
verifying the package manifest the installer trusts.
"""

import json
import player_installer.gamebuild as gb
import player_installer.manifest as mf
import pytest
from pathlib import Path


def _windows_game(game: Path) -> Path:
    (game / "Megabonk_Data").mkdir(parents=True)
    (game / "Megabonk.exe").write_bytes(b"MZ")
    (game / "UnityPlayer.dll").write_bytes(b"MZ")
    return game


def _native_game(game: Path) -> Path:
    (game / "Megabonk_Data").mkdir(parents=True)
    (game / "Megabonk.x86_64").write_bytes(b"\x7fELF")
    return game


def test_classify_detects_the_windows_build(tmp_path: Path) -> None:
    assert gb.classify_game_dir(_windows_game(tmp_path / "Megabonk")).build == gb.WINDOWS


def test_classify_detects_the_native_linux_build(tmp_path: Path) -> None:
    assert gb.classify_game_dir(_native_game(tmp_path / "Megabonk")).build == gb.NATIVE_LINUX


def test_classify_detects_both_binaries_as_mixed(tmp_path: Path) -> None:
    game = _windows_game(tmp_path / "Megabonk")
    (game / "Megabonk.x86_64").write_bytes(b"\x7fELF")
    assert gb.classify_game_dir(game).build == gb.MIXED


def test_classify_unknown_when_no_game_binary(tmp_path: Path) -> None:
    assert gb.classify_game_dir(tmp_path / "Megabonk").build == gb.UNKNOWN


def test_only_a_windows_capable_build_is_supported(tmp_path: Path) -> None:
    assert gb.is_supported(gb.WINDOWS) is True
    assert gb.is_supported(gb.MIXED) is True
    assert gb.is_supported(gb.NATIVE_LINUX) is False
    assert gb.is_supported(gb.UNKNOWN) is False


def test_native_build_message_names_the_blocker_and_the_way_out() -> None:
    text = gb.native_build_message(melonloader_version="0.7.3")
    for needle in ("Megabonk.x86_64", "MelonLoader", "0.7.3", "Windows", "Proton", "Steam Play"):
        assert needle in text


def test_unknown_build_message_says_what_was_expected() -> None:
    text = gb.unknown_build_message(Path("/games/Megabonk"))
    assert "/games/Megabonk" in text and "Megabonk.exe" in text


def _manifest_dict(package_dir: Path) -> dict:
    return {
        "schema": mf.PACKAGE_SCHEMA,
        "platform": "linux",
        "package_id": "megabonk-levels-0.0.1-ml0.7.3-linux",
        "mod_version": "0.0.1",
        "melonloader_version": "0.7.3",
        "game_buildid": "21750826",
        "generated": "2026-10-31T03:30:00Z",
        "verified_on": ["macOS Wine (reference)"],
        "vendors": [
            {
                "name": "MelonLoader.x64.zip",
                "url": "https://example.invalid/MelonLoader.x64.zip",
                "sha256": "a" * 64,
                "kind": "melonloader",
                "version": "0.7.3",
            },
            {
                "name": "dotnet-runtime-6.0.36-win-x64.zip",
                "url": "https://example.invalid/dotnet.zip",
                "sha256": "b" * 64,
                "kind": "dotnet",
                "version": "6.0.36",
            },
        ],
        "files": [
            {"path": "mod/MegabonkLevels.Mod.dll", "sha256": "c" * 64, "dest": "Mods/MegabonkLevels.Mod.dll"},
            {"path": "mod/NLayer.dll", "sha256": "d" * 64, "dest": "Mods/NLayer.dll"},
            {"path": "mod/NLayer.dll", "sha256": "d" * 64, "dest": "UserLibs/NLayer.dll"},
        ],
    }


def _write_package(tmp_path: Path, files: dict[str, bytes]) -> Path:
    package = tmp_path / "package"
    package.mkdir(parents=True, exist_ok=True)
    for rel, data in files.items():
        target = package / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return package


def test_manifest_round_trips(tmp_path: Path) -> None:
    package = _write_package(tmp_path, {})
    manifest = mf.PackageManifest.from_dict(_manifest_dict(package))
    mf.save_manifest(package / "manifest.json", manifest)
    loaded = mf.load_manifest(package / "manifest.json")
    assert loaded == manifest


def test_load_manifest_rejects_a_foreign_schema(tmp_path: Path) -> None:
    package = _write_package(tmp_path, {})
    bad = _manifest_dict(package) | {"schema": "megabonk-player-package/9"}
    (package / "manifest.json").write_text(json.dumps(bad))
    with pytest.raises(mf.ManifestError):
        mf.load_manifest(package / "manifest.json")


def test_load_manifest_reports_a_missing_key_by_name(tmp_path: Path) -> None:
    package = _write_package(tmp_path, {})
    bad = _manifest_dict(package)
    del bad["melonloader_version"]
    (package / "manifest.json").write_text(json.dumps(bad))
    with pytest.raises(mf.ManifestError, match="melonloader_version"):
        mf.load_manifest(package / "manifest.json")


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    import hashlib

    target = tmp_path / "f.bin"
    target.write_bytes(b"megabonk")
    assert mf.sha256_file(target) == hashlib.sha256(b"megabonk").hexdigest()


def test_verify_package_passes_on_matching_digests(tmp_path: Path) -> None:
    dll = b"mod dll bytes"
    files = {
        "vendor/MelonLoader.x64.zip": b"ml",
        "vendor/dotnet-runtime-6.0.36-win-x64.zip": b"dn",
        "mod/MegabonkLevels.Mod.dll": dll,
        "mod/NLayer.dll": b"nlayer",
    }
    package = _write_package(tmp_path, files)
    doc = _manifest_dict(package)
    import hashlib

    doc["vendors"][0]["sha256"] = hashlib.sha256(b"ml").hexdigest()
    doc["vendors"][1]["sha256"] = hashlib.sha256(b"dn").hexdigest()
    doc["files"][0]["sha256"] = hashlib.sha256(dll).hexdigest()
    doc["files"][1]["sha256"] = hashlib.sha256(b"nlayer").hexdigest()
    doc["files"][2]["sha256"] = hashlib.sha256(b"nlayer").hexdigest()
    (package / "manifest.json").write_text(json.dumps(doc))
    assert mf.verify_package(package) == []


def test_verify_package_names_a_tampered_file(tmp_path: Path) -> None:
    import hashlib

    package = _write_package(
        tmp_path,
        {
            "vendor/MelonLoader.x64.zip": b"ml",
            "vendor/dotnet-runtime-6.0.36-win-x64.zip": b"dn",
            "mod/MegabonkLevels.Mod.dll": b"tampered",
            "mod/NLayer.dll": b"nlayer",
        },
    )
    doc = _manifest_dict(package)
    doc["vendors"][0]["sha256"] = hashlib.sha256(b"ml").hexdigest()
    doc["vendors"][1]["sha256"] = hashlib.sha256(b"dn").hexdigest()
    doc["files"][0]["sha256"] = hashlib.sha256(b"mod dll bytes").hexdigest()
    doc["files"][1]["sha256"] = hashlib.sha256(b"nlayer").hexdigest()
    doc["files"][2]["sha256"] = hashlib.sha256(b"nlayer").hexdigest()
    (package / "manifest.json").write_text(json.dumps(doc))
    problems = mf.verify_package(package)
    assert len(problems) == 1 and "mod/MegabonkLevels.Mod.dll" in problems[0]


def test_verify_package_names_a_missing_vendor_archive(tmp_path: Path) -> None:
    import hashlib

    package = _write_package(
        tmp_path,
        {
            "vendor/MelonLoader.x64.zip": b"ml",
            "mod/MegabonkLevels.Mod.dll": b"dll",
            "mod/NLayer.dll": b"nlayer",
        },
    )
    doc = _manifest_dict(package)
    doc["vendors"][0]["sha256"] = hashlib.sha256(b"ml").hexdigest()
    doc["files"][0]["sha256"] = hashlib.sha256(b"dll").hexdigest()
    doc["files"][1]["sha256"] = hashlib.sha256(b"nlayer").hexdigest()
    doc["files"][2]["sha256"] = hashlib.sha256(b"nlayer").hexdigest()
    (package / "manifest.json").write_text(json.dumps(doc))
    problems = mf.verify_package(package)
    assert any("dotnet-runtime-6.0.36-win-x64.zip" in p for p in problems)


def test_verify_package_without_a_manifest_errors(tmp_path: Path) -> None:
    package = _write_package(tmp_path, {})
    with pytest.raises(mf.ManifestError):
        mf.verify_package(package)


def test_vendor_for_kind_returns_the_named_archive(tmp_path: Path) -> None:
    manifest = mf.PackageManifest.from_dict(_manifest_dict(tmp_path))
    assert manifest.vendor("dotnet").version == "6.0.36"
    with pytest.raises(mf.ManifestError):
        manifest.vendor("nope")
