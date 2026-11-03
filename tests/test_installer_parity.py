"""
Parity harness for the Go port of the player installer.

Drives the Go binary and the Python reference through the same scenarios in
twin fixture trees and compares what a player would see and what lands on
disk: exit codes, installed and removed file trees, the install record as
parsed JSON, and the messages that name a path, key, or flag. Quoting style is
free; see docs/player-installer.md for the contract.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import pytest
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
INSTALLER_DIR = REPO / ".tools" / "installer"
APP_ID = "3405340"
RECORD_NAME = "MegabonkLevels.installer.json"
WINE_LOG = "wine-invoked"

sys.path.insert(0, str(SCRIPTS))

TIMESTAMP = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\b")


def go_binary() -> Path:
    """The host-native Go installer built by task installer:build."""
    system = {"Darwin": "darwin", "Linux": "linux", "Windows": "windows"}[platform.system()]
    machine = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "amd64"}[platform.machine()]
    suffix = ".exe" if system == "windows" else ""
    return INSTALLER_DIR / f"megabonk-installer-{system}-{machine}{suffix}"


pytestmark = pytest.mark.skipif(
    not go_binary().exists(),
    reason=f"build the Go installer first: task installer:build (looking for {go_binary()})",
)


# --------------------------------------------------------------------------- fixtures


def _write(root: Path, relative: str, body: bytes) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)


def _zip(path: Path, entries: dict[str, bytes]) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name in sorted(entries):
            archive.writestr(name, entries[name])
    return path.read_bytes()


def _digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def make_package(root: Path) -> Path:
    """The unzipped player package, byte-identical for any root."""
    package = root / "package"
    loader = _zip(
        package / "vendor" / "MelonLoader.x64.zip",
        {
            "version.dll": b"MZ",
            "MelonLoader/net6/MelonLoader.dll": b"MZ",
            "MelonLoader/net6/MelonLoader.runtimeconfig.json": b"{}",
        },
    )
    runtime = _zip(
        package / "vendor" / "dotnet-runtime-6.0.36-win-x64.zip",
        {
            "dotnet.exe": b"MZ",
            "host/fxr/6.0.36/hostfxr.dll": b"MZ",
            "shared/Microsoft.NETCore.App/6.0.36/System.Private.CoreLib.dll": b"MZ",
        },
    )
    mod = b"mod dll"
    pdb = b"pdb"
    nlayer = b"nlayer"
    _write(package, "mod/MegabonkLevels.Mod.dll", mod)
    _write(package, "mod/MegabonkLevels.Mod.pdb", pdb)
    _write(package, "mod/NLayer.dll", nlayer)
    document = {
        "schema": "megabonk-player-package/1",
        "platform": "linux",
        "package_id": "megabonk-levels-0.0.1-ml0.7.3-linux",
        "mod_version": "0.0.1",
        "melonloader_version": "0.7.3",
        "game_buildid": "21750826",
        "generated": "2026-10-31T03:30:00Z",
        "verified_on": [],
        "vendors": [
            {"name": "MelonLoader.x64.zip", "url": "u", "sha256": _digest(loader), "kind": "melonloader", "version": "0.7.3"},
            {
                "name": "dotnet-runtime-6.0.36-win-x64.zip",
                "url": "u",
                "sha256": _digest(runtime),
                "kind": "dotnet",
                "version": "6.0.36",
            },
        ],
        "files": [
            {"path": "mod/MegabonkLevels.Mod.dll", "sha256": _digest(mod), "dest": "Mods/MegabonkLevels.Mod.dll"},
            {"path": "mod/MegabonkLevels.Mod.pdb", "sha256": _digest(pdb), "dest": "Mods/MegabonkLevels.Mod.pdb"},
            {"path": "mod/NLayer.dll", "sha256": _digest(nlayer), "dest": "Mods/NLayer.dll"},
            {"path": "mod/NLayer.dll", "sha256": _digest(nlayer), "dest": "UserLibs/NLayer.dll"},
        ],
    }
    _write(package, "manifest.json", json.dumps(document).encode())
    return package


def make_game(root: Path, name: str = "Megabonk") -> Path:
    """A vanilla Windows Megabonk install."""
    game = root / "game" / name
    (game / "Megabonk_Data").mkdir(parents=True, exist_ok=True)
    _write(game, "Megabonk.exe", b"MZ")
    _write(game, "GameAssembly.dll", b"MZ")
    _write(game, "README.txt", b"the player's own file\n")
    return game


def make_native_game(root: Path) -> Path:
    game = root / "game" / "Megabonk"
    (game / "Megabonk_Data").mkdir(parents=True, exist_ok=True)
    _write(game, "Megabonk.x86_64", b"ELF")
    return game


def make_prefix(root: Path, library: Path | None = None) -> Path:
    """A Proton prefix Steam would have created, optionally under a library."""
    base = library if library is not None else root / "orphan"
    prefix = base / "steamapps" / "compatdata" / APP_ID / "pfx"
    (prefix / "drive_c").mkdir(parents=True, exist_ok=True)
    return prefix


def make_level(root: Path, name: str = "skate.mblevel.json") -> Path:
    path = root / "inputs" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": 2, "name": "Skate Plaza"}) + "\n", encoding="utf-8")
    return path


def make_pack(root: Path, pack_id: str = "thps") -> Path:
    source = root / "inputs" / "packsrc" / pack_id
    _write(source, "manifest.json", json.dumps(
        {"id": pack_id, "name": "THPS", "author": "user", "version": "1", "assets": ["a"]}).encode())
    _write(source, "attachments.json", json.dumps({"schema": "pack-attachments/1"}).encode())
    _write(source, pack_id, b"bundle bytes")
    _write(source, "skater.bundle", b"bundle bytes two")
    return source


def stub_flatpak(home: Path) -> None:
    """A persisted flatpak override with no grants, so discovery never shells out to the host's flatpak CLI."""
    stored = home / ".var" / "app" / "com.valvesoftware.Steam" / "configuration" / "flatpak" / "local-overrides"
    stored /= "com.valvesoftware.Steam"
    stored.parent.mkdir(parents=True, exist_ok=True)
    stored.write_text("[Context]\nfilesystems=\n", encoding="utf-8")


def make_library(root: Path, *, with_game: bool = True, wine: bool = False) -> Path:
    """A Steam library, its client, and the libraryfolders.vdf tying them together."""
    library = root / "library"
    (library / "steamapps" / "common").mkdir(parents=True, exist_ok=True)
    client = root / "steam"
    (client / "steamapps").mkdir(parents=True, exist_ok=True)
    (client / "config").mkdir(parents=True, exist_ok=True)
    body = '\t"0"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n' % str(library).replace("\\", "/")
    (client / "steamapps" / "libraryfolders.vdf").write_text('"libraryfolders"\n{\n%s}\n' % body, encoding="utf-8")
    if with_game:
        game = library / "steamapps" / "common" / "Megabonk"
        (game / "Megabonk_Data").mkdir(parents=True, exist_ok=True)
        _write(game, "Megabonk.exe", b"MZ")
    if wine:
        stub = library / "steamapps" / "common" / "Proton 10.0" / "files" / "bin" / "wine"
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text(f'#!/bin/sh\necho called >> "{root / WINE_LOG}"\nexit 0\n', encoding="utf-8")
        stub.chmod(0o755)
    return library


# --------------------------------------------------------------------------- comparison


def snapshot(root: Path, ignore: tuple[str, ...] = ()) -> dict:
    """Every file and directory under root, as digests and relative paths.

    The install record records absolute paths, so it is compared as parsed JSON
    instead of as a digest; the caller names it in `ignore`.
    """
    files: dict[str, str] = {}
    directories: list[str] = []
    if not root.exists():
        return {"files": files, "dirs": directories}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            directories.append(relative)
        elif path.is_file() and relative not in ignore:
            files[relative] = _digest(path.read_bytes())
    return {"files": files, "dirs": directories}


PROG_PATTERN = re.compile(r"(?:python3? -m )?(?:player_installer|megabonk-installer[\w.-]*)")


def normalise(text: str, roots: list[Path]) -> str:
    """Strip what legitimately differs between two runs in two directories.

    Backslashes go first: a Windows-shaped path (the DOTNET_ROOT launch option)
    only matches a fixture root once its separators are the host's. The program
    name is the one thing a hint line cannot share, so both runs call it <PROG>.
    """
    text = text.replace("\\", "/")
    text = text.replace(str(go_binary()), "<PROG>")
    text = PROG_PATTERN.sub("<PROG>", text)
    for root in sorted(roots, key=lambda path: len(str(path)), reverse=True):
        text = text.replace(str(root), "<ROOT>")
    return TIMESTAMP.sub("<TIME>", text).rstrip()


def _scrub(value, roots: list[Path]):
    if isinstance(value, dict):
        return {
            key: _scrub(item, roots)
            for key, item in sorted(value.items())
            if not (key == "installed_at" or (key == "path" and item is None))
        }
    if isinstance(value, list):
        return [_scrub(item, roots) for item in value]
    if isinstance(value, str):
        return normalise(value, roots)
    return value


def parse_json(text: str, roots: list[Path]):
    try:
        return _scrub(json.loads(text), roots)
    except json.JSONDecodeError as exc:  # pragma: no cover - surfaced as a diff
        pytest.fail(f"stdout is not JSON: {exc}\n{text}")


# --------------------------------------------------------------------------- runners


@dataclass
class Result:
    exit: int
    stdout: str
    stderr: str


@dataclass
class Scenario:
    """One installer session: fixture shape, the steps to run, and what to anchor on."""

    name: str
    steps: list[list[str]]
    anchors: list[str] = field(default_factory=list)
    shape: str = "game"
    json_steps: set[int] = field(default_factory=set)
    compare_prefix: bool = False
    # files that must exist under the run root afterwards, whatever the installer did
    require: list[str] = field(default_factory=list)

    def argv(self, step: list[str], paths: dict[str, Path]) -> list[str]:
        return [item.format(**{key: str(value) for key, value in paths.items()}) for item in step]


def _shape_roots(shape: str) -> dict[str, bool]:
    return {
        "game": {"package": True, "game": True},
        "native": {"package": True, "native": True},
        "empty": {"package": True},
        "discovery": {"package": True, "library": True},
        "discovery-empty": {"package": True, "home": True},
        "discovery-wine": {"package": True, "library_wine": True},
        "prefix": {"package": True, "game": True, "prefix": True},
        "prefix-wine": {"package": True, "game": True, "library_prefix_wine": True},
    }[shape]


def build_shape(root: Path, shape: str) -> dict[str, Path]:
    """Create the fixture tree a scenario needs and return the paths its argv uses."""
    wanted = _shape_roots(shape)
    paths: dict[str, Path] = {}
    if wanted.get("package"):
        paths["package"] = make_package(root)
    if wanted.get("game"):
        paths["game"] = make_game(root)
    if wanted.get("native"):
        paths["game"] = make_native_game(root)
    if wanted.get("prefix"):
        paths["prefix"] = make_prefix(root)
    if wanted.get("library"):
        paths["library"] = make_library(root)
        paths["game"] = paths["library"] / "steamapps" / "common" / "Megabonk"
        paths["home"] = root / "steamhome"
        (paths["home"] / ".local" / "share" / "Steam").mkdir(parents=True, exist_ok=True)
        shutil.copytree(root / "steam", paths["home"] / ".local" / "share" / "Steam", dirs_exist_ok=True)
        paths["library"] = paths["home"] / "library"
    if wanted.get("library_wine"):
        paths["library"] = make_library(root, wine=True)
        paths["game"] = paths["library"] / "steamapps" / "common" / "Megabonk"
        paths["home"] = root / "steamhome"
        (paths["home"] / ".local" / "share" / "Steam").mkdir(parents=True, exist_ok=True)
        shutil.copytree(root / "steam", paths["home"] / ".local" / "share" / "Steam", dirs_exist_ok=True)
        paths["library"] = paths["home"] / "library"
    if wanted.get("home"):
        paths["home"] = root / "home"
        (paths["home"] / "empty").mkdir(parents=True, exist_ok=True)
    if wanted.get("library_prefix_wine"):
        paths["game"] = make_game(root)
        paths["prefix"] = make_prefix(root, library=make_library(root, with_game=False, wine=True))
        paths["library"] = paths["prefix"].parents[2]
    (root / "bare").mkdir(parents=True, exist_ok=True)
    paths["bare"] = root / "bare"
    paths["level"] = make_level(root)
    paths["pack"] = make_pack(root)
    paths["root"] = root
    paths.setdefault("home", root / "home")
    paths.setdefault("game", root / "game" / "Megabonk")
    paths.setdefault("prefix", root / "missing" / "pfx")
    paths.setdefault("library", root / "library")
    stub_flatpak(paths["home"])
    return paths


def run(cmd: list[str], env: dict[str, str], cwd: Path) -> Result:
    completed = subprocess.run(  # noqa: S603
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    return Result(completed.returncode, completed.stdout, completed.stderr)


def python_command() -> list[str]:
    return [sys.executable, "-m", "player_installer"]


def environment(home: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SCRIPTS)
    env["HOME"] = str(home)
    env["MEGABONK_NON_INTERACTIVE"] = "1"
    env["MEGABONK_MOUNT_ROOTS"] = ""
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    env["COLUMNS"] = "200"
    return env


def run_scenario(root: Path, scenario: Scenario, cmd: list[str]):
    paths = build_shape(root, scenario.shape)
    env = environment(paths["home"])
    results = []
    for index, step in enumerate(scenario.steps):
        argv = scenario.argv(step, paths)
        results.append(run(cmd + argv, env, REPO))
    return results, paths


def _record(game: Path) -> str | None:
    path = game / RECORD_NAME
    return path.read_text(encoding="utf-8") if path.is_file() else None


def compare(scenario: Scenario, python_run, go_run, python_paths, go_paths) -> None:
    assert len(python_run) == len(go_run), "the runs took a different number of steps"
    for index, (expected, actual) in enumerate(zip(python_run, go_run)):
        assert actual.exit == expected.exit, (
            f"{scenario.name} step {index}: exit {actual.exit}, want {expected.exit}\n"
            f"go stdout:\n{actual.stdout}\ngo stderr:\n{actual.stderr}"
        )
        if index in scenario.json_steps:
            assert parse_json(actual.stdout, [go_paths["root"]]) == parse_json(
                expected.stdout, [python_paths["root"]]
            ), f"{scenario.name} step {index}: JSON payload differs"
            assert normalise(actual.stderr, [go_paths["root"]]) == normalise(
                expected.stderr, [python_paths["root"]]
            ), f"{scenario.name} step {index}: stderr differs\n{actual.stderr}\n{expected.stderr}"
            continue
        for label in ("stdout", "stderr"):
            got = normalise(getattr(actual, label), [go_paths["root"]])
            want = normalise(getattr(expected, label), [python_paths["root"]])
            assert got == want, (
                f"{scenario.name} step {index}: {label} differs\n--- go ---\n{actual.stdout}"
                f"\n--- go stderr ---\n{actual.stderr}\n--- python ---\n{expected.stdout}"
                f"\n--- python stderr ---\n{expected.stderr}"
            )

    assert snapshot(go_paths["game"], (RECORD_NAME,)) == snapshot(python_paths["game"], (RECORD_NAME,)), (
        f"{scenario.name}: the game trees differ"
    )
    if scenario.compare_prefix:
        assert snapshot(go_paths["prefix"]) == snapshot(python_paths["prefix"]), (
            f"{scenario.name}: the prefix trees differ"
        )

    python_record = _record(python_paths["game"])
    go_record = _record(go_paths["game"])
    assert (go_record is None) == (python_record is None), f"{scenario.name}: one run left no install record"
    if python_record is not None:
        assert parse_json(go_record, [go_paths["root"]]) == parse_json(python_record, [python_paths["root"]]), (
            f"{scenario.name}: the install record differs"
        )

    for relative in scenario.require:
        assert (go_paths["root"] / relative).is_file(), f"{scenario.name}: the Go run never wrote {relative}"
        assert (python_paths["root"] / relative).is_file(), f"{scenario.name}: the reference never wrote {relative}"

    combined = "\n".join(result.stdout + result.stderr for result in [*python_run, *go_run])
    for anchor in scenario.anchors:
        assert anchor in combined, f"{scenario.name}: {anchor!r} never appears in either run's output"


@pytest.mark.parametrize(
    "scenario",
    [
        Scenario(
            name="install-fresh",
            shape="game",
            steps=[["--package", "{package}", "--game-dir", "{game}", "--no-gui"]],
            anchors=[
                "installed MegabonkLevels 0.0.1 (MelonLoader 0.7.3) (7 step(s))",
                "1/7 MelonLoader 0.7.3 into",
                "Start Megabonk from Steam",
                "MelonLoader/Latest.log",
            ],
        ),
        Scenario(
            name="install-twice",
            shape="game",
            steps=[
                ["--package", "{package}", "--game-dir", "{game}", "--no-gui"],
                ["--package", "{package}", "--game-dir", "{game}", "--no-gui"],
            ],
            anchors=["nothing to do —", "already in place:", "already installed"],
        ),
        Scenario(
            name="install-prefix",
            shape="prefix",
            compare_prefix=True,
            steps=[
                [
                    "--package", "{package}", "--game-dir", "{game}", "--prefix", "{prefix}",
                    "--wine-override", "registry", "--no-gui",
                ]
            ],
            anchors=[
                "8 step(s)",
                "enable-dll-override:",
                ".NET 6.0.36 in prefix at",
                "version.dll override: native,builtin via registry",
            ],
        ),
        Scenario(
            name="install-prefix-by-wine",
            shape="prefix-wine",
            compare_prefix=True,
            steps=[
                [
                    "--package", "{package}", "--game-dir", "{game}", "--prefix", "{prefix}",
                    "--wine-override", "wine", "--no-gui",
                ]
            ],
            require=[WINE_LOG],
            anchors=["8 step(s)", "enable-dll-override:", "installed MegabonkLevels 0.0.1 (MelonLoader 0.7.3)"],
        ),
        Scenario(
            name="install-gamedir-mode",
            shape="game",
            steps=[["--package", "{package}", "--game-dir", "{game}", "--dotnet-in", "gamedir", "--no-gui"]],
            anchors=[
                "DOTNET_ROOT=Z:",
                "%command%",
                "Steam > Library > Megabonk > Properties",
                "Steam rewrites its own config while it runs",
                ".NET 6.0.36 in gamedir at",
            ],
        ),
        Scenario(
            name="unusable-prefix-warns",
            shape="game",
            steps=[["--package", "{package}", "--game-dir", "{game}", "--prefix", "{prefix}", "--no-gui"]],
            anchors=[
                "warning: no usable Proton prefix at",
                "so the .NET runtime goes beside the game",
                "pass --prefix <path to the pfx directory> to install into an existing Proton prefix",
            ],
        ),
        Scenario(
            name="install-level-and-pack",
            shape="game",
            steps=[
                [
                    "--package", "{package}", "--game-dir", "{game}", "--level", "{level}",
                    "--pack", "{pack}", "--no-gui",
                ]
            ],
            anchors=[
                "UserData/Levels/skate.mblevel.json",
                "thps/skater.bundle",
                "packs: thps",
            ],
        ),
        Scenario(
            name="check-drift",
            shape="game",
            steps=[["--package", "{package}", "--game-dir", "{game}", "--check", "--no-gui"]],
            anchors=[
                "thing(s) are out of date with package megabonk-levels-0.0.1-ml0.7.3-linux",
                "  - install-loader:",
                "  - install-runtime:",
                "  - create-levels-dir:",
            ],
        ),
        Scenario(
            name="check-clean",
            shape="game",
            steps=[
                ["--package", "{package}", "--game-dir", "{game}", "--no-gui"],
                ["--package", "{package}", "--game-dir", "{game}", "--check", "--no-gui"],
            ],
            anchors=["nothing to do — the install matches the package"],
        ),
        Scenario(
            name="dry-run",
            shape="game",
            steps=[["--package", "{package}", "--game-dir", "{game}", "--dry-run", "--no-gui"]],
            anchors=["would do 7 thing(s) to", "  - install-loader:", "  - install-runtime:"],
        ),
        Scenario(
            name="uninstall",
            shape="game",
            steps=[
                ["--package", "{package}", "--game-dir", "{game}", "--no-gui"],
                ["--game-dir", "{game}", "--uninstall", "--no-gui"],
            ],
            anchors=["removed ", "uninstalled"],
        ),
        Scenario(
            name="uninstall-twice",
            shape="game",
            steps=[
                ["--package", "{package}", "--game-dir", "{game}", "--no-gui"],
                ["--game-dir", "{game}", "--uninstall", "--no-gui"],
                ["--game-dir", "{game}", "--uninstall", "--no-gui"],
            ],
            anchors=["nothing to uninstall: no installer record in"],
        ),
        Scenario(
            name="repair-after-tampering",
            shape="game",
            steps=[
                ["--package", "{package}", "--game-dir", "{game}", "--no-gui"],
                ["--package", "{package}", "--game-dir", "{game}", "--no-gui"],
            ],
            anchors=["already in place:"],
        ),
        Scenario(
            name="json-install",
            shape="game",
            json_steps={0},
            steps=[["--package", "{package}", "--game-dir", "{game}", "--json"]],
            anchors=["megabonk-levels-0.0.1-ml0.7.3-linux"],
        ),
        Scenario(
            name="json-check",
            shape="game",
            json_steps={0},
            steps=[["--package", "{package}", "--game-dir", "{game}", "--check", "--json"]],
            anchors=['"ok": false', '"drift"', "install-loader"],
        ),
        Scenario(
            name="json-uninstall",
            shape="game",
            json_steps={0, 1},
            steps=[
                ["--package", "{package}", "--game-dir", "{game}", "--json"],
                ["--game-dir", "{game}", "--uninstall", "--json"],
            ],
            anchors=["removed"],
        ),
        Scenario(
            name="missing-package",
            shape="empty",
            steps=[["--game-dir", "{game}", "--no-gui"]],
            anchors=["no --package: point it at the unzipped MegabonkLevels download"],
        ),
        Scenario(
            name="package-without-manifest",
            shape="empty",
            steps=[["--package", "{bare}", "--game-dir", "{game}", "--no-gui"]],
            anchors=["has no manifest.json — pass the unzipped download folder, not the .zip"],
        ),
        Scenario(
            name="native-build-refused",
            shape="native",
            steps=[["--package", "{package}", "--game-dir", "{game}", "--no-gui"]],
            anchors=["Linux native build", "Install the Windows build instead"],
        ),
        Scenario(
            name="missing-game-dir",
            shape="game",
            steps=[["--package", "{package}", "--game-dir", "{root}/nope", "--no-gui"]],
            anchors=["does not look like a Megabonk install"],
        ),
        Scenario(
            name="invalid-level",
            shape="game",
            steps=[["--package", "{package}", "--game-dir", "{game}", "--level", "{root}/inputs/broken.mblevel.json"]],
            anchors=["the level or level-pack inputs are not valid"],
        ),
        Scenario(
            name="discovery-not-found",
            shape="discovery-empty",
            steps=[["--package", "{package}", "--home", "{home}", "--no-gui"]],
            anchors=[
                "Megabonk was not found in any Steam library.",
                "Steam clients considered:",
                "Libraries searched: none — pass --library <path> to add one",
                "--game-dir <path to the folder holding Megabonk.exe>",
            ],
        ),
    ],
    ids=lambda scenario: scenario.name,
)
def test_parity(scenario: Scenario, tmp_path: Path) -> None:
    python_root = tmp_path / "python"
    go_root = tmp_path / "go"
    python_root.mkdir()
    go_root.mkdir()
    _prepare(scenario, python_root)
    _prepare(scenario, go_root)

    python_results, python_paths = run_scenario(python_root, scenario, python_command())
    go_results, go_paths = run_scenario(go_root, scenario, [str(go_binary())])
    compare(scenario, python_results, go_results, python_paths, go_paths)


def _prepare(scenario: Scenario, root: Path) -> None:
    """Scenario fixtures that are not part of the shape itself."""
    build_shape(root, scenario.shape)
    if scenario.name == "invalid-level":
        broken = root / "inputs" / "broken.mblevel.json"
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_text('{"schema": "two"}\n', encoding="utf-8")
    if scenario.name == "package-without-manifest":
        return
    if scenario.name == "missing-package":
        return


def test_discovery_finds_the_game(tmp_path: Path) -> None:
    """The installer locates Megabonk through a libraryfolders.vdf and installs it."""
    scenario = Scenario(
        name="discovery-found",
        shape="discovery",
        steps=[["--package", "{package}", "--home", "{home}", "--no-gui"]],
        anchors=["installed MegabonkLevels 0.0.1", "Megabonk/Mods/MegabonkLevels.Mod.dll"],
    )
    python_root, go_root = tmp_path / "python", tmp_path / "go"
    python_root.mkdir()
    go_root.mkdir()
    python_results, python_paths = run_scenario(python_root, scenario, python_command())
    go_results, go_paths = run_scenario(go_root, scenario, [str(go_binary())])
    compare(scenario, python_results, go_results, python_paths, go_paths)


def test_wine_override_without_a_wine_binary(tmp_path: Path) -> None:
    """--wine-override wine refuses to fall back to editing user.reg by hand."""
    scenario = Scenario(
        name="wine-override-no-binary",
        shape="prefix",
        steps=[
            [
                "--package", "{package}", "--game-dir", "{game}", "--prefix", "{prefix}",
                "--wine-override", "wine", "--no-gui",
            ]
        ],
        anchors=["no wine binary found in the Proton tools under"],
    )
    python_root, go_root = tmp_path / "python", tmp_path / "go"
    python_root.mkdir()
    go_root.mkdir()
    for root in (python_root, go_root):
        paths = build_shape(root, scenario.shape)
        # A compatdata layout with no Proton tools next to it.
        (paths["prefix"] / "drive_c").mkdir(parents=True, exist_ok=True)
    python_results, python_paths = run_scenario(python_root, scenario, python_command())
    go_results, go_paths = run_scenario(go_root, scenario, [str(go_binary())])
    compare(scenario, python_results, go_results, python_paths, go_paths)


def test_progress_lines_are_numbered(tmp_path: Path) -> None:
    """Both installers count steps the same way, in the same order."""
    scenario = Scenario(
        name="progress",
        shape="game",
        steps=[["--package", "{package}", "--game-dir", "{game}", "--no-gui"]],
    )
    python_root, go_root = tmp_path / "python", tmp_path / "go"
    python_root.mkdir()
    go_root.mkdir()
    python_results, python_paths = run_scenario(python_root, scenario, python_command())
    go_results, go_paths = run_scenario(go_root, scenario, [str(go_binary())])
    python_lines = [
        line for line in python_results[0].stdout.splitlines() if re.match(r"^\d+/\d+ ", line)
    ]
    go_lines = [line for line in go_results[0].stdout.splitlines() if re.match(r"^\d+/\d+ ", line)]
    assert normalise("\n".join(go_lines), [go_paths["root"]]) == normalise(
        "\n".join(python_lines), [python_paths["root"]]
    )
    assert python_lines, "the reference printed no numbered progress"
