import ast
import build_player_package as module
import hashlib
import io
import os
import pytest
import shutil
import subprocess
import sys
import zipfile
from build_player_package import (
    DOTNET_WINDOWS_ASSET,
    MELONLOADER_ASSET,
    MIN_PYTHON,
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

    return {
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


class TestInstallSh:
    def test_wrapper_runs_the_package_installer(self):
        text = install_sh_content()
        assert '"$PYTHON" -m player_installer' in text
        assert "--package" in text
        assert text.startswith("#!/bin/sh")

    def test_wrapper_says_what_to_install_when_python_is_missing(self):
        assert "sudo dnf install python3" in install_sh_content()

    def test_wrapper_declares_and_enforces_the_python_floor(self):
        text = install_sh_content()
        version = f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
        assert f"Requires Python {version} or newer" in text
        assert f"sys.version_info >= {MIN_PYTHON!r}" in text
        assert "--python" in text

    def test_wrapper_is_valid_sh(self, tmp_path):
        path = tmp_path / "install.sh"
        path.write_text(install_sh_content(), encoding="utf-8")
        subprocess.run(["sh", "-n", str(path)], check=True)

    def test_wrapper_reaches_the_bundled_installer(self, workspace):
        build(workspace)
        script = workspace["output"] / "install.sh"
        env = {**os.environ, "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"}
        result = subprocess.run(
            [str(script), "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(workspace["output"].parent),
        )
        assert result.returncode == 0, result.stderr
        assert "usage: player_installer" in result.stdout


FLOOR_TEXT = f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}"


def _stub_python(path: Path, *, version: str, at_or_above_floor: bool) -> Path:
    """A python3 that reports a chosen version and hands module runs to the real interpreter."""
    body = (
        "#!/bin/sh\n"
        'if [ -n "${STUB_LOG:-}" ]; then printf \'%s\\n\' "$*" >> "$STUB_LOG"; fi\n'
        'code="$2"\n'
        "case \"$code\" in\n"
        f'  *"sys.exit(0 if"*) exit {0 if at_or_above_floor else 1};;\n'
        f'  *"version_info"*) echo "{version}";;\n'
        "esac\n"
        'case "$*" in\n'
        '  *"-m player_installer"*) exec "$STUB_REAL" "$@";;\n'
        "esac\n"
        "exit 0\n"
    )
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


class TestPythonFloor:
    def test_bundled_modules_stay_parseable_on_the_floor(self):
        for path in sorted(INSTALLER_SOURCE.glob("*.py")):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=MIN_PYTHON)

    def test_bundled_modules_stay_importable_below_the_floor(self):
        # ruff targets 3.13 and would autofix timezone.utc to datetime.UTC, which is 3.11+:
        # a real player box still runs a 3.10-era interpreter, and the modules must load there.
        for path in sorted(INSTALLER_SOURCE.glob("*.py")):
            assert "from datetime import UTC" not in path.read_text(encoding="utf-8"), path.name

    def test_the_floor_stays_within_the_interpreter_a_current_lts_ships(self):
        assert MIN_PYTHON <= (3, 12)

    def test_wrapper_accepts_an_interpreter_at_the_floor(self, workspace, tmp_path):
        build(workspace)
        stub_dir = tmp_path / "bin"
        stub_dir.mkdir()
        _stub_python(stub_dir / "python3", version=FLOOR_TEXT, at_or_above_floor=True)
        env = {
            **os.environ,
            "PATH": f"{stub_dir}{os.pathsep}{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}",
            "STUB_REAL": sys.executable,
        }
        result = subprocess.run(
            [str(workspace["output"] / "install.sh"), "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(workspace["output"].parent),
        )
        assert result.returncode == 0, result.stderr
        assert "usage: player_installer" in result.stdout

    def test_wrapper_refuses_an_interpreter_below_the_floor_by_name(self, workspace, tmp_path):
        build(workspace)
        stub_dir = tmp_path / "bin"
        stub_dir.mkdir()
        below = (MIN_PYTHON[0], MIN_PYTHON[1] - 1)
        _stub_python(stub_dir / "python3", version=f"{below[0]}.{below[1]}", at_or_above_floor=False)
        env = {**os.environ, "PATH": f"{stub_dir}{os.pathsep}{os.environ['PATH']}", "STUB_REAL": sys.executable}
        result = subprocess.run(
            [str(workspace["output"] / "install.sh"), "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(workspace["output"].parent),
        )
        assert result.returncode == 1
        assert f"needs Python {FLOOR_TEXT} or newer" in result.stderr
        assert f"found {below[0]}.{below[1]}" in result.stderr
        assert "--python" in result.stderr

    def test_wrapper_runs_with_an_explicit_interpreter(self, workspace, tmp_path):
        build(workspace)
        stub = _stub_python(tmp_path / "py-3.99", version="3.99", at_or_above_floor=True)
        log = tmp_path / "calls.log"
        env = {
            **os.environ,
            "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}",
            "STUB_REAL": sys.executable,
            "STUB_LOG": str(log),
        }
        result = subprocess.run(
            [str(workspace["output"] / "install.sh"), "--python", str(stub), "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(workspace["output"].parent),
        )
        assert result.returncode == 0, result.stderr
        assert "usage: player_installer" in result.stdout
        assert "-m player_installer" in log.read_text(encoding="utf-8")

    def test_wrapper_runs_with_an_interpreter_named_in_the_environment(self, workspace, tmp_path):
        build(workspace)
        stub = _stub_python(tmp_path / "py-env", version="3.99", at_or_above_floor=True)
        env = {
            **os.environ,
            "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}",
            "STUB_REAL": sys.executable,
            "STUB_LOG": str(tmp_path / "calls.log"),
            "MEGABONK_PYTHON": str(stub),
        }
        result = subprocess.run(
            [str(workspace["output"] / "install.sh"), "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(workspace["output"].parent),
        )
        assert result.returncode == 0, result.stderr
        assert (tmp_path / "calls.log").exists()

    def test_wrapper_refuses_an_interpreter_path_it_cannot_run(self, workspace, tmp_path):
        build(workspace)
        missing = tmp_path / "no-such-python"
        env = {**os.environ, "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"}
        result = subprocess.run(
            [str(workspace["output"] / "install.sh"), "--python", str(missing), "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(workspace["output"].parent),
        )
        assert result.returncode == 2
        assert str(missing) in result.stderr

    def test_built_wrapper_runs_on_a_floor_interpreter_when_one_is_installed(self, workspace):
        homes = Path.home() / ".local/share/mise/installs/python"
        candidates = sorted(homes.glob(f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}*/bin/python3")) if homes.is_dir() else []
        if not candidates:
            pytest.skip(f"no mise interpreter at the {FLOOR_TEXT} floor installed")
        build(workspace)
        env = {**os.environ, "PATH": f"{candidates[-1].parent}{os.pathsep}{os.environ['PATH']}"}
        result = subprocess.run(
            [str(workspace["output"] / "install.sh"), "--help"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(workspace["output"].parent),
        )
        assert result.returncode == 0, result.stderr
        assert "usage: player_installer" in result.stdout


class TestWindowsPackage:
    @pytest.fixture
    def binary(self, tmp_path):
        path = tmp_path / "megabonk-installer-windows-amd64.exe"
        path.write_bytes(b"MZ installer")
        return path

    def test_carries_the_installer_binary_instead_of_the_python_installer(self, workspace, binary):
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
            build(workspace, platform="windows")

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
            build(workspace, platform="macos")

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
