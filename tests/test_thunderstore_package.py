import io
import json
import pytest
import re
import shutil
import subprocess
import tomllib
import zipfile
from check_thunderstore_package import check_package
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "BepInEx/plugins/MegabonkLevels/"
BIN = "src/MegabonkLevels.Mod/bin/Release/net6.0/"


@pytest.mark.skipif(shutil.which("task") is None, reason="Task CLI is not installed")
@pytest.mark.parametrize("platform", ["linux", "windows", "macos"])
def test_legacy_package_tasks_reject_direct_invocation(platform):
    result = subprocess.run(
        ["task", "--dry", f"package:{platform}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "internal" in output.lower()
    assert "dotnet build" not in output


@pytest.mark.skipif(shutil.which("task") is None, reason="Task CLI is not installed")
def test_only_current_package_build_is_listed():
    result = subprocess.run(
        ["task", "--list-all"], cwd=ROOT, capture_output=True, text=True, check=True,
    )
    assert "package:thunderstore:" in result.stdout
    for platform in ("linux", "windows", "macos"):
        assert f"package:{platform}:" not in result.stdout


def test_package_metadata_matches_plugin():
    config = tomllib.loads((ROOT / "thunderstore.toml").read_text())
    package = config["package"]
    manifest = json.loads((ROOT / "pkg/manifest.json").read_text())
    assert manifest == {
        "name": package["name"],
        "version_number": package["versionNumber"],
        "website_url": package["websiteUrl"],
        "description": package["description"],
        "dependencies": [f"{k}-{v}" for k, v in package["dependencies"].items()],
    }
    assert manifest["dependencies"] == ["BepInEx-BepInExPack_IL2CPP-6.0.788"]
    assert re.fullmatch(r"[A-Za-z0-9_]+", manifest["name"])
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version_number"])
    assert 0 < len(manifest["description"]) <= 250
    source = (ROOT / "src/MegabonkLevels.Mod/megabonk_levels_mod.cs").read_text()
    assert f'"Megabonk Level Editor", "{manifest["version_number"]}"' in source
    assert config["publish"]["communities"] == ["megabonk"]
    assert config["publish"]["categories"]["megabonk"] == ["mods", "tools"]
    assert package["containsNsfwContent"] is False


def test_package_only_copies_runtime_and_license():
    config = tomllib.loads((ROOT / "thunderstore.toml").read_text())
    assert config["build"]["copy"] == [
        {"source": BIN + "MegabonkLevels.Mod.dll", "target": PLUGIN},
        {"source": BIN + "NLayer.dll", "target": PLUGIN},
        {"source": "pkg/NLayer.LICENSE.txt", "target": PLUGIN},
    ]
    with Image.open(ROOT / config["build"]["icon"]) as image:
        assert image.format == "PNG"
        assert image.size == (256, 256)
    readme = (ROOT / config["build"]["readme"]).read_text(encoding="utf-8")
    assert not readme.startswith("\ufeff")
    assert "![" in readme
    assert all(url.startswith("https://") for url in re.findall(r"!\[[^]]*\]\(([^)]+)\)", readme))


@pytest.fixture
def package_files(tmp_path):
    for name in ("thunderstore.toml",):
        shutil.copy(ROOT / name, tmp_path / name)
    config = tomllib.loads((tmp_path / "thunderstore.toml").read_text())
    paths = [config["build"]["icon"], config["build"]["readme"], "pkg/manifest.json", "pkg/NLayer.LICENSE.txt"]
    for name in paths:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / name, path)
    files = {"manifest.json": (tmp_path / "pkg/manifest.json").read_bytes()}
    for name, key in (("icon.png", "icon"), ("README.md", "readme")):
        files[name] = (tmp_path / config["build"][key]).read_bytes()
    for entry in config["build"]["copy"]:
        source = tmp_path / entry["source"]
        if source.suffix == ".dll":
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(b"MZ-test-runtime")
        files[entry["target"] + source.name] = source.read_bytes()
    return tmp_path, files


def write_zip(root, files):
    path = root / "package.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return path


def test_valid_package(package_files):
    root, files = package_files
    assert check_package(write_zip(root, files), root) == []


@pytest.mark.parametrize("name", ["README.md", PLUGIN + "NLayer.dll", PLUGIN + "NLayer.LICENSE.txt"])
def test_missing_required_file(package_files, name):
    root, files = package_files
    del files[name]
    assert any("missing" in p and name in p for p in check_package(write_zip(root, files), root))


@pytest.mark.parametrize("name", ["Assembly-CSharp.dll", "dotnet/coreclr.dll", "UserData/Levels/thps.mblevel.json", "../escape", ".env"])
def test_unexpected_files_rejected(package_files, name):
    root, files = package_files
    files[name] = b"unshippable"
    assert any("unexpected" in p for p in check_package(write_zip(root, files), root))


def test_stale_binary_rejected(package_files):
    root, files = package_files
    files[PLUGIN + "MegabonkLevels.Mod.dll"] = b"old-build"
    assert any("differs" in p for p in check_package(write_zip(root, files), root))


def test_generated_manifest_must_match_source(package_files):
    root, files = package_files
    files["manifest.json"] = json.dumps({"name": "WrongMod"}).encode()
    assert any("manifest" in p for p in check_package(write_zip(root, files), root))


def test_tcli_generated_identity_fields_accepted(package_files):
    root, files = package_files
    config = tomllib.loads((root / "thunderstore.toml").read_text())
    manifest = json.loads(files["manifest.json"])
    namespace = config["package"]["namespace"]
    manifest.update(namespace=namespace, FullName=f'{namespace}-{manifest["name"]}')
    files["manifest.json"] = json.dumps(manifest).encode()
    assert check_package(write_zip(root, files), root) == []


def test_wrong_tcli_identity_rejected(package_files):
    root, files = package_files
    manifest = json.loads(files["manifest.json"])
    manifest.update(namespace="WrongTeam", FullName="WrongTeam-WrongName")
    files["manifest.json"] = json.dumps(manifest).encode()
    assert any("identity" in p for p in check_package(write_zip(root, files), root))


@pytest.mark.parametrize("value", [b"[]", b"null", b"{broken"])
def test_invalid_manifest_reported(package_files, value):
    root, files = package_files
    files["manifest.json"] = value
    assert any("manifest" in p for p in check_package(write_zip(root, files), root))


@pytest.mark.parametrize("value", [b"\xff", b"\xef\xbb\xbf# Readme", b""])
def test_invalid_readme_reported(package_files, value):
    root, files = package_files
    files["README.md"] = value
    assert any("UTF-8" in p for p in check_package(write_zip(root, files), root))


def test_wrong_icon_dimensions_rejected(package_files):
    root, files = package_files
    buffer = io.BytesIO()
    Image.new("RGB", (64, 64)).save(buffer, format="PNG")
    files["icon.png"] = buffer.getvalue()
    assert any("256" in p for p in check_package(write_zip(root, files), root))


def test_duplicate_entries_rejected(package_files):
    root, files = package_files
    path = write_zip(root, files)
    with pytest.warns(UserWarning, match="Duplicate"), zipfile.ZipFile(path, "a") as archive:
        archive.writestr("manifest.json", files["manifest.json"])
    assert any("duplicate" in p for p in check_package(path, root))


def test_corrupt_zip_reported(tmp_path):
    path = tmp_path / "package.zip"
    path.write_bytes(b"not a zip")
    assert any("zip" in p.lower() for p in check_package(path, ROOT))
