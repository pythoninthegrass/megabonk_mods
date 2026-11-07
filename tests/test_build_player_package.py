import build_player_package as module
import hashlib
import io
import os
import pytest
import shutil
import subprocess
import zipfile
from build_player_package import (
    DOTNET_WINDOWS_ASSET,
    MELONLOADER_ASSET,
    BuildError,
    build_package,
    make_zip,
)
from package_contract.manifest import load_manifest, verify_package
from pathlib import Path

MOD_VERSION = "0.4.2"
MELONLOADER_VERSION = "0.7.3"


def archive_bytes(payloads: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, payload in payloads.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    mod_dir = tmp_path / "repo/src/MegabonkLevels.Mod/bin/Release/net6.0"
    mod_dir.mkdir(parents=True)
    (mod_dir / "MegabonkLevels.Mod.dll").write_bytes(b"mod dll")
    (mod_dir / "MegabonkLevels.Mod.pdb").write_bytes(b"pdb bytes")
    (mod_dir / "NLayer.dll").write_bytes(b"nlayer")
    (mod_dir / "MegabonkLevels.Mod.deps.json").write_text("{}")

    levels = tmp_path / "repo/levels"
    levels.mkdir(parents=True)
    (levels / "example-forest.mblevel.json").write_text('{"version":1}')
    (levels / "scratch.local.mblevel.json").write_text('{"version":1}')
    (levels / "example-forest.png").write_bytes(b"png bytes")
    (levels / "example-forest.biome.png").write_bytes(b"biome bytes")
    (levels / "scratch.local.png").write_bytes(b"scratch png")
    (levels / "other-level.png").write_bytes(b"not bundled")

    bundles = tmp_path / "repo/.tools/bundles/windows"
    bundles.mkdir(parents=True)
    (bundles / "thps").write_bytes(b"bundle bytes")
    packs_src = tmp_path / "repo/unity/pack-authoring/packs/thps"
    packs_src.mkdir(parents=True)
    (packs_src / "manifest.json").write_text(
        '{"id":"thps","name":"THPS","author":"a","version":"1","assets":["thps"]}'
    )
    (packs_src / "attachments.json").write_text('{"schema":"pack-attachments/1","assets":{}}')

    melonloader = archive_bytes({"MelonLoader/Version.dll": b"v"})
    dotnet = archive_bytes({"dotnet.exe": b"d"})
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / MELONLOADER_ASSET).write_bytes(melonloader)
    (cache / DOTNET_WINDOWS_ASSET).write_bytes(dotnet)

    monkeypatch.setattr(module, "release_asset", lambda system, version: ("https://example.test/ml.zip", hashlib.sha256(melonloader).hexdigest()))
    monkeypatch.setattr(module, "DOTNET_WINDOWS_SHA256", hashlib.sha256(dotnet).hexdigest())
    monkeypatch.chdir(tmp_path)

    binary = tmp_path / "megabonk-installer-linux-amd64"
    binary.write_bytes(b"ELF installer")

    return {
        "binary": binary,
        "mod": mod_dir,
        "levels": levels,
        "bundles": tmp_path / "repo/.tools/bundles",
        "packs_src": tmp_path / "repo/unity/pack-authoring/packs",
        "cache": cache,
        "melonloader": melonloader,
        "dotnet": dotnet,
        "output": tmp_path / "dist/pkg",
    }


def _dry_run(*variables: str) -> str:
    """The commands `task package:linux` would run, with the given task variables."""
    result = subprocess.run(
        ["task", "--dry", "package:linux", *variables],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent,
        check=False,
    )
    return result.stdout + result.stderr


def build(workspace, **overrides):
    kwargs = {
        "mod_dir": workspace["mod"],
        "levels_dir": workspace["levels"],
        "level_names": ["example-forest.mblevel.json", "scratch.local.mblevel.json"],
        "bundles_dir": workspace["bundles"],
        "packs_src": workspace["packs_src"],
        "pack_names": ["thps"],
        "allow_download": False,
    }
    kwargs.setdefault("installer_binary", workspace["binary"])
    kwargs.update(overrides)
    return build_package(workspace["output"], cache=workspace["cache"], **kwargs)


class TestLayout:
    def test_builds_vendor_installer_and_content_tree(self, workspace):
        record = build(workspace)
        out = workspace["output"]
        assert (out / "vendor" / MELONLOADER_ASSET).is_file()
        assert (out / "vendor" / DOTNET_WINDOWS_ASSET).is_file()
        assert (out / "megabonk-installer").read_bytes() == b"ELF installer"
        assert not (out / "install.sh").exists()
        assert not (out / "installer").exists()
        assert (out / "manifest.json").is_file()
        assert [(v.kind, v.version) for v in record.vendors] == [("melonloader", MELONLOADER_VERSION), ("dotnet", "6.0.36")]
        assert [v.name for v in record.vendors] == [MELONLOADER_ASSET, DOTNET_WINDOWS_ASSET]

    def test_manifest_is_loadable_and_every_hash_verifies(self, workspace):
        record = build(workspace)
        loaded = load_manifest(workspace["output"] / "manifest.json")
        assert [(f.path, f.dest) for f in loaded.files] == [(f.path, f.dest) for f in record.files]
        problems = verify_package(workspace["output"])
        assert problems == []

    def test_mod_goes_to_mods_and_userlibs(self, workspace):
        record = build(workspace)
        dests = {f.path: f.dest for f in record.files}
        assert dests["MegabonkLevels.Mod.dll"] == "Mods/MegabonkLevels.Mod.dll"
        assert dests["NLayer.dll"] == "UserLibs/NLayer.dll"
        assert not any(f.path.endswith(".pdb") for f in record.files)
        assert not any(f.path.endswith("deps.json") for f in record.files)

    def test_levels_exclude_local_scratch_files(self, workspace, capsys):
        record = build(workspace)
        bundled = {f.path for f in record.files}
        assert "content/levels/example-forest.mblevel.json" in bundled
        assert not any("scratch.local" in path for path in bundled)
        assert "working file" in capsys.readouterr().out

    def test_level_sidecar_image_is_bundled_beside_its_level(self, workspace):
        record = build(workspace)
        dests = {f.path: f.dest for f in record.files}
        assert dests["content/levels/example-forest.png"] == "UserData/Levels/example-forest.png"
        assert not any("other-level" in path for path in dests)
        assert not any("scratch.local" in path for path in dests)

    def test_level_biome_icon_is_bundled_beside_its_level(self, workspace):
        record = build(workspace)
        entry = next(f for f in record.files if f.path == "content/levels/example-forest.biome.png")
        assert entry.dest == "UserData/Levels/example-forest.biome.png"
        assert entry.sha256 == hashlib.sha256(b"biome bytes").hexdigest()

    def test_sidecar_image_in_zip_matches_manifest_hash(self, workspace):
        record = build(workspace)
        entry = next(f for f in record.files if f.path == "content/levels/example-forest.png")
        assert entry.sha256 == hashlib.sha256(b"png bytes").hexdigest()

    def test_level_and_pack_destinations(self, workspace):
        record = build(workspace)
        dests = {f.path: f.dest for f in record.files}
        assert dests["content/levels/example-forest.mblevel.json"] == "UserData/Levels/example-forest.mblevel.json"
        assert dests["content/packs/thps/thps"] == "UserData/LevelPacks/thps/thps"

    def test_default_task_bundles_only_the_starter_level(self):
        if shutil.which("task") is None:
            pytest.skip("task is not installed")
        commands = _dry_run()
        assert "for level in bramblecrown-hill.mblevel.json;" in commands
        assert "example-forest.mblevel.json" not in commands
        assert "thps.mblevel.json" not in commands
        assert "for pack in ;" in commands

    def test_starter_package_contains_only_approved_content(self, workspace):
        record = build(
            workspace,
            levels_dir=Path(__file__).resolve().parents[1] / "levels",
            level_names=["bramblecrown-hill.mblevel.json"],
            pack_names=[],
        )
        assert {entry.path for entry in record.files if entry.path.startswith("content/")} == {
            "content/levels/bramblecrown-hill.mblevel.json",
            "content/levels/bramblecrown-hill.png",
            "content/levels/bramblecrown-hill.biome.png",
        }
        assert verify_package(workspace["output"]) == []

    def test_a_pack_whose_id_disagrees_with_its_folder_is_refused(self, workspace):
        (workspace["packs_src"] / "thps/manifest.json").write_text(
            '{"id":"other","name":"THPS","author":"a","version":"1","assets":["thps"]}'
        )
        with pytest.raises(BuildError, match="thps"):
            build(workspace)

    def test_a_pack_without_a_bundle_is_refused(self, workspace):
        (workspace["bundles"] / "windows/thps").unlink()
        with pytest.raises(BuildError, match="AssetBundle"):
            build(workspace)


class TestVendorHandling:
    def test_a_tampered_archive_is_refused(self, workspace):
        (workspace["cache"] / DOTNET_WINDOWS_ASSET).write_bytes(b"tampered")
        with pytest.raises(BuildError, match=DOTNET_WINDOWS_ASSET):
            build(workspace)

    def test_nothing_is_written_when_an_archive_fails(self, workspace):
        (workspace["cache"] / MELONLOADER_ASSET).write_bytes(b"tampered")
        with pytest.raises(BuildError):
            build(workspace)
        assert not (workspace["output"] / "manifest.json").exists()
        assert not (workspace["output"] / "vendor").exists()

    def test_a_missing_archive_needs_allow_download(self, workspace):
        (workspace["cache"] / DOTNET_WINDOWS_ASSET).unlink()
        with pytest.raises(BuildError, match="allow-download"):
            build(workspace)

    def test_an_existing_cache_is_never_downloaded(self, workspace, monkeypatch):
        def explode(*args, **kwargs):
            raise AssertionError("network use")

        import asset_download

        monkeypatch.setattr(asset_download, "download_to", explode)
        build(workspace)

    def test_a_404_from_the_vendor_url_reads_as_a_missing_archive(self, workspace, monkeypatch):
        import asset_download
        import build_player_package as module

        (workspace["cache"] / DOTNET_WINDOWS_ASSET).unlink()

        def not_there(url, destination, **kwargs):
            raise asset_download.MissingAsset(f"{url} returned HTTP 404: the asset is not there")

        monkeypatch.setattr(asset_download, "download_to", not_there)
        with pytest.raises(module.MissingInput, match="404") as caught:
            build(workspace, allow_download=True)
        assert "place the file at" in str(caught.value).lower()
        assert not (workspace["cache"] / (DOTNET_WINDOWS_ASSET + ".part")).exists()

    def test_a_network_failure_is_an_error_rather_than_a_missing_input(self, workspace, monkeypatch):
        import asset_download
        import build_player_package as module

        (workspace["cache"] / DOTNET_WINDOWS_ASSET).unlink()

        def broken(url, destination, **kwargs):
            raise asset_download.DownloadError(f"{url} redirects to a different host")

        monkeypatch.setattr(asset_download, "download_to", broken)
        with pytest.raises(module.BuildError, match="different host") as caught:
            build(workspace, allow_download=True)
        assert not isinstance(caught.value, module.MissingInput)

    def test_a_download_is_verified_against_the_pinned_digest_before_it_is_cached(self, workspace, monkeypatch):
        import asset_download

        (workspace["cache"] / DOTNET_WINDOWS_ASSET).unlink()
        seen: dict[str, object] = {}
        real_to = asset_download.download_to

        def record(url, destination, **kwargs):
            seen[Path(destination).name] = kwargs.get("expected_sha256")
            return real_to(url, destination, **kwargs)

        monkeypatch.setattr(asset_download, "download_to", record)
        monkeypatch.setattr(asset_download, "download", lambda url, **kwargs: workspace["dotnet"])
        build(workspace, allow_download=True)
        assert seen[DOTNET_WINDOWS_ASSET] == hashlib.sha256(workspace["dotnet"]).hexdigest()
        assert (workspace["cache"] / DOTNET_WINDOWS_ASSET).read_bytes() == workspace["dotnet"]

    def test_the_package_task_forwards_allow_download_to_the_script(self):
        if shutil.which("task") is None:
            pytest.skip("task is not installed")
        assert 'if [ "true" = "true" ]; then args+=(--allow-download); fi' in _dry_run("ALLOW_DOWNLOAD=true")
        assert 'if [ "false" = "true" ]; then args+=(--allow-download); fi' in _dry_run()


class TestLinuxPackage:
    def test_carries_the_installer_binary_with_no_extension(self, workspace):
        record = build(workspace)
        out = workspace["output"]
        assert (out / "megabonk-installer").read_bytes() == b"ELF installer"
        assert not (out / "install.sh").exists()
        assert not (out / "install.exe").exists()
        assert not (out / "installer").exists()
        assert record.platform == "linux"

    def test_manifest_loads_and_every_hash_verifies(self, workspace):
        build(workspace)
        assert load_manifest(workspace["output"] / "manifest.json").platform == "linux"
        assert verify_package(workspace["output"]) == []

    def test_a_missing_binary_is_a_missing_input(self, workspace, tmp_path):
        with pytest.raises(module.MissingInput, match="installer:build"):
            build(workspace, installer_binary=tmp_path / "absent")

    def test_linux_needs_a_binary_argument(self, workspace):
        with pytest.raises(BuildError, match="installer binary"):
            build(workspace, installer_binary=None)

    def test_zip_keeps_the_installer_executable(self, workspace, capsys):
        code = module.main(
            [
                "--installer-binary", str(workspace["binary"]),
                "--output", str(workspace["output"]),
                "--cache", str(workspace["cache"]),
                "--mod-dir", str(workspace["mod"]),
                "--mod-version", MOD_VERSION,
            ]
        )
        assert code == 0
        name = f"megabonk-levels-{MOD_VERSION}-ml{MELONLOADER_VERSION}-linux.zip"
        assert name in capsys.readouterr().out
        with zipfile.ZipFile(workspace["output"].parent / name) as archive:
            info = archive.getinfo("megabonk-installer")
            assert (info.external_attr >> 16) & 0o111 == 0o111


class TestWindowsPackage:
    @pytest.fixture
    def binary(self, tmp_path):
        path = tmp_path / "megabonk-installer-windows-amd64.exe"
        path.write_bytes(b"MZ installer")
        return path

    def test_carries_the_installer_binary_as_install_exe(self, workspace, binary):
        record = build(workspace, platform="windows", installer_binary=binary)
        out = workspace["output"]
        assert (out / "install.exe").read_bytes() == b"MZ installer"
        assert not (out / "install.sh").exists()
        assert not (out / "installer").exists()
        assert record.platform == "windows"

    def test_manifest_loads_and_every_hash_verifies(self, workspace, binary):
        build(workspace, platform="windows", installer_binary=binary)
        assert load_manifest(workspace["output"] / "manifest.json").platform == "windows"
        assert verify_package(workspace["output"]) == []

    def test_a_missing_binary_is_a_missing_input(self, workspace, tmp_path):
        with pytest.raises(module.MissingInput, match="installer:build"):
            build(workspace, platform="windows", installer_binary=tmp_path / "absent.exe")

    def test_windows_needs_a_binary_argument(self, workspace):
        with pytest.raises(BuildError, match="installer binary"):
            build(workspace, platform="windows", installer_binary=None)

    def test_zip_name_and_cli(self, workspace, binary, capsys):
        code = module.main(
            [
                "--platform", "windows",
                "--installer-binary", str(binary),
                "--output", str(workspace["output"]),
                "--cache", str(workspace["cache"]),
                "--mod-dir", str(workspace["mod"]),
                "--mod-version", MOD_VERSION,
            ]
        )
        assert code == 0
        name = f"megabonk-levels-{MOD_VERSION}-ml{MELONLOADER_VERSION}-windows.zip"
        assert name in capsys.readouterr().out
        with zipfile.ZipFile(workspace["output"].parent / name) as archive:
            assert "install.exe" in archive.namelist()


class TestMacosPackage:
    @pytest.fixture
    def binary(self, tmp_path):
        path = tmp_path / "megabonk-installer-darwin-arm64"
        path.write_bytes(b"Mach-O installer")
        return path

    def test_carries_the_installer_binary_with_no_extension(self, workspace, binary):
        record = build(workspace, platform="macos", installer_binary=binary)
        out = workspace["output"]
        assert (out / "megabonk-installer").read_bytes() == b"Mach-O installer"
        assert not (out / "install.sh").exists()
        assert not (out / "install.exe").exists()
        assert not (out / "installer").exists()
        assert record.platform == "macos"

    def test_manifest_loads_and_every_hash_verifies(self, workspace, binary):
        build(workspace, platform="macos", installer_binary=binary)
        assert load_manifest(workspace["output"] / "manifest.json").platform == "macos"
        assert verify_package(workspace["output"]) == []

    def test_a_missing_binary_is_a_missing_input(self, workspace, tmp_path):
        with pytest.raises(module.MissingInput, match="installer:build"):
            build(workspace, platform="macos", installer_binary=tmp_path / "absent")

    def test_macos_needs_a_binary_argument(self, workspace):
        with pytest.raises(BuildError, match="installer binary"):
            build(workspace, platform="macos", installer_binary=None)

    def test_zip_keeps_the_installer_executable(self, workspace, binary, capsys):
        code = module.main(
            [
                "--platform", "macos",
                "--installer-binary", str(binary),
                "--output", str(workspace["output"]),
                "--cache", str(workspace["cache"]),
                "--mod-dir", str(workspace["mod"]),
                "--mod-version", MOD_VERSION,
            ]
        )
        assert code == 0
        name = f"megabonk-levels-{MOD_VERSION}-ml{MELONLOADER_VERSION}-macos.zip"
        assert name in capsys.readouterr().out
        with zipfile.ZipFile(workspace["output"].parent / name) as archive:
            info = archive.getinfo("megabonk-installer")
            assert (info.external_attr >> 16) & 0o111 == 0o111


class TestZip:
    def test_zip_is_deterministic(self, workspace, tmp_path):
        build(workspace)
        first = make_zip(workspace["output"], tmp_path / "a.zip")
        second = make_zip(workspace["output"], tmp_path / "b.zip")
        assert first.read_bytes() == second.read_bytes()

    def test_zip_entries_are_sorted_and_the_installer_is_executable(self, workspace, tmp_path):
        build(workspace)
        path = make_zip(workspace["output"], tmp_path / "pkg.zip")
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            assert names == sorted(names)
            assert "megabonk-installer" in names
            assert archive.getinfo("megabonk-installer").external_attr >> 16 == 0o755
            assert "__pycache__" not in "".join(names)


class TestCli:
    def test_success_and_zip_name(self, workspace, capsys):
        import build_player_package as module

        code = module.main(
            [
                "--installer-binary", str(workspace["binary"]),
                "--output", str(workspace["output"]),
                "--cache", str(workspace["cache"]),
                "--mod-dir", str(workspace["mod"]),
                "--levels-dir", str(workspace["levels"]),
                "--level", "example-forest.mblevel.json",
                "--bundles-dir", str(workspace["bundles"]),
                "--packs-src", str(workspace["packs_src"]),
                "--pack", "thps",
                "--mod-version", MOD_VERSION,
            ]
        )
        assert code == 0
        out = capsys.readouterr().out
        assert f"megabonk-levels-{MOD_VERSION}-ml{MELONLOADER_VERSION}-linux.zip" in out
        assert (workspace["output"].parent / f"megabonk-levels-{MOD_VERSION}-ml{MELONLOADER_VERSION}-linux.zip").is_file()

    def test_nothing_is_bundled_without_being_asked(self, workspace, capsys):
        import build_player_package as module

        code = module.main(
            [
                "--installer-binary", str(workspace["binary"]),
                "--output", str(workspace["output"]),
                "--cache", str(workspace["cache"]),
                "--mod-dir", str(workspace["mod"]),
                "--skip-zip",
            ]
        )
        assert code == 0
        bundled = {p.relative_to(workspace["output"]).as_posix() for p in (workspace["output"]).rglob("*")}
        assert not any(p.startswith("content/levels/") for p in bundled)
        assert not any(p.startswith("content/packs/") for p in bundled)

    def test_a_level_that_does_not_exist_is_exit_3(self, workspace, capsys):
        import build_player_package as module

        code = module.main(
            [
                "--output", str(workspace["output"]),
                "--cache", str(workspace["cache"]),
                "--mod-dir", str(workspace["mod"]),
                "--levels-dir", str(workspace["levels"]),
                "--level", "nope.mblevel.json",
            ]
        )
        assert code == 3
        assert "nope.mblevel.json" in capsys.readouterr().err

    def test_a_pack_without_a_built_bundle_is_exit_3(self, workspace, capsys):
        import build_player_package as module

        code = module.main(
            [
                "--output", str(workspace["output"]),
                "--cache", str(workspace["cache"]),
                "--mod-dir", str(workspace["mod"]),
                "--bundles-dir", str(workspace["bundles"]),
                "--packs-src", str(workspace["packs_src"]),
                "--pack", "thps",
                "--pack-platform", "linux",
            ]
        )
        assert code == 3
        assert "task pack" in capsys.readouterr().err

    def test_a_missing_mod_build_is_exit_3(self, tmp_path, capsys):
        import build_player_package as module

        code = module.main(
            [
                "--output", str(tmp_path / "dist/pkg"),
                "--cache", str(tmp_path / "cache"),
                "--mod-dir", str(tmp_path / "nope"),
            ]
        )
        assert code == 3
        assert "task mod:build" in capsys.readouterr().err
