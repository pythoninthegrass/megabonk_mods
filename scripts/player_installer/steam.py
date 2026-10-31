"""Finding Steam and the Megabonk install on a Linux machine.

Covers the layouts the installer has to cope with: a native Steam client, a Flatpak
client whose data lives under ~/.var, libraries on internal disks and on removable
media, and the Proton prefix Steam keeps per library.
"""

from __future__ import annotations

import os
import subprocess
from . import vdf
from dataclasses import dataclass
from pathlib import Path

APP_ID = "3405340"
GAME_NAME = "Megabonk"
GAME_EXE = "Megabonk.exe"
NATIVE_EXE = "Megabonk.x86_64"
DATA_DIR = "Megabonk_Data"
STEAM_ROOT_NAMES = ("Steam", "steam")
FLATPAK_ID = "com.valvesoftware.Steam"
CLIENT_MARKERS = ("steamapps",)
SCAN_DEPTH = 2


@dataclass(frozen=True)
class SteamClient:
    kind: str
    root: Path


@dataclass(frozen=True)
class LibraryRoot:
    path: Path
    source: str
    client: SteamClient | None = None
    granted: bool | None = None


def _is_steam_root(candidate: Path) -> bool:
    return candidate.is_dir() and all((candidate / marker).exists() for marker in CLIENT_MARKERS)


def client_roots(home: Path | str, xdg_data_home: Path | str | None = None) -> list[SteamClient]:
    """Steam clients for a user: the native install first, then a Flatpak one."""
    home = Path(home).expanduser()
    data_homes: list[Path] = []
    if xdg_data_home:
        data_homes.append(Path(xdg_data_home).expanduser())
    configured = os.environ.get("XDG_DATA_HOME")
    if configured:
        configured_path = Path(configured).expanduser()
        data_homes.append(configured_path if configured_path.is_absolute() else home / configured_path)
    data_homes.append(home / ".local" / "share")
    candidates: list[tuple[str, Path]] = [(kind, path) for kind, path in (
        ("native", data_home / "Steam") for data_home in data_homes
    )]
    candidates += [
        ("native", home / ".steam" / "root"),
        ("native", home / ".steam" / "steam"),
        ("flatpak", home / ".var" / "app" / FLATPAK_ID / ".local" / "share" / "Steam"),
        ("flatpak", home / ".var" / "app" / FLATPAK_ID / "data" / "Steam"),
    ]
    clients: list[SteamClient] = []
    seen: set[Path] = set()
    for kind, candidate in candidates:
        if not _is_steam_root(candidate):
            continue
        key = _identity(candidate)
        if key in seen:
            continue
        seen.add(key)
        clients.append(SteamClient(kind, candidate))
    return clients


def flatpak_override_paths(text: str, home: Path | str | None = None) -> list[Path]:
    """Absolute paths a Flatpak Steam is allowed to read, from `flatpak override --show` output."""
    home = Path(home).expanduser() if home else Path.home()
    in_context = False
    paths: list[Path] = []
    seen: set[Path] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            in_context = line == "[Context]"
            continue
        if not in_context or not line.startswith("filesystems="):
            continue
        for entry in line.split("=", 1)[1].split(";"):
            entry = entry.strip()
            if not entry or entry.startswith("!"):
                continue
            path = _expand_flatpak_path(entry, home)
            if path is None or path in seen:
                continue
            seen.add(path)
            paths.append(path)
    return paths


def _expand_flatpak_path(entry: str, home: Path) -> Path | None:
    if entry in {"host", "host-os", "host-etc", "home", "os", "etc"} or entry.startswith(("host-", "xdg-", "home/")):
        return None
    if entry == "~":
        return home
    if entry.startswith("~/"):
        return home / entry[2:]
    path = Path(entry)
    return path if path.is_absolute() else home / path


def _flatpak_override_file(home: Path) -> Path | None:
    path = home / ".var" / "app" / FLATPAK_ID / "configuration" / "flatpak" / "local-overrides" / FLATPAK_ID
    return path if path.is_file() else None


def flatpak_granted_paths(home: Path | str) -> list[Path]:
    """Paths Flatpak Steam may read, from the persisted override file or the flatpak CLI."""
    home = Path(home).expanduser()
    stored = _flatpak_override_file(home)
    if stored is not None:
        try:
            return flatpak_override_paths(stored.read_text(encoding="utf-8", errors="replace"), home=home)
        except OSError:
            pass
    for binary in ("flatpak", "/usr/bin/flatpak", "/var/lib/flatpak/exports/bin/flatpak"):
        try:
            proc = subprocess.run(
                [binary, "override", "--show", FLATPAK_ID],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode == 0 and proc.stdout:
            return flatpak_override_paths(proc.stdout, home=home)
    return []


def libraryfolders(client: SteamClient) -> list[Path]:
    path = client.root / "steamapps" / "libraryfolders.vdf"
    if not path.is_file():
        return []
    try:
        data = vdf.load_vdf(path)
    except vdf.VdfError:
        return []
    return [Path(value) for value in vdf.library_folder_paths(data)]


def library_roots(
    clients: list[SteamClient],
    *,
    overrides: list[Path] | None = None,
    extra_paths: list[Path] | None = None,
    mount_roots: list[Path] | None = None,
    include_missing: bool = False,
) -> list[LibraryRoot]:
    """Libraries to search, in priority order: the client's own list, Flatpak grants, explicit paths, then a media scan."""
    found: list[LibraryRoot] = []
    seen: set[Path] = set()

    def add(path: Path, source: str, client: SteamClient | None = None, granted: bool | None = None) -> None:
        path = Path(path)
        if not include_missing and not _plausible(path):
            return
        key = _identity(path)
        if key in seen:
            return
        seen.add(key)
        found.append(LibraryRoot(path, source, client, granted))

    for client in clients:
        for path in libraryfolders(client):
            add(path, "client", client)

    granted_paths = list(overrides or [])
    granted = {granted_path for granted_path in granted_paths}
    for path in granted_paths:
        add(path, "flatpak-override", granted=True if path in granted else None)

    for path in extra_paths or []:
        add(Path(path), "explicit", granted=None)

    for mount in mount_roots or []:
        for path in scan_for_libraries(mount):
            add(path, "scan")
    return found


def scan_for_libraries(mount_root: Path | str, depth: int = SCAN_DEPTH) -> list[Path]:
    """Directories under a mount point that look like a Steam library (they hold steamapps/common)."""
    mount_root = Path(mount_root)
    if not mount_root.is_dir():
        return []
    found: list[Path] = []
    frontier = [mount_root]
    for _ in range(depth):
        nxt: list[Path] = []
        for directory in frontier:
            try:
                children = sorted(child for child in directory.iterdir() if child.is_dir())
            except OSError:
                continue
            for child in children:
                if child.name.startswith("."):
                    continue
                if (child / "steamapps" / "common").is_dir():
                    found.append(child)
                else:
                    nxt.append(child)
        frontier = nxt
    return found


def _looks_like_game(directory: Path) -> bool:
    return directory.is_dir() and (
        (directory / GAME_EXE).is_file()
        or (directory / NATIVE_EXE).is_file()
        or (directory / "GameAssembly.dll").is_file()
        or (directory / DATA_DIR).is_dir()
    )


def find_game_dir(roots: list[LibraryRoot], game_name: str = GAME_NAME) -> Path | None:
    """The first library holding a Megabonk install, using Steam's own appmanifest when it has one."""
    for root in roots:
        common = root.path / "steamapps" / "common"
        install_dir = _install_dir_from_manifests(root.path, game_name)
        if install_dir is not None and _looks_like_game(install_dir):
            return install_dir
        if _looks_like_game(common / game_name):
            return common / game_name
        if common.is_dir():
            for candidate in sorted(common.iterdir()):
                if candidate.is_dir() and _looks_like_game(candidate):
                    return candidate
    return None


def _install_dir_from_manifests(library: Path, game_name: str) -> Path | None:
    steamapps = library / "steamapps"
    if not steamapps.is_dir():
        return None
    for manifest in sorted(steamapps.glob(f"appmanifest_{APP_ID}.acf")):
        try:
            data = vdf.load_vdf(manifest)
        except vdf.VdfError:
            continue
        install = vdf.find(data, ("appid", "installdir")) or vdf.find(data, (str(APP_ID), "installdir"))
        if install:
            return steamapps / "common" / str(install)
    return None


def prefix_root(library: Path | str, app_id: str = APP_ID) -> Path:
    return Path(library) / "steamapps" / "compatdata" / app_id / "pfx"


def prefix_for_game_dir(game_dir: Path | str, app_id: str = APP_ID) -> Path | None:
    """The compatdata prefix that belongs to an install, when the library layout is Steam's."""
    game_dir = Path(game_dir)
    for parent in game_dir.parents:
        if parent.name == "common":
            library = parent.parent.parent
            candidate = prefix_root(library, app_id)
            if candidate.is_dir():
                return candidate
            return None
    return None


def compatdata_root(game_dir: Path | str, app_id: str = APP_ID) -> Path | None:
    prefix = prefix_for_game_dir(game_dir, app_id)
    return prefix.parent if prefix else None


def localconfig(client: SteamClient) -> dict | None:
    path = client.root / "config" / "localconfig.vdf"
    if not path.is_file():
        return None
    try:
        return vdf.load_vdf(path)
    except vdf.VdfError:
        return None


STEAM_PROCESS_MARKERS = ("/Steam/ubuntu12_32/steam", "/steamapps/common/SteamLinuxRuntime", "com.valvesoftware.Steam", "steamwebhelper")


def steam_running() -> bool:
    """Whether a Steam client is running, which is when it rewrites localconfig.vdf."""
    try:
        proc = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return any(marker in line for line in proc.stdout.splitlines() for marker in STEAM_PROCESS_MARKERS)


def _plausible(path: Path) -> bool:
    """A library is worth searching when it exists, or its parent does: a parent that is gone too means the drive is not attached."""
    return path.is_dir() or path.parent.is_dir()


def _identity(path: Path) -> str:
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    try:
        stat = resolved.stat()
        return f"{stat.st_dev}:{stat.st_ino}"
    except OSError:
        return str(resolved)
