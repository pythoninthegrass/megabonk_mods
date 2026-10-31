import build_player_package as module
import hashlib
import io
import pytest
import zipfile
from build_player_package import (
    DOTNET_WINDOWS_ASSET,
    MELONLOADER_ASSET,
    BuildError,
    build_package,
    install_sh_content,
    make_zip,
)
from pathlib import Path
from player_installer.manifest import load_manifest, verify_package

MOD_VERSION = "0.4.2"
MELONLOADER_VERSION = "0.7.3"
INSTALLER_SOURCE = Path(__file__).resolve().parent.parent / "scripts/player_installer"


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

    return {
        "mod": mod_dir,
        "levels": levels,
        "bundles": tmp_path / "repo/.tools/bundles",
        "packs_src": tmp_path / "repo/unity/pack-authoring/packs",
        "cache": cache,
        "output": tmp_path / "dist/pkg",
    }


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
    kwargs.update(overrides)
    return build_package(workspace["output"], cache=workspace["cache"], **kwargs)


class TestLayout:
    def test_builds_vendor_installer_and_content_tree(self, workspace):
        record = build(workspace)
        out = workspace["output"]
        assert (out / "vendor" / MELONLOADER_ASSET).is_file()
        assert (out / "vendor" / DOTNET_WINDOWS_ASSET).is_file()
        assert (out / "installer/player_installer/cli.py").is_file()
        assert (out / "install.sh").is_file()
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

    def test_level_and_pack_destinations(self, workspace):
        record = build(workspace)
        dests = {f.path: f.dest for f in record.files}
        assert dests["content/levels/example-forest.mblevel.json"] == "UserData/Levels/example-forest.mblevel.json"
        assert dests["content/packs/thps/thps"] == "UserData/LevelPacks/thps/thps"

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

    def test_installer_is_copied_not_imported(self, workspace):
        build(workspace)
        copied = workspace["output"] / "installer/player_installer/manifest.py"
        assert copied.read_text(encoding="utf-8") == (INSTALLER_SOURCE / "manifest.py").read_text(encoding="utf-8")


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

        import build_player_package as module

        monkeypatch.setattr(module.urllib.request, "urlopen", explode)
        build(workspace)


class TestInstallSh:
    def test_wrapper_runs_the_package_installer(self):
        text = install_sh_content()
        assert "python3 -m player_installer" in text
        assert "--package" in text
        assert text.startswith("#!/bin/sh")

    def test_wrapper_says_what_to_install_when_python_is_missing(self):
        assert "sudo dnf install python3" in install_sh_content()


class TestZip:
    def test_zip_is_deterministic(self, workspace, tmp_path):
        build(workspace)
        first = make_zip(workspace["output"], tmp_path / "a.zip")
        second = make_zip(workspace["output"], tmp_path / "b.zip")
        assert first.read_bytes() == second.read_bytes()

    def test_zip_entries_are_sorted_and_install_sh_is_executable(self, workspace, tmp_path):
        build(workspace)
        path = make_zip(workspace["output"], tmp_path / "pkg.zip")
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            assert names == sorted(names)
            assert "install.sh" in names
            assert archive.getinfo("install.sh").external_attr >> 16 == 0o755
            assert "__pycache__" not in "".join(names)


class TestCli:
    def test_success_and_zip_name(self, workspace, capsys):
        import build_player_package as module

        code = module.main(
            [
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
